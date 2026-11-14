import json
from pathlib import Path
import sqlite3
from threading import RLock
from datetime import timedelta

from app.models.domain import Evidence, Incident, LifecycleEvent, MetricSample, ScenarioSnapshot


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS runtime_state (
    state_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL,
    trigger TEXT NOT NULL,
    impact TEXT NOT NULL,
    summary TEXT NOT NULL,
    affected_services_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    service_id TEXT NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    threshold REAL NOT NULL,
    operator TEXT NOT NULL,
    breach_severity TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    service_id TEXT NOT NULL,
    source TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL REFERENCES incidents(id),
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incidents_created ON incidents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_incident_time ON metrics(incident_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_evidence_incident_time ON evidence(incident_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_events_incident_time ON events(incident_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_kind_time ON artifacts(kind, created_at DESC);
"""


def sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only local SQLite database URLs are supported")
    path = Path(database_url[len(prefix):])
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


class SQLiteDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = RLock()

    def initialize(self) -> None:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(SCHEMA)
            connection.execute(
                """DELETE FROM metrics WHERE id NOT IN (
                    SELECT MIN(id) FROM metrics
                    GROUP BY incident_id, service_id, name, observed_at
                )"""
            )
            connection.execute(
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_metrics_unique_sample
                ON metrics(incident_id, service_id, name, observed_at)"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def save_snapshot(self, snapshot: ScenarioSnapshot) -> None:
        if snapshot.incident is None:
            raise ValueError("Cannot persist a simulator snapshot without a detected incident")
        incident = snapshot.incident
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO incidents (
                    id, scenario_id, title, severity, status, trigger, impact, summary,
                    affected_services_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status, updated_at=excluded.updated_at""",
                (
                    incident.id,
                    incident.scenario_id,
                    incident.title,
                    incident.severity,
                    incident.status,
                    incident.trigger,
                    incident.impact,
                    incident.summary,
                    json.dumps(incident.affected_services),
                    incident.created_at.isoformat(),
                    incident.updated_at.isoformat(),
                ),
            )
            connection.executemany(
                """INSERT OR IGNORE INTO metrics (
                    incident_id, service_id, name, value, unit, threshold,
                    operator, breach_severity, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        incident.id,
                        metric.service_id,
                        metric.name,
                        metric.value,
                        metric.unit,
                        metric.threshold,
                        metric.operator,
                        metric.breach_severity,
                        metric.observed_at.isoformat(),
                    )
                    for metric in snapshot.metrics
                ],
            )
            connection.executemany(
                """INSERT OR IGNORE INTO evidence (
                    id, incident_id, service_id, source, level, message, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        item.id,
                        incident.id,
                        item.service_id,
                        item.source,
                        item.level,
                        item.message,
                        item.observed_at.isoformat(),
                    )
                    for item in snapshot.evidence
                ],
            )
            connection.executemany(
                """INSERT OR IGNORE INTO events (
                    id, incident_id, event_type, occurred_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)""",
                [
                    (
                        f"{incident.id}:scenario-injected",
                        incident.id,
                        "scenario.injected",
                        incident.created_at.isoformat(),
                        json.dumps({"scenario_id": snapshot.scenario_id}),
                    ),
                    (
                        f"{incident.id}:incident-detected",
                        incident.id,
                        "incident.detected",
                        (incident.created_at + timedelta(microseconds=1)).isoformat(),
                        json.dumps({"severity": incident.severity, "trigger": incident.trigger}),
                    ),
                ],
            )
            connection.execute(
                """INSERT INTO runtime_state (state_key, payload_json) VALUES ('active', ?)
                ON CONFLICT(state_key) DO UPDATE SET payload_json=excluded.payload_json""",
                (snapshot.model_dump_json(),),
            )

    def load_snapshot(self) -> ScenarioSnapshot | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM runtime_state WHERE state_key='active'"
            ).fetchone()
        if row is None:
            return None
        return ScenarioSnapshot.model_validate_json(row["payload_json"])

    @staticmethod
    def _incident_from_row(row: sqlite3.Row) -> Incident:
        return Incident(
            id=row["id"],
            scenario_id=row["scenario_id"],
            title=row["title"],
            severity=row["severity"],
            status=row["status"],
            trigger=row["trigger"],
            impact=row["impact"],
            summary=row["summary"],
            affected_services=json.loads(row["affected_services_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        return self._incident_from_row(row) if row else None

    def list_incidents(self, limit: int = 100) -> list[Incident]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._incident_from_row(row) for row in rows]

    def list_metrics(self, service_id: str | None = None, incident_id: str | None = None, limit: int = 500) -> list[MetricSample]:
        query = """SELECT service_id, name, value, unit, threshold, operator,
            breach_severity, observed_at FROM metrics"""
        values: list[object] = []
        filters: list[str] = []
        if service_id:
            filters.append("service_id=?")
            values.append(service_id)
        if incident_id:
            filters.append("incident_id=?")
            values.append(incident_id)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY id DESC LIMIT ?"
        values.append(limit)
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [MetricSample(**dict(row)) for row in rows]

    def list_evidence(self, service_id: str | None = None, query_text: str = "", incident_id: str | None = None, limit: int = 500) -> list[Evidence]:
        query = """SELECT id, incident_id, service_id, source, level, message, observed_at
            FROM evidence WHERE 1=1"""
        values: list[object] = []
        if service_id:
            query += " AND service_id=?"
            values.append(service_id)
        if incident_id:
            query += " AND incident_id=?"
            values.append(incident_id)
        if query_text:
            query += " AND lower(message) LIKE ?"
            values.append(f"%{query_text.lower()}%")
        query += " ORDER BY observed_at DESC LIMIT ?"
        values.append(limit)
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [Evidence(**dict(row)) for row in rows]

    def list_events(self, incident_id: str | None = None, limit: int = 500) -> list[LifecycleEvent]:
        query = """SELECT id, incident_id, event_type, occurred_at, payload_json FROM events"""
        values: list[object] = []
        if incident_id:
            query += " WHERE incident_id=?"
            values.append(incident_id)
        query += " ORDER BY occurred_at DESC LIMIT ?"
        values.append(limit)
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [
            LifecycleEvent(
                id=row["id"],
                incident_id=row["incident_id"],
                event_type=row["event_type"],
                occurred_at=row["occurred_at"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        ]

    def save_artifact(self, kind: str, artifact_id: str, incident_id: str, created_at: str, payload: dict) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT INTO artifacts (id, incident_id, kind, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET
                kind=excluded.kind, created_at=excluded.created_at, payload_json=excluded.payload_json""",
                (artifact_id, incident_id, kind, created_at, json.dumps(payload)),
            )

    def get_artifact(self, kind: str, artifact_id: str) -> dict | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM artifacts WHERE kind=? AND id=?", (kind, artifact_id)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list_artifacts(self, kind: str, incident_id: str | None = None, limit: int = 100) -> list[dict]:
        query = "SELECT payload_json FROM artifacts WHERE kind=?"
        values: list[object] = [kind]
        if incident_id:
            query += " AND incident_id=?"
            values.append(incident_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        values.append(limit)
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def record_event(self, event: LifecycleEvent) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO events (id, incident_id, event_type, occurred_at, payload_json)
                VALUES (?, ?, ?, ?, ?)""",
                (event.id, event.incident_id, event.event_type, event.occurred_at.isoformat(), json.dumps(event.payload)),
            )

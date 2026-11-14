from pathlib import Path

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import Settings
from app.database.sqlite import SQLiteDatabase, sqlite_path_from_url
from app.integrations.ollama import OllamaClient
from app.monitoring.detector import IncidentDetector
from app.simulator.engine import Simulator


def create_app(database_path: str | Path | None = None) -> FastAPI:
    settings = Settings.from_env()
    resolved_path = Path(database_path) if database_path is not None else sqlite_path_from_url(settings.database_url)
    database = SQLiteDatabase(resolved_path)
    database.initialize()

    simulator = Simulator()
    detector = IncidentDetector()
    snapshot = database.load_snapshot()
    if snapshot is None:
        snapshot = simulator.inject("checkout-double-fault")
        incident = detector.detect(snapshot)
        if incident is None:
            raise RuntimeError("Default checkout fixture did not trigger an incident")
        snapshot = simulator.attach_incident(snapshot, incident)
        database.save_snapshot(snapshot)

    app = FastAPI(
        title="Nightwatch AI API",
        description="Local-only API for the Nightwatch AI incident-response simulator.",
        version="0.2.0",
    )
    app.state.settings = settings
    app.state.database = database
    app.state.ollama = OllamaClient(settings)
    app.state.simulator = simulator
    app.state.detector = detector
    app.state.snapshot = snapshot
    app.include_router(router, prefix="/api")
    return app


app = create_app()

const state = { current: null, scenarios: [], selectedService: "", allServices: [], actions: [], diagnoses: [], logTimer: null, toastTimer: null };
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const serviceLabel = (id) => state.allServices.find((service) => service.id === id)?.name || id;
const WORKSPACE_PASSWORD = "prathith";
const shopState = { category: "All finds", search: "", cart: 0, toastTimer: null };
const products = [
  { id: "headphones", name: "Cloud nine wireless headphones", category: "Tech & audio", group: "Tech", price: 64, rating: "4.9", reviews: "128", badge: "BESTSELLER", emoji: "🎧", color: "#d8d1ff" },
  { id: "mug", name: "Sunday slow-morning mug", category: "Home & living", group: "Home", price: 18, rating: "4.8", reviews: "86", badge: "LITTLE FAVORITE", emoji: "☕", color: "#ffd6c9" },
  { id: "keyboard", name: "Click-clack compact keyboard", category: "Desk essentials", group: "Desk", price: 49, rating: "4.7", reviews: "94", badge: "DESK UPGRADE", emoji: "⌨️", color: "#d2eee3" },
  { id: "lamp", name: "Golden hour mini desk lamp", category: "Desk essentials", group: "Desk", price: 36, rating: "4.9", reviews: "63", badge: "GOOD GLOW", emoji: "💡", color: "#ffe7a9" },
  { id: "speaker", name: "Pocket-sized happy speaker", category: "Tech & audio", group: "Tech", price: 42, rating: "4.6", reviews: "57", badge: "ON THE GO", emoji: "🔊", color: "#cfe4ff" },
  { id: "plant", name: "Little leafy desk companion", category: "Home & living", group: "Home", price: 22, rating: "4.8", reviews: "72", badge: "FRESH PICK", emoji: "🪴", color: "#d5edbd" },
  { id: "notebook", name: "Big ideas, little notebook set", category: "Desk essentials", group: "Desk", price: 16, rating: "4.9", reviews: "114", badge: "COLOR POP", emoji: "📒", color: "#ffd2df" },
  { id: "camera", name: "Instant joy pocket camera", category: "Tech & audio", group: "Tech", price: 79, rating: "4.7", reviews: "41", badge: "WEEKEND READY", emoji: "📸", color: "#d8d5fa" },
];

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json();
  if (!response.ok && response.status !== 409) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("visible"), 2800);
}

function formatElapsed(minutes) {
  return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes}m`;
}

function renderStats() {
  const services = state.current.services;
  const critical = services.filter((service) => service.status === "critical").length;
  const degraded = services.filter((service) => service.status === "degraded").length;
  const resolved = state.current.resolved;
  const cards = [
    ["AFFECTED SERVICES", `${critical + degraded} / 12`, `${critical} critical · ${degraded} degraded`, critical ? "negative" : "positive"],
    ["CUSTOMER IMPACT", resolved ? "Mitigated" : state.current.incident.severity === "SEV-1" ? "High" : "Moderate", resolved ? "Signals recovering" : state.current.incident.impact.split(";")[0], resolved ? "positive" : "negative"],
    ["REMEDIATIONS", `${state.current.fixed_actions.length} / ${state.actions.filter((action) => !action.unsafe).length}`, "Safe actions applied", state.current.fixed_actions.length ? "positive" : ""],
    ["INCIDENT AGE", formatElapsed(state.current.elapsed_minutes), "Since first alert", ""],
  ];
  $("#statsRow").innerHTML = cards.map(([label, value, note, tone]) => `<article class="stat-card"><div class="stat-label">${esc(label)}</div><div class="stat-line"><strong class="stat-value">${esc(value)}</strong><span class="stat-note ${tone}">${esc(note)}</span></div></article>`).join("");
}

function renderHeader() {
  const incident = state.current.incident;
  $("#incidentTitle").textContent = incident.title;
  $("#incidentImpact").textContent = incident.impact;
  $("#severityPill").textContent = incident.severity;
  $("#triggerName").textContent = incident.trigger;
  $("#alertStatus").lastChild.textContent = state.current.resolved ? " MITIGATED" : " OPEN";
  $("#alertStatus").style.color = state.current.resolved ? "var(--green)" : "";
  $("#elapsed").textContent = formatElapsed(state.current.elapsed_minutes);
  $("#incident-id").textContent = `INC-${2408 + state.scenarios.findIndex((scenario) => scenario.id === state.current.scenario_id)}`;
  $("#alertBanner").classList.toggle("resolved", state.current.resolved);
  if (state.current.resolved) {
    $("#alertBanner").style.borderColor = "#31563e";
    $("#alertBanner").style.background = "linear-gradient(100deg,rgba(43,94,58,.23),rgba(28,48,38,.2))";
    $("#severityPill").textContent = "MITIGATED";
    $("#severityPill").style.color = "var(--green)";
    $("#severityPill").style.borderColor = "#31563e";
    $("#severityPill").style.background = "#244a3028";
  } else {
    $("#alertBanner").style.borderColor = "";
    $("#alertBanner").style.background = "";
    $("#severityPill").style.color = "";
    $("#severityPill").style.borderColor = "";
    $("#severityPill").style.background = "";
  }
  $("#elapsed").textContent = formatElapsed(state.current.elapsed_minutes);
}

function renderServices() {
  const groups = [...new Set(state.allServices.map((service) => service.group))];
  $("#serviceMap").innerHTML = groups.map((group) => {
    const services = state.current.services.filter((service) => service.group === group);
    return `<section class="service-group"><div class="group-title"><span>${esc(group)}</span><span class="group-count">${services.length} NODES</span></div><div class="service-items">${services.map((service) => `<button class="service-node ${state.selectedService === service.id ? "selected" : ""}" data-service="${esc(service.id)}" title="${esc(service.name)} depends on: ${esc(service.depends_on.join(", ") || "no upstream dependencies")}"><span class="service-name">${esc(service.name)}</span><span class="node-status"><i class="dot ${esc(service.status)}"></i>${esc(service.status)}</span></button>`).join("")}</div></section>`;
  }).join("");
  $("#serviceMap").querySelectorAll("[data-service]").forEach((button) => button.addEventListener("click", () => {
    const serviceId = button.dataset.service;
    state.selectedService = state.selectedService === serviceId ? "" : serviceId;
    $("#logServiceFilter").value = state.selectedService;
    $("#metricSelect").value = state.selectedService && state.current.services.some((service) => service.id === state.selectedService) ? state.selectedService : "";
    renderServices();
    refreshLogs();
    refreshMetrics();
  }));
}

function renderSelects() {
  const serviceOptions = state.allServices.map((service) => `<option value="${esc(service.id)}">${esc(service.name)}</option>`).join("");
  $("#logServiceFilter").innerHTML = `<option value="">All services</option>${serviceOptions}`;
  $("#metricSelect").innerHTML = `<option value="">Auto · incident signals</option>${serviceOptions}`;
  $("#scenarioSelect").innerHTML = state.scenarios.map((scenario) => `<option value="${esc(scenario.id)}">${esc(scenario.severity)} · ${esc(scenario.title)}</option>`).join("");
  $("#scenarioSelect").value = state.current.scenario_id;
}

function relativeTime(timestamp) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

async function refreshLogs() {
  const params = new URLSearchParams();
  const service = $("#logServiceFilter").value;
  const query = $("#logSearch").value.trim();
  if (service) params.set("service", service);
  if (query) params.set("q", query);
  const logs = await api(`/api/logs?${params}`);
  $("#logCount").textContent = logs.length;
  $("#logList").innerHTML = logs.length ? logs.map((log) => `<article class="log-entry"><time class="log-time" title="${esc(new Date(log.time).toLocaleString())}">${esc(relativeTime(log.time))}</time><div><div class="log-meta"><span class="log-service">${esc(log.service)}</span><span class="log-level ${esc(log.level)}">${esc(log.level)}</span></div><div class="log-message">${esc(log.message)}</div></div></article>`).join("") : `<div class="empty-state">No logs match these filters.</div>`;
}

function renderChart(series, labels) {
  const width = 620, height = 118, left = 34, right = 12, top = 10, bottom = 22;
  const values = series.values;
  const min = Math.min(...values), max = Math.max(...values);
  const spread = max - min || Math.max(1, max * .15);
  const low = Math.max(0, min - spread * .16), high = max + spread * .16;
  const x = (index) => left + index * (width - left - right) / (values.length - 1);
  const y = (value) => top + (high - value) * (height - top - bottom) / (high - low || 1);
  const points = values.map((value, index) => `${x(index)},${y(value)}`);
  const line = points.join(" ");
  const area = `${left},${height - bottom} ${line} ${x(values.length - 1)},${height - bottom}`;
  const yTicks = [0, 1, 2].map((index) => top + index * (height - top - bottom) / 2);
  const labelsSvg = labels.map((label, index) => `<text class="chart-label" text-anchor="middle" x="${x(index)}" y="${height - 5}">${esc(label)}</text>`).join("");
  const circles = values.map((value, index) => `<circle class="chart-point" cx="${x(index)}" cy="${y(value)}" r="2.3"/>`).join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(series.service)} metric over the last 40 minutes"><defs><linearGradient id="chartFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#6edbd0" stop-opacity=".2"/><stop offset="100%" stop-color="#6edbd0" stop-opacity="0"/></linearGradient></defs>${yTicks.map((tick) => `<line class="chart-grid" x1="${left}" x2="${width - right}" y1="${tick}" y2="${tick}"/>`).join("")}<polygon class="chart-area" points="${area}"/><polyline class="chart-line" points="${line}"/>${circles}${labelsSvg}</svg>`;
}

function prettyMetric(value, unit) {
  if (unit.includes("%")) return `${Math.round(value)}%`;
  if (unit.includes("ms")) return value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${Math.round(value)}ms`;
  return Number(value).toLocaleString();
}

async function refreshMetrics() {
  const serviceId = $("#metricSelect").value;
  const data = await api(`/api/metrics${serviceId ? `?service=${encodeURIComponent(serviceId)}` : ""}`);
  const series = data.series;
  if (!series.length) {
    $("#metricCards").innerHTML = `<div class="empty-state">No metrics available for this service in the active incident.</div>`;
    $("#metricChart").innerHTML = "";
    return;
  }
  const labels = series.length > 3 ? series.slice(0, 3).map((item) => item.service) : series.map((item) => item.service);
  $("#metricCards").innerHTML = series.map((item) => {
    const start = item.values[0], current = item.values[item.values.length - 1];
    const unit = item.unit;
    const changed = Math.round(((current - start) / Math.max(1, start)) * 100);
    const direction = unit.includes("%") || unit.includes("success") ? changed > 0 : changed < 0;
    const recovered = state.current.fixed_actions.some((actionId) => state.actions.find((action) => action.id === actionId)?.service === item.service);
    return `<article class="metric-card"><div class="metric-name">${esc(serviceLabel(item.service))}</div><div class="metric-value">${esc(prettyMetric(current, unit))} <small>${esc(unit)}</small></div><div class="metric-delta ${recovered ? "recovered" : direction ? "recovered" : ""}">${changed > 0 ? "+" : ""}${changed}% from start</div></article>`;
  }).join("");
  const selected = series.find((item) => item.service === serviceId) || series[0];
  $("#chartUnit").textContent = `${serviceLabel(selected.service).toUpperCase()} · ${selected.unit.toUpperCase()}`;
  $("#metricChart").innerHTML = renderChart(selected, data.labels);
}

function renderActions() {
  $("#actionList").innerHTML = state.actions.map((action) => {
    const done = state.current.fixed_actions.includes(action.id);
    const blocked = action.unsafe;
    const primary = !blocked;
    return `<button type="button" class="action-card ${blocked ? "unsafe" : ""}" data-action="${esc(action.id)}" ${done || state.current.closed ? "disabled" : ""}><span class="action-icon">${blocked ? "⚠" : done ? "✓" : "↗"}</span><span class="action-copy"><strong>${esc(action.label)}</strong><span>${esc(action.description)}</span></span>${done ? `<span class="action-state">APPLIED</span>` : blocked ? `<span class="action-arrow">⛨</span>` : `<span class="action-arrow">→</span>`}</button>`;
  }).join("");
  $("#actionList").querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => runAction(button.dataset.action)));
}

function renderDiagnoses() {
  $("#diagnosisList").innerHTML = state.diagnoses.map((cause) => `<label class="diagnosis-option"><input type="checkbox" value="${esc(cause.id)}" /><span>${esc(cause.description)}</span></label>`).join("");
}

function renderSubmission(result) {
  const box = $("#scoreResult");
  box.hidden = false;
  box.classList.toggle("failed", !result.resolved);
  const truth = result.ground_truth.map((cause) => cause.description).join("; ");
  const feedback = [result.missing_causes.length ? `Missing cause(s): ${result.missing_causes.map((id) => CAUSE_NAME(id)).join(", ")}.` : "All causes identified.", result.fixes_complete ? "All required remediations applied." : "One or more required remediations are still outstanding.", result.summary_valid ? "Summary meets the minimum length." : "Add a summary of at least 40 characters."].join(" ");
  box.innerHTML = `<div class="score-head"><span>${result.resolved ? "EXERCISE COMPLETE" : "REVIEW SUBMITTED"}</span><strong>${result.score}<small style="font:10px var(--mono);color:#82918d"> / 100</small></strong></div><p>${esc(result.message)} ${esc(feedback)}</p><div class="score-breakdown"><span>Diagnosis ${result.diagnosis_score}</span><span>Remediation ${result.remediation_score}</span><span>Postmortem ${result.postmortem_score}</span></div><div class="ground-truth"><strong>Ground truth:</strong> ${esc(truth)}</div>`;
  $("#submitButton").textContent = "Submitted";
  $("#submitButton").disabled = true;
}

function CAUSE_NAME(id) {
  return state.diagnoses.find((cause) => cause.id === id)?.description || id;
}

async function runAction(actionId) {
  const feedback = $("#actionFeedback");
  try {
    const result = await api("/api/actions", { method: "POST", body: JSON.stringify({ action: actionId }) });
    feedback.hidden = false;
    feedback.className = `action-feedback ${result.ok ? "good" : "bad"}`;
    feedback.textContent = result.message;
    await refreshState(false);
  } catch (error) {
    feedback.hidden = false;
    feedback.className = "action-feedback bad";
    feedback.textContent = error.message;
  }
}

async function submitPostmortem() {
  const summary = $("#postmortemSummary").value.trim();
  const causeIds = [...document.querySelectorAll("#diagnosisList input:checked")].map((input) => input.value);
  try {
    const result = await api("/api/postmortem", { method: "POST", body: JSON.stringify({ summary, cause_ids: causeIds }) });
    renderSubmission(result);
    await refreshState(false);
    showToast(result.resolved ? "Incident resolved. Ground truth revealed." : "Review submitted. Ground truth revealed.");
  } catch (error) {
    showToast(error.message);
  }
}

async function refreshState(reloadActions = true) {
  state.current = await api("/api/state");
  if (reloadActions) state.actions = await api("/api/actions");
  renderHeader();
  renderStats();
  renderServices();
  renderActions();
  await Promise.all([refreshLogs(), refreshMetrics()]);
  if (state.current.closed) {
    $("#submitButton").disabled = true;
    $("#submitButton").textContent = "Exercise complete";
  }
}

async function resetScenario(scenarioId = state.current?.scenario_id || "checkout-double-fault") {
  await api("/api/reset", { method: "POST", body: JSON.stringify({ scenario_id: scenarioId }) });
  $("#scoreResult").hidden = true;
  $("#scoreResult").innerHTML = "";
  $("#postmortemSummary").value = "";
  $("#charCount").textContent = "0 / 40 min characters";
  $("#submitButton").disabled = false;
  $("#submitButton").innerHTML = 'Submit review <span>→</span>';
  $("#actionFeedback").hidden = true;
  $("#diagnosisList").querySelectorAll("input").forEach((input) => { input.checked = false; });
  state.selectedService = "";
  await refreshState();
  showToast("Scenario reset. Initial evidence restored.");
}

function bindEvents() {
  $("#scenarioSelect").addEventListener("change", (event) => resetScenario(event.target.value));
  $("#resetButton").addEventListener("click", () => resetScenario());
  $("#logSearch").addEventListener("input", () => {
    clearTimeout(state.logTimer);
    state.logTimer = setTimeout(() => refreshLogs().catch((error) => showToast(error.message)), 130);
  });
  $("#logServiceFilter").addEventListener("change", () => refreshLogs().catch((error) => showToast(error.message)));
  $("#metricSelect").addEventListener("change", () => refreshMetrics().catch((error) => showToast(error.message)));
  $("#clearFilters").addEventListener("click", () => {
    $("#logSearch").value = "";
    $("#logServiceFilter").value = "";
    $("#metricSelect").value = "";
    state.selectedService = "";
    renderServices();
    refreshLogs();
    refreshMetrics();
  });
  $("#postmortemSummary").addEventListener("input", (event) => {
    const length = event.target.value.trim().length;
    $("#charCount").textContent = `${length} / 40 min characters`;
    $("#charCount").style.color = length >= 40 ? "var(--green)" : "";
  });
  $("#submitButton").addEventListener("click", submitPostmortem);
}

function renderCategories() {
  const categories = ["All finds", "Home & living", "Tech & audio", "Desk essentials"];
  $("#categoryBar").innerHTML = categories.map((category) => `<button class="category-pill ${shopState.category === category ? "active" : ""}" data-category="${esc(category)}">${esc(category)}</button>`).join("");
  $("#categoryBar").querySelectorAll("[data-category]").forEach((button) => button.addEventListener("click", () => {
    shopState.category = button.dataset.category;
    renderCategories();
    renderProducts();
    $("#collection").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
}

function renderProducts() {
  const search = shopState.search.trim().toLowerCase();
  const visible = products.filter((product) => {
    const categoryMatches = shopState.category === "All finds" || product.category === shopState.category;
    const searchMatches = !search || `${product.name} ${product.category} ${product.badge}`.toLowerCase().includes(search);
    return categoryMatches && searchMatches;
  });
  $("#productGrid").innerHTML = visible.map((product) => `<article class="product-card"><div class="product-art" style="background:${product.color}"><span class="product-badge">${esc(product.badge)}</span><button class="favorite-button" type="button" aria-label="Favorite ${esc(product.name)}" aria-pressed="false">♡</button><span class="product-emoji" aria-hidden="true">${product.emoji}</span></div><div class="product-info"><div class="product-category">${esc(product.category)}</div><h3 class="product-name">${esc(product.name)}</h3><div class="product-rating"><span aria-label="${product.rating} out of 5 stars">★★★★★</span><small>${product.rating} (${product.reviews})</small></div><div class="product-buy"><strong class="product-price">$${product.price.toFixed(2)}</strong><button class="add-cart" type="button" data-add="${esc(product.id)}">Add to cart</button></div></div></article>`).join("");
  $("#shopEmpty").hidden = visible.length > 0;
  $("#productGrid").hidden = visible.length === 0;
  $("#shopResultCount").textContent = search ? `${visible.length} find${visible.length === 1 ? "" : "s"} for “${shopState.search.trim()}”.` : shopState.category === "All finds" ? "A fresh little lineup of everyday favorites." : `A few of our favorite ${shopState.category.toLowerCase()} finds.`;
  $("#productGrid").querySelectorAll("[data-add]").forEach((button) => button.addEventListener("click", () => {
    const product = products.find((item) => item.id === button.dataset.add);
    shopState.cart += 1;
    $("#cartCount").textContent = shopState.cart;
    button.textContent = "Added ✓";
    button.classList.add("added");
    button.disabled = true;
    showShopToast(`${product.name} added to your cart.`);
    setTimeout(() => { if (button.isConnected) { button.textContent = "Add to cart"; button.classList.remove("added"); button.disabled = false; } }, 1100);
  }));
  $("#productGrid").querySelectorAll(".favorite-button").forEach((button) => button.addEventListener("click", () => {
    const active = button.classList.toggle("active");
    button.setAttribute("aria-pressed", String(active));
    button.textContent = active ? "♥" : "♡";
    showShopToast(active ? "Saved to your favorites." : "Removed from your favorites.");
  }));
}

function showShopToast(message) {
  const toast = $("#shopToast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(shopState.toastTimer);
  shopState.toastTimer = setTimeout(() => toast.classList.remove("visible"), 2500);
}

function openWorkspaceModal() {
  $("#workspaceModal").hidden = false;
  $("#loginError").hidden = true;
  $("#workspacePassword").value = "";
  $("#workspacePassword").type = "password";
  $("#togglePassword").textContent = "Show";
  requestAnimationFrame(() => $("#workspacePassword").focus());
}

function closeWorkspaceModal() {
  $("#workspaceModal").hidden = true;
  $("#loginError").hidden = true;
}

function enterWorkspace(event) {
  event.preventDefault();
  if ($("#workspacePassword").value !== WORKSPACE_PASSWORD) {
    $("#loginError").hidden = false;
    $("#workspacePassword").setAttribute("aria-invalid", "true");
    $("#workspacePassword").focus();
    return;
  }
  $("#workspacePassword").removeAttribute("aria-invalid");
  closeWorkspaceModal();
  $("#storefront").hidden = true;
  $("#dashboard").hidden = false;
  window.scrollTo({ top: 0, behavior: "instant" });
  $("#resetButton").focus();
}

function leaveWorkspace() {
  $("#dashboard").hidden = true;
  $("#storefront").hidden = false;
  window.scrollTo({ top: 0, behavior: "instant" });
}

function bindShopEvents() {
  renderCategories();
  renderProducts();
  $("#shopSignIn").addEventListener("click", openWorkspaceModal);
  $("#footerWorkspace").addEventListener("click", openWorkspaceModal);
  $("#workspaceLogin").addEventListener("submit", enterWorkspace);
  $("#workspacePassword").addEventListener("input", () => {
    $("#loginError").hidden = true;
    $("#workspacePassword").removeAttribute("aria-invalid");
  });
  $("#togglePassword").addEventListener("click", () => {
    const input = $("#workspacePassword");
    const visible = input.type === "password";
    input.type = visible ? "text" : "password";
    $("#togglePassword").textContent = visible ? "Hide" : "Show";
    $("#togglePassword").setAttribute("aria-label", visible ? "Hide password" : "Show password");
    input.focus();
  });
  document.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", closeWorkspaceModal));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#workspaceModal").hidden) closeWorkspaceModal();
  });
  $("#backToShop").addEventListener("click", leaveWorkspace);
  $("#shopSearch").addEventListener("input", (event) => {
    shopState.search = event.target.value;
    renderProducts();
  });
  $("#shopSearchButton").addEventListener("click", () => {
    shopState.search = $("#shopSearch").value;
    renderProducts();
    $("#collection").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("#shopNow").addEventListener("click", () => $("#collection").scrollIntoView({ behavior: "smooth", block: "start" }));
  $("#viewAll").addEventListener("click", () => {
    shopState.category = "All finds";
    shopState.search = "";
    $("#shopSearch").value = "";
    renderCategories();
    renderProducts();
  });
  $("#cartButton").addEventListener("click", () => showShopToast(shopState.cart ? `Your cart has ${shopState.cart} happy little find${shopState.cart === 1 ? "" : "s"}.` : "Your cart is waiting for a happy little find."));
  $("#newsletterForm").addEventListener("submit", (event) => {
    event.preventDefault();
    showShopToast("You’re on the list. Watch this space for good things!");
    event.currentTarget.reset();
  });
}

async function init() {
  bindShopEvents();
  try {
    const [health, scenarios, services, diagnoses, actions, current] = await Promise.all([api("/api/health"), api("/api/scenarios"), api("/api/services"), api("/api/diagnoses"), api("/api/actions"), api("/api/state")]);
    if (!health.ok || health.services !== 12) throw new Error("Simulator health check failed.");
    state.scenarios = scenarios;
    state.allServices = services;
    state.diagnoses = diagnoses;
    state.actions = actions;
    state.current = current;
    renderSelects();
    renderDiagnoses();
    bindEvents();
    await refreshState(false);
  } catch (error) {
    document.body.innerHTML = `<main style="padding:48px;color:#e7edf5;font-family:system-ui"><h1>Could not connect to On-call Lab</h1><p style="margin-top:12px;color:#9aa8b7">${esc(error.message)} Start the local server with <code>python server.py</code>, then reload this page.</p></main>`;
  }
}

init();
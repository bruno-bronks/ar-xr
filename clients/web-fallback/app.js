"use strict";

// Painel 2D (SPEC-007). Todo texto vindo da API entra via textContent (nunca innerHTML).
const POLL_MS = 2000;

const STATUS = {
  NORMAL: { icon: "✓", label: "Normal", note: "" },
  WARNING: { icon: "!", label: "Atenção", note: "Algum sensor passou do limite de atenção." },
  CRITICAL: { icon: "✕", label: "Crítico", note: "Algum sensor passou do limite crítico." },
  OFFLINE: { icon: "⏻", label: "Offline", note: "Sem dados recentes deste equipamento." },
  UNKNOWN: { icon: "?", label: "Desconhecido", note: "Dados insuficientes para afirmar que está normal." },
};
const SEVERITY = { CRITICAL: "Crítico", WARNING: "Atenção", OFFLINE: "Offline" };

const els = {
  org: document.getElementById("org"),
  cards: document.getElementById("cards"),
  alerts: document.getElementById("alerts"),
  noAlerts: document.getElementById("no-alerts"),
  count: document.getElementById("alert-count"),
  error: document.getElementById("error-banner"),
  freshness: document.getElementById("freshness"),
};

let lastOk = null;
let generation = 0; // incrementa a cada troca de organizacao: respostas antigas sao descartadas
let inFlightGeneration = null;

function el(tag, attrs, text) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, value);
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

async function api(path, token) {
  const response = await fetch(path, {
    headers: { Authorization: "Bearer " + token },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(response.status === 401 ? "não autenticado (401)" : "erro HTTP " + response.status);
  }
  return response.json();
}

function ageSeconds(twin, observedAt) {
  if (!observedAt) return null;
  return Math.max(0, Math.round((Date.parse(twin.evaluated_at) - Date.parse(observedAt)) / 1000));
}

function formatValue(value) {
  return value === null || value === undefined ? "—" : value.toFixed(1);
}

function renderCard(equipment, twin) {
  const meta = STATUS[twin.status] || STATUS.UNKNOWN;
  const card = el("article", {
    class: "card",
    "data-testid": "card-" + equipment.id,
    "data-status": twin.status,
    "data-stale": "false",
  });
  card.appendChild(el("h3", {}, equipment.name));
  card.appendChild(el("p", { class: "meta" }, equipment.id + " · " + equipment.type + " · " + equipment.location));

  const badge = el("span", { class: "badge", "data-testid": "status-" + equipment.id, "data-status": twin.status });
  badge.appendChild(el("span", { "aria-hidden": "true" }, meta.icon));
  badge.appendChild(el("span", {}, meta.label));
  card.appendChild(badge);
  if (meta.note) card.appendChild(el("p", { class: "status-note" }, meta.note));

  const table = el("table");
  const head = el("tr");
  for (const title of ["Sensor", "Valor", "Limites (atenção / crítico)", "Idade"]) head.appendChild(el("th", { scope: "col" }, title));
  table.appendChild(head);
  for (const sensor of twin.sensors) {
    const row = el("tr", { "data-valid": String(sensor.valid), "data-sensor": sensor.sensor_type });
    row.appendChild(el("td", {}, sensor.sensor_type));
    const value = sensor.value === null ? "sem dados" : formatValue(sensor.value) + " " + sensor.unit;
    row.appendChild(el("td", { class: "num" }, sensor.quality === "BAD" ? value + " (defeito)" : value));
    row.appendChild(el("td", { class: "num" }, formatValue(sensor.warn) + " / " + formatValue(sensor.crit)));
    const age = ageSeconds(twin, sensor.observed_at);
    row.appendChild(el("td", { class: "num" }, age === null ? "—" : age + " s"));
    table.appendChild(row);
  }
  card.appendChild(table);
  return card;
}

function renderAlerts(items) {
  els.alerts.replaceChildren();
  for (const { equipment, alert } of items) {
    const li = el("li", { "data-testid": "alert", "data-severity": alert.severity });
    const detail =
      alert.sensor_type && alert.value !== undefined
        ? alert.sensor_type + " = " + formatValue(alert.value) + " (limite " + formatValue(alert.limit) + ")"
        : "sem dados recentes";
    li.textContent = SEVERITY[alert.severity] + " · " + equipment.name + " (" + equipment.id + ") · " + detail;
    els.alerts.appendChild(li);
  }
  els.count.textContent = String(items.length);
  els.noAlerts.hidden = items.length > 0;
}

function markStale(isStale) {
  for (const card of els.cards.children) card.setAttribute("data-stale", String(isStale));
  els.freshness.setAttribute("data-stale", String(isStale));
}

async function refresh() {
  const mine = generation;
  const token = els.org.value; // fixado no inicio: uma troca de org nao contamina requisicoes em voo
  if (inFlightGeneration === mine) return;
  inFlightGeneration = mine;
  try {
    const equipmentList = await api("/api/v1/equipment", token);
    const details = await Promise.all(
      equipmentList.map(async (equipment) => {
        const base = "/api/v1/equipment/" + encodeURIComponent(equipment.id);
        const [twin, alerts] = await Promise.all([api(base + "/twin", token), api(base + "/alerts", token)]);
        return { equipment, twin, alerts };
      }),
    );
    if (mine !== generation) return; // a organizacao mudou enquanto esperavamos: descarta
    els.cards.replaceChildren(...details.map((d) => renderCard(d.equipment, d.twin)));
    renderAlerts(details.flatMap((d) => d.alerts.map((alert) => ({ equipment: d.equipment, alert }))));
    els.error.hidden = true;
    lastOk = Date.now();
    markStale(false);
  } catch (error) {
    if (mine !== generation) return;
    // mantem o ultimo estado visivel (da MESMA organizacao), mas marcado como desatualizado
    els.error.textContent = "Falha ao atualizar: " + error.message + ". Os dados exibidos podem estar desatualizados.";
    els.error.hidden = false;
    markStale(true);
  } finally {
    if (inFlightGeneration === mine) inFlightGeneration = null;
    updateFreshness();
  }
}

function updateFreshness() {
  if (lastOk === null) {
    els.freshness.textContent = "Sem dados carregados";
    return;
  }
  const seconds = Math.round((Date.now() - lastOk) / 1000);
  els.freshness.textContent = "Atualizado há " + seconds + " s";
}

els.org.addEventListener("change", () => {
  generation += 1;
  inFlightGeneration = null;
  els.cards.replaceChildren();
  renderAlerts([]);
  els.error.hidden = true;
  lastOk = null;
  refresh();
});

refresh();
setInterval(refresh, POLL_MS);
setInterval(updateFreshness, 1000);

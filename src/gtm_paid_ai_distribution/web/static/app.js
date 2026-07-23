"use strict";

// --- tiny API helper -------------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

const CHANNELS = ["google", "linkedin", "meta", "tiktok", "microsoft", "x", "reddit"];
const STATUS_BADGE = {
  draft: "", running: "brand", winner: "good", paused: "warn", archived: "bad",
  live: "good",
};

// Extract the FastAPI `detail` message from an api() error (msg is "STATUS: BODY").
function detailOf(err) {
  const body = String(err.message || "").split(": ").slice(1).join(": ");
  try {
    return JSON.parse(body).detail || body || err.message;
  } catch {
    return body || err.message;
  }
}

const view = () => document.getElementById("view");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pct = (n) => (n * 100).toFixed(1) + "%";
const money = (n) => "$" + Number(n).toLocaleString();
const list = (items) => `<ul>${(items || []).map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`;
const badge = (status) =>
  `<span class="badge ${STATUS_BADGE[status] || ""}">${esc(status)}</span>`;

function setBreadcrumb(parts) {
  document.getElementById("breadcrumb").innerHTML = parts
    .map((p, i) => (i === parts.length - 1 ? `<b>${esc(p)}</b>` : esc(p)))
    .join(" › ");
}

// A plausible per-experiment performance sample so the rules engine has data.
function sampleSnapshot(seed) {
  const imp = 6000 + seed * 1500;
  const clicks = Math.round(imp * (0.02 + seed * 0.004));
  const conversions = Math.round(clicks * (0.03 + (seed % 3) * 0.02));
  const spend = Math.round(clicks * (4 + seed));
  const revenue = Math.round(conversions * (180 + seed * 30));
  return { impressions: imp, clicks, conversions, spend, revenue };
}

// --- views -----------------------------------------------------------------
const stat = (label, val) => `<div class="stat"><span>${label}</span><b>${val}</b></div>`;

function metricsGrid(m) {
  return `<div class="stats">
    ${stat("Impressions", m.impressions.toLocaleString())}
    ${stat("CTR", pct(m.ctr))}
    ${stat("CPC", money(m.cpc))}
    ${stat("Conversions", m.conversions)}
    ${stat("CPA / CPL", money(m.cpa))}
    ${stat("Conv. rate", pct(m.conversion_rate))}
    ${stat("ROAS", m.roas + "x")}
    ${stat("Spend", money(m.spend))}
  </div>`;
}

async function renderCampaigns() {
  setBreadcrumb(["Campaigns"]);
  const campaigns = await api("/campaigns");
  if (!campaigns.length) {
    view().innerHTML = `<p class="eyebrow">Overview</p><h1>Campaigns</h1>
      <div class="empty"><span class="empty-mark">◆</span>
      No campaigns yet — describe a product and let the AI draft the rest.<br/><br/>
      <a href="#/new"><button>✨ Create your first campaign</button></a></div>`;
    return;
  }
  view().innerHTML = `
    <p class="eyebrow">Overview</p>
    <div class="row"><h1>Campaigns</h1><div class="spacer"></div>
      <a href="#/new"><button>✨ New campaign</button></a></div>
    <p class="lede muted">Every campaign runs A/B experiments across channels — the AI finds the winning combination.</p>
    <div class="cards">
      ${campaigns.map((c) => `
        <a href="#/campaigns/${c.id}"><div class="card clickable">
          <div class="row">${badge(c.status)}<div class="spacer"></div>
            <span class="muted">${c.experiments.length} experiment(s)</span></div>
          <h3>${esc(c.product_description)}</h3>
          <p class="muted">${esc(c.goal)} · ${money(c.monthly_budget)}/mo · ${esc(c.geography || "—")}</p>
        </div></a>`).join("")}
    </div>`;
}

async function renderCampaign(id) {
  const c = await api(`/campaigns/${id}`);
  const analysis = await api(`/campaigns/${id}/analysis`);
  setBreadcrumb(["Campaigns", c.product_description.slice(0, 40)]);
  const a = c.audience || {};
  const metricByExp = Object.fromEntries(
    analysis.experiments.map((e) => [e.experiment_id, e])
  );

  view().innerHTML = `
    <p class="eyebrow">Campaign</p>
    <div class="row"><h1>${esc(c.product_description)}</h1><div class="spacer"></div>${badge(c.status)}</div>
    <p class="muted">${esc(c.goal)} · ${money(c.monthly_budget)}/mo · ${esc(c.geography || "—")}</p>

    <div class="card">
      <h3>🎯 Audience <span class="muted">(campaign-level)</span></h3>
      <p>${esc(a.icp)} — ${esc(a.company_size)}</p>
      <p class="muted">Industries: ${esc((a.industries || []).join(", "))}<br/>
        Titles: ${esc((a.job_titles || []).join(", "))}</p>
    </div>

    <div class="row"><h2>🧪 Experiments (A/B)</h2><div class="spacer"></div>
      <button class="ghost sm" id="add-exp">+ Add experiment</button>
      <button class="sm" id="seed-metrics">Import sample metrics</button></div>
    <div class="cards" id="exp-cards">
      ${c.experiments.map((e) => {
        const m = metricByExp[e.id]?.metrics;
        return `<a href="#/experiments/${e.id}"><div class="card clickable">
          <div class="row"><b>${esc(e.name)}</b><div class="spacer"></div>${badge(e.status)}</div>
          <p class="muted">📣 ${esc(e.channel)}</p>
          <p>“${esc(e.message.headline)}”</p>
          ${m && m.impressions ? `<p class="muted">CPA ${money(m.cpa)} · CTR ${pct(m.ctr)}</p>` : `<p class="muted">No data yet</p>`}
        </div></a>`;
      }).join("")}
    </div>

    <h2>📈 Dashboard totals</h2>
    ${metricsGrid(analysis.totals)}

    <h2>💡 Insights</h2>
    ${analysis.insights.map((i) => `<div class="insight ${i.severity}"><b>${esc(i.title)}</b> — ${esc(i.detail)}</div>`).join("")}

    <h2>🛠️ Optimization suggestions</h2>
    ${analysis.suggestions.length
      ? analysis.suggestions.map((s) => `<div class="suggestion">${badge(s.action)}<span><b>${esc(s.target)}</b> — ${esc(s.rationale)}</span></div>`).join("")
      : `<p class="muted">Import performance data to generate suggestions.</p>`}
  `;

  document.getElementById("add-exp").onclick = async () => {
    await api(`/campaigns/${id}/experiments`, {
      method: "POST",
      body: JSON.stringify({ channel: "linkedin", generate: true }),
    });
    renderCampaign(id);
  };
  document.getElementById("seed-metrics").onclick = async () => {
    await Promise.all(
      c.experiments.map((e, i) =>
        api(`/experiments/${e.id}/metrics`, {
          method: "POST",
          body: JSON.stringify({ snapshots: [sampleSnapshot(i + 1)] }),
        })
      )
    );
    renderCampaign(id);
  };
}

async function renderExperiment(id) {
  const e = await api(`/experiments/${id}`);
  const m = await api(`/experiments/${id}/analysis`);
  setBreadcrumb(["Campaigns", "Experiment", e.name]);

  view().innerHTML = `
    <p class="eyebrow">Experiment · ${esc(e.channel)}</p>
    <div class="row"><h1>${esc(e.name)}</h1><div class="spacer"></div>${badge(e.status)}</div>

    <div class="card">
      <div class="row">
        <div><label>Channel</label>
          <select id="channel">${CHANNELS.map((ch) =>
            `<option value="${ch}" ${ch === e.channel ? "selected" : ""}>${ch}</option>`).join("")}</select></div>
        <div><label>Status</label>
          <select id="status">${["draft","running","paused","winner","archived"].map((s) =>
            `<option value="${s}" ${s === e.status ? "selected" : ""}>${s}</option>`).join("")}</select></div>
        <div style="align-self:end"><button class="sm" id="save-exp">Save</button></div>
      </div>
    </div>

    <div class="card">
      <h3>✍️ Marketing message</h3>
      <p><b>${esc(e.message.headline)}</b></p>
      <p>${esc(e.message.description)}</p>
      <p class="badge brand">CTA: ${esc(e.message.cta)}</p>
    </div>

    <div class="card">
      <div class="row"><h3>📄 Landing page</h3><div class="spacer"></div>
        <a href="/experiments/${id}/landing" target="_blank" rel="noopener">
          <button class="ghost sm">Open full page ↗</button></a></div>
      <p class="muted">Live preview of the real, responsive page a visitor sees:</p>
      <div class="preview"><iframe src="/experiments/${id}/landing" title="Landing page preview"></iframe></div>
    </div>

    <div class="row"><h2>📈 Performance</h2><div class="spacer"></div>
      <button class="ghost sm" id="import-google">Import from Google Ads</button>
      <button class="sm" id="add-metrics">Import sample data</button></div>
    <p id="google-msg" class="muted" style="margin:.2rem 0 .6rem"></p>
    ${m.impressions ? metricsGrid(m) : `<p class="muted">No performance data yet.</p>`}
  `;

  document.getElementById("import-google").onclick = async () => {
    const msg = document.getElementById("google-msg");
    msg.textContent = "Importing from Google Ads…";
    try {
      const r = await api(`/integrations/google/import`, {
        method: "POST",
        body: JSON.stringify({ experiment_id: id, days: 7 }),
      });
      msg.textContent = `✅ Imported ${r.snapshots_imported} snapshot(s) from Google Ads.`;
      renderExperiment(id);
    } catch (err) {
      msg.innerHTML = `⚠️ ${esc(detailOf(err))} — connect it on <a href="#/integrations">Integrations</a>.`;
    }
  };

  document.getElementById("save-exp").onclick = async () => {
    await api(`/experiments/${id}`, {
      method: "PATCH",
      body: JSON.stringify({
        channel: document.getElementById("channel").value,
        status: document.getElementById("status").value,
      }),
    });
    renderExperiment(id);
  };
  document.getElementById("add-metrics").onclick = async () => {
    await api(`/experiments/${id}/metrics`, {
      method: "POST",
      body: JSON.stringify({ snapshots: [sampleSnapshot(2)] }),
    });
    renderExperiment(id);
  };
}

// New-campaign wizard driven by the data-driven questionnaire.
async function renderNew() {
  setBreadcrumb(["New campaign"]);
  view().innerHTML = `<p class="eyebrow">Create</p><h1>New campaign</h1>
    <p class="lede muted">Answer a few questions; the AI drafts the audience and your first A/B experiments.</p>
    <div class="card" id="wiz"><button id="start">Start</button></div>`;
  let sessionId = null;

  const renderQ = (q) => {
    if (!q) return;
    let input;
    if (q.type === "single_choice")
      input = `<select id="ans">${q.options.map((o) => `<option>${o}</option>`).join("")}</select>`;
    else if (q.type === "number") input = `<input id="ans" type="number" />`;
    else input = `<textarea id="ans" rows="2"></textarea>`;
    document.getElementById("wiz").innerHTML = `
      <label>${esc(q.prompt)}</label>
      ${q.help_text ? `<p class="muted">${esc(q.help_text)}</p>` : ""}
      ${input}<br/><br/><button id="next">Submit</button>`;
    document.getElementById("next").onclick = submit;
  };
  const submit = async () => {
    const data = await api("/questionnaire/answer", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, answer: document.getElementById("ans").value }),
    });
    if (data.complete) location.hash = `#/campaigns/${data.campaign.id}`;
    else renderQ(data.question);
  };
  document.getElementById("start").onclick = async () => {
    const data = await api("/questionnaire/start", { method: "POST" });
    sessionId = data.session_id;
    renderQ(data.question);
  };
}

async function renderIntegrations() {
  setBreadcrumb(["Integrations"]);
  const [platforms, g] = await Promise.all([
    api("/integrations"),
    api("/integrations/google/status"),
  ]);
  const others = platforms.filter((p) => p.key !== "google");

  const gConnected = g.connected;
  const gBadge = gConnected
    ? `<span class="badge good">connected</span>`
    : `<span class="badge ${g.library_installed ? "warn" : "bad"}">not connected</span>`;
  const connectBtn = g.oauth_ready
    ? `<a href="/integrations/google/oauth/start"><button class="sm">${gConnected ? "Reconnect" : "Connect Google Ads"}</button></a>`
    : `<button class="ghost sm" disabled title="Set GTM_GOOGLE_CLIENT_ID / SECRET">Connect Google Ads</button>`;

  view().innerHTML = `<p class="eyebrow">Connections</p><h1>Integrations</h1>
    <p class="lede muted">Google Ads is a live integration — connect it to import real performance data. The other platforms are stubs (publishing is on the roadmap).</p>

    <div class="card">
      <div class="row">
        <span class="badge brand">Live</span>
        <b>Google Ads</b>
        <div class="spacer"></div>
        ${gBadge}
      </div>
      <p class="muted" style="margin:.6rem 0">${esc(g.detail)}</p>
      <div class="row">
        ${connectBtn}
        <button class="ghost sm" id="g-publish">Test publish (dry-run)</button>
        <span class="badge ${g.publish_enabled ? "good" : ""}">${g.publish_enabled ? "publishing ENABLED" : "publish: dry-run only"}</span>
      </div>
      <p id="g-msg" class="muted" style="margin:.6rem 0 0"></p>
      ${g.oauth_ready ? "" : `<p class="muted" style="margin:.6rem 0 0">To enable: <code>uv sync --extra google</code>, set the <code>GTM_GOOGLE_*</code> env vars, then reload.</p>`}
    </div>

    <h2>Other platforms</h2>
    <div class="cards">
      ${others.map((p) => `<div class="card">
        <div class="row"><b>${esc(p.display_name)}</b><div class="spacer"></div>
        <span class="badge">stub</span></div>
        <p class="muted">Publishing adapter — coming soon.</p></div>`).join("")}
    </div>`;

  document.getElementById("g-publish").onclick = async () => {
    const msg = document.getElementById("g-msg");
    msg.textContent = "Requesting…";
    try {
      const r = await api("/integrations/google/publish", {
        method: "POST",
        body: JSON.stringify({ name: "AdLift test campaign", objective: "leads", daily_budget: 50 }),
      });
      msg.textContent = `${r.status === "dry_run" ? "🧪" : "✅"} ${r.detail}`;
    } catch (err) {
      msg.textContent = `⚠️ ${detailOf(err)}`;
    }
  };
}

function renderAbout() {
  setBreadcrumb(["About"]);
  view().innerHTML = `<p class="eyebrow">About</p><h1>AdLift</h1>
    <div class="card">
      <p><b>AdLift — the AI Campaign Optimizer for B2B SaaS.</b></p>
      <p class="muted">Campaign → Experiments (A/B) → each experiment has a channel,
      one marketing message, and a landing page. The AI drafts everything, you import
      performance data, and the rules engine surfaces the winning combination and
      optimization suggestions. AI runs in stub mode — no key required.</p>
    </div>`;
}

// --- router ----------------------------------------------------------------
async function route() {
  const hash = location.hash || "#/campaigns";
  const parts = hash.slice(2).split("/"); // strip "#/"
  const [section, id] = parts;

  document.querySelectorAll(".sidebar nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.match === (section || "campaigns")));
  document.getElementById("sidebar").classList.remove("open");

  try {
    if (section === "campaigns" && id) await renderCampaign(id);
    else if (section === "experiments" && id) await renderExperiment(id);
    else if (section === "new") await renderNew();
    else if (section === "integrations") await renderIntegrations();
    else if (section === "about") renderAbout();
    else await renderCampaigns();
  } catch (err) {
    view().innerHTML = `<div class="empty">⚠️ ${esc(err.message)}</div>`;
  }
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);
document.getElementById("menu-btn").onclick = () =>
  document.getElementById("sidebar").classList.toggle("open");

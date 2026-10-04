/* Maria's dashboard: knowledge graph, actions, pulse, trials and search ledger for the focus disease. */
const TYPES = {
  disease: { label: "Diseases", color: "#6ea8fe" },
  gene: { label: "Genes", color: "#f6c453" },
  variant: { label: "Variants", color: "#f5a05c" },
  mechanism: { label: "Mechanisms", color: "#c59bf5" },
  symptom: { label: "Symptoms", color: "#7ddc9a" },
  group: { label: "Patient groups", color: "#e58fc8" },
  paper: { label: "Papers", color: "#9fb8d8" },
  study: { label: "Treatment studies", color: "#f08a8a" },
  asset: { label: "Research assets", color: "#5fd4d6" },
};
const LEVELS = {
  observed: { label: "Observed", hint: "a database record, registry entry or published statement", color: "#6ea8fe", dash: "" },
  inferred: { label: "Inferred", hint: "computed by ConstellAI from observed data", color: "#f6c453", dash: "7 5" },
  hypothesis: { label: "Hypothesis", hint: "proposed by the team's curation, not confirmed by a source we query", color: "#c59bf5", dash: "2 5" },
  nodata: { label: "No data", hint: "we searched and found nothing", color: "#7b869e", dash: "1 6" },
};
const D = { kg: null, trials: null, pulse: null, selected: null, hidden: new Set(), profile: { age: "", country: "" } };
try { Object.assign(D.profile, JSON.parse(localStorage.getItem("profile") || "{}")); } catch (e) { /* private mode */ }

const short = (s, n) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);
const shortDisease = (s) => short(s.replace(/Developmental and epileptic encephalopathy,?/i, "DEE").replace(/Neurodevelopmental disorder/i, "NDD")
  .replace(/Generalized epilepsy with febrile seizures plus/i, "GEFS+"), 30);
const state = (s) => s.replace(/_/g, " ").toLowerCase();
const levelBadge = (l) => `<span class="badge lvl-${l}">${LEVELS[l].label}</span>`;

/* ------------------------------------------------------------------ knowledge graph */
const W = 1280, ROW = 30, COL = { left: 250, midLeft: 500, center: 640, midRight: 790, right: 1030 };

function layout(kg) {
  const by = (t) => kg.nodes.filter((n) => n.type === t && !n.focus);
  const pos = new Map(), heads = [];
  const column = (x, side, groups) => {
    let y = 34;
    for (const [type, list] of groups) {
      if (!list.length) continue;
      heads.push({ x, y, side, type });
      y += ROW;
      for (const n of list) { pos.set(n.id, { x, y, side }); y += ROW; }
      y += 12;
    }
    return y;
  };
  const focus = kg.nodes.find((n) => n.focus);
  const genes = by("gene").filter((g) => g.id !== `g:${kg.gene}`);
  const diseaseOf = new Map(kg.edges.filter((e) => e.relation === "causes").map((e) => [e.source, e.target]));
  genes.sort((a, b) => (diseaseOf.has(b.id) ? 1 : 0) - (diseaseOf.has(a.id) ? 1 : 0));
  const h1 = column(COL.left, "left", [["paper", by("paper")], ["group", by("group")]]);
  const h2 = column(COL.midLeft, "left", [["variant", by("variant")], ["mechanism", by("mechanism")], ["asset", by("asset")]]);
  const h4 = column(COL.midRight, "right", [["gene", genes], ["symptom", by("symptom")]]);
  for (const g of genes) {
    const d = diseaseOf.get(g.id);
    if (d && pos.has(g.id)) pos.set(d, { x: COL.right, y: pos.get(g.id).y, side: "right" });
  }
  heads.push({ x: COL.right, y: 34, side: "right", type: "disease" });
  const H = Math.max(h1, h2, h4, 640) + 10, cy = Math.round(H * 0.34);
  pos.set(`g:${kg.gene}`, { x: COL.center, y: cy - 120, side: "center" });
  pos.set(focus.id, { x: COL.center, y: cy, side: "center" });
  const studies = by("study");
  heads.push({ x: COL.center, y: cy + 130, side: "center", type: "study" });
  studies.forEach((n, i) => pos.set(n.id, { x: COL.center, y: cy + 168 + i * 62, side: "center" }));
  return { pos, heads, H };
}

function edgePath(a, b) {
  if (a.x === b.x) {
    const bend = a.side === "right" ? 46 : -46, k = Math.min(90, Math.abs(b.y - a.y) * 0.6) * Math.sign(bend);
    return `M${a.x},${a.y} C${a.x + k},${a.y} ${b.x + k},${b.y} ${b.x},${b.y}`;
  }
  const dx = (b.x - a.x) / 2;
  return `M${a.x},${a.y} C${a.x + dx},${a.y} ${b.x - dx},${b.y} ${b.x},${b.y}`;
}

function renderKG() {
  const kg = D.kg, { pos, heads, H } = layout(kg);
  const visible = (n) => !D.hidden.has(n.type);
  const nodeById = new Map(kg.nodes.map((n) => [n.id, n]));
  const shown = kg.edges.filter((e) => pos.has(e.source) && pos.has(e.target) && visible(nodeById.get(e.source)) && visible(nodeById.get(e.target)));
  const sel = D.selected;
  const active = new Set();
  if (sel && sel.kind === "node") { active.add(sel.id); shown.forEach((e) => { if (e.source === sel.id || e.target === sel.id) { active.add(e.source); active.add(e.target); } }); }
  if (sel && sel.kind === "edge") { const e = kg.edges.find((x) => x.id === sel.id); if (e) { active.add(e.source); active.add(e.target); } }
  const edgeOn = (e) => sel && ((sel.kind === "node" && (e.source === sel.id || e.target === sel.id)) || (sel.kind === "edge" && e.id === sel.id));

  const edgesSvg = shown.map((e) => {
    const d = edgePath(pos.get(e.source), pos.get(e.target)), L = LEVELS[e.level], on = edgeOn(e);
    return `<g class="edge ${on ? "on" : sel ? "dim" : ""}" data-edge="${e.id}">
      <path d="${d}" stroke="${L.color}" stroke-dasharray="${L.dash}" ${e.contradiction ? 'class="flagged"' : ""}/>
      <path class="hit" d="${d}"><title>${esc(nodeById.get(e.source).label)} — ${esc(e.relation)} → ${esc(nodeById.get(e.target).label)} (${L.label})</title></path></g>`;
  }).join("");
  const nodesSvg = kg.nodes.filter((n) => pos.has(n.id) && visible(n)).map((n) => {
    const p = pos.get(n.id), c = TYPES[n.type].color, r = n.focus ? 17 : 7;
    const label = n.focus ? n.label : n.type === "disease" ? shortDisease(n.label) : short(n.label, p.side === "center" ? 26 : 30);
    const flagged = n.flags && n.flags.length;
    const tx = p.side === "left" ? p.x - 14 : p.side === "right" ? p.x + 14 : p.x;
    const ty = p.side === "center" ? p.y + r + 17 : p.y + 5;
    const anchor = p.side === "left" ? "end" : p.side === "right" ? "start" : "middle";
    return `<g class="node ${active.has(n.id) ? "on" : sel ? "dim" : ""} ${n.focus ? "focus" : ""}" data-node="${esc(n.id)}">
      ${n.focus ? `<circle cx="${p.x}" cy="${p.y}" r="30" fill="${c}" opacity=".14"/>` : ""}
      <circle cx="${p.x}" cy="${p.y}" r="${r}" ${n.gap ? `fill="none" stroke="${c}" stroke-dasharray="3 3" stroke-width="1.5"` : `fill="${c}"`}/>
      ${flagged ? `<circle cx="${p.x}" cy="${p.y}" r="${r + 4}" fill="none" stroke="#f08a8a" stroke-width="1.5"/>` : ""}
      <text x="${tx}" y="${ty}" text-anchor="${anchor}">${esc(label)}${flagged ? " ⚠" : ""}</text>
      ${p.side === "center" && n.sub && !n.focus ? `<text class="sub" x="${tx}" y="${ty + 16}" text-anchor="middle">${esc(n.sub)} · ${esc(state(n.status || ""))}</text>` : ""}
      <rect class="hit" x="${p.side === "left" ? p.x - 240 : p.side === "right" ? p.x - 12 : p.x - 110}" y="${p.y - 13}" width="${p.side === "center" ? 220 : 252}" height="${p.side === "center" ? r + 36 : 26}"/>
    </g>`;
  }).join("");
  const headsSvg = heads.filter((h) => !D.hidden.has(h.type)).map((h) => `<text class="head" x="${h.side === "left" ? h.x - 14 : h.side === "right" ? h.x + 14 : h.x}" y="${h.y + 5}"
    text-anchor="${h.side === "left" ? "end" : h.side === "right" ? "start" : "middle"}" fill="${TYPES[h.type].color}">${TYPES[h.type].label.toUpperCase()}</text>`).join("");
  $("#kg").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Knowledge graph for STXBP1">${edgesSvg}${headsSvg}${nodesSvg}</svg>`;

  $("#kg-legend").innerHTML = Object.entries(TYPES).filter(([t]) => kg.counts[t]).map(([t, v]) =>
    `<button class="chip ${D.hidden.has(t) ? "off" : ""}" data-type="${t}"><i style="background:${v.color}"></i>${v.label} ${kg.counts[t]}</button>`).join("")
    + `<span class="ladder">${Object.entries(LEVELS).map(([l, v]) => `<span title="${esc(v.hint)}"><svg width="26" height="8"><line x1="0" y1="4" x2="26" y2="4" stroke="${v.color}" stroke-width="2" stroke-dasharray="${v.dash}"/></svg>${v.label} ${kg.levels[l] || 0}</span>`).join("")}</span>`;
}

function evidenceCard(e, nodeById, from) {
  const a = nodeById.get(e.source), b = nodeById.get(e.target);
  return `<div class="card ev-card" data-edge="${e.id}">
    <div class="meta">${levelBadge(e.level)} ${from ? "" : ""}<strong>${esc(a.label)}</strong> ${esc(e.relation)} <strong>${esc(b.label)}</strong></div>
    <div class="small" style="margin-top:5px">${esc(e.text)}</div>
    ${e.contradiction ? `<div class="note stop small" style="margin:6px 0 2px">${esc(e.contradiction)}</div>` : ""}
    <div class="meta" style="margin-top:4px">Source: ${link(e.url, e.evidence_source)}${e.date ? " · " + esc(e.date) : ""}</div>
  </div>`;
}

function renderDrawer() {
  const kg = D.kg, sel = D.selected, nodeById = new Map(kg.nodes.map((n) => [n.id, n]));
  if (!sel) {
    $("#drawer").innerHTML = `<p class="label">How to read this</p>
      <h2 style="margin-top:6px">Every line is a claim with a source</h2>
      <p class="small muted">Click a dot to see everything connected to it, or a line to see the evidence behind that one link.</p>
      <p class="label" style="margin-top:16px">Evidence ladder</p>
      ${Object.entries(LEVELS).map(([l, v]) => `<div class="small" style="margin:7px 0">${levelBadge(l)} ${esc(v.hint)} <span class="muted">· ${kg.levels[l] || 0} links</span></div>`).join("")}
      <p class="label" style="margin-top:16px">In this graph</p>
      <p class="small">${kg.nodes.length} things and ${kg.edges.length} links around ${esc(kg.gene)}: ${Object.entries(TYPES).filter(([t]) => kg.counts[t]).map(([t, v]) => `${kg.counts[t]} ${v.label.toLowerCase()}`).join(", ")}.</p>
      <p class="small muted">⚠ marks a study whose registry record needs checking before you rely on it. Dashed circles are gaps: things we looked for and did not find.</p>
      <p class="small muted">Seed papers were supplied by the team and matched to PubMed on ${esc(kg.seed.verified)}; their one-line summaries are the team's.</p>`;
    return;
  }
  if (sel.kind === "edge") {
    const e = kg.edges.find((x) => x.id === sel.id);
    $("#drawer").innerHTML = `<button class="chip" data-clear>← Back</button><p class="label" style="margin-top:12px">One link</p>${evidenceCard(e, nodeById)}
      <p class="small muted">${esc(LEVELS[e.level].label)}: ${esc(LEVELS[e.level].hint)}.</p>`;
    return;
  }
  const n = nodeById.get(sel.id), es = kg.edges.filter((e) => e.source === n.id || e.target === n.id);
  const order = { observed: 0, inferred: 1, hypothesis: 2, nodata: 3 };
  es.sort((a, b) => order[a.level] - order[b.level]);
  $("#drawer").innerHTML = `<button class="chip" data-clear>← Back</button>
    <p class="label" style="margin-top:12px;color:${TYPES[n.type].color}">${TYPES[n.type].label.replace(/s$/, "")}</p>
    <h2 style="margin-top:4px">${n.url ? link(n.url, n.label) : esc(n.label)}</h2>
    ${n.sub ? `<p class="small muted">${esc(n.sub)}</p>` : ""}
    ${n.status ? `<p class="small">Registered as <strong>${esc(state(n.status))}</strong> · last updated ${esc(n.updated)} · ${n.enrollment ?? "?"} participants (${esc((n.enrollment_type || "not stated").toLowerCase())}) · ${esc(n.sponsor || "")}</p>` : ""}
    ${(n.flags || []).map((f) => `<div class="note stop small">${esc(f)}</div>`).join("")}
    ${n.detail ? `<p class="small def" title="Click to expand">${esc(n.detail)}</p>` : ""}
    ${n.atlas_id ? `<p class="small"><a href="/atlas#c/${kg.focus}/${n.atlas_id}">Open the full connection to ${esc(kg.gene)} →</a></p>` : ""}
    <p class="label" style="margin-top:14px">${plural(es.length, "link")}</p>
    ${es.map((e) => evidenceCard(e, nodeById)).join("")}`;
}

document.addEventListener("click", (ev) => {
  const t = ev.target;
  if (t.classList.contains("def")) t.classList.toggle("open");
  const type = t.closest("[data-type]");
  if (type) { const k = type.dataset.type; D.hidden.has(k) ? D.hidden.delete(k) : D.hidden.add(k); renderKG(); return; }
  if (t.closest("[data-clear]")) { D.selected = null; renderKG(); renderDrawer(); return; }
  const n = t.closest("#kg [data-node]"), e = t.closest("[data-edge]");
  if (n) { D.selected = { kind: "node", id: n.dataset.node }; renderKG(); renderDrawer(); return; }
  if (e && !t.closest("a")) { D.selected = { kind: "edge", id: e.dataset.edge }; renderKG(); renderDrawer(); return; }
  if (t.closest("#kg svg")) { D.selected = null; renderKG(); renderDrawer(); }
});

/* ------------------------------------------------------------------ tiles */
function renderTiles() {
  const kg = D.kg, tr = D.trials, pu = D.pulse;
  const named = tr && tr.trials ? tr.trials.filter((t) => t.screen.verdict === "names_disease" && !(t.flags || []).length).length : null;
  const could = tr && tr.trials ? tr.trials.filter((t) => t.screen.verdict === "could_include" && t.type === "INTERVENTIONAL").length : null;
  const openDrug = kg.ledger.find((l) => l.what.startsWith("Open treatment trials"));
  const flagged = kg.studies.filter((s) => s.flags.length).length;
  const tile = (v, label, sub, href) => `<a class="tile" href="${href}"><b>${v ?? "…"}</b><span>${label}</span><small>${sub}</small></a>`;
  $("#tiles").innerHTML =
    tile(openDrug.found, "open treatment trials name STXBP1", "as registered on ClinicalTrials.gov", "#ledger") +
    tile(named, "STXBP1 registries and studies to join", "open, with a current record", "#trials") +
    tile(could, "broader trials a child might qualify for", "screened by AI; study team decides", "#trials") +
    tile(flagged, "study records that need checking", "withdrawn, stopped or out of date", "#actions") +
    tile(pu ? pu.items.length : null, `updates in the last ${pu ? pu.window_days : 60} days`, "papers, preprints, study records", "#pulse");
}

/* ------------------------------------------------------------------ actions + study status */
function enquiry(t) {
  const who = t.contacts && t.contacts[0] ? t.contacts[0].name : "study team";
  return `Subject: Enquiry about ${t.nct} for a child with STXBP1-related disorder

Dear ${who},

I lead the STXBP1 patient group and am writing on behalf of our families. We found your study "${t.title}" (${t.nct}, ${t.url}), registered as ${state(t.status)} and last updated on ${t.updated}.

Our children have a confirmed pathogenic STXBP1 variant, usually with early-onset epilepsy and developmental delay${D.profile.age !== "" ? `; the child I am asking for is ${D.profile.age} years old` : ""}${D.profile.country ? `, based in ${D.profile.country}` : ""}.

Could you confirm whether the study is still enrolling, whether children with STXBP1-related disorder can be considered, which inclusion criteria usually rule them out, and which site is closest to us?

Thank you,
Maria
`;
}

function renderActions() {
  const kg = D.kg, focusName = kg.gene;
  const current = kg.studies.filter((s) => s.type !== "INTERVENTIONAL" && s.status === "RECRUITING" && !s.flags.length
    && (s.title + s.conditions.join(" ")).toLowerCase().includes(focusName.toLowerCase()));
  const closest = kg.nodes.find((n) => n.type === "disease" && n.atlas_id);
  const gap = kg.nodes.find((n) => n.gap && n.type === "group");
  const stopped = kg.studies.filter((s) => s.type === "INTERVENTIONAL" && s.flags.length);
  $("#actions").innerHTML = `<div class="panel-head"><h2>What to do this week</h2></div>
    <ol class="steps">
      ${current.slice(0, 2).map((s) => `<li><strong>Ask whether your families can enrol in ${esc(s.nct)}.</strong> ${esc(short(s.title, 90))} — registered as recruiting, record updated ${esc(s.updated)}, sponsor ${esc(s.sponsor)}.
        <div><button class="chip" data-enquiry="${s.nct}">Draft the e-mail</button> ${link(s.url, "Check live status")}</div></li>`).join("")}
      ${closest ? `<li><strong>Look at your closest neighbour, ${esc(shortDisease(closest.label))} (${esc(closest.sub)}).</strong>
        ${gap ? "No patient group was found for it in the sources we searched, so its families may be looking for a community like yours. " : ""}The link is a hypothesis to validate with an expert${(closest.inheritance || []).length ? `; it is inherited differently (${esc(closest.inheritance.join(", ").toLowerCase())})` : ""}.
        <div><a class="chip" href="/atlas#c/${kg.focus}/${closest.atlas_id}">See the evidence and the sourced proposal</a></div></li>` : ""}
      ${stopped.map((s) => `<li><strong>Do not count on ${esc(s.nct)}.</strong> ${esc(short(s.title, 80))}: ${esc(s.flags.join("; "))}. ${link(s.url, "Registry record")}</li>`).join("")}
      <li><strong>Add what your families know.</strong> Symptoms, registries or contacts missing here can be contributed, marked unverified. <div><a class="chip" href="/atlas#">Open the contribution form (Community tab)</a></div></li>
    </ol>
    <p class="label" style="margin-top:18px">Every STXBP1 study, as registered</p>
    <p class="small muted">“Recruiting” is self-reported by sponsors. Check the date before you rely on it.</p>
    <table class="status"><tr><th>Study</th><th>Status</th><th>Updated</th><th>Enrolled</th></tr>
    ${kg.studies.map((s) => `<tr class="${s.flags.length ? "flag" : ""}"><td>${link(s.url, s.nct)} <span class="muted">${esc(s.kind.split(" ")[0])}</span><div>${esc(short(s.title, 70))}</div>${s.flags.map((f) => `<div class="warn">⚠ ${esc(f)}</div>`).join("")}</td>
      <td>${esc(state(s.status))}</td><td>${esc(s.updated)}</td><td>${s.enrollment ?? "?"} <span class="muted">${esc((s.enrollment_type || "").toLowerCase())}</span></td></tr>`).join("")}</table>`;
}

/* ------------------------------------------------------------------ pulse */
function renderPulse() {
  const p = D.pulse;
  if (p.error) { $("#pulse").innerHTML = `<div class="note stop">Could not load updates: ${esc(p.error)}</div>`; return; }
  const fresh = p.items.filter((i) => i.new).length;
  $("#pulse").innerHTML = `<div class="panel-head"><h2>Pulse <span class="muted small">· last ${p.window_days} days</span></h2>
      <button class="chip" id="pulse-refresh">Check now</button></div>
    <p class="small muted">Checked ${esc(p.checked.replace("T", " "))}; re-checked every 6 hours. ${fresh ? `<strong style="color:var(--ok)">${plural(fresh, "item")} new since the last check.</strong>` : "Nothing new since the last check."}
      Collected automatically and not reviewed${p.model ? `; one-line notes by ${esc(p.model)} from titles only` : ""}.</p>
    ${p.errors.length ? `<div class="note warn small">Sources that did not answer: ${esc(p.errors.join(", "))}</div>` : ""}
    <div class="feed">${p.items.map((i) => `<div class="item"><div class="meta">${i.new ? `<span class="badge viable">new</span> ` : ""}${esc(i.date)} · ${esc(i.kind)}${i.detail ? " · " + esc(i.detail) : ""}</div>
      <div>${link(i.url, i.title.replace(/^\[|\]$/g, ""))}</div>${i.summary ? `<div class="small muted">${esc(i.summary)}</div>` : ""}</div>`).join("") || `<p class="muted small">No updates found in this window.</p>`}</div>`;
}

/* ------------------------------------------------------------------ ledger */
function renderLedger() {
  const kg = D.kg, tr = D.trials;
  $("#ledger").innerHTML = `<div class="panel-head"><h2>What we searched</h2></div>
    <p class="small muted">A zero means “none found in these sources on this date”, not “none exists”.</p>
    <table><tr><th>Search</th><th>Found</th><th>Date</th></tr>
    ${kg.ledger.map((l) => `<tr><td>${l.url ? link(l.url, l.what) : esc(l.what)}<div class="muted">${esc(l.where)}</div></td>
      <td class="${l.found ? "" : "zero"}">${l.found.toLocaleString()}</td><td>${esc(l.date)}</td></tr>`).join("")}
    ${tr && tr.trials ? `<tr><td>Open studies screened for eligibility<div class="muted">${esc(tr.queries.length)} ClinicalTrials.gov queries; read by ${esc(tr.model)}</div></td><td>${tr.trials.length}</td><td>${esc(tr.fetched.slice(0, 10))}</td></tr>` : ""}
    </table>
    <p class="small muted">Atlas built ${esc(kg.meta.built)} from ${kg.meta.sources.map((s) => link(s.url, s.name.split(" (")[0])).join(", ")}.
      ${kg.llm.enabled ? `AI steps run on ${esc(kg.llm.model)} via ${esc(kg.llm.provider)}.` : "AI steps are off (template mode)."}</p>`;
}

/* ------------------------------------------------------------------ trials to join */
const VERDICT = {
  names_disease: { label: "Made for STXBP1", cls: "viable" },
  could_include: { label: "Could include your child", cls: "speculative" },
  excludes: { label: "Likely excludes STXBP1", cls: "thin" },
  other_gene_only: { label: "Other gene only", cls: "unsupported" },
};
const ageFits = (t, age) => age === "" || ((t.min_age == null || age >= t.min_age) && (t.max_age == null || age <= t.max_age));

function trialCard(t) {
  const sc = t.screen, country = D.profile.country;
  const sites = country ? t.sites.filter((x) => x.country === country) : [];
  const countries = [...new Set(t.sites.map((x) => x.country).filter(Boolean))];
  const phase = t.phases.filter((p) => p !== "NA").map((p) => p.replace("EARLY_PHASE1", "Early phase 1").replace("PHASE", "Phase ")).join("/");
  const contact = t.contacts[0];
  return `<div class="card trial">
    <div class="meta"><span class="badge ${VERDICT[sc.verdict].cls}">${VERDICT[sc.verdict].label}</span>
      ${esc(t.kind)}${phase ? " · " + esc(phase) : ""} · ${esc(state(t.status))} · record updated ${esc(t.updated)}</div>
    <div class="title" style="margin-top:6px">${link(t.url, t.title)}</div>
    ${(t.flags || []).map((f) => `<div class="note stop small">${esc(f)}</div>`).join("")}
    <p class="small" style="margin:6px 0">${esc(sc.reason)}</p>
    ${sc.quote ? `<blockquote>“${esc(sc.quote)}” <span class="muted">— eligibility criteria, ${esc(t.nct)}</span></blockquote>` : ""}
    ${sc.requirements && sc.requirements.length ? `<div class="chips">${sc.requirements.map((r) => `<span class="chip">${esc(r)}</span>`).join("")}</div>` : ""}
    <div class="meta">Ages ${esc(t.ages)}${t.interventions.length ? " · " + t.interventions.slice(0, 2).map((i) => esc(i.name)).join(", ") : ""} · ${esc(t.sponsor)}</div>
    <div class="meta">${sites.length ? `<span style="color:var(--ok)">${plural(sites.length, "site")} in ${esc(country)}</span>: ${sites.slice(0, 3).map((x) => esc(x.city || x.facility)).join(", ")}`
      : countries.length ? `${country ? `No site in ${esc(country)} · ` : ""}Sites in ${countries.slice(0, 4).map(esc).join(", ")}${countries.length > 4 ? ` +${countries.length - 4}` : ""}` : "Sites not listed yet"}</div>
    ${contact ? `<div class="meta">Contact: ${esc(contact.name)}${contact.email ? ` · <a href="mailto:${esc(contact.email)}">${esc(contact.email)}</a>` : ""}${contact.phone ? " · " + esc(contact.phone) : ""}</div>` : ""}
    <div style="margin-top:8px"><button class="chip" data-enquiry="${esc(t.nct)}">Draft an enquiry to the study team</button></div>
  </div>`;
}

function renderTrials() {
  const r = D.trials;
  if (r.error) { $("#trials").innerHTML = `<div class="note stop">Could not load trials: ${esc(r.error)}</div>`; return; }
  const age = D.profile.age === "" ? "" : +D.profile.age, all = r.trials, country = D.profile.country;
  const countries = [...new Set(all.flatMap((t) => t.sites.map((x) => x.country)).filter(Boolean))].sort();
  const usable = all.filter((t) => ["names_disease", "could_include"].includes(t.screen.verdict));
  const fits = usable.filter((t) => ageFits(t, age));
  const near = (t) => (country && t.sites.some((x) => x.country === country) ? 0 : 1);
  const sorted = (list) => [...list].sort((a, b) => near(a) - near(b));
  const experimental = sorted(fits.filter((t) => t.type === "INTERVENTIONAL"));
  const named = sorted(fits.filter((t) => t.screen.verdict === "names_disease" && t.type !== "INTERVENTIONAL"));
  const groups = {};
  for (const t of experimental) (groups[t.kind] = groups[t.kind] || []).push(t);
  const notFor = all.filter((t) => !usable.includes(t)), tooOld = usable.length - fits.length;
  const noDrug = !all.some((t) => t.screen.verdict === "names_disease" && t.type === "INTERVENTIONAL");
  $("#trials").innerHTML = `<div class="panel-head"><h2>Trials your families could ask to join</h2></div>
    <p class="small muted">Every open study that mentions STXBP1, plus children's interventional trials for the epilepsies STXBP1 patients have, read and screened by ${esc(r.model)}.
      A screening aid, not medical advice: only the study team can confirm eligibility.</p>
    <form class="profile">
      <label>Child's age (years)<input name="age" type="number" min="0" max="80" step="0.5" value="${esc(D.profile.age)}" placeholder="any"></label>
      <label>Country<select name="country"><option value="">Any</option>${countries.map((c) => `<option ${c === country ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
    </form>
    ${tooOld ? `<p class="small muted">${plural(tooOld, "study")} hidden because a ${esc(D.profile.age)}-year-old is outside the age range.</p>` : ""}
    ${noDrug ? `<div class="note warn"><strong>No open drug or gene-therapy trial names STXBP1 today.</strong> The experimental trials below are for broader epilepsies your families may qualify for. Joining a natural-history study keeps them trial-ready for when an STXBP1 therapy reaches the clinic.</div>` : ""}
    <div class="split">
      <div><h3>Experimental trials <span class="muted small">· ${experimental.length}</span></h3>
        ${Object.keys(groups).length ? Object.entries(groups).map(([k, ts]) => `<p class="label" style="margin-top:14px">${esc(k)} · ${ts.length}</p>${ts.map(trialCard).join("")}`).join("") : `<p class="muted small">None match the filters.</p>`}</div>
      <div><h3>STXBP1 studies to join now <span class="muted small">· ${named.length}</span></h3>
        <p class="small muted">Registries and natural-history studies. They test no treatment, but they build the data every future STXBP1 trial will need.</p>
        ${named.map(trialCard).join("") || `<p class="muted small">None match the filters.</p>`}
        <details><summary>Not suitable for STXBP1 <span>${notFor.length} studies</span></summary><div>
          ${notFor.map((t) => `<div class="small" style="margin:8px 0"><span class="badge ${VERDICT[t.screen.verdict].cls}">${VERDICT[t.screen.verdict].label}</span> ${link(t.url, t.title)}<div class="muted">${esc(t.screen.reason)}</div></div>`).join("")}
        </div></details></div>
    </div>`;
}

document.addEventListener("change", (ev) => {
  const f = ev.target.closest("form.profile");
  if (!f) return;
  D.profile = { age: f.age.value, country: f.country.value };
  try { localStorage.setItem("profile", JSON.stringify(D.profile)); } catch (e) { /* ignore */ }
  renderTrials();
});
document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-enquiry]");
  if (b) {
    const id = b.dataset.enquiry;
    const t = (D.trials && D.trials.trials || []).find((x) => x.nct === id) || D.kg.studies.find((x) => x.nct === id);
    openSheet(enquiry(t), "Enquiry to the study team");
  }
  if (ev.target.id === "pulse-refresh") {
    ev.target.textContent = "Checking…";
    try { D.pulse = await api("/api/pulse?refresh=true"); } catch (e) { D.pulse = { error: e.message }; }
    renderPulse(); renderTiles();
  }
});

/* ------------------------------------------------------------------ init */
(async function init() {
  try {
    D.kg = await api("/api/dashboard");
  } catch (e) {
    $("#kg").innerHTML = `<div class="note stop">Could not build the dashboard: ${esc(e.message)}</div>`;
    return;
  }
  renderKG(); renderDrawer(); renderTiles(); renderActions(); renderLedger();
  api("/api/pulse").then((p) => { D.pulse = p; }).catch((e) => { D.pulse = { error: e.message, items: [], window_days: 60 }; })
    .finally(() => { renderPulse(); renderTiles(); });
  api(`/api/disease/${D.kg.focus}/trials`).then((t) => { D.trials = t; }).catch((e) => { D.trials = { error: e.message }; })
    .finally(() => { renderTrials(); renderTiles(); renderLedger(); });
})();

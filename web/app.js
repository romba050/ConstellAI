/* ConstellAI frontend: constellation map + evidence panel. No build step. */
const COLORS = ["#6ea8fe", "#f6c453", "#7ddc9a", "#f08a8a", "#c59bf5", "#5fd4d6", "#f5a05c", "#e58fc8",
  "#a5d65a", "#8f9cf7", "#e8d27a", "#58c7a0", "#f27fa5", "#9fb8d8"];
const OTHER = "#56617d";
const MARIA = { audience: "maria", tab: "connections", hint: "Patient organisation leader: closest constellations, reusable assets, next step." };
const S = { points: [], byId: new Map(), groups: [], meta: null, llm: null,
  selected: null, neighbors: [], highlight: null, tab: null, evidence: {}, conn: null };

const $ = (s, el = document) => el.querySelector(s);
const panel = $("#panel");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const api = async (path) => {
  const r = await fetch(path);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
};
const color = (g) => (g >= 0 && g < COLORS.length ? COLORS[g] : OTHER);
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
const lay = (p) => p.name;
const link = (url, text) => (url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text)}</a>` : esc(text));
const refLink = (ref) => {
  const [db, id] = ref.split(":");
  const url = db === "PMID" ? `https://pubmed.ncbi.nlm.nih.gov/${id}/` : db === "OMIM" ? `https://omim.org/entry/${id}`
    : db === "ORPHA" ? `https://www.orpha.net/en/disease/detail/${id}` : "";
  return link(url, ref);
};
const diseaseHref = (id) => `#d/${id}`;
const geneChip = (g) => `<a class="chip gene" href="#e/gene/${esc(g)}">${esc(g)}</a>`;

/* ------------------------------------------------------------------ map */
const canvas = $("#map"), ctx = canvas.getContext("2d"), tip = $("#tip");
let W = 0, H = 0, base = 1, T = d3.zoomIdentity, edges = [], quad = null, hover = null, dirty = true;
const zoom = d3.zoom().scaleExtent([0.6, 60]).on("zoom", (e) => { T = e.transform; dirty = true; });
d3.select(canvas).call(zoom).on("dblclick.zoom", null);

function resize() {
  const r = canvas.parentElement.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  if (r.width <= 0 || r.height <= 0) return;
  const center = W > 0 && H > 0 && base > 0 ? {
    x: (T.invertX(W / 2) - W / 2) / base,
    y: (T.invertY(H / 2) - H / 2) / base,
  } : null;
  const scale = T.k;
  W = r.width; H = r.height; base = Math.min(W, H) * 0.47;
  canvas.width = W * dpr; canvas.height = H * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (center) {
    const t = d3.zoomIdentity.translate(W / 2 - scale * (W / 2 + center.x * base), H / 2 - scale * (H / 2 + center.y * base)).scale(scale);
    d3.select(canvas).interrupt().call(zoom.transform, t);
  }
  hover = null; tip.hidden = true;
  dirty = true;
}
const px = (p) => T.applyX(W / 2 + p.x * base);
const py = (p) => T.applyY(H / 2 + p.y * base);

function draw() {
  requestAnimationFrame(draw);
  if (!dirty || !S.points.length) return;
  dirty = false;
  ctx.clearRect(0, 0, W, H);
  const k = T.k, hl = S.highlight, sel = S.selected;
  const rOf = (p) => Math.min(4.5, (1.0 + Math.min(p.deg, 12) * 0.06) * Math.pow(k, 0.4));

  if (!hl) {
    ctx.strokeStyle = "#8fa6d8"; ctx.globalAlpha = Math.min(0.16, 0.035 * k); ctx.lineWidth = 0.6;
    ctx.beginPath();
    for (const [i, j] of edges) {
      const a = S.points[i], b = S.points[j];
      ctx.moveTo(px(a), py(a)); ctx.lineTo(px(b), py(b));
    }
    ctx.stroke();
  }
  const buckets = new Map();
  for (const p of S.points) {
    const dim = hl && !hl.has(p.id);
    const key = (dim ? "d" : "n") + p.group;
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(p);
  }
  for (const [key, pts] of buckets) {
    ctx.globalAlpha = key[0] === "d" ? 0.13 : 0.92;
    ctx.fillStyle = color(pts[0].group);
    ctx.beginPath();
    for (const p of pts) {
      const x = px(p), y = py(p);
      if (x < -10 || y < -10 || x > W + 10 || y > H + 10) continue;
      const r = rOf(p) * (hl && key[0] === "n" ? 1.5 : 1);
      ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, 6.2832);
    }
    ctx.fill();
  }
  ctx.globalAlpha = 1;

  if (sel) {
    const s = S.byId.get(sel);
    for (const nb of S.neighbors) {
      const p = S.byId.get(nb.id);
      ctx.strokeStyle = color(p.group); ctx.lineWidth = 0.8 + nb.score * 2.2;
      ctx.globalAlpha = S.conn && S.conn !== nb.id ? 0.25 : 0.9;
      ctx.setLineDash(nb.cross_group ? [5, 4] : []);
      ctx.beginPath(); ctx.moveTo(px(s), py(s)); ctx.lineTo(px(p), py(p)); ctx.stroke();
    }
    ctx.setLineDash([]); ctx.globalAlpha = 1;
    ctx.font = "11.5px Inter, sans-serif"; ctx.textBaseline = "middle";
    for (const nb of S.neighbors) {
      const p = S.byId.get(nb.id), x = px(p), y = py(p);
      ctx.fillStyle = color(p.group); ctx.beginPath(); ctx.arc(x, y, rOf(p) + 1.5, 0, 6.2832); ctx.fill();
      if (k > 2.5 || S.conn === nb.id) { ctx.fillStyle = "#c6cde0"; ctx.fillText(p.genes, x + 8, y); }
    }
    const x = px(s), y = py(s);
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(x, y, rOf(s) + 5, 0, 6.2832); ctx.stroke();
    ctx.fillStyle = color(s.group); ctx.beginPath(); ctx.arc(x, y, rOf(s) + 2, 0, 6.2832); ctx.fill();
    ctx.fillStyle = "#fff"; ctx.font = "600 12.5px Inter, sans-serif"; ctx.fillText(s.genes, x + 12, y);
  } else if (k < 2.4 && !hl) {
    ctx.font = "600 10.5px Inter, sans-serif"; ctx.textAlign = "center";
    for (const g of S.groups) {
      if (g.id < 0 || g.id >= 10 || g.cx === undefined) continue;
      ctx.fillStyle = color(g.id); ctx.globalAlpha = 0.85;
      ctx.fillText(g.short.toUpperCase(), T.applyX(W / 2 + g.cx * base), T.applyY(H / 2 + g.cy * base));
    }
    ctx.textAlign = "left"; ctx.globalAlpha = 1;
  }
  if (k >= 5) {
    const vis = S.points.filter((p) => { const x = px(p), y = py(p); return x > 0 && y > 0 && x < W && y < H; });
    if (vis.length <= 70) {
      ctx.font = "11px Inter, sans-serif"; ctx.fillStyle = "#8d98b0"; ctx.textBaseline = "middle";
      const skip = new Set(S.neighbors.map((n) => n.id).concat(sel || []));
      for (const p of vis) if (!skip.has(p.id)) ctx.fillText(p.genes, px(p) + 7, py(p));
    }
  }
  if (hover) {
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(px(hover), py(hover), rOf(hover) + 3, 0, 6.2832); ctx.stroke();
  }
}

function pointAt(ev) {
  const [mx, my] = d3.pointer(ev, canvas);
  const x = (T.invertX(mx) - W / 2) / base, y = (T.invertY(my) - H / 2) / base;
  return quad.find(x, y, 9 / (T.k * base));
}
canvas.addEventListener("mousemove", (ev) => {
  const p = pointAt(ev);
  if (p !== hover) { hover = p; dirty = true; }
  canvas.style.cursor = p ? "pointer" : "grab";
  tip.hidden = !p;
  if (p) {
    const g = S.groups.find((g) => g.id === p.group);
    tip.innerHTML = `<strong>${esc(p.name)}</strong><em>${esc(p.genes)} · ${esc(g ? g.label : "")}</em>`;
    const [mx, my] = d3.pointer(ev, canvas);
    tip.style.left = Math.min(mx + 14, W - 290) + "px"; tip.style.top = my + 14 + "px";
  }
});
canvas.addEventListener("mouseleave", () => { hover = null; tip.hidden = true; dirty = true; });
canvas.addEventListener("click", (ev) => { const p = pointAt(ev); if (p) location.hash = diseaseHref(p.id); });
$("#reset").onclick = () => { location.hash = ""; d3.select(canvas).transition().duration(600).call(zoom.transform, d3.zoomIdentity); };

function focus(ids, maxK = 14) {
  const pts = ids.map((i) => S.byId.get(i)).filter(Boolean);
  if (!pts.length) return;
  const xs = d3.extent(pts, (p) => p.x), ys = d3.extent(pts, (p) => p.y);
  const w = Math.max((xs[1] - xs[0]) * base, 1), h = Math.max((ys[1] - ys[0]) * base, 1);
  const k = Math.max(0.8, Math.min(maxK, 0.62 * Math.min(W / w, H / h)));
  const cx = W / 2 + ((xs[0] + xs[1]) / 2) * base, cy = H / 2 + ((ys[0] + ys[1]) / 2) * base;
  const t = d3.zoomIdentity.translate(W / 2 - k * cx, H / 2 - k * cy).scale(k);
  // Background tabs throttle animation frames; jump straight to the target there.
  if (document.hidden) d3.select(canvas).call(zoom.transform, t);
  else d3.select(canvas).transition().duration(750).call(zoom.transform, t);
}

/* ------------------------------------------------------------------ legend */
function renderLegend() {
  const c = S.meta.counts;
  $("#legend").innerHTML = `<h3>Constellations</h3>` + S.groups.map((g) => `
    <div class="group" data-group="${g.id}" title="${esc(g.enrichment_label || g.label)}">
      <i style="background:${color(g.color)}"></i><b>${esc(g.short)}</b><span>${g.size}</span>
    </div>`).join("") + `
    <div class="foot">
      <p>Grouped by shared symptoms and pathways, not by disease name.</p>
      <p>${c.diseases.toLocaleString()} monogenic diseases · ${c.genes.toLocaleString()} genes · ${c.similarity_edges.toLocaleString()} evidence-backed links · ${c.clusters} clusters</p>
      <p>Built ${esc(S.meta.built)} · ${S.llm.enabled ? "OpenAI " + esc(S.llm.model) : "template mode (no OpenAI key)"}</p>
    </div>`;
}
$("#legend").addEventListener("click", (ev) => {
  const el = ev.target.closest(".group");
  if (!el) return;
  const gid = +el.dataset.group, on = el.classList.contains("on");
  document.querySelectorAll(".group.on").forEach((x) => x.classList.remove("on"));
  if (on) { S.highlight = null; } else {
    el.classList.add("on");
    const ids = S.points.filter((p) => p.group === gid).map((p) => p.id);
    S.highlight = new Set(ids);
    if (gid >= 0) focus(ids, 6);
  }
  dirty = true;
});

/* ------------------------------------------------------------------ search */
const q = $("#q"), hitsEl = $("#hits");
let hits = [], hitIx = 0, searchSeq = 0;
const TYPE_LABEL = { disease: "Disease", gene: "Gene", phenotype: "Symptom", mechanism: "Mechanism", group: "Patient group" };
function renderHits() {
  hitsEl.hidden = false;
  hitsEl.innerHTML = hits.length ? hits.map((h, i) => `
    <div class="hit ${i === hitIx ? "on" : ""}" data-i="${i}">
      <span class="type">${TYPE_LABEL[h.type]}</span>
      <span>${esc(h.label)}${h.matched ? `<small>matched “${esc(h.matched)}”</small>` : ""}</span>
      <span class="sub">${esc(h.sub || "")}</span>
    </div>`).join("")
    : `<div class="hit none">No disease, gene, symptom, mechanism or patient group matches “${esc(q.value)}”. The atlas covers monogenic diseases with HPO annotations; try a gene symbol or an OMIM number.</div>`;
}
q.addEventListener("input", async () => {
  const seq = ++searchSeq, text = q.value.trim();
  if (text.length < 2) { hitsEl.hidden = true; return; }
  const r = await api("/api/search?q=" + encodeURIComponent(text));
  if (seq !== searchSeq) return;
  hits = r.hits; hitIx = 0; renderHits();
});
function choose(h) {
  if (!h) return;
  hitsEl.hidden = true; q.blur();
  if (h.matched) S.resolved = { from: h.matched, id: h.id };
  location.hash = h.type === "disease" ? diseaseHref(h.id) : `#e/${h.type}/${encodeURIComponent(h.id)}`;
}
q.addEventListener("keydown", (ev) => {
  if (ev.key === "ArrowDown") { hitIx = Math.min(hitIx + 1, hits.length - 1); renderHits(); ev.preventDefault(); }
  else if (ev.key === "ArrowUp") { hitIx = Math.max(hitIx - 1, 0); renderHits(); ev.preventDefault(); }
  else if (ev.key === "Enter") choose(hits[hitIx]);
  else if (ev.key === "Escape") hitsEl.hidden = true;
});
hitsEl.addEventListener("mousedown", (ev) => { const el = ev.target.closest(".hit[data-i]"); if (el) choose(hits[+el.dataset.i]); });
q.addEventListener("blur", () => setTimeout(() => (hitsEl.hidden = true), 150));

/* ------------------------------------------------------------------ home */
function renderHome() {
  const c = S.meta.counts;
  const ex = [["STXBP1", "STXBP1"], ["Tay-Sachs disease", "Tay-Sachs"], ["SYNGAP1", "SYNGAP1"], ["Sanfilippo", "Sanfilippo"], ["Epileptic spasm", "Epileptic spasm"]];
  panel.innerHTML = `
    <h1>Five thousand scattered points of light. One map to see the constellations.</h1>
    <p class="lede" style="margin-top:12px">Every star is a rare disease caused by a single gene. Stars sit together when patients share
      symptoms and their genes work in the same pathway — whatever the diseases are called.</p>
    <p class="muted">${esc(MARIA.hint)}</p>
    <h2>Start from your disease</h2>
    <div class="chips">${ex.map(([l, v]) => `<button class="chip" data-example="${esc(v)}">${esc(l)}</button>`).join("")}</div>
    <h2>The atlas answers three questions</h2>
    <ol class="steps">
      <li><strong>Who shares our disease characteristics?</strong><br><span class="muted">Closest diseases by mechanism and symptoms, with the evidence for each link.</span></li>
      <li><strong>What useful work already exists?</strong><br><span class="muted">Registries, natural-history studies, models, grants and the groups behind them.</span></li>
      <li><strong>What should we do together next?</strong><br><span class="muted">What to check first, who to write to, and a sourced proposal to send.</span></li>
    </ol>
    <h2>What is in the map</h2>
    <table>
      <tr><td>Diseases</td><td>${c.diseases.toLocaleString()} monogenic, reconciled to MONDO identifiers</td></tr>
      <tr><td>Symptom links</td><td>${c.phenotype_annotations.toLocaleString()} HPO annotations, each with its reference</td></tr>
      <tr><td>Mechanism links</td><td>${c.pathways.toLocaleString()} Reactome pathways across ${c.genes.toLocaleString()} genes</td></tr>
      <tr><td>Live evidence</td><td>PubMed, ClinicalTrials.gov, NIH RePORTER and ClinVar, fetched when you open a disease</td></tr>
      <tr><td>Communities</td><td>${S.orgs} patient organisations, websites checked</td></tr>
    </table>
    <h2>Sources</h2>
    <p class="small muted">${S.meta.sources.map((s) => `${link(s.url, s.name)} (${esc(s.version)})`).join(" · ")}</p>
    <p class="small muted">ConstellAI connects public research data. It is not medical advice, and an inferred link is a hypothesis, not proof that a treatment exists.</p>`;
}
panel.addEventListener("click", (ev) => {
  const ex = ev.target.closest("[data-example]");
  if (ex) { q.value = ex.dataset.example; q.focus(); q.dispatchEvent(new Event("input")); }
});

/* ------------------------------------------------------------------ disease */
const GRADE_TEXT = { viable: "Viable lead", speculative: "Speculative", thin: "Thin data", unsupported: "Unsupported" };

async function openDisease(id) {
  panel.innerHTML = `<div class="loading">Opening the atlas</div>`;
  const d = await api("/api/disease/" + id);
  S.selected = id; S.neighbors = d.neighbors; S.highlight = null; S.conn = null; S.detail = d;
  focus([id, ...d.neighbors.map((n) => n.id)]);
  dirty = true;
  renderDisease();
  if (!S.evidence[id]) {
    api(`/api/disease/${id}/evidence`).then((e) => { S.evidence[id] = e; if (S.selected === id && !S.conn) renderDisease(); })
      .catch((err) => { S.evidence[id] = { error: err.message }; if (S.selected === id && !S.conn) renderDisease(); });
  }
}

function renderDisease() {
  const d = S.detail, e = S.evidence[d.id], tab = S.tab || MARIA.tab;
  const resolved = S.resolved && S.resolved.id === d.id ? S.resolved.from : null;
  const tabs = [["connections", `Connections ${d.neighbors.length}`], ["biology", "Biology"], ["community", "Community"], ["people", "People"]];
  panel.innerHTML = `
    <a class="back" href="#">← Whole atlas</a>
    <h1>${esc(d.name)}</h1>
    ${resolved ? `<p class="small" style="color:var(--accent)">“${esc(resolved)}” resolves to this disease.</p>` : ""}
    <div class="chips">${d.genes.map((g) => geneChip(g.symbol)).join("")}
      ${d.inheritance.map((i) => `<span class="chip">${esc(i.replace(" inheritance", ""))}</span>`).join("")}
      ${d.onset.slice(0, 2).map((i) => `<span class="chip">${esc(i)}</span>`).join("")}</div>
    ${d.def ? `<p class="def muted" title="Click to expand">${esc(d.def)}</p>` : ""}
    <p class="small muted">${d.synonyms.length ? `Also known as ${d.synonyms.slice(0, 4).map(esc).join("; ")}${d.synonyms.length > 4 ? ` and ${d.synonyms.length - 4} more names` : ""}. ` : ""}
      ${d.links.map((l) => link(l.url, l.label)).join(" · ")}</p>
    <p class="small">Constellation: <a href="#k/${esc(d.cluster.id)}"><span style="color:${color(d.group)}">●</span> ${esc(d.cluster.label)}</a>
      <span class="muted">· ${plural(d.cluster.size, "disease")}</span></p>
    <div class="tabs">${tabs.map(([k, l]) => `<button data-tab="${k}" class="${k === tab ? "on" : ""}">${l}</button>`).join("")}</div>
    <div id="tab">${{ connections: tabConnections, biology: tabBiology, community: tabCommunity, people: tabPeople }[tab](d, e)}</div>`;
}
panel.addEventListener("click", (ev) => {
  if (ev.target.classList.contains("def")) ev.target.classList.toggle("open");
  const t = ev.target.closest("[data-tab]");
  if (t) { S.tab = t.dataset.tab; renderDisease(); }
});

function tabConnections(d) {
  if (!d.neighbors.length) return noRoute(d);
  return `${d.sparse ? `<div class="note warn">Only ${d.phenotypes.length} symptoms are recorded for this disease, so every link below rests on thin data.</div>` : ""}
    <p class="small muted" style="margin-top:12px">Closest diseases by shared symptoms <span style="color:var(--info)">▬</span> and shared pathway <span style="color:var(--accent)">▬</span>. Open one to see why, what differs and what to do next.</p>
    ${d.neighbors.map((n) => {
      const why = [n.same_gene ? "Same gene — check the variant effect" : n.shared_pathway ? `Shares “${n.shared_pathway}”` : "Symptom overlap only",
        n.cross_group ? "bridge to another constellation" : ""].filter(Boolean).join(" · ");
      const ph = 0.65 * n.pheno, pa = n.score - ph > 0.005 && n.path ? n.score - ph : 0;
      return `<a class="row" href="#c/${d.id}/${n.id}" data-nb="${n.id}">
        <div class="top"><span class="name" style="color:var(--text)">${esc(n.name)}</span>${n.genes.map((g) => `<span class="chip gene">${esc(g)}</span>`).join("")}</div>
        <div class="why"><span class="badge ${n.grade}">${GRADE_TEXT[n.grade]}</span> ${esc(why)}</div>
        <div class="bar"><i style="width:${(pa ? ph : n.score) * 100}%;background:var(--info)"></i><i style="width:${pa * 100}%;background:var(--accent)"></i></div>
      </a>`;
    }).join("")}`;
}

function noRoute(d) {
  const c = S.meta.counts;
  const missing = [];
  if (d.sparse) missing.push(`Only ${plural(d.phenotypes.length, "symptom")} recorded in HPO for this disease — too few to compare reliably.`);
  if (!d.has_pathway) missing.push(`${d.genes.map((g) => g.symbol).join(", ")} has no curated Reactome pathway, so mechanistic overlap could not be tested.`);
  if (!missing.length) missing.push("Symptoms and pathway are recorded, but no other disease overlaps enough to pass the atlas threshold. This disease may be mechanistically distinct.");
  return `<h2>No supported connection — yet</h2>
    <div class="note stop">The atlas found no disease that overlaps enough to call it a lead. That is a finding, not a failure: here is what was searched and what would change it.</div>
    <h2>What was searched</h2>
    <p class="small muted">${c.diseases.toLocaleString()} monogenic diseases, ${c.phenotype_annotations.toLocaleString()} symptom annotations, ${c.pathways.toLocaleString()} pathways. Links below a similarity of ${S.meta.params.min_score} are not shown.</p>
    <h2>What is missing</h2>
    ${missing.map((m) => `<div class="note warn">${esc(m)}</div>`).join("")}
    <h2>The next question to test</h2>
    <ol class="steps">
      <li>Ask your clinical team to record each patient's symptoms as HPO terms (a structured checklist takes one visit). Five to ten well-described patients are enough to re-run the comparison.</li>
      <li>Ask a researcher which cellular process ${d.genes.map((g) => esc(g.symbol)).join(", ")} belongs to; a functional study or a Reactome curation request would place it on the map.</li>
      <li>Add what your families already know below. It appears immediately, marked unverified.</li>
    </ol>
    ${contribForm(d)}`;
}

function effectBlock(eff) {
  if (!eff) return "";
  const cls = eff.direction === "mixed" ? "warn" : eff.direction === "unknown" ? "info" : "ok";
  return `<div class="note ${cls}"><strong>How the variants act: ${esc(eff.label)}</strong>${eff.dominant_negative ? " · dominant-negative effects also reported" : ""}
    ${eff.signals.map((s) => `<div class="small">${esc(s.text)} <span class="badge ${s.kind}">${s.kind}</span> ${link(s.url, s.source)}</div>`).join("")}
    ${Object.entries(eff.literature).filter(([, v]) => v.length).map(([k, v]) => `<div class="small">${esc(k.replace(/_/g, " "))}: ${v.slice(0, 5).map((p) => refLink("PMID:" + p)).join(", ")}</div>`).join("")}
    ${eff.direction === "unknown" ? `<div class="small muted">No curated dosage record and too few explicit statements in the literature searched.</div>` : ""}</div>`;
}

function tabBiology(d, e) {
  const inf = d.phenotypes.filter((p) => p.specificity === "informative"), rest = d.phenotypes.filter((p) => p.specificity !== "informative");
  const chip = (p) => `<a class="chip ${p.specificity}" href="#e/phenotype/${p.hp}" title="${esc(p.name)} · ${p.freq_raw ? "frequency " + esc(p.freq_raw) + " · " : ""}${esc(p.ev_label)} · ${esc(p.refs.join(", "))}">${esc(lay(p))}</a>`;
  const claims = e && e.pubmed ? e.pubmed.claims.filter((c) => c.kind === "variant_effect").slice(0, 4) : [];
  return `<h2>Mechanism</h2>
    ${e ? (e.error ? `<div class="note stop">Live evidence failed: ${esc(e.error)}</div>` : effectBlock(e.effect)) : `<div class="loading">Reading ClinVar and PubMed</div>`}
    ${claims.map((c) => `<blockquote>“${esc(c.quote)}” — ${link(c.url, "PMID " + c.pmid)} (${esc(c.year)}) <span class="badge ${c.method === "llm" ? "observed" : "unverified"}">${c.method === "llm" ? "AI-extracted, quote verified" : "pattern match"}</span></blockquote>`).join("")}
    ${d.genes.map((g) => `
      <div class="card"><div class="title">${link(g.url, g.symbol)}</div>
        ${g.clingen ? `<div class="meta">ClinGen: ${esc(g.clingen.haploinsufficiency)} (${esc(g.clingen.date)}) ${link(g.clingen.url, "record")}</div>` : `<div class="meta">No ClinGen dosage curation.</div>`}
        ${g.pathways.length ? `<div class="chips">${g.pathways.slice(0, 8).map((p) => `<a class="chip" href="#e/mechanism/${p.id}" title="${p.n_genes} genes · Reactome ${p.id} · evidence ${esc(p.ev)}">${esc(p.name)}</a>`).join("")}</div>`
          : `<div class="meta">No curated Reactome pathway — mechanism links cannot be tested for this gene yet.</div>`}
        ${g.other_diseases.length ? `<div class="meta">Same gene, other diseases: ${g.other_diseases.map((o) => `<a href="${diseaseHref(o.id)}">${esc(o.name)}</a>`).join("; ")}</div>` : ""}
      </div>`).join("")}
    <h2>Unusually informative symptoms <span class="muted small">· seen in fewer than 2% of diseases</span></h2>
    <div class="chips">${inf.slice(0, 24).map(chip).join("") || `<span class="muted small">None recorded.</span>`}</div>
    <h2>Common symptoms <span class="muted small">· shared with many diseases, weak evidence alone</span></h2>
    <div class="chips">${rest.slice(0, 24).map(chip).join("")}</div>
    ${d.excluded.length ? `<p class="small muted">Explicitly excluded: ${d.excluded.map((x) => esc(x.name)).join(", ")}</p>` : ""}
    <details><summary>All ${d.phenotypes.length} symptoms with sources</summary><div>
      <table><tr><th>Symptom</th><th>Frequency</th><th>Evidence</th><th>Reference</th><th>Curated</th></tr>
      ${d.phenotypes.map((p) => `<tr><td>${link(p.url, p.name)}</td><td>${esc(p.freq_raw.startsWith("HP:") ? Math.round(p.freq * 100) + "%" : p.freq_raw)}</td><td>${esc(p.ev)}</td><td>${p.refs.map(refLink).join(", ")}</td><td>${esc(p.date)}</td></tr>`).join("")}
      </table></div></details>`;
}

function studyCard(s) {
  return `<div class="card"><div class="title">${link(s.url, s.title)}</div>
    <div class="meta">${esc(s.kind)} · ${esc(s.nct)} · ${esc(s.status.replace(/_/g, " ").toLowerCase())}${s.enrollment ? ` · n=${s.enrollment}` : ""}${s.start ? ` · since ${esc(s.start.slice(0, 4))}` : ""}${s.phase ? ` · ${esc(s.phase)}` : ""}</div>
    <div class="meta">Sponsor: ${esc(s.sponsor)}${s.officials.length ? ` · ${s.officials.slice(0, 2).map((o) => esc(o.name)).join(", ")}` : ""}</div>
    ${s.interventions.length ? `<div class="meta">Intervention: ${s.interventions.map((i) => esc(i.name)).join(", ")}</div>` : ""}
    ${s.outcomes.length ? `<div class="meta">Primary outcome: ${esc(s.outcomes[0])}</div>` : ""}</div>`;
}
const orgCard = (o) => `<div class="card"><div class="title">${link(o.url, o.name)}</div>
  <div class="meta">${o.source === "curated" ? `Matched on ${esc(o.matched_on)} · website checked ${esc(o.verified)}` : `${esc(o.source)} (${esc(o.via)}) — not independently verified`}</div></div>`;

function contribForm(d) {
  return `<h2>Add what your community knows</h2>
    ${d.contributions.map((c) => `<div class="card"><div class="meta"><span class="badge unverified">unverified · ${esc(c.kind)}</span> ${esc(c.date)}${c.author ? " · " + esc(c.author) : ""}</div>${esc(c.text)}${c.source ? `<div class="meta">Source: ${esc(c.source)}</div>` : ""}</div>`).join("")}
    <form class="contrib" data-disease="${d.id}">
      <select name="kind"><option value="phenotype">A symptom our patients have</option><option value="asset">A registry, study, model or biobank</option><option value="group">A patient group</option><option value="correction">A correction</option></select>
      <textarea name="text" rows="2" required placeholder="What should the atlas know?"></textarea>
      <input name="source" placeholder="Source: link, PMID or “family survey, n=12”">
      <input name="author" placeholder="Your name or organisation (optional)">
      <button class="cta" type="submit">Contribute evidence</button>
      <span class="small muted">Shown immediately as unverified; it never changes the similarity scores until a curator confirms it.</span>
    </form>`;
}
panel.addEventListener("submit", async (ev) => {
  const f = ev.target.closest("form.contrib");
  if (!f) return;
  ev.preventDefault();
  const body = Object.fromEntries(new FormData(f)); body.disease = f.dataset.disease;
  const r = await fetch("/api/contribute", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (r.ok) { S.detail.contributions.push(await r.json()); renderDisease(); }
});

function tabCommunity(d, e) {
  if (!e) return `<div class="loading">Searching ClinicalTrials.gov, NIH RePORTER, PubMed and patient-group directories</div>`;
  if (e.error) return `<div class="note stop">Live evidence failed: ${esc(e.error)}</div>`;
  const specific = e.trials.studies.filter((s) => s.specific);
  const reusable = specific.filter((s) => s.type !== "INTERVENTIONAL"), trials = specific.filter((s) => s.type === "INTERVENTIONAL");
  const related = d.neighbors.filter((n) => n.orgs && n.orgs.length && !n.same_gene).slice(0, 4);
  const exact = e.organizations.some((o) => o.scope === "gene" || o.source !== "curated");
  const assets = {};
  for (const c of e.pubmed.claims) if (c.kind === "asset") (assets[c.asset_type] = assets[c.asset_type] || []).push(c);
  return `${e.errors.length ? `<div class="note warn">Some sources did not answer (${esc(e.errors.join(", "))}); results may be incomplete.</div>` : ""}
    <h2>Patient groups</h2>
    ${e.organizations.map(orgCard).join("")}
    ${exact ? "" : `<div class="note ${e.organizations.length ? "warn" : "stop"}"><strong>No patient group found for this exact diagnosis.</strong> Searched ${S.orgs} curated organisations and every sponsor of ${e.trials.count} registered studies.</div>
      ${related.length ? `<p>Closest related communities:</p>${related.map((n) => `<div class="card"><div class="title">${n.orgs.map(esc).join(", ")}</div><div class="meta">works on <a href="#c/${d.id}/${n.id}">${esc(n.name)}</a> (${n.genes.map(esc).join(", ")}) — <span class="badge ${n.grade}">${GRADE_TEXT[n.grade]}</span> Open the connection to see what is shared.</div></div>`).join("")}` : ""}`}
    <h2>${exact ? "Registries your families can join" : "How to help build the missing one"}</h2>
    ${e.registries.map((r) => `<div class="card"><div class="title">${link(r.url, r.name)}</div><div class="meta">${esc(r.what)}</div></div>`).join("")}
    <p class="small muted">Directories to check: ${e.directories.map((x) => link(x.url, x.name)).join(" · ")}</p>
    <h2>Registries and natural-history studies <span class="muted small">· ${reusable.length}</span></h2>
    ${reusable.map(studyCard).join("") || `<p class="muted small">None registered on ClinicalTrials.gov for “${esc(e.trials.query)}”.</p>`}
    <h2>Interventional trials <span class="muted small">· ${trials.length}</span></h2>
    ${trials.slice(0, 6).map(studyCard).join("") || `<p class="muted small">None registered.</p>`}
    <h2>NIH-funded projects <span class="muted small">· ${e.grants.count} in ${e.grants.years.join("–")}</span></h2>
    ${e.grants.grants.slice(0, 6).map((g) => `<div class="card"><div class="title">${link(g.url, g.title)}</div><div class="meta">${esc(g.num)} · ${g.pis.map((p) => esc(p.first + " " + p.last)).join(", ")} · ${esc(g.org)} · ${esc(g.ic)} FY${g.year}${g.amount ? " · $" + g.amount.toLocaleString() : ""}</div></div>`).join("") || `<p class="muted small">No active NIH project mentions ${esc(e.grants.query)} — a funding gap.</p>`}
    <h2>Research assets reported in papers</h2>
    ${Object.entries(assets).map(([k, v]) => `<p><strong>${esc(k.replace(/_/g, " "))}</strong></p>${v.slice(0, 2).map((c) => `<blockquote>“${esc(c.quote)}” — ${link(c.url, "PMID " + c.pmid)} (${esc(c.year)})</blockquote>`).join("")}`).join("") || `<p class="muted small">No models, biomarkers or registries mentioned in the ${e.pubmed.papers.length} papers read.</p>`}
    <p class="small muted">Fetched ${esc(e.fetched)} · PubMed query ${link(e.pubmed.url, e.pubmed.query)} (${e.pubmed.count} papers) · ${link(e.trials.url, "ClinicalTrials.gov query")} · claims extracted by ${e.pubmed.claim_method === "llm" ? "OpenAI, quotes verified against the abstract" : "pattern matching"}</p>
    ${contribForm(d)}`;
}

function tabPeople(d, e) {
  if (!e) return `<div class="loading">Reading author lists, trial officials and grant investigators</div>`;
  if (e.error) return `<div class="note stop">Live evidence failed: ${esc(e.error)}</div>`;
  const net = S.network && S.network.id === d.id ? S.network : null;
  return `<p class="small muted" style="margin-top:12px">Ranked by senior authorship, trial leadership and NIH funding on ${d.genes.map((g) => esc(g.symbol)).join(", ")}. Names are matched as written; verify identity before contacting.</p>
    <table><tr><th>Investigator</th><th>Papers</th><th>Studies</th><th>Grants</th></tr>
    ${e.investigators.slice(0, 15).map((p) => `<tr><td><strong>${esc(p.name)}</strong><div class="muted">${esc(p.affiliation.slice(0, 90))}</div></td>
      <td>${p.papers.length ? link("https://pubmed.ncbi.nlm.nih.gov/?term=" + p.papers.slice(0, 20).join("+"), p.papers.length) : ""}</td>
      <td>${p.trials.map((t) => link("https://clinicaltrials.gov/study/" + t, t)).join(" ")}</td><td>${p.grants.length || ""}</td></tr>`).join("")}
    </table>
    ${e.investigators.length ? "" : `<p class="muted">No investigator with a senior-author paper, study or grant was found.</p>`}
    <h2>Who works on this mechanism under other gene names</h2>
    ${net ? networkBlock(net) : `<p class="small muted">Reads the literature, studies and grants of the closest diseases and finds people and sponsors who appear in more than one community.</p>
      <button class="cta" data-network="${d.id}">Scan the constellation</button>`}`;
}
function networkBlock(n) {
  if (n.loading) return `<div class="loading">Reading PubMed, ClinicalTrials.gov and NIH RePORTER for the closest diseases</div>`;
  return `${n.bridges.length ? n.bridges.map((b) => `<div class="card"><div class="title">${esc(b.name)}</div><div class="meta">${esc(b.affiliation.slice(0, 100))}</div>
      <div class="meta">Appears in: ${b.diseases.map((x) => `<a href="${diseaseHref(x.id)}">${esc(x.genes.join("/"))}</a>`).join(", ")}</div></div>`).join("")
    : `<p class="muted">No investigator appears in more than one of these communities — the people working on this mechanism are not yet connected.</p>`}
    <table><tr><th>Disease</th><th>Lead investigator</th><th>Studies</th><th>Groups</th></tr>
    ${n.diseases.map((x) => `<tr><td><a href="${diseaseHref(x.id)}">${esc(x.name)}</a> <span class="muted">${esc(x.genes.join(", "))}</span></td><td>${esc(x.lead || "—")}</td><td>${x.studies}</td><td>${esc(x.orgs.join(", ") || "—")}</td></tr>`).join("")}</table>`;
}
panel.addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-network]");
  if (!b) return;
  const id = b.dataset.network;
  S.network = { id, loading: true }; renderDisease();
  try { S.network = { id, ...(await api(`/api/disease/${id}/network`)) }; } catch (err) { S.network = { id, bridges: [], diseases: [] }; }
  if (S.selected === id && !S.conn) renderDisease();
});

/* ------------------------------------------------------------------ connection */
async function openConnection(a, b) {
  if (S.selected !== a) await openDisease(a);
  S.conn = b; dirty = true; focus([a, b], 10);
  const A = S.byId.get(a), B = S.byId.get(b);
  panel.innerHTML = `<a class="back" href="${diseaseHref(a)}">← ${esc(A.name)}</a>
    <h1>${esc(A.name)} <span class="muted">↔</span> ${esc(B.name)}</h1>
    <div class="loading">Reading both diseases' papers, studies and grants, and checking whether anyone has connected them before</div>`;
  let c;
  try { c = await api(`/api/connection?a=${a}&b=${b}&audience=${MARIA.audience}`); }
  catch (err) { panel.querySelector(".loading").outerHTML = `<div class="note stop">Could not build this connection: ${esc(err.message)}</div>`; return; }
  if (S.conn !== b || S.selected !== a) return;
  S.connection = c;
  renderConnection(c);
}

const evChip = (id) => `<button class="ev" data-e="${id}">${id}</button>`;
const cite = (text) => esc(text).replace(/\[(E\d+)\]/g, (_, id) => evChip(id));

function renderConnection(c) {
  const A = c.a, B = c.b, pw = c.path.pathways[0];
  const mid = pw ? `<div class="n mid"><small>shared pathway</small>${esc(pw.name)}</div>`
    : `<div class="n mid"><small>shared symptoms</small>${c.shared_phenotypes.slice(0, 2).map((p) => esc(p.name)).join(", ") || "none"}</div>`;
  const midE = pw ? pw.e : (c.shared_phenotypes[0] || {}).e;
  const pchip = (p) => `<span class="chip ${p.specificity}" title="${p.exact ? "Recorded in both" : esc(A.name + ": " + p.a.name + " · " + B.name + ": " + p.b.name)} · ${p.n} diseases">${esc(lay(p))} ${p.e ? evChip(p.e) : ""}</span>`;
  const assetList = (as, name) => {
    const studies = as.reusable.concat(as.interventional).slice(0, 4);
    return `<p class="label" style="margin-top:12px">${esc(name)}</p>
      ${as.organizations.slice(0, 3).map(orgCard).join("")}${studies.map(studyCard).join("")}
      ${Object.entries(as.literature).slice(0, 3).map(([k, v]) => `<div class="small">${esc(k.replace(/_/g, " "))} reported: ${v.map((x) => link(x.url, "PMID " + x.pmid)).join(", ")}</div>`).join("")}
      ${as.grant_count ? `<div class="small">${plural(as.grant_count, "NIH project")}: ${as.grants.slice(0, 2).map((g) => link(g.url, g.num)).join(", ")}</div>` : ""}
      ${!as.organizations.length && !studies.length && !as.grant_count ? `<p class="small muted">No group, study or NIH project found — nothing to reuse here yet.</p>` : ""}`;
  };
  const nReuse = c.assets_b.reusable.length + c.assets_b.interventional.length + c.assets_b.organizations.length;
  panel.innerHTML = `
    <a class="back" href="${diseaseHref(A.id)}">← ${esc(A.name)}</a>
    <h1>${esc(A.name)} <span class="muted">↔</span> <a href="${diseaseHref(B.id)}" style="color:inherit">${esc(B.name)}</a></h1>
    <p style="margin-top:10px"><span class="badge ${c.verdict.grade}">${GRADE_TEXT[c.verdict.grade]}</span> <span class="muted">${esc(c.verdict.why)}</span></p>
    ${c.verdict.novelty ? `<p>${esc(c.verdict.novelty)} ${c.comention ? link(c.comention.url, "See search") : ""}</p>` : ""}
    <div class="path">
      <div class="n"><small>disease</small>${esc(A.name)}</div>
      <div class="e">${evChip(c.path.a_gene[0].e)}<span>caused by variants in</span></div>
      <div class="n"><small>gene</small><b style="color:var(--accent)">${esc(A.genes.join(", "))}</b></div>
      <div class="e">${midE ? evChip(midE) : ""}<span>${pw ? "takes part in" : "patients show"}</span></div>
      ${mid}
      <div class="e">${midE ? evChip(midE) : ""}<span>${pw ? "also involves" : "also seen with"}</span></div>
      <div class="n"><small>gene</small><b style="color:var(--accent)">${esc(B.genes.join(", "))}</b></div>
      <div class="e">${evChip(c.path.b_gene[0].e)}<span>whose variants cause</span></div>
      <div class="n"><small>disease</small>${esc(B.name)}</div>
    </div>
    <div id="evcard"></div>
    <p class="small muted">Each numbered tag opens the source behind that step.</p>
    ${c.narrative.split("\n\n").map((p) => `<p>${cite(p)}</p>`).join("")}
    <p class="small muted">${c.narrative_by === "openai" ? "Explanation written by OpenAI from the evidence ledger; citations checked against it." : "Explanation assembled from the evidence ledger (template mode)."}</p>

    <details open><summary>Why they are connected <span>${c.shared_pathways.length} pathways · ${c.shared_phenotypes.length} symptoms</span></summary><div>
      ${c.path.pathways.length ? `<p class="label">Shared pathways (observed)</p>${c.path.pathways.map((p) => `<div class="small">${link(p.url, p.name)} <span class="muted">· ${p.n_genes} genes</span> ${evChip(p.e)}</div>`).join("")}` : `<div class="note warn">No shared curated pathway.</div>`}
      <p class="label" style="margin-top:12px">Shared symptoms (observed)</p>
      <div class="chips">${c.shared_phenotypes.map(pchip).join("") || `<span class="muted small">None above the generic level.</span>`}</div>
      <p class="small muted">Green = unusually informative (fewer than 2% of diseases). Grey = common, weak on its own.</p>
    </div></details>

    <details open><summary>What must be checked before joining forces <span>${c.checks.length + c.contradictions.length} items</span></summary><div>
      ${c.checks.map((x) => `<div class="note ${x.level}">${esc(x.text)}</div>`).join("")}
      ${c.contradictions.map((x) => `<div class="note stop"><strong>Contradictory evidence: ${esc(x.title)}</strong><div class="small">${esc(x.detail)}</div>
        ${x.quotes.map((qt) => `<blockquote><span class="badge ${qt.effect === "gain_of_function" ? "inferred" : "observed"}">${esc(qt.effect.replace(/_/g, " "))}</span> “${esc(qt.quote)}” — ${link(qt.url, "PMID " + qt.pmid)} (${esc(qt.year)})</blockquote>`).join("")}</div>`).join("")}
      <p class="label" style="margin-top:12px">How the variants act</p>
      <p class="small"><strong>${esc(A.genes.join("/"))}</strong></p>${effectBlock(c.effects.a)}
      <p class="small"><strong>${esc(B.genes.join("/"))}</strong></p>${effectBlock(c.effects.b)}
      ${c.only_a.length || c.only_b.length ? `<p class="label" style="margin-top:12px">What differs</p>
        <p class="small">Only in ${esc(A.name)}: ${c.only_a.map((p) => esc(lay(p))).join(", ") || "—"}</p>
        <p class="small">Only in ${esc(B.name)}: ${c.only_b.map((p) => esc(lay(p))).join(", ") || "—"}</p>` : ""}
    </div></details>

    <details ${nReuse ? "open" : ""}><summary>What already exists <span>${nReuse} from the other community</span></summary><div>
      ${assetList(c.assets_b, B.name)}${assetList(c.assets_a, A.name)}
    </div></details>

    <details ${c.people.length || c.sponsors.length ? "open" : ""}><summary>Who already bridges both <span>${c.people.length} people · ${c.sponsors.length} sponsors</span></summary><div>
      ${c.people.map((p) => `<div class="card"><div class="title">${esc(p.name)}</div><div class="meta">${esc(p.affiliation.slice(0, 110))}</div>
        <div class="meta">${esc(A.genes.join("/"))}: ${p.a.papers.map((x) => refLink("PMID:" + x)).join(", ")} ${p.a.trials.join(" ")} · ${esc(B.genes.join("/"))}: ${p.b.papers.map((x) => refLink("PMID:" + x)).join(", ")} ${p.b.trials.join(" ")}</div></div>`).join("")}
      ${c.sponsors.map((s) => `<div class="small">${esc(s.name)} sponsors studies in both (${esc(s.a)}, ${esc(s.b)})</div>`).join("")}
      ${!c.people.length && !c.sponsors.length ? `<p class="small muted">No investigator, sponsor or collaborator appears in both communities' papers, studies or grants. The two fields are not talking yet.</p>` : `<p class="small muted">Name-level matches; verify identity.</p>`}
    </div></details>

    <details open><summary>What to do this week</summary><div>
      <ol class="steps">${c.actions.map((x) => `<li>${esc(x.text)} ${x.url ? link(x.url, "Open") : ""}</li>`).join("")}</ol>
      <div class="card"><div class="title">The next experiment</div>
        <p><strong>Question.</strong> ${esc(c.experiment.question)}</p><p><strong>How.</strong> ${esc(c.experiment.design)}</p>
        <p class="muted"><strong>What it decides.</strong> ${esc(c.experiment.decides)}</p></div>
      <button class="cta" id="openbrief">Open the sourced proposal</button>
    </div></details>

    <details><summary>The 10× case <span>shared natural-history baseline</span></summary><div>${tenX()}</div></details>

    <details><summary>Evidence ledger <span>${c.evidence.length} items</span></summary><div>
      <table><tr><th></th><th>Statement</th><th>Type</th><th>Source</th></tr>
      ${c.evidence.map((e) => `<tr id="row-${e.id}"><td>${e.id}</td><td>${esc(e.text)}<div class="muted">${esc(e.relation)}</div></td>
        <td><span class="badge ${e.kind}">${e.kind}</span><div class="muted">${Math.round(e.confidence * 100)}%${e.date ? " · " + esc(e.date) : ""}</div></td><td>${link(e.url, e.source)}</td></tr>`).join("")}
      </table></div></details>

    <details><summary>Search coverage <span>fetched ${esc(c.coverage.fetched)}</span></summary><div>
      <ul class="small">${c.coverage.searched.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
      ${c.coverage.errors.length ? `<div class="note warn">Sources that failed: ${esc(c.coverage.errors.join(", "))}</div>` : ""}
    </div></details>`;
}

function tenX() {
  const seg = (w, c, t) => `<i style="width:${w}%;background:${c}" title="${t}">${t}</i>`;
  return `<p class="small">Milestone: two communities enrolling into one natural-history protocol with shared outcome measures — the baseline any trial needs.</p>
    <div class="timeline">
      <div class="t"><span>Today · ~40 mo</span><div class="track">${seg(22, "#9fb8d8", "find partners")}${seg(38, "#8f9cf7", "build registry")}${seg(25, "#c59bf5", "design protocol")}${seg(15, "#e58fc8", "first enrolment")}</div></div>
      <div class="t"><span>Atlas · ~4 mo</span><div class="track" style="width:10%">${seg(100, "#f6c453", "")}</div></div>
    </div>
    <table>
      <tr><th>Step</th><th>Alone</th><th>With the atlas</th></tr>
      <tr><td>Find a mechanistically related community</td><td>6–12 months of conferences and cold e-mail</td><td>Minutes: ranked, evidence-backed neighbours</td></tr>
      <tr><td>Registry and data model</td><td>12–18 months to fund and build</td><td>Weeks: join the partner's or an open registry</td></tr>
      <tr><td>Protocol and outcome measures</td><td>9–12 months to draft and validate</td><td>4–8 weeks: adapt an existing protocol to the shared symptoms</td></tr>
      <tr><td>First patient enrolled</td><td>3–6 months of site start-up</td><td>4–8 weeks as an amendment at existing sites</td></tr>
    </table>
    <p class="small muted">Assumptions to validate: the partner agrees to share its protocol; outcome measures are valid in both diseases (the shared informative symptoms are the candidates);
      ethics boards accept an amendment rather than a new study; the variant-effect check above passes. Durations are planning estimates, not measured data.</p>`;
}

panel.addEventListener("click", (ev) => {
  const b = ev.target.closest(".ev");
  if (b && S.connection) {
    ev.preventDefault();
    const e = S.connection.evidence.find((x) => x.id === b.dataset.e), card = $("#evcard");
    if (!e || !card) return;
    document.querySelectorAll(".ev.on").forEach((x) => x.classList.remove("on"));
    document.querySelectorAll(`.ev[data-e="${e.id}"]`).forEach((x) => x.classList.add("on"));
    card.innerHTML = `<div class="card"><div class="meta">${e.id} · ${esc(e.relation)}</div><div>${esc(e.text)}</div>
      <div class="meta" style="margin-top:6px"><span class="badge ${e.kind}">${e.kind}</span> confidence<span class="conf"><i style="width:${e.confidence * 100}%"></i></span>${Math.round(e.confidence * 100)}%
      · ${link(e.url, e.source)}${e.date ? " · " + esc(e.date) : ""}</div></div>`;
    if (!b.closest(".path")) card.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  if (ev.target.id === "openbrief") { $("#brief").textContent = S.connection.brief; $("#modal").hidden = false; }
});
$("#close").onclick = () => ($("#modal").hidden = true);
$("#modal").addEventListener("click", (ev) => { if (ev.target.id === "modal") $("#modal").hidden = true; });
$("#copy").onclick = async () => { await navigator.clipboard.writeText(S.connection.brief); $("#copy").textContent = "Copied"; setTimeout(() => ($("#copy").textContent = "Copy"), 1500); };
$("#download").onclick = () => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([S.connection.brief], { type: "text/markdown" }));
  a.download = "proposal.md"; a.click(); URL.revokeObjectURL(a.href);
};

/* ------------------------------------------------------------------ entity + cluster */
function clusterRows(clusters) {
  return clusters.map((c, i) => `
    <details ${i === 0 ? "open" : ""}><summary><span style="color:${color(c.group)};margin:0">●</span> ${esc(c.label)}
      <span>${c.matching} of ${c.size} diseases</span></summary><div>
      ${c.sub ? `<p class="small muted">${esc(c.sub)}</p>` : ""}
      <div class="chips">${c.genes.slice(0, 14).map((g) => `<span class="chip gene" title="${c.haploinsufficient.includes(g) ? "ClinGen: haploinsufficient (loss of one copy causes disease)" : ""}">${esc(g)}${c.haploinsufficient.includes(g) ? " ◐" : ""}</span>`).join("")}</div>
      <p class="small">${c.organizations.length ? "Patient groups: " + c.organizations.map(esc).join(", ") : `<span class="muted">No curated patient group — unmet community need.</span>`}</p>
      ${c.diseases.slice(0, 12).map((d) => `<a class="row" href="${diseaseHref(d.id)}"><span class="name" style="color:var(--text)">${esc(d.name)}</span> <span class="muted small">${esc(d.genes.join(", "))}</span></a>`).join("")}
      ${c.diseases.length > 12 ? `<p class="small muted">and ${c.diseases.length - 12} more — zoom into the map.</p>` : ""}
    </div></details>`).join("");
}
async function openEntity(type, id) {
  panel.innerHTML = `<div class="loading">Searching the atlas</div>`;
  const e = await api(`/api/entity/${type}/${encodeURIComponent(id)}`);
  if (type === "gene" && e.count === 1) { S.resolved = { from: `gene ${id}`, id: e.ids[0] }; location.replace(diseaseHref(e.ids[0])); return; }
  S.selected = null; S.neighbors = []; S.conn = null; S.highlight = new Set(e.ids); dirty = true;
  focus(e.ids, 8);
  panel.innerHTML = `<a class="back" href="#">← Whole atlas</a>
    <p class="label">${esc(e.kind)}</p><h1>${e.url ? link(e.url, e.title) : esc(e.title)}</h1>
    ${e.def ? `<p class="muted">${esc(e.def)}</p>` : ""}
    <p>${esc(e.note)}</p>
    ${e.specificity ? `<p><span class="chip ${e.specificity}">${e.specificity === "informative" ? "Unusually informative symptom" : e.specificity === "broad" ? "Broad symptom — weak evidence alone" : "Moderately specific symptom"}</span></p>` : ""}
    <h2>${plural(e.count, "disease")} across ${plural(e.clusters.length, "constellation")}, ranked</h2>
    <p class="small muted">Highlighted on the map. Open a disease to see its connections.</p>
    ${clusterRows(e.clusters)}`;
}
async function openCluster(cid) {
  panel.innerHTML = `<div class="loading">Opening constellation</div>`;
  const c = await api("/api/cluster/" + encodeURIComponent(cid));
  const ids = c.members.map((m) => m.id);
  S.selected = null; S.neighbors = []; S.conn = null; S.highlight = new Set(ids); dirty = true; focus(ids, 10);
  panel.innerHTML = `<a class="back" href="#">← Whole atlas</a>
    <p class="label">Constellation</p><h1>${esc(c.label)}</h1>
    <p class="muted">${plural(c.size, "disease")} that sit together because they share the features below — not because of their names.</p>
    ${c.pathways.length ? `<h2>Pathways they share</h2><div class="chips">${c.pathways.map((p) => `<a class="chip" href="#e/mechanism/${p.id}">${esc(p.name)} · ${Math.round(p.frac * 100)}%</a>`).join("")}</div>` : ""}
    <h2>Symptoms they share</h2><div class="chips">${c.phenotypes.map((p) => `<a class="chip" href="#e/phenotype/${p.hp}">${esc(p.name)} · ${Math.round(p.frac * 100)}%</a>`).join("")}</div>
    <h2>Members</h2>
    ${c.members.map((d) => `<a class="row" href="${diseaseHref(d.id)}"><span class="name" style="color:var(--text)">${esc(d.name)}</span> <span class="muted small">${esc(d.genes.join(", "))}</span></a>`).join("")}`;
}

/* ------------------------------------------------------------------ router */
async function route() {
  const parts = decodeURIComponent(location.hash.slice(1)).split("/");
  document.querySelectorAll(".group.on").forEach((x) => x.classList.remove("on"));
  try {
    if (parts[0] === "d" && S.byId.has(parts[1])) { S.conn = null; await openDisease(parts[1]); }
    else if (parts[0] === "c" && S.byId.has(parts[1]) && S.byId.has(parts[2])) await openConnection(parts[1], parts[2]);
    else if (parts[0] === "e") await openEntity(parts[1], parts.slice(2).join("/"));
    else if (parts[0] === "k") await openCluster(parts.slice(1).join("/"));
    else { S.selected = null; S.neighbors = []; S.highlight = null; S.conn = null; dirty = true; renderHome(); }
  } catch (err) {
    panel.innerHTML = `<a class="back" href="#">← Whole atlas</a><div class="note stop">${esc(err.message)}</div>`;
  }
  panel.scrollTop = 0;
}
window.addEventListener("hashchange", route);
window.addEventListener("resize", resize);

(async function init() {
  resize();
  panel.innerHTML = `<div class="loading">Loading the atlas</div>`;
  const a = await api("/api/atlas");
  S.meta = a.meta; S.llm = a.llm; S.orgs = a.organizations; edges = a.edges;
  S.points = a.points.map(([id, name, x, y, group, cluster, genes, deg]) => ({ id, name, x, y, group, cluster, genes, deg }));
  S.points.forEach((p) => S.byId.set(p.id, p));
  S.groups = a.groups.map((g) => {
    const pts = S.points.filter((p) => p.group === g.id);
    return { ...g, short: g.label.split(" · ")[0], cx: d3.median(pts, (p) => p.x), cy: d3.median(pts, (p) => p.y) };
  });
  quad = d3.quadtree(S.points, (p) => p.x, (p) => p.y);
  renderLegend(); draw(); route();
})();

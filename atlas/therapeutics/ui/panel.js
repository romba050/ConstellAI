"use strict";
const form = document.getElementById("context-form");
const output = document.getElementById("results");
const status = document.getElementById("status");
let busy = false;
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const direction = value => value === 1 ? "↑ increase" : value === -1 ? "↓ reduce" : "Unknown";
const readable = value => esc(String(value ?? "unknown").replaceAll("_", " "));
const number = value => value === null || value === undefined ? "Unknown" : esc(value.toFixed(2));
function link(url, label) {
  try { if (new URL(url).protocol !== "https:") return esc(label); }
  catch { return esc(label); }
  return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
}
const list = rows => `<ul>${rows.map(row => `<li>${esc(row)}</li>`).join("")}</ul>`;
function source(source) {
  return `<article class="source">
    <h4>${link(source.source_url, source.title || source.source)}</h4>
    <p class="meta">${esc(source.pmid ? `PMID ${source.pmid}` : source.source_family)} · ${esc(source.journal || source.source_family)} · ${esc(source.publication_year || source.publication_date || "Year unavailable")}</p>
    ${source.doi ? `<p>DOI: ${esc(source.doi)}</p>` : ""}
    <p><strong>Evidence:</strong> ${readable(source.evidence_type)} · ${readable(source.claim_kind)}</p>
    <p><strong>Study design:</strong> ${esc(source.study_design)}</p>
    <p><strong>Sample size:</strong> ${esc(source.sample_size?.reported || "Not available / not applicable to this source.")}</p>
    <p><strong>Extracted claim:</strong> ${esc(source.extracted_claim)}</p>
    <p class="muted"><strong>Uncertainty:</strong> ${esc(source.uncertainty)}</p>
    <details><summary>Bibliography and provenance</summary>
      <p>${esc((source.authors || []).join(", ") || "No author list supplied.")}</p>
      <p>Publication type: ${esc((source.publication_types || []).join(", ") || "Not available")}</p>
      <p>Retrieved ${esc(source.retrieved_at)} · ${readable(source.verification_status)}</p>
    </details>
  </article>`;
}
function edge(effect) {
  return `<div class="edge"><div class="label">${readable(effect.relation)} → ${esc(effect.label)} · ${direction(effect.direction)}</div>
    <p>${esc(effect.context)}</p><code>${esc(effect.id)}</code>
    <p>${effect.sources.map(s => link(s.source_url, s.pmid ? `PMID ${s.pmid}` : s.source_family)).join(" · ") || "Provenance unknown"}</p></div>`;
}
function card(row) {
  const intervention = row.candidate_intervention;
  const coverage = row.mechanistic_coverage;
  const coverageText = coverage.value === null ? "Unknown" : `${coverage.covered_targets.length}/${coverage.axis_count}`;
  const edges = row.direction_match.items.flatMap(item => item.edges).concat(row.spillover.items.flatMap(item => item.edges));
  const refs = new Map();
  for (const effect of edges) for (const s of effect.sources) refs.set(s.id, s);
  return `<article class="card" data-candidate="${esc(intervention.id)}">
    <div class="card-head"><h3>${esc(intervention.name)}</h3><span class="tag">${row.rank ? `Provisional rank ${row.rank}` : readable(row.ranking_status)}</span></div>
    <p class="summary">${readable(intervention.kind)} · ${esc(intervention.summary)}</p>
    <div class="metrics">
      <div class="metric"><small>Direction match</small><strong>${number(row.direction_match.value)}</strong><span>+1 desired · −1 opposed</span></div>
      <div class="metric"><small>Modeled coverage</small><strong>${esc(coverageText)}</strong><span>curated molecular axes</span></div>
      <div class="metric"><small>Mechanistic fit</small><strong>${number(row.mechanistic_fit.score)}</strong><span>known-effect heuristic</span></div>
      <div class="metric"><small>Listed spillover</small><strong>${row.spillover.known_count}</strong><span>inventory incomplete</span></div>
    </div>
    <p class="scope">${esc(coverage.scope)} Fit scores describe the listed effects, with no clinical probability attached.</p>
    <div class="dimension"><strong>Wrong-direction effects</strong><p>${row.wrong_direction_effects.items.length ? esc(row.wrong_direction_effects.items.map(item => item.label).join(", ")) : row.direction_match.value === null ? "Unknown / insufficient direction evidence." : "None in the reviewed causal-axis effects."} · penalty ${number(row.wrong_direction_effects.penalty)}</p></div>
    <div class="dimension"><strong>Evidence strength</strong><p>${row.evidence_strength.types.length ? row.evidence_strength.types.map(readable).join(" · ") : "Unknown"}. Clinical benefit is not established by this pilot.</p></div>
    <div class="dimension"><strong>Spillover comparison</strong><p>${row.spillover.items.map(item => `${esc(item.label)} · ${direction(item.direction)}`).join("<br>") || "No sourced spillover listed; selectivity remains unknown."}</p><p class="muted">Listed penalty ${number(row.spillover.listed_penalty)}. The off-target inventory is incomplete.</p></div>
    <details><summary>Inspect sourced relationships and evidence (${refs.size} sources)</summary>${edges.map(edge).join("")}${[...refs.values()].map(source).join("")}</details>
    <details><summary>Uncertainty and remaining deviation</summary>${list(row.uncertainty.items)}${list(row.remaining_deviation.targets.map(t => `${t.label}: ${t.reason.replaceAll("_", " ")}`))}</details>
  </article>`;
}
function render(data, responseUrl) {
  const primary = data.candidates.find(row => row.rank === 1);
  const remaining = primary?.remaining_deviation || {targets: data.signed_targets.map(t => ({label: t.label, reason: "unknown directional coverage"})), unresolved_biology: data.unresolved};
  const warnings = data.candidates.flatMap(row => row.clinical_safety_evidence.warnings.map(warning => ({...warning, intervention: row.candidate_intervention.name})));
  const targets = data.signed_targets.map(t => `${esc(t.label)} deviation ${direction(t.disease_direction)} → desired ${direction(t.desired_direction)}`).join("<br>");
  output.innerHTML = `<section class="context">
      <h2>${esc(data.disease.name)} <span class="tag">${readable(data.status)}</span></h2>
      <p class="signature">${targets || "Signed target representation unknown"}</p>
      <p>${esc(data.context.scope)}</p>
      ${data.context.variant ? `<p class="amber">Variant ${esc(data.context.variant)}: functional direction unknown; ranking withheld.</p>` : ""}
      ${data.uncertainty.length ? `<p class="amber">${data.uncertainty.map(esc).join(" ")}</p>` : ""}
      <details><summary>Inspect disease mechanism and assumptions</summary>${list(data.context.assumptions)}${data.signed_targets.flatMap(t => t.sources).concat(data.context.variant_sources || []).filter((s,i,all) => all.findIndex(x => x.id === s.id) === i).map(source).join("")}</details>
    </section>
    <div class="layout"><section aria-label="Candidate interventions">
      <h2>Candidate interventions</h2>
      ${data.candidates.length ? data.candidates.map(card).join("") : `<div class="empty"><h3>Therapeutic direction unknown</h3><p>No sourced intervention matches are curated here. The existing ConstellAI graph and evidence remain available.</p><a href="/#d/${encodeURIComponent(data.disease.id)}">Open this disease in the atlas ↗</a></div>`}
    </section><aside>
      <section class="card risk"><h2>Clinical safety evidence</h2><p class="amber">Not established for this disease</p><p>Mechanistic fit does not establish clinical benefit, tolerability or combination suitability.</p>
      ${warnings.length ? warnings.map(w => `<p><strong>${esc(w.intervention)} · ${esc(w.domain)}</strong><br>${esc(w.label)}<br>${w.sources.map(s => link(s.source_url, s.source_family)).join(" · ")}</p>`).join("") : "<p>No disease-context clinical risk assessment is available.</p>"}
      <p class="muted">Drug interactions: unknown. No dose or treatment recommendation is generated.</p></section>
      <section class="card"><h2>Remaining deviation</h2>
      <p>${remaining.targets.length ? "Molecular axes without modeled coverage:" : "The listed UBE3A axis has directional coverage; whole-disease rescue remains unresolved."}</p>
      ${list(remaining.targets.map(t => `${t.label}: ${t.reason.replaceAll("_", " ")}`))}<h4>Biology still unresolved</h4>${list(remaining.unresolved_biology)}</section>
      <section class="card"><h2>Complementary / add-on logic</h2><p>${readable(data.complementary.status)}</p><p>${esc(data.complementary.reason)}</p>
      ${data.complementary.evaluated.map(c => `<div class="dimension"><strong>${esc(c.candidate_intervention.name)}</strong><p>${esc(c.reason)}</p><p>Remaining-axis gain ${number(c.closure_weight)} · redundancy penalty ${number(c.redundancy_penalty)}</p><p class="muted">${esc(c.uncertainty)} Clinical interaction evidence: unknown.</p></div>`).join("")}</section>
      <section class="card"><h2>Transparent method</h2><p>${esc(data.method.formula)}</p><p class="muted">${esc(data.method.unknown_policy)}</p><details><summary>Read the JSON response</summary><a href="${esc(responseUrl)}" target="_blank" rel="noopener noreferrer">Open therapeutics endpoint ↗</a></details></section>
    </aside></div>`;
}
function apiUrl() {
  const values = new FormData(form);
  const query = new URLSearchParams();
  for (const key of ["mechanism", "variant"]) if (String(values.get(key)).trim()) query.set(key, String(values.get(key)).trim());
  return `/api/disease/${encodeURIComponent(values.get("disease"))}/therapeutics${query.size ? `?${query}` : ""}`;
}
async function evaluate(event) {
  event?.preventDefault();
  if (busy) return;
  const url = apiUrl();
  busy = true;
  output.hidden = true;
  for (const control of form.elements) control.disabled = true;
  status.textContent = "Evaluating reviewed signed relationships…";
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Request failed (${response.status}).`);
    const data = await response.json();
    render(data, url);
    output.hidden = false;
    status.textContent = `${data.disease.id} · ${data.candidates.filter(c => c.rank).length} provisional medicine candidate(s) · ${data.status === "unknown" ? "direction or evidence unknown" : "disease-level research context"}`;
  } catch (error) {
    status.textContent = `Unable to evaluate. ${error.message} Retry when the endpoint is available.`;
  } finally {
    busy = false;
    for (const control of form.elements) control.disabled = false;
  }
}
form.addEventListener("submit", evaluate);
form.addEventListener("input", () => {
  if (!busy) { output.hidden = true; status.textContent = "Inputs changed. Evaluate the mechanism to see the corresponding evidence."; }
});
evaluate();

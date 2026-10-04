"use strict";

(() => {
  const $ = (selector) => document.querySelector(selector);
  const form = $("#analysis-form");
  const results = $("#analysis-results");
  const status = $("#query-status");
  const errorBox = $("#query-error");
  const analyzeButton = $("#analyze-button");
  const diseaseInput = $("#disease");
  const fixtureMode = new URLSearchParams(location.search).get("data") === "mock";
  const allowedStatuses = new Set(["supported_candidate", "research_hypothesis", "rejected", "insufficient_evidence"]);
  const eligibleStatuses = new Set(["supported_candidate", "research_hypothesis"]);
  const statusLabels = {
    supported_candidate: "Supported research candidate",
    research_hypothesis: "Research hypothesis",
    rejected: "Excluded from ranking",
    insufficient_evidence: "Insufficient evidence",
  };
  const evidenceLabels = {
    human_clinical: "Human clinical evidence",
    human_observational: "Human observational evidence",
    preclinical: "Preclinical evidence",
    mechanistic_inference: "Mechanistic inference",
    regulatory_label: "Regulatory label",
    trial_registry: "Trial registry",
    disease_reference: "Disease reference",
    official_resource: "Official resource",
    unknown: "Evidence not established",
  };
  const roleLabels = {
    mechanism_targeting: "Mechanism-targeting hypothesis",
    symptom_targeting: "Symptom-targeting hypothesis",
    research_tool: "Research tool",
  };
  const assessmentLabels = {
    mechanism_of_action: "Mechanism of action",
    mechanism_alignment: "Mechanism alignment",
    variant_effect_compatibility: "Variant compatibility",
    human_evidence: "Human evidence",
    preclinical_evidence: "Preclinical evidence",
    phenotype_relevance: "Phenotype relevance",
    evidence_quality: "Evidence quality",
    toxicity: "Toxicity",
    organ_burden: "Organ burden",
    drug_interactions: "Drug interactions",
    off_target_spillover: "Off-target effects",
    uncertainty: "Uncertainty",
    toxicity_organ_burden: "Toxicity / organ burden",
  };
  const kindLabels = {
    patient_group: "Patient organisation",
    study: "Study",
    investigator: "Research investigator",
    published_model: "Published research model",
    resource: "Research resource",
  };
  let requestSequence = 0;
  let activeController = null;
  let lastRequest = null;
  let currentAnalysis = null;
  let openaiEnabled = false;
  let sourceIndex = new Map();
  let sourceList = [];
  let searchSequence = 0;
  let searchTimer = null;
  const searchChoices = new Map();

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[character]));
  }

  function safeHref(value) {
    if (typeof value !== "string") return null;
    const href = value.trim();
    if (/^\/atlas(?:[#?]|$)/.test(href) && !/[\u0000-\u0020\\]/.test(href)) return href;
    if (!/^https?:\/\//i.test(href)) return null;
    try {
      const parsed = new URL(href);
      return ["http:", "https:"].includes(parsed.protocol) && !parsed.username && !parsed.password ? parsed.href : null;
    } catch (_) { return null; }
  }

  function link(url, label, className = "", title = "") {
    const href = safeHref(url);
    if (!href) return `<span class="${esc(className)}">${esc(label)}</span>`;
    const external = /^https?:/i.test(href) ? ' target="_blank" rel="noopener noreferrer"' : "";
    return `<a href="${esc(href)}"${external}${className ? ` class="${esc(className)}"` : ""}${title ? ` title="${esc(title)}"` : ""}>${esc(label)}</a>`;
  }

  function readableName(value) {
    return assessmentLabels[value] || String(value ?? "").replaceAll("_", " ");
  }

  function num(value, decimals = 1) {
    return typeof value === "number" && Number.isFinite(value) ? String(Number(value.toFixed(decimals))) : "—";
  }

  function evidenceTag(type) {
    const known = Object.prototype.hasOwnProperty.call(evidenceLabels, type) ? type : "unknown";
    return `<span class="evidence-type ${known}">${esc(evidenceLabels[known])}</span>`;
  }

  function citations(ids) {
    if (!Array.isArray(ids) || !ids.length) return "";
    const unique = [...new Set(ids)];
    return `<div class="source-links"><span>Sources</span>${unique.map((id) => {
      const entry = sourceIndex.get(id);
      if (!entry) return `<span class="source-unlinked">${esc(id)} · unresolved reference</span>`;
      const label = `[${entry.number}]`;
      return link(entry.source.url, label, "", entry.source.title);
    }).join("")}</div>`;
  }

  function claim(claimData, label = "", withTag = false) {
    if (!claimData) return "";
    return `<div class="claim-block">${label ? `<div class="claim-label">${esc(label)}</div>` : ""}${withTag ? evidenceTag(claimData.evidence_type) : ""}<p>${esc(claimData.summary)}</p>${citations(claimData.source_ids)}</div>`;
  }

  function collectSources(data) {
    sourceIndex = new Map();
    sourceList = [];
    for (const source of [...data.sources, ...data.candidate_treatments.flatMap((candidate) => candidate.sources)]) {
      if (!sourceIndex.has(source.id)) {
        sourceList.push(source);
        sourceIndex.set(source.id, { source, number: sourceList.length });
      }
    }
  }

  function validateResponse(data) {
    const lists = ["candidate_treatments", "related_disease_evidence", "collaborators_or_assets", "sources", "limitations"];
    const claims = ["variant_effect", "functional_mechanism", "pathway"];
    const validClaim = (value) => value && typeof value.summary === "string" && Array.isArray(value.source_ids);
    if (!data || data.schema_version !== "constellai-analysis-v1" || !data.disease || typeof data.disease.name !== "string" ||
        !Array.isArray(data.disease.source_ids) || !lists.every((key) => Array.isArray(data[key])) ||
        !claims.every((key) => validClaim(data[key])) || typeof data.conclusion !== "string" ||
        !["research_hypotheses_found", "insufficient_evidence"].includes(data.analysis_status) || !data.llm ||
        !Array.isArray(data.llm.verified_claims) || !data.recommended_next_experiment) {
      throw new Error("The analysis response did not match the expected contract. Please retry after the service is ready.");
    }
    for (const candidate of data.candidate_treatments) {
      if (!allowedStatuses.has(candidate.status) || !Array.isArray(candidate.sources) ||
          typeof candidate.compound_name !== "string" || typeof candidate.id !== "string" ||
          typeof candidate.final_score !== "number" || candidate.final_score < 0 || candidate.final_score > 100 ||
          !Object.keys(assessmentLabels).filter((key) => key !== "toxicity_organ_burden").every((key) => validClaim(candidate[key])) ||
          !candidate.score_breakdown || !Array.isArray(candidate.score_breakdown.positive_components) ||
          !Array.isArray(candidate.score_breakdown.risk_penalties)) {
        throw new Error("A candidate response is incomplete. No research ranking is shown; please retry after the service is ready.");
      }
    }
    const experiment = data.recommended_next_experiment;
    if (!Array.isArray(experiment.readouts) || !Array.isArray(experiment.prerequisites) || !Array.isArray(experiment.source_ids)) {
      throw new Error("The next-experiment response is incomplete. Please retry after the service is ready.");
    }
    return data;
  }

  function overview(data) {
    const effect = data.variant_effect;
    const scopeLabels = { disease_context: "Known disease context", variant_specific: "Evidence for this variant", unresolved: "Variant effect unresolved" };
    const effectLabels = { variant_dependent: "Variant dependent", loss_of_function: "Loss of function", gain_of_function: "Gain of function", dominant_negative: "Dominant negative", unknown: "Effect unknown" };
    const diseaseSources = citations(data.disease.source_ids);
    const atlasLink = data.disease.id ? link(`/atlas#d/${encodeURIComponent(data.disease.id).replaceAll("%3A", ":")}`, "Explore this disease in the atlas ↗", "small-action") : "";
    return `<section class="research-section" aria-labelledby="understand-title">
      <div class="section-head"><span class="step-number" aria-hidden="true">01</span><div class="section-copy"><div class="disease-title"><h2 id="understand-title">${esc(data.disease.name)}</h2>${data.gene ? `<span class="gene-chip">${esc(data.gene)}</span>` : ""}</div><p class="section-subtitle">What the biology tells us — and what still needs to be established.</p>${diseaseSources}</div><div class="review-date">Evidence reviewed<br>${esc(data.evidence_reviewed_on)}</div></div>
      <div class="overview-grid">
        <article class="overview-card"><div class="card-eyebrow">What does the mutation do?</div><p class="context-label">${esc(scopeLabels[effect.scope] || "Unresolved")} · ${esc(effectLabels[effect.effect] || "Effect unknown")}</p><p>${esc(effect.summary)}</p>${citations(effect.source_ids)}${data.variant ? `<p class="variant-note">Variant supplied: <strong>${esc(data.variant)}</strong>. ${effect.scope === "variant_specific" ? "Variant-specific evidence is shown; compatibility and safety still require expert review." : "Specific variant compatibility must be established before a candidate can be ranked."}</p>` : `<p class="variant-note">No individual variant supplied. This describes the disease context; it does not classify a specific mutation.</p>`}</article>
        <article class="overview-card"><div class="card-eyebrow">From gene to function</div>${claim(data.functional_mechanism, "Functional mechanism")}${claim(data.pathway, "Relevant pathway")}${atlasLink}</article>
      </div>
    </section>`;
  }

  function technicalAssessment(candidate, key) {
    const assessment = candidate[key];
    return `<div class="assessment"><h4>${esc(readableName(key))}</h4><p>${esc(assessment.summary)}</p><div class="assessment-meta">${evidenceTag(assessment.evidence_type)}${Object.prototype.hasOwnProperty.call(assessment, "value") ? `<span>Curator rating: ${assessment.value === null ? "unreviewed" : `${num(assessment.value, 3)} / 1`}</span>` : ""}</div>${citations(assessment.source_ids)}</div>`;
  }

  function scoreAudit(candidate) {
    const breakdown = candidate.score_breakdown;
    const rows = (terms, penalty) => terms.map((term) => `<tr${penalty ? ' class="penalty"' : ""}><td>${esc(readableName(term.component))}<small>${esc(term.missing_policy)}</small></td><td>${num(term.weight, 3)}</td><td>${term.input_value === null ? "Unknown" : num(term.input_value, 3)}</td><td>${num(term.used_value, 3)}</td><td>${penalty ? "−" : "+"}${num(term.contribution, 3)}</td></tr>`).join("");
    return `<div class="score-audit"><h4>Research-priority score audit</h4><p class="score-formula">${esc(breakdown.formula)}</p><div class="audit-table-wrap" tabindex="0" role="region" aria-label="Scrollable score audit for ${esc(candidate.compound_name)}"><table class="audit-table"><thead><tr><th scope="col">Component &amp; missing-data policy</th><th scope="col">Weight</th><th scope="col">Rating</th><th scope="col">Used</th><th scope="col">Points</th></tr></thead><tbody>${rows(breakdown.positive_components, false)}${rows(breakdown.risk_penalties, true)}<tr class="total-row"><td colspan="4">Positive evidence</td><td>+${num(breakdown.positive_total, 3)}</td></tr><tr class="total-row"><td colspan="4">Risk penalties</td><td>−${num(breakdown.penalty_total, 3)}</td></tr><tr class="total-row"><td colspan="4">Before clamping</td><td>${num(breakdown.unclamped_score, 3)}</td></tr><tr class="total-row"><td colspan="4">Final score, bounded 0–100</td><td>${num(breakdown.final_score, 3)}</td></tr></tbody></table></div><p class="audit-foot">${esc(breakdown.interpretation)} Config: ${esc(breakdown.config_version)}. Ratings are curator judgments. Unknown positive evidence adds no points; unreviewed risks receive the configured penalty. Toxicity and organ burden share one penalty using the worse rating.</p></div>`;
  }

  function sourceDetails(source) {
    const entry = sourceIndex.get(source.id);
    return `${link(source.url, `${entry ? `[${entry.number}] ` : ""}${source.title}`)}<div class="source-scope">${evidenceTag(source.evidence_type)} ${esc(source.scope)}</div><div class="source-date">Reviewed ${esc(source.reviewed_on)}</div>`;
  }

  function candidateCard(candidate, isBest = false) {
    const toxicity = candidate.toxicity;
    const organ = candidate.organ_burden;
    const mainRisk = toxicity.value === null ? toxicity : organ.value === null ? organ : toxicity.value >= organ.value ? toxicity : organ;
    const whySources = [...candidate.mechanism_alignment.source_ids, ...candidate.preclinical_evidence.source_ids, ...candidate.human_evidence.source_ids];
    const ranked = Number.isInteger(candidate.rank) && eligibleStatuses.has(candidate.status);
    const score = ranked ? `<div class="score" aria-label="Research priority ${num(candidate.final_score)} out of 100">${num(candidate.final_score)}<small>priority / 100</small></div>` : `<div class="score unranked">Unranked<small>${candidate.status === "rejected" ? "excluded candidate" : "evidence unresolved"}</small></div>`;
    const technicalKeys = Object.keys(assessmentLabels).filter((key) => key !== "toxicity_organ_burden");
    return `<article class="candidate-card${isBest ? " best" : ""}">${isBest ? '<div class="best-label"><span aria-hidden="true">✦</span> Leading hypothesis for investigation</div>' : ""}<div class="candidate-body"><div class="candidate-top"><div class="candidate-name"><span class="status-pill ${candidate.status}">${esc(statusLabels[candidate.status])}</span><h3>${ranked ? `${esc(candidate.rank)}. ` : ""}${esc(candidate.compound_name)}</h3></div>${score}</div><p class="role-label">${esc(roleLabels[candidate.therapeutic_role] || "Research hypothesis")}</p><dl class="candidate-facts">
      <dt>Why it might work</dt><dd>${esc(candidate.rationale)}${citations(whySources)}</dd>
      <dt>Evidence strength &amp; type</dt><dd><div class="evidence-line">${esc(candidate.evidence_quality.summary)}${citations(candidate.evidence_quality.source_ids)}</div><div class="evidence-line">${evidenceTag(candidate.preclinical_evidence.evidence_type)}<p>${esc(candidate.preclinical_evidence.summary)}</p>${citations(candidate.preclinical_evidence.source_ids)}</div><div class="evidence-line">${evidenceTag(candidate.human_evidence.evidence_type)}<p>${esc(candidate.human_evidence.summary)}</p>${citations(candidate.human_evidence.source_ids)}</div></dd>
      <dt class="safety-label">Main safety concern</dt><dd>${esc(mainRisk.summary)}${citations(mainRisk.source_ids)}</dd>
      <dt>What remains uncertain</dt><dd>${esc(candidate.uncertainty.summary)}${citations(candidate.uncertainty.source_ids)}</dd>
      <dt>Next research step</dt><dd class="next-step">${esc(candidate.next_validation_step)}</dd>
      </dl></div><details class="technical"><summary>Mechanisms, safety &amp; score audit</summary><div class="technical-content"><div class="technical-grid">${technicalKeys.map((key) => technicalAssessment(candidate, key)).join("")}</div>${scoreAudit(candidate)}<div class="technical-sources"><h4>Candidate source record</h4><ol>${candidate.sources.map((source) => `<li>${sourceDetails(source)}</li>`).join("")}</ol></div></div></details></article>`;
  }

  function bestCandidate(data) {
    if (data.analysis_status !== "research_hypotheses_found" || (data.variant && data.variant_effect.scope !== "variant_specific")) return null;
    return data.candidate_treatments.find((candidate) => candidate.id === data.best_hypothesis_id && eligibleStatuses.has(candidate.status) && Number.isInteger(candidate.rank)) || null;
  }

  function candidates(data) {
    const best = bestCandidate(data);
    const primary = data.analysis_status === "research_hypotheses_found" ? data.candidate_treatments.filter((candidate) => eligibleStatuses.has(candidate.status)) : [];
    const primaryIds = new Set(primary.map((candidate) => candidate.id));
    const excluded = data.candidate_treatments.filter((candidate) => !primaryIds.has(candidate.id));
    return `<section class="research-section" aria-labelledby="hypotheses-title"><div class="section-head"><span class="step-number" aria-hidden="true">02</span><div class="section-copy"><h2 id="hypotheses-title">${primary.length ? "Therapeutic hypotheses" : "Therapeutic evidence"}</h2><p class="section-subtitle">${primary.length ? "Compare candidates for investigation. Each remains a research question that requires expert validation." : "No ranked hypothesis is available for this query. Review the evidence gap before considering experiments."}</p></div></div><div class="priority-note"><span class="note-icon" aria-hidden="true">ⓘ</span><p>The 0–100 research-priority score is an auditable heuristic. It is not a probability, clinical confidence, or expected treatment efficacy. Preclinical findings do not establish benefit in patients.</p></div>
      ${primary.length ? `<div class="candidates">${primary.map((candidate) => candidateCard(candidate, best && candidate.id === best.id)).join("")}</div>` : ""}
      ${excluded.length ? `<details class="excluded-candidates"><summary>${primary.length ? "Candidates outside the ranking" : "Unranked candidate evidence"}<span>${excluded.length} ${excluded.length === 1 ? "record" : "records"}</span></summary><div><p class="empty-note">Rejected and insufficient-evidence candidates are excluded from the research ranking.</p><div class="candidates">${excluded.map((candidate) => candidateCard(candidate)).join("")}</div></div></details>` : ""}
      ${best ? `<div class="conclusion"><div class="card-eyebrow">Best research hypothesis in this evidence set</div><h3>${esc(best.compound_name)}</h3><p>${esc(data.conclusion)}</p>${citations([...best.mechanism_alignment.source_ids, ...best.preclinical_evidence.source_ids, ...best.human_evidence.source_ids])}<a class="small-action" href="#validation-title">Where can this hypothesis be validated? <span aria-hidden="true">↓</span></a></div>` : `<div class="empty-conclusion"><h3>${data.analysis_status === "insufficient_evidence" ? "Insufficient evidence" : "No leading hypothesis established"}</h3><p>${esc(data.conclusion)}</p></div>`}
    </section>`;
  }

  function validation(data) {
    const related = data.related_disease_evidence.map((record) => `<article class="related-card"><div class="card-eyebrow">Related disease evidence</div><h3>${esc(record.disease.name)}</h3><span class="gene-chip">${esc(record.gene)}</span>${citations(record.disease.source_ids)}${claim(record.shared_mechanism, "Shared mechanism")}${claim(record.key_difference, "Key difference")}${record.research_use ? `<p class="research-use">${esc(record.research_use)}</p>` : ""}<div class="atlas-actions">${link(record.atlas_url, "Explore related disease in the atlas ↗", "small-action")}${data.disease.id === "MONDO:0012812" && record.disease.id === "MONDO:0033372" ? link("/atlas#c/MONDO:0033372/MONDO:0012812", "Compare CPLX1 and STXBP1 ↗", "small-action") : ""}</div></article>`).join("");
    const assets = data.collaborators_or_assets.map((asset) => `<div class="asset"><div class="asset-kind">${esc(kindLabels[asset.kind] || "Research asset")}</div>${link(asset.url, asset.name, "asset-name")}<p>${esc(asset.description)}</p><p class="access-status">${esc(asset.access_status)}</p>${citations(asset.source_ids)}</div>`).join("");
    return `<section class="research-section" aria-labelledby="validation-title"><div class="section-head"><span class="step-number" aria-hidden="true">03</span><div class="section-copy"><h2 id="validation-title">Where can this therapeutic hypothesis be validated?</h2><p class="section-subtitle">Use shared biology to find comparison models, research partners and available assets. A shared pathway does not transfer efficacy or safety.</p></div></div><div class="validation-grid"><div>${related || '<div class="related-card"><p class="empty-note">No related-disease evidence is available for this query.</p></div>'}</div><article class="assets-panel"><h3>Research collaborators &amp; assets</h3>${assets || '<p class="empty-note">No verified research collaborators or assets are available for this query.</p>'}</article></div></section>`;
  }

  function experiment(data) {
    const experimentData = data.recommended_next_experiment;
    const insufficient = data.analysis_status === "insufficient_evidence";
    return `<section class="research-section" aria-labelledby="experiment-title"><div class="section-head"><div class="section-copy"><h2 id="experiment-title">${insufficient ? "Next evidence-building step" : "Proposed next experiment"}</h2><p class="section-subtitle">${insufficient ? "Resolve the evidence gap before investigating a therapeutic candidate." : "A testable question for a research team, with a result that could disprove the hypothesis."}</p></div></div><article class="experiment"><div class="experiment-intro"><div class="card-eyebrow">${insufficient ? "Evidence first" : "From hypothesis to validation"}</div><h3>${esc(experimentData.title)}</h3><p>${esc(experimentData.question)}</p><span class="experiment-status">${experimentData.status === "expert_review_required" ? "Expert review required" : "Proposed research"}</span>${citations(experimentData.source_ids)}</div><div class="experiment-design"><h4>Study design</h4><p>${esc(experimentData.design)}</p>${experimentData.readouts.length ? `<h4 style="margin-top:18px">Measure</h4><ul class="readouts">${experimentData.readouts.map((readout) => `<li>${esc(readout)}</li>`).join("")}</ul>` : ""}<div class="falsification"><h4>What would disprove it?</h4><p>${esc(experimentData.falsification)}</p></div>${experimentData.prerequisites.length ? `<details class="experiment-details"><summary>Requirements before starting</summary><ul>${experimentData.prerequisites.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></details>` : ""}</div></article></section>`;
  }

  function review(data) {
    const explanation = data.llm.verified_claims.length ? `<div class="ai-explanation">${data.llm.verified_claims.map((item) => claim(item, "Source-checked explanation", true)).join("")}</div>` : "";
    const aiAvailable = openaiEnabled && !fixtureMode;
    const aiStatus = fixtureMode ? "Fixture mode uses the saved source record." : aiAvailable ? "Optional: generate an explanation from the supplied sources using the server-side OpenAI connection." : "Available when the server key is configured. Cached research analysis is ready to use.";
    return `<section class="review-panel" aria-label="Analysis details"><details><summary>Limitations &amp; responsible research use</summary><div><ul class="limitations">${data.limitations.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></div></details><details><summary>Source bibliography &amp; review dates<span>${sourceList.length} ${sourceList.length === 1 ? "source" : "sources"}</span></summary><div><ol class="bibliography">${sourceList.map((source, index) => `<li id="source-${index + 1}">${sourceDetails(source)}</li>`).join("")}</ol></div></details><details id="ai-details"><summary>Optional source-bound AI explanation<span id="ai-availability">${aiAvailable ? "Available" : "Not configured"}</span></summary><div class="ai-detail"><p id="ai-status">${esc(aiStatus)}</p>${explanation}<button class="secondary-button" id="openai-button" type="button"${aiAvailable ? "" : " disabled"}>Generate source-bound explanation</button><p class="provenance" style="margin-top:12px">${esc(data.llm.detail)}${data.llm.model ? ` Model: ${esc(data.llm.model)}.` : ""}</p></div></details></section>`;
  }

  function render(data) {
    collectSources(data);
    results.innerHTML = overview(data) + candidates(data) + validation(data) + experiment(data) + review(data);
    $("#openai-button").addEventListener("click", () => {
      if (openaiEnabled && !fixtureMode && lastRequest) analyze({ ...lastRequest, use_openai: true }, true);
    });
    updateMode(data);
  }

  function updateMode(data = null) {
    const modeBanner = $("#mode-banner");
    modeBanner.classList.toggle("fixture", fixtureMode);
    const mode = data?.llm?.mode;
    $("#mode-text").textContent = fixtureMode ? "Fixture demo · cached evidence" : mode === "openai_verified" ? "Source-checked AI explanation · cached evidence" : mode === "fallback" ? "Cached evidence · AI explanation unavailable" : "Cached evidence · source-grounded analysis";
  }

  function updateAiAvailability() {
    const button = $("#openai-button");
    if (!button || !currentAnalysis) return;
    const available = openaiEnabled && !fixtureMode;
    button.disabled = !available;
    $("#ai-availability").textContent = fixtureMode ? "Fixture mode" : available ? "Available" : "Not configured";
    $("#ai-status").textContent = fixtureMode ? "Fixture mode uses the saved source record." : available ? "Optional: generate an explanation from the supplied sources using the server-side OpenAI connection." : "Available when the server key is configured. Cached research analysis is ready to use.";
  }

  function requestFromForm() {
    const enteredDisease = diseaseInput.value.trim();
    return {
      disease: searchChoices.get(enteredDisease) || enteredDisease,
      gene: $("#gene").value.trim() || null,
      variant: $("#variant").value.trim() || null,
      use_openai: false,
    };
  }

  function fixtureMatches(request, data) {
    const norm = (value) => String(value ?? "").trim().toLowerCase();
    const aliases = ["stxbp1", "stxbp1-related neurodevelopmental disorder", "stxbp1 encephalopathy", "mondo:0012812", data.disease.id, data.disease.name].map(norm);
    return aliases.includes(norm(request.disease)) && (!request.gene || norm(request.gene) === norm(data.gene)) && norm(request.variant) === norm(data.variant);
  }

  async function analyze(request, aiRequested = false) {
    const sequence = ++requestSequence;
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    const timeout = setTimeout(() => controller.abort(), aiRequested ? 70000 : 35000);
    const priorAnalysis = currentAnalysis;
    status.textContent = aiRequested ? "Generating an explanation and checking claims against the source record…" : fixtureMode ? "Loading the cached STXBP1 fixture…" : "Connecting disease biology to the curated evidence…";
    status.classList.add("loading");
    errorBox.hidden = true;
    errorBox.textContent = "";
    results.setAttribute("aria-busy", "true");
    analyzeButton.disabled = true;
    if (aiRequested) {
      const aiButton = $("#openai-button");
      if (aiButton) aiButton.disabled = true;
    } else {
      results.innerHTML = "";
      currentAnalysis = null;
      lastRequest = null;
    }
    try {
      const response = fixtureMode ? await fetch("/demo-analysis.json", { signal: controller.signal, cache: "no-store" }) : await fetch("/api/v1/analyze_disease", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request), signal: controller.signal,
      });
      if (!response.ok) {
        if (response.status === 422) throw new Error("The query could not be accepted. Check the disease, gene and variant, then try again.");
        throw new Error(`The analysis service is unavailable (HTTP ${response.status}). Please retry when the service is ready.`);
      }
      const data = validateResponse(await response.json());
      if (fixtureMode && !fixtureMatches(request, data)) {
        throw new Error("This fixture contains one STXBP1 example without a supplied variant. Use cached analysis to explore a different query.");
      }
      if (sequence !== requestSequence) return;
      currentAnalysis = data;
      lastRequest = { ...request, use_openai: false };
      const aiWasOpen = aiRequested;
      render(data);
      if (aiWasOpen) $("#ai-details").open = true;
      status.textContent = `${fixtureMode ? "Fixture loaded" : "Analysis ready"} · ${data.analysis_status === "insufficient_evidence" ? "Insufficient evidence — no leading therapeutic hypothesis" : "Therapeutic hypotheses require expert validation"}`;
      if (aiRequested && data.llm.mode !== "openai_verified") status.textContent = "Cached analysis retained · AI explanation could not be verified; review the explanation details.";
    } catch (error) {
      if (sequence !== requestSequence) return;
      const message = error.name === "AbortError" ? "The analysis took longer than expected. Please retry when the service is ready." : error instanceof TypeError ? "The analysis service could not be reached. Check that the server is running, then retry." : error.message;
      errorBox.innerHTML = `<p>${esc(message)}</p>${fixtureMode ? '<p><a href="/">Use cached analysis →</a></p>' : ""}`;
      errorBox.hidden = false;
      status.textContent = aiRequested && priorAnalysis ? "Cached analysis remains available." : "Analysis unavailable · no research ranking is shown.";
      if (aiRequested && priorAnalysis) { currentAnalysis = priorAnalysis; updateAiAvailability(); }
    } finally {
      clearTimeout(timeout);
      if (sequence === requestSequence) {
        activeController = null;
        status.classList.remove("loading");
        results.setAttribute("aria-busy", "false");
        analyzeButton.disabled = false;
      }
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const request = requestFromForm();
    if (!request.disease) {
      diseaseInput.setCustomValidity("Enter a disease or gene to analyze.");
      diseaseInput.reportValidity();
      return;
    }
    analyze(request);
  });

  diseaseInput.addEventListener("input", () => {
    diseaseInput.setCustomValidity("");
    clearTimeout(searchTimer);
    const sequence = ++searchSequence;
    const query = diseaseInput.value.trim();
    if (fixtureMode || query.length < 2) return;
    searchTimer = setTimeout(async () => {
      try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&use_openai=false`);
        if (!response.ok) return;
        const data = await response.json();
        if (sequence !== searchSequence || !Array.isArray(data.hits)) return;
        const hits = data.hits.filter((hit) => ["disease", "gene"].includes(hit.type) && typeof hit.label === "string" && typeof hit.id === "string");
        hits.forEach((hit) => searchChoices.set(hit.label, hit.id));
        $("#disease-options").innerHTML = hits.map((hit) => `<option value="${esc(hit.label)}">${esc(hit.type === "gene" ? "Gene" : "Disease")} · ${esc(hit.sub || hit.id)}</option>`).join("");
      } catch (_) { /* A missing search service does not prevent direct analysis. */ }
    }, 180);
  });

  async function loadHealth() {
    if (fixtureMode) return;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch("/api/v1/health", { signal: controller.signal });
      if (response.ok) {
        const health = await response.json();
        openaiEnabled = health.openai_enabled === true;
        updateAiAvailability();
      }
    } catch (_) { openaiEnabled = false; }
    finally { clearTimeout(timeout); }
  }

  updateMode();
  loadHealth();
  analyze(requestFromForm());
})();

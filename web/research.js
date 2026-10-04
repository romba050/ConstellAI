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
  const graphKindLabels = {
    disease: "Disease", gene: "Gene", variant: "Variant", mechanism: "Mechanism",
    pathway: "Pathway", phenotype: "Phenotype", candidate: "Research candidate",
    paper: "Paper", clinical_study: "Clinical study", patient_organisation: "Patient organisation",
    investigator: "Investigator", research_asset: "Research asset",
  };
  const confidenceLabels = { strong: "Strong", moderate: "Moderate", limited: "Limited", unresolved: "Unresolved" };
  const assertionLabels = { observed: "Observed", inferred: "Inferred", unknown: "Unknown" };
  let requestSequence = 0;
  let activeController = null;
  let lastRequest = null;
  let currentAnalysis = null;
  let openaiEnabled = false;
  let sourceIndex = new Map();
  let sourceList = [];
  let searchSequence = 0;
  let searchTimer = null;
  let graphFocusId = null;
  let selectedGraphEdgeId = null;
  let graphKindFilter = "all";
  let graphSearchQuery = "";
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
    if (!data || data.schema_version !== "constellai-analysis-v2" || !data.disease || typeof data.disease.name !== "string" ||
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
    const graph = data.knowledge_graph;
    if (!graph || !Array.isArray(graph.nodes) || !Array.isArray(graph.edges) || !Array.isArray(graph.limitations)) {
      throw new Error("The connected evidence graph is missing. Please retry when the v2 service is ready.");
    }
    const nodeIds = new Set();
    const edgeIds = new Set();
    const sourceIds = new Set([...data.sources, ...data.candidate_treatments.flatMap((candidate) => candidate.sources)].map((source) => source.id));
    const closedReferences = (ids) => Array.isArray(ids) && ids.every((id) => typeof id === "string" && sourceIds.has(id));
    for (const node of graph.nodes) {
      if (typeof node.id !== "string" || !node.id || nodeIds.has(node.id) || !Object.prototype.hasOwnProperty.call(graphKindLabels, node.kind) ||
          typeof node.label !== "string" || typeof node.description !== "string" || !closedReferences(node.source_ids) ||
          !(node.url === null || typeof node.url === "string")) {
        throw new Error("An evidence-graph entity did not match the expected contract. No graph or ranking is shown.");
      }
      nodeIds.add(node.id);
    }
    for (const edge of graph.edges) {
      if (typeof edge.id !== "string" || !edge.id || edgeIds.has(edge.id) || !nodeIds.has(edge.source) || !nodeIds.has(edge.target) ||
          typeof edge.relationship_type !== "string" || !validClaim(edge.claim) || !closedReferences(edge.claim.source_ids) ||
          !Object.prototype.hasOwnProperty.call(confidenceLabels, edge.confidence) || !Object.prototype.hasOwnProperty.call(assertionLabels, edge.assertion) ||
          typeof edge.confidence_basis !== "string" || typeof edge.scope !== "string" || !Array.isArray(edge.contradictions) ||
          !edge.contradictions.every((item) => validClaim(item) && closedReferences(item.source_ids))) {
        throw new Error("An evidence-graph connection did not match the expected contract. No graph or ranking is shown.");
      }
      edgeIds.add(edge.id);
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

  function graphNodeById(data, id) {
    return data.knowledge_graph.nodes.find((node) => node.id === id);
  }

  function edgeTitle(data, edge) {
    const from = graphNodeById(data, edge.source);
    const to = graphNodeById(data, edge.target);
    return `${from?.label || edge.source} → ${to?.label || edge.target}`;
  }

  function visibleGraphNodes(data) {
    const graph = data.knowledge_graph;
    const focus = graphNodeById(data, graphFocusId) || graph.nodes[0];
    if (!focus) return [];
    const selectedEdge = graph.edges.find((edge) => edge.id === selectedGraphEdgeId);
    if (!selectedEdge && focus.kind === "disease" && data.disease.id && focus.id.includes(data.disease.id)) {
      const preferred = [
        graph.nodes.find((node) => node.kind === "gene" && node.label === data.gene),
        graph.nodes.find((node) => node.kind === "mechanism"),
        graph.nodes.find((node) => node.kind === "pathway"),
        data.variant ? graph.nodes.find((node) => node.kind === "variant" && node.id.startsWith("variant:entered:")) : null,
        data.analysis_status === "research_hypotheses_found" && data.best_hypothesis_id ? graph.nodes.find((node) => node.kind === "candidate" && node.id.includes(data.best_hypothesis_id)) : null,
      ].filter(Boolean);
      const backbone = [focus];
      for (const target of preferred) {
        const routes = [[focus.id]];
        const explored = new Set();
        let route = null;
        while (routes.length) {
          const current = routes.shift();
          const id = current[current.length - 1];
          if (id === target.id) { route = current; break; }
          if (explored.has(id)) continue;
          explored.add(id);
          graph.edges.filter((edge) => edge.source === id || edge.target === id).forEach((edge) => {
            const nextId = edge.source === id ? edge.target : edge.source;
            if (!explored.has(nextId)) routes.push([...current, nextId]);
          });
        }
        if (route) {
          const extra = route.map((id) => graphNodeById(data, id)).filter((node) => !backbone.some((existing) => existing.id === node.id));
          if (backbone.length + extra.length <= 6) backbone.push(...extra);
        }
      }
      if (backbone.length > 1) return backbone;
    }
    const priority = ["variant", "gene", "mechanism", "pathway", "candidate", "disease", "phenotype", "paper", "clinical_study", "patient_organisation", "investigator", "research_asset"];
    const queue = [focus];
    const selected = [];
    const visited = new Set();
    while (queue.length && selected.length < 6) {
      const node = queue.shift();
      if (visited.has(node.id)) continue;
      visited.add(node.id);
      selected.push(node);
      const neighbors = graph.edges.filter((edge) => edge.source === node.id || edge.target === node.id)
        .map((edge) => graphNodeById(data, edge.source === node.id ? edge.target : edge.source))
        .filter(Boolean).sort((a, b) => {
          const aSelected = selectedEdge && [selectedEdge.source, selectedEdge.target].includes(a.id);
          const bSelected = selectedEdge && [selectedEdge.source, selectedEdge.target].includes(b.id);
          return Number(bSelected) - Number(aSelected) || priority.indexOf(a.kind) - priority.indexOf(b.kind) || a.label.localeCompare(b.label);
        });
      queue.push(...neighbors.filter((neighbor) => !visited.has(neighbor.id)));
    }
    return selected;
  }

  function graphLabelLines(label, maxLength = 23) {
    const words = String(label).split(/\s+/);
    const lines = [];
    let line = "";
    for (const word of words) {
      if (line && `${line} ${word}`.length > maxLength) { lines.push(line); line = word; }
      else line = line ? `${line} ${word}` : word;
    }
    if (line) lines.push(line);
    const display = lines.slice(0, 2).map((text) => text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text);
    if (lines.length > 2) display[display.length - 1] = `${display[display.length - 1].replace(/…$/, "").slice(0, maxLength - 1)}…`;
    return display;
  }

  function graphSvg(data) {
    const nodes = visibleGraphNodes(data);
    if (!nodes.length) return '<p class="empty-note">No graph entities are recorded for this input.</p>';
    const narrow = typeof window !== "undefined" && window.innerWidth < 1000;
    const columns = narrow ? 2 : 3;
    const width = narrow ? 350 : 555;
    const nodeWidth = narrow ? 155 : 160;
    const nodeHeight = 78;
    const rowHeight = narrow ? 117 : 134;
    const positions = new Map(nodes.map((node, index) => [node.id, {
      x: 15 + (index % columns) * (narrow ? 170 : 182), y: 18 + Math.floor(index / columns) * rowHeight,
    }]));
    const height = Math.ceil(nodes.length / columns) * rowHeight + 3;
    const visibleIds = new Set(nodes.map((node) => node.id));
    const edges = data.knowledge_graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
    const endpoint = (a, b) => {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const scale = Math.min(dx === 0 ? Infinity : (nodeWidth / 2 + 4) / Math.abs(dx), dy === 0 ? Infinity : (nodeHeight / 2 + 4) / Math.abs(dy));
      return { x: a.x + nodeWidth / 2 + dx * scale, y: a.y + nodeHeight / 2 + dy * scale };
    };
    const edgeShapes = edges.map((edge) => {
      const source = positions.get(edge.source);
      const target = positions.get(edge.target);
      const a = endpoint(source, target);
      const b = endpoint(target, source);
      const edgeIndex = data.knowledge_graph.edges.indexOf(edge);
      const path = edge.source === edge.target ? `M${source.x + 45},${source.y - 3} C${source.x + 45},${source.y - 16} ${source.x + 115},${source.y - 16} ${source.x + 115},${source.y - 3}` : `M${a.x},${a.y} L${b.x},${b.y}`;
      const bounds = edge.source === edge.target ? { x: source.x + 35, y: source.y - 25, width: 90, height: 30 } : {
        x: Math.min(a.x, b.x) - 9, y: Math.min(a.y, b.y) - 9,
        width: Math.max(Math.abs(b.x - a.x) + 18, 18), height: Math.max(Math.abs(b.y - a.y) + 18, 18),
      };
      const label = `${edgeTitle(data, edge)}: ${readableName(edge.relationship_type)}; ${assertionLabels[edge.assertion]}`;
      return `<g class="graph-edge ${edge.assertion}${selectedGraphEdgeId === edge.id ? " selected" : ""}" data-graph-edge="${edgeIndex}" tabindex="0" role="button" aria-label="${esc(label)}"><title>${esc(label)}</title><rect class="edge-bounds" x="${bounds.x}" y="${bounds.y}" width="${bounds.width}" height="${bounds.height}" rx="3"/><path class="edge-hit" d="${path}"/><path class="edge-line" d="${path}" marker-end="url(#graph-arrow)"/></g>`;
    }).join("");
    const nodeShapes = nodes.map((node) => {
      const position = positions.get(node.id);
      const index = data.knowledge_graph.nodes.indexOf(node);
      const lines = graphLabelLines(node.label, narrow ? 21 : 23);
      return `<g class="graph-node${graphFocusId === node.id ? " selected" : ""}" data-kind="${node.kind}" data-graph-node="${index}" transform="translate(${position.x},${position.y})" tabindex="0" role="button" aria-label="${esc(`${graphKindLabels[node.kind]}: ${node.label}. Explore connections.`)}"><title>${esc(node.label)}</title><rect width="${nodeWidth}" height="${nodeHeight}" rx="9"/><text class="graph-kind" x="11" y="20">${esc(graphKindLabels[node.kind])}</text><text class="graph-label" x="11" y="42">${lines.map((line, lineIndex) => `<tspan x="11" dy="${lineIndex ? 15 : 0}">${esc(line)}</tspan>`).join("")}</text></g>`;
    }).join("");
    return `<svg class="graph-canvas" viewBox="0 0 ${width} ${height}" aria-label="Connected evidence around ${esc(graphNodeById(data, graphFocusId)?.label || nodes[0].label)}" role="group"><defs><marker id="graph-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 10 5 0 10Z" fill="#8495b5"/></marker></defs>${edgeShapes}${nodeShapes}</svg>`;
  }

  function graphEdgeButtons(data, edges, emptyText, visibleLimit = null) {
    if (!edges.length) return `<p class="empty-note">${esc(emptyText)}</p>`;
    const ordered = [...edges].sort((a, b) => Number(b.id === selectedGraphEdgeId) - Number(a.id === selectedGraphEdgeId));
    const button = (edge) => `<button class="graph-connection${selectedGraphEdgeId === edge.id ? " selected" : ""}" type="button" data-graph-edge="${data.knowledge_graph.edges.indexOf(edge)}" aria-pressed="${selectedGraphEdgeId === edge.id}"><span class="graph-connection-title">${esc(edgeTitle(data, edge))}</span><span class="graph-connection-meta"><span>${esc(readableName(edge.relationship_type))}</span><span class="assertion-badge ${edge.assertion}">${esc(assertionLabels[edge.assertion])}</span></span></button>`;
    if (visibleLimit && ordered.length > visibleLimit) return `${ordered.slice(0, visibleLimit).map(button).join("")}<details class="graph-more-connections"><summary>${ordered.length - visibleLimit} more connections in this view</summary><div>${ordered.slice(visibleLimit).map(button).join("")}</div></details>`;
    return ordered.map(button).join("");
  }

  function graphNodeEvidence(data, node) {
    if (!node) return '<p class="empty-note">No source-backed graph context is available for this input.</p>';
    const connectedCount = data.knowledge_graph.edges.filter((edge) => edge.source === node.id || edge.target === node.id).length;
    return `<div class="card-eyebrow">${esc(graphKindLabels[node.kind])}</div><h3>${esc(node.label)}</h3><p class="graph-detail-summary">${esc(node.description)}</p>${citations(node.source_ids)}${node.url ? link(node.url, "Open entity source ↗", "small-action") : ""}<p class="graph-selection-hint">${connectedCount} recorded ${connectedCount === 1 ? "connection" : "connections"}. Select a connection to inspect the claim, confidence basis, study scope and contrasting findings.</p>`;
  }

  function graphEdgeEvidence(data, edge) {
    const sourceIds = [...new Set([...edge.claim.source_ids, ...edge.contradictions.flatMap((item) => item.source_ids)])];
    return `<div class="card-eyebrow">Selected connection</div><h3>${esc(edgeTitle(data, edge))}</h3><p class="graph-relation">${esc(readableName(edge.relationship_type))}</p><div class="graph-assertion-row"><span class="assertion-badge ${edge.assertion}">${esc(assertionLabels[edge.assertion])}</span>${evidenceTag(edge.claim.evidence_type)}</div><p class="graph-detail-summary">${esc(edge.claim.summary)}</p>${citations(edge.claim.source_ids)}<dl class="graph-evidence-facts"><dt>Qualitative confidence · ${esc(confidenceLabels[edge.confidence])}</dt><dd>${esc(edge.confidence_basis)}<span class="confidence-note">A curator category, not a probability or treatment confidence.</span></dd><dt>Scope &amp; limits of this connection</dt><dd>${esc(edge.scope)}</dd></dl><details class="graph-contradictions"><summary>Contrasting findings &amp; uncertainty<span>${edge.contradictions.length} recorded</span></summary><div>${edge.contradictions.length ? edge.contradictions.map((item) => claim(item, "Contrasting claim", true)).join("") : '<p class="empty-note">No contrasting claim is recorded for this connection. The record may not contain all contrary evidence.</p>'}</div></details>${sourceIds.length ? `<details class="graph-source-record"><summary>Connection source records<span>${sourceIds.length}</span></summary><ol>${sourceIds.map((id) => sourceIndex.get(id)?.source).filter(Boolean).map((source) => `<li>${sourceDetails(source)}</li>`).join("")}</ol></details>` : '<p class="graph-selection-hint">No source is cited for this unresolved connection.</p>'}`;
  }

  function graphNodeBrowser(data) {
    const query = graphSearchQuery.trim().toLowerCase();
    const nodes = data.knowledge_graph.nodes.filter((node) => (graphKindFilter === "all" || node.kind === graphKindFilter) && (!query || `${node.label} ${node.description} ${graphKindLabels[node.kind]}`.toLowerCase().includes(query)));
    if (!nodes.length) return '<p class="empty-note">No graph entities match these filters.</p>';
    return nodes.map((node) => `<button type="button" class="graph-entity${graphFocusId === node.id ? " selected" : ""}" data-kind="${node.kind}" data-graph-node="${data.knowledge_graph.nodes.indexOf(node)}" aria-pressed="${graphFocusId === node.id}"><span class="graph-entity-kind">${esc(graphKindLabels[node.kind])}</span><span>${esc(node.label)}</span></button>`).join("");
  }

  function researchWorkflow(data) {
    return `<details class="research-workflow"><summary>How the research steps are assembled<span>10× thesis · unmeasured</span></summary><div><p class="workflow-thesis">A 10× faster research workflow is a product hypothesis. This release assembles five reviewable stages; time saved has not been measured.</p><ol class="workflow-steps"><li><strong>Confirm identity.</strong><p>Match disease and gene; keep a supplied variant unresolved unless its function has been reviewed.</p></li><li><strong>Read the mechanism.</strong><p>Attach the functional mechanism and pathway to the source record and preserve their model or variant scope.</p></li><li><strong>Inspect connections.</strong><p>${data.knowledge_graph.nodes.length} entities and ${data.knowledge_graph.edges.length} recorded relationships carry their own claim, assertion, qualitative confidence basis and limitations.</p></li><li><strong>Compare evidence &amp; safety.</strong><p>Disclose candidate evidence, missing data, safety concerns and every research-priority score term. Unreviewed variants receive no candidate rank.</p></li><li><strong>Build the validation plan.</strong><p>Assemble the research question, design, readouts, falsification criteria and available research assets for expert review.</p></li></ol></div></details>`;
  }

  function evidenceGraph(data) {
    const graph = data.knowledge_graph;
    const kinds = Object.keys(graphKindLabels).filter((kind) => graph.nodes.some((node) => node.kind === kind));
    const focus = graphNodeById(data, graphFocusId);
    const visibleIds = new Set(visibleGraphNodes(data).map((node) => node.id));
    const shownEdges = graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target));
    const connected = graph.edges.filter((edge) => edge.source === graphFocusId || edge.target === graphFocusId);
    return `<section class="research-section graph-section" aria-labelledby="graph-title"><div class="section-head"><div class="section-copy"><div class="card-eyebrow">Follow the evidence</div><h2 id="graph-title">A connected evidence map</h2><p class="section-subtitle">Select a node to explore its connections. Select an edge to inspect what supports it, the scope of the claim and what remains uncertain.</p></div><span class="graph-count">${graph.nodes.length} entities · ${graph.edges.length} connections</span></div><div class="evidence-map"><div class="graph-layout"><div class="graph-visual"><div id="graph-stage">${graphSvg(data)}</div><div class="graph-legend"><span><i class="observed"></i> Observed</span><span><i class="inferred"></i> Inferred</span><span><i class="unknown"></i> Unknown</span></div><p class="graph-caption">Only recorded relationships are drawn. Connections do not establish therapeutic efficacy or transfer evidence between diseases.</p><div class="graph-visible-connections"><h4>Connections in this view</h4><div id="graph-visible-edges">${graphEdgeButtons(data, shownEdges, "No recorded connections are available in this view.", 3)}</div></div></div><aside id="graph-evidence-detail" class="graph-evidence-detail" aria-label="Selected entity or connection evidence">${graphNodeEvidence(data, focus)}</aside></div><div id="graph-selection-status" class="graph-selection-status" role="status" aria-live="polite">Viewing ${esc(focus?.label || "unresolved input")}</div><details id="graph-expand" class="graph-expand"><summary>Expand the evidence graph<span>All entity types &amp; connections</span></summary><div><div class="graph-selection-tools"><label for="graph-kind-filter">Entity type<select id="graph-kind-filter"><option value="all">All types</option>${kinds.map((kind) => `<option value="${kind}">${esc(graphKindLabels[kind])}</option>`).join("")}</select></label><label for="graph-node-search">Find an entity<input id="graph-node-search" type="search" placeholder="Gene, candidate, paper, study…" autocomplete="off" maxlength="200"></label></div><div id="graph-node-browser" class="graph-node-browser">${graphNodeBrowser(data)}</div><h4 class="graph-focused-title" id="graph-focused-title">Connections around ${esc(focus?.label || "unresolved input")}</h4><div id="graph-connected-edges" class="graph-connected-edges">${graphEdgeButtons(data, connected, "No recorded connections are available for this entity.")}</div><details class="graph-limitations"><summary>Graph scope &amp; limitations</summary><ul>${graph.limitations.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></details></div></details></div>${researchWorkflow(data)}</section>`;
  }

  function updateGraph(data, announcement = "") {
    const graph = data.knowledge_graph;
    const focus = graphNodeById(data, graphFocusId);
    const selectedEdge = graph.edges.find((edge) => edge.id === selectedGraphEdgeId);
    const visibleIds = new Set(visibleGraphNodes(data).map((node) => node.id));
    $("#graph-stage").innerHTML = graphSvg(data);
    $("#graph-visible-edges").innerHTML = graphEdgeButtons(data, graph.edges.filter((edge) => visibleIds.has(edge.source) && visibleIds.has(edge.target)), "No recorded connections are available in this view.", 3);
    $("#graph-evidence-detail").innerHTML = selectedEdge ? graphEdgeEvidence(data, selectedEdge) : graphNodeEvidence(data, focus);
    $("#graph-node-browser").innerHTML = graphNodeBrowser(data);
    $("#graph-connected-edges").innerHTML = graphEdgeButtons(data, graph.edges.filter((edge) => edge.source === graphFocusId || edge.target === graphFocusId), "No recorded connections are available for this entity.");
    $("#graph-focused-title").textContent = `Connections around ${focus?.label || "unresolved input"}`;
    $("#graph-selection-status").textContent = announcement || `Viewing ${focus?.label || "unresolved input"}`;
  }

  function selectGraphControl(control) {
    if (!currentAnalysis || !control) return;
    const preserveFocus = document.activeElement === control;
    const region = preserveFocus ? ["#graph-node-browser", "#graph-connected-edges", "#graph-visible-edges"].find((selector) => control.closest(selector)) || "#graph-stage" : null;
    const nodeIndex = control.getAttribute("data-graph-node");
    const edgeIndex = control.getAttribute("data-graph-edge");
    if (nodeIndex !== null) {
      const node = currentAnalysis.knowledge_graph.nodes[Number(nodeIndex)];
      if (!node) return;
      graphFocusId = node.id;
      selectedGraphEdgeId = null;
      updateGraph(currentAnalysis, `Viewing ${graphKindLabels[node.kind]}: ${node.label}`);
    } else if (edgeIndex !== null) {
      const edge = currentAnalysis.knowledge_graph.edges[Number(edgeIndex)];
      if (!edge) return;
      graphFocusId = edge.source;
      selectedGraphEdgeId = edge.id;
      updateGraph(currentAnalysis, `Selected connection: ${edgeTitle(currentAnalysis, edge)}`);
    }
    if (preserveFocus) $(nodeIndex !== null ? `${region} [data-graph-node="${Number(nodeIndex)}"]` : `${region} [data-graph-edge="${Number(edgeIndex)}"]`)?.focus();
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
    const score = ranked ? `<div class="score" aria-label="Research priority ${num(candidate.final_score, 2)} out of 100">${num(candidate.final_score, 2)}<small>priority / 100</small></div>` : `<div class="score unranked">Unranked<small>${candidate.status === "rejected" ? "excluded candidate" : "evidence unresolved"}</small></div>`;
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

  function literatureSourceClaims(data, sourceId) {
    const entries = new Map();
    const add = (label, item, scope = "", contrasting = false) => {
      if (!item?.source_ids?.includes(sourceId)) return;
      const key = `${item.summary}\u0000${scope}\u0000${contrasting}`;
      if (!entries.has(key)) entries.set(key, { labels: new Set(), item, scope, contrasting });
      entries.get(key).labels.add(label);
    };
    for (const edge of data.knowledge_graph.edges) {
      const relation = `${edgeTitle(data, edge)} · ${readableName(edge.relationship_type)}`;
      add(relation, edge.claim, edge.scope);
      edge.contradictions.forEach((item) => add(`Contrasting finding for ${relation}`, item, edge.scope, true));
    }
    add("Variant effect", data.variant_effect);
    add("Functional mechanism", data.functional_mechanism);
    add("Relevant pathway", data.pathway);
    for (const candidate of data.candidate_treatments) {
      Object.keys(assessmentLabels).filter((key) => key !== "toxicity_organ_burden").forEach((key) => add(`${candidate.compound_name} · ${readableName(key)}`, candidate[key]));
    }
    for (const record of data.related_disease_evidence) {
      add(`${record.disease.name} · Shared mechanism`, record.shared_mechanism);
      add(`${record.disease.name} · Key difference`, record.key_difference);
    }
    for (const item of data.llm.verified_claims) add("Source-checked AI explanation", item);
    return [...entries.values()];
  }

  function literatureSourceLimits(data, source) {
    const notes = new Set([source.scope]);
    for (const edge of data.knowledge_graph.edges) {
      if (edge.claim.source_ids.includes(source.id) || edge.contradictions.some((item) => item.source_ids.includes(source.id))) {
        if (edge.scope) notes.add(edge.scope);
        if (["limited", "unresolved"].includes(edge.confidence) && edge.confidence_basis) notes.add(edge.confidence_basis);
      }
    }
    for (const candidate of data.candidate_treatments) {
      if (candidate.uncertainty.source_ids.includes(source.id)) notes.add(candidate.uncertainty.summary);
      if (candidate.evidence_quality.source_ids.includes(source.id)) notes.add(candidate.evidence_quality.summary);
    }
    return [...notes].filter(Boolean);
  }

  function literatureReview(data) {
    const order = ["human_clinical", "human_observational", "preclinical", "regulatory_label", "trial_registry", "disease_reference", "mechanistic_inference", "official_resource", "unknown"];
    const groups = order.map((type) => ({ type, sources: sourceList.filter((source) => (Object.prototype.hasOwnProperty.call(evidenceLabels, source.evidence_type) ? source.evidence_type : "unknown") === type) })).filter((group) => group.sources.length);
    const groupMarkup = groups.map((group) => `<section class="literature-group" aria-label="${esc(evidenceLabels[group.type])}"><div class="literature-group-head"><h3>${esc(evidenceLabels[group.type])}</h3><span>${group.sources.length} ${group.sources.length === 1 ? "source" : "sources"}</span></div>${group.sources.map((source) => {
      const supports = literatureSourceClaims(data, source.id);
      const limits = literatureSourceLimits(data, source);
      const contradictions = supports.filter((entry) => entry.contrasting);
      const supporting = supports.filter((entry) => !entry.contrasting);
      const entries = (items) => items.map((entry) => `<div class="literature-claim${entry.contrasting ? " contrasting" : ""}"><h4>${esc([...entry.labels].join(" · "))}</h4>${evidenceTag(entry.item.evidence_type)}<p>${esc(entry.item.summary)}</p>${entry.scope ? `<p class="literature-claim-scope">Scope: ${esc(entry.scope)}</p>` : ""}${citations(entry.item.source_ids)}</div>`).join("");
      return `<details class="literature-source"><summary><span class="literature-source-title">${esc(source.title)}</span><span class="literature-source-count">${supports.length} ${supports.length === 1 ? "claim" : "claims"}</span></summary><div class="literature-source-body">${sourceDetails(source)}<div class="literature-limits"><h4>Recorded scope &amp; study limitations</h4><ul>${limits.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></div><div class="literature-support"><h4 class="literature-subhead">Which mechanism &amp; candidate claims this source supports</h4>${supporting.length ? entries(supporting) : '<p class="empty-note">This source has no mapped mechanism or candidate assessment claim; consult its graph entity and source scope for the recorded use.</p>'}</div>${contradictions.length ? `<div class="literature-support"><h4 class="literature-subhead">Contrasting findings cited to this source</h4>${entries(contradictions)}</div>` : ""}</div></details>`;
    }).join("")}</section>`).join("");
    return `<details id="literature-review" class="literature-review"><summary>Literature review · evidence, claims &amp; study limitations<span>${sourceList.length} sources</span></summary><div><p class="literature-intro">Review sources by evidence type, then inspect the exact mechanism or candidate claims mapped to each paper, study or resource. Study scope, confidence limits and contrasting findings come from the recorded evidence graph and assessments.</p>${groupMarkup || '<p class="empty-note">No reviewed literature is available for this query. Therapeutic ranking remains withheld.</p>'}</div></details>`;
  }

  function review(data) {
    const explanation = data.llm.verified_claims.length ? `<div class="ai-explanation">${data.llm.verified_claims.map((item) => claim(item, "Source-checked explanation", true)).join("")}</div>` : "";
    const aiAvailable = openaiEnabled && !fixtureMode;
    const aiStatus = fixtureMode ? "Fixture mode uses the saved source record." : aiAvailable ? "Optional: generate an explanation from the supplied sources using the server-side OpenAI connection." : "Available when the server key is configured. Cached research analysis is ready to use.";
    return `<section class="review-panel" aria-label="Analysis details">${literatureReview(data)}<details><summary>Limitations &amp; responsible research use</summary><div><ul class="limitations">${data.limitations.map((item) => `<li>${esc(item)}</li>`).join("")}</ul></div></details><details><summary>Source bibliography &amp; review dates<span>${sourceList.length} ${sourceList.length === 1 ? "source" : "sources"}</span></summary><div><ol class="bibliography">${sourceList.map((source, index) => `<li id="source-${index + 1}">${sourceDetails(source)}</li>`).join("")}</ol></div></details><details id="ai-details"><summary>Optional source-bound AI explanation<span id="ai-availability">${aiAvailable ? "Available" : "Not configured"}</span></summary><div class="ai-detail"><p id="ai-status">${esc(aiStatus)}</p>${explanation}<button class="secondary-button" id="openai-button" type="button"${aiAvailable ? "" : " disabled"}>Generate source-bound explanation</button><p class="provenance" style="margin-top:12px">${esc(data.llm.detail)}${data.llm.model ? ` Model: ${esc(data.llm.model)}.` : ""}</p></div></details></section>`;
  }

  function render(data) {
    collectSources(data);
    graphFocusId = data.knowledge_graph.nodes.find((node) => node.kind === "disease" && data.disease.id && node.id.includes(data.disease.id))?.id || data.knowledge_graph.nodes[0]?.id || null;
    selectedGraphEdgeId = null;
    graphKindFilter = "all";
    graphSearchQuery = "";
    results.innerHTML = overview(data) + evidenceGraph(data) + candidates(data) + validation(data) + experiment(data) + review(data);
    $("#openai-button").addEventListener("click", () => {
      if (openaiEnabled && !fixtureMode && lastRequest) analyze({ ...lastRequest, use_openai: true }, true);
    });
    $("#graph-kind-filter").addEventListener("change", (event) => {
      graphKindFilter = event.target.value;
      $("#graph-node-browser").innerHTML = graphNodeBrowser(data);
    });
    $("#graph-node-search").addEventListener("input", (event) => {
      graphSearchQuery = event.target.value;
      $("#graph-node-browser").innerHTML = graphNodeBrowser(data);
    });
    updateMode(data);
  }

  results.addEventListener("click", (event) => {
    selectGraphControl(event.target.closest("[data-graph-node], [data-graph-edge]"));
  });
  results.addEventListener("keydown", (event) => {
    const control = event.target.closest("[data-graph-node], [data-graph-edge]");
    if (["Enter", " "].includes(event.key) && control?.namespaceURI === "http://www.w3.org/2000/svg") {
      event.preventDefault();
      selectGraphControl(control);
    }
  });
  if (typeof window !== "undefined") window.addEventListener("resize", () => {
    if (currentAnalysis && $("#graph-stage")) $("#graph-stage").innerHTML = graphSvg(currentAnalysis);
  });

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

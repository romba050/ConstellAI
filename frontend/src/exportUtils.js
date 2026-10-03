export function isoNow() {
  return new Date().toISOString();
}

export function safeSlug(s) {
  return String(s || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
}

export function downloadJSON(filenameBase, payload) {
  const ts = new Date().toISOString().replace(/[:.]/g, "-");
  const name = `${safeSlug(filenameBase || "medr_export")}_${ts}.json`;
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });

  const a = document.createElement("a");
  const href = URL.createObjectURL(blob);
  a.href = href;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(() => URL.revokeObjectURL(href), 2500);
}

export function buildExportEnvelope({ tabId, title, data }) {
  return {
    schema: "MED-R5_EXPORT_V1",
    generated_at: isoNow(),
    tab: tabId,
    title: title || "",
    data: data || {},
    governance: {
      research_mode: true,
      human_review_required: true,
      traceable_export: true,
      backend_dependency: "recommended",
      disclaimer:
        "Research-use workflow export. Outputs support hypothesis triage, QA review, and internal research discussion. Human review is required before any real-world decision.",
    },
  };
}

export function buildRareDiseaseCaseExport({
  diseaseId,
  geneText,
  effectiveDiseaseGenes,
  spilloverWeight,
  maxBundleItems,
  rankDepth,
  startYear,
  endYear,
  seed,
  analyzeData,
  memoryData,
}) {
  const disease = analyzeData?.disease || null;
  const primary = analyzeData?.primary || null;
  const deviation = analyzeData?.deviation || null;
  const addons = Array.isArray(analyzeData?.addons) ? analyzeData.addons : [];
  const bundle = analyzeData?.bundle || null;
  const futurePath = analyzeData?.future_path || null;
  const proposals = Array.isArray(analyzeData?.proposals) ? analyzeData.proposals : [];
  const simContext = analyzeData?.sim_context || memoryData || null;

  return buildExportEnvelope({
    tabId: "rare_disease",
    title: `${disease?.name || "custom rare disease"} case export`,
    data: {
      input: {
        disease_id: diseaseId || disease?.id || "custom",
        disease_name: disease?.name || null,
        disease_gene_text: geneText || "",
        disease_genes: effectiveDiseaseGenes || [],
        controls: {
          spillover_weight: Number(spilloverWeight || 0.12),
          max_bundle_items: Number(maxBundleItems || 4),
          rank_depth: Number(rankDepth || 8),
        },
        simulation_window: {
          start_year: Number(startYear || 1970),
          end_year: Number(endYear || 2005),
          seed: Number(seed || 1337),
        },
      },
      case_flow: {
        primary,
        deviation,
        addons,
        bundle,
        future_path: futurePath,
        proposals,
        sim_context: simContext,
      },
      legacy: {
        ranked: Array.isArray(analyzeData?.ranked) ? analyzeData.ranked : [],
        summary: analyzeData?.summary || {},
      },
      notes: {
        purpose: "q.pdf rare disease workflow state export",
        export_mode: "case_state",
      },
    },
  });
}

export function exportRareDiseaseCase(args) {
  const payload = buildRareDiseaseCaseExport(args);
  const diseaseName = args?.analyzeData?.disease?.name || args?.diseaseId || "rare_disease_case";
  downloadJSON(`${diseaseName}_rare_case`, payload);
  return payload;
}

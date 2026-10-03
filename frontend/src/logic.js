// frontend/src/logic.js

import { COMPOUND_DB, TARGET_INDEX, getObjectiveEvidenceForId } from "./mockData.js";

let RUNTIME_LIBRARY = null;

function buildIndex(items) {
  const index = {};
  for (const item of items || []) {
    for (const raw of item.targets || []) {
      const norm = normalizeTargetLabel(raw);
      const bare = norm.replace(/[↑↓]/g, "").trim();
      for (const key of [String(raw || "").trim(), norm, bare].filter(Boolean)) {
        if (!index[key]) index[key] = [];
        if (!index[key].includes(item.id)) index[key].push(item.id);
      }
    }
  }
  return index;
}

function inferTags(item) {
  const tags = new Set(Array.isArray(item.tags) ? item.tags : []);
  const name = String(item.name || "").toLowerCase();
  if (name.includes("nicotinamide") || name.includes("nr") || name.includes("nad")) tags.add("nad_booster");
  if (name.includes("niacin") || name.includes("nicotinamide") || name.includes("nr")) tags.add("b3_derivative");
  return Array.from(tags);
}

function normalizeRuntimeItem(item, fallbackKind = "compound") {
  const targets = Array.isArray(item?.targets)
    ? item.targets.map((target) => typeof target === "string" ? target : target?.gene || target?.label || target?.name || "").filter(Boolean)
    : [];
  return {
    ...item,
    id: item?.id || `${fallbackKind}_${String(item?.name || "item").toLowerCase().replace(/[^a-z0-9]+/g, "_")}`,
    name: item?.name || item?.label || "unnamed item",
    kind: item?.kind || fallbackKind,
    targets,
    liverLoad: Number(item?.liverLoad || item?.liver_load || 0),
    nadBoost: Number(item?.nadBoost || item?.nad_boost || 0),
    cypFlags: Array.isArray(item?.cypFlags) ? item.cypFlags : [],
    tags: inferTags(item),
    source: item?.source || "registry",
  };
}

export function setRuntimeMimicLibrary(compounds = [], physiology = []) {
  const runtimeCompounds = (compounds || []).map((item) => normalizeRuntimeItem(item, item?.kind || "compound"));
  const runtimePhysiology = (physiology || []).map((item) => normalizeRuntimeItem(item, item?.kind || "physiology"));
  const items = [...runtimeCompounds, ...runtimePhysiology];
  RUNTIME_LIBRARY = {
    items,
    byId: new Map(items.map((item) => [item.id, item])),
    targetIndex: buildIndex(items),
  };
}

function activeLibrary() {
  if (RUNTIME_LIBRARY?.items?.length) return RUNTIME_LIBRARY;
  return { items: COMPOUND_DB, byId: new Map(COMPOUND_DB.map((c) => [c.id, c])), targetIndex: TARGET_INDEX };
}

export function getCompoundById(id) {
  return activeLibrary().byId.get(id) || null;
}

export function getCompoundByName(name) {
  const needle = String(name || "").trim().toLowerCase();
  if (!needle) return null;
  return activeLibrary().items.find((c) => String(c.id || "").trim().toLowerCase() === needle || String(c.name || "").trim().toLowerCase() === needle) || null;
}

export function normalizeTargetLabel(label) {
  let s = String(label || "").trim();
  s = s.replace(/\s*\([^)]*\)\s*/g, " ").trim();
  s = s.replace(/\s+/g, " ").trim();
  return s;
}

export function compoundsForTarget(targetLabel) {
  const raw = String(targetLabel || "").trim();
  const norm = normalizeTargetLabel(raw);
  const bare = norm.replace(/[↑↓]/g, "").trim();
  const ids = activeLibrary().targetIndex[raw] || activeLibrary().targetIndex[norm] || activeLibrary().targetIndex[bare] || [];
  return ids.map(getCompoundById).filter(Boolean);
}

export function compoundsForDrug(drug) {
  const ids = Array.isArray(drug?.candidateMimics) ? drug.candidateMimics : [];
  return ids.map(getCompoundByName).filter(Boolean);
}

export function normalizeGeneLike(label) {
  return String(label || "").trim();
}

export function scoreStack(compounds) {
  const liverLoad = compounds.reduce((a, c) => a + (c.liverLoad || 0), 0);
  const nadBoost = compounds.reduce((a, c) => a + (c.nadBoost || 0), 0);
  const cypFlags = {};
  for (const c of compounds) for (const f of c.cypFlags || []) cypFlags[f] = (cypFlags[f] || 0) + 1;
  const nadBoosters = compounds.filter((c) => (c.tags || []).includes("nad_booster"));
  const b3Derivs = compounds.filter((c) => (c.tags || []).includes("b3_derivative"));
  return { liverLoad, nadBoost, cypFlags, nadBoosterCount: nadBoosters.length, b3DerivativeCount: b3Derivs.length };
}

export function interactionReport(compounds) {
  const score = scoreStack(compounds);
  const warnings = [];
  if (score.liverLoad >= 7) warnings.push({ level: "HIGH", title: "HIGH LIVER LOAD", detail: `TOTAL LIVER LOAD SCORE = ${score.liverLoad}. CONSIDER REMOVING HIGHEST-LOAD COMPOUNDS.` });
  else if (score.liverLoad >= 4) warnings.push({ level: "MED", title: "MODERATE LIVER LOAD", detail: `TOTAL LIVER LOAD SCORE = ${score.liverLoad}. MONITOR STACK SIZE AND DOSE.` });
  if (score.nadBoost >= 7) warnings.push({ level: "HIGH", title: "METABOLIC REDUNDANCY", detail: `METABOLIC ACTIVATION SCORE = ${score.nadBoost}. MULTIPLE SUPPORTS MAY BE PUSHING THE SAME REGENERATIVE AXIS TOO HARD.` });
  else if (score.nadBoost >= 4) warnings.push({ level: "MED", title: "OVERLAPPING METABOLIC PUSH", detail: `METABOLIC ACTIVATION SCORE = ${score.nadBoost}. CONSIDER A LEANER STACK WITH FEWER REDUNDANT SUPPORTS.` });
  if (score.b3DerivativeCount >= 2) warnings.push({ level: "MED", title: "SAME-AXIS REDUNDANCY", detail: "MULTIPLE SUPPORTS APPEAR TO BE HITTING A VERY SIMILAR METABOLIC AXIS." });
  const cypHot = Object.entries(score.cypFlags).filter(([, n]) => n >= 2);
  if (cypHot.length) warnings.push({ level: "MED", title: "CYP OVERLAP", detail: `MULTIPLE COMPOUNDS SHARE CYP FLAGS: ${cypHot.map(([k]) => k).join(", ")}.` });
  return { score, warnings };
}

export function optimizeStack({ selected, mandatoryIds = [] }) {
  const mandatory = new Set(mandatoryIds);
  let cur = [...selected];
  for (let i = 0; i < 12; i++) {
    const { score } = interactionReport(cur);
    if (score.liverLoad < 7 && score.nadBoost < 7) break;
    let worst = null;
    for (const c of cur) {
      if (mandatory.has(c.id)) continue;
      const penalty = (c.liverLoad || 0) * 2 + (c.nadBoost || 0) * 2 + (c.cypFlags || []).length;
      if (!worst || penalty > worst.penalty) worst = { id: c.id, penalty };
    }
    if (!worst) break;
    cur = cur.filter((c) => c.id !== worst.id);
  }
  return cur;
}

export function generateEarlyKillExperiments({ drug, chosenTargets = [], selectedCompounds = [] }) {
  const drugName = drug?.name || "THE DRUG";
  const tRaw = chosenTargets.slice(0, 8).map((x) => String(x || "").trim()).filter(Boolean);
  const t = tRaw.map(normalizeTargetLabel);
  const c = selectedCompounds.slice(0, 8);
  const tLabel = t.length ? t.join(", ") : "TARGETS";
  const cLabel = c.length ? c.map((x) => x.name).join(", ") : "CANDIDATE COMPOUNDS";
  const joined = `${t.join(" ")} ${drugName}`.toUpperCase();
  let targetFamily = "mixed biology";
  if (/EGFR|BCR-ABL|KIT|PDGFRA|MAPK|PI3K|AKT|MTOR/.test(joined)) targetFamily = "kinase / growth signaling";
  else if (/PDCD1|PD-1|IFNG|GZMB|PRF1/.test(joined)) targetFamily = "immune checkpoint / cytotoxic";
  else if (/AMPK|SREBF1|METABOLIC/.test(joined)) targetFamily = "metabolic control";
  else if (/ESR1|ER/.test(joined)) targetFamily = "hormonal signaling";
  const nT = Math.min(8, t.length || 1);
  const nC = Math.min(8, c.length || 1);
  const base = 2200 + 550 * nT + 420 * nC;
  const mk = ({ i, tier, title, assayType, days, costMul, hypothesis, why, stopSignal }) => {
    const tierUpside = tier === "heavy" ? 1.18 : tier === "medium" ? 1.0 : 0.82;
    const cost = Math.round(base * costMul);
    const profit = Math.round((90000 + 18000 * nT + 12000 * nC) * (0.72 + 0.1 * i) * tierUpside);
    const failProb = Math.min(85, Math.round((26 + i * 8) + (tier === "heavy" ? 10 : tier === "medium" ? 5 : 0) + (nC >= 5 ? 8 : 0)));
    return { id: `${drug?.id || "drug"}_ek_${i}`, title, tier, assayType, targetFamily, hypothesis, why, costEUR: cost, profitEUR: profit, failProb, stopSignal, days };
  };
  return [
    mk({ i: 1, tier: "cheap", title: "EARLY-KILL 1 · TARGET ENGAGEMENT PROXY", assayType: "western / phospho / reporter proxy", days: 7, costMul: 0.82, hypothesis: `IF ${drugName} SHOWS A CONSISTENT SIGNATURE ON (${tLabel}), THEN ${cLabel} SHOULD MATCH A SUBSET IN A LOW-COST TARGET-ENGAGEMENT PROXY.`, why: "LOGIC: FIRST PROVE THERE IS EVEN A SIGNAL WINDOW BEFORE SPENDING INTO HEAVIER WORK.", stopSignal: "STOP IF NO TARGET-ENGAGEMENT SIGNAL APPEARS AT ANY NON-TOXIC DOSE RANGE." }),
    mk({ i: 2, tier: "cheap", title: "EARLY-KILL 2 · MINI PATHWAY PANEL", assayType: "qPCR / focused signature panel", days: 10, costMul: 0.98, hypothesis: `IF ${cLabel} IS A TRUE PARTIAL MIMIC OF ${drugName}, THEN A SMALL SIGNATURE PANEL SHOULD SHIFT IN THE SAME DIRECTION AS (${tLabel}).`, why: "LOGIC: SMALL PANELS BEAT STORYTELLING. GET A FAST CORRELATION CHECK BEFORE FULL OMICS.", stopSignal: "STOP IF SIGNATURE CORRELATION IS WEAK OR ONLY APPEARS IN A SINGLE REPLICATE." }),
    mk({ i: 3, tier: "medium", title: "EARLY-KILL 3 · PHENOTYPIC SHIFT", assayType: "viability / stress / inflammatory phenotype", days: 12, costMul: 1.12, hypothesis: `IF THE TARGET SHIFT IS REAL, THEN A SIMPLE PHENOTYPE SHOULD MOVE WITH ${cLabel} IN THE EXPECTED DIRECTION.`, why: "LOGIC: TARGET MATCH WITHOUT A PHENOTYPE IS OFTEN A DEAD END.", stopSignal: "STOP IF PHENOTYPE SHIFT IS LESS THAN 10 PERCENT VS CONTROL OR ONLY APPEARS AT TOXIC LEVELS." }),
    mk({ i: 4, tier: "medium", title: "EARLY-KILL 4 · COMBO REDUNDANCY MATRIX", assayType: "small factorial combo screen", days: 14, costMul: 1.28, hypothesis: `IF MULTIPLE COMPOUNDS ARE NEEDED, A SMALL MATRIX SHOULD SHOW NON-REDUNDANT CONTRIBUTION RATHER THAN JUST MORE MASS.`, why: "LOGIC: STACKS FAIL WHEN THEY ARE REDUNDANT OR INTERACTION-HEAVY. TEST STRUCTURE EARLY.", stopSignal: "STOP IF THE BEST SINGLE AGENT BEATS THE COMBO OR IF THE COMBO ADDS TOXICITY WITHOUT SIGNAL." }),
    mk({ i: 5, tier: "heavy", title: "EARLY-KILL 5 · OFF-TARGET / SAFETY WINDOW", assayType: "counter-screen / hepatic / off-target panel", days: 16, costMul: 1.55, hypothesis: `IF ${cLabel} REALLY MIMICS ${drugName}, IT SHOULD KEEP SOME SIGNAL WHILE MAINTAINING A BASIC SAFETY WINDOW.`, why: "LOGIC: CHEAP SIGNAL WITHOUT WINDOW IS NOT A PRODUCT CANDIDATE.", stopSignal: "STOP IF THE SIGNAL WINDOW COLLAPSES ON COUNTER-SCREEN OR HEPATIC STRESS." }),
  ];
}

export function targetHitCount(item, targetsSelected = []) {
  const selected = new Set((targetsSelected || []).map((t) => normalizeTargetLabel(t)));
  return (item?.targets || []).map((t) => normalizeTargetLabel(t)).filter((t) => selected.has(t)).length;
}

export function rankMimicCandidates(targetsSelected = [], rows = []) {
  return [...rows].map((row) => ({ ...row, _hitCount: targetHitCount(row, targetsSelected), _refCount: (getObjectiveEvidenceForId(row.id)?.refs || []).length }))
    .sort((a, b) => b._hitCount - a._hitCount || b._refCount - a._refCount || String(a.name || "").localeCompare(String(b.name || "")));
}

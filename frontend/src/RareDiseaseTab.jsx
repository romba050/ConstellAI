import React, { useEffect, useMemo, useState } from "react";
import {
  apiRareAnalyze,
  apiRareDiseases,
  apiRareFillRankings,
  apiRareProposalProtocol,
  apiRareSimMemory,
  apiRareSimTrain,
  apiRegistrySummary,
} from "./apiClient";
import { exportRareDiseaseCase } from "./exportUtils";
import {
  getHistoricalReplayBank,
  replayHistoricalCase,
  seedHistoricalReplayBank,
  storeHistoricalHit,
  trainHistoricalReplay,
} from "./rareHistoryClient";

function uniq(arr) {
  return Array.from(new Set((arr || []).filter(Boolean)));
}

function normalizeGene(value) {
  return String(value || "")
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9_-]/g, "")
    .replace(/-/g, "");
}

function normalizeDirection(value) {
  const raw = String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[,_-]+/g, " ")
    .replace(/\s+/g, " ");

  if (!raw) return "unknown";
  if (["up", "high", "elevated", "overactive", "over activated", "hyperactive", "gain", "gain of function", "gof"].includes(raw)) return "up";
  if (["down", "low", "reduced", "suppressed", "underactive", "under activated", "loss", "loss of function", "lof"].includes(raw)) return "down";
  if (raw.includes("loss of function")) return "loss of function";
  if (raw.includes("gain of function")) return "gain of function";
  if (raw.includes("overactive") || raw.includes("hyperactive")) return "overactive";
  if (raw.includes("underactive")) return "underactive";
  return raw;
}

function parseSignedGeneText(text) {
  const chunks = String(text || "")
    .split(/[\n;,|]+/g)
    .map((chunk) => String(chunk || "").trim())
    .filter(Boolean);

  const entries = [];
  for (const chunk of chunks) {
    const tokens = chunk.split(/\s+/).filter(Boolean);
    if (!tokens.length) continue;
    const gene = normalizeGene(tokens[0]);
    if (!gene) continue;
    const direction = normalizeDirection(tokens.slice(1).join(" "));
    entries.push({ gene, direction });
  }
  return uniq(entries.map((row) => `${row.gene}::${row.direction}`)).map((key) => {
    const [gene, direction] = key.split("::");
    return { gene, direction: direction || "unknown" };
  });
}

function signedEntriesFromDisease(selectedDisease, geneText, diseaseId) {
  if (diseaseId === "custom") {
    const custom = parseSignedGeneText(geneText);
    if (custom.length) return custom;
  }

  const genes = Array.isArray(selectedDisease?.genes) ? selectedDisease.genes : [];
  const directions = selectedDisease?.directions || {};
  return uniq(genes.map(normalizeGene)).map((gene) => ({
    gene,
    direction: normalizeDirection(directions?.[gene] || "unknown"),
  }));
}

function num(v, digits = 3) {
  const n = Number(v || 0);
  if (!Number.isFinite(n)) return "0.000";
  return n.toFixed(digits);
}

function pct(v) {
  const n = Number(v || 0);
  if (!Number.isFinite(n)) return "0%";
  return `${Math.round(n * 100)}%`;
}

function directionTone(direction) {
  const d = normalizeDirection(direction);
  if (["up", "overactive", "gain of function"].includes(d)) return "warn";
  if (["down", "underactive", "loss of function"].includes(d)) return "soft";
  return "default";
}

function directionText(direction) {
  const d = normalizeDirection(direction);
  if (d === "unknown") return "signal present";
  return d;
}

function neededAction(direction) {
  const d = normalizeDirection(direction);
  if (["up", "overactive", "gain of function"].includes(d)) return "needs downregulation";
  if (["down", "underactive", "loss of function"].includes(d)) return "needs restoration / activation";
  return "needs targeted modulation";
}

function signalLabel(gene, direction) {
  const d = normalizeDirection(direction);
  return d === "unknown" ? gene : `${gene} ${directionText(d)}`;
}

function StatCard({ label, value, sub }) {
  return (
    <div style={styles.statCard}>
      <div style={styles.statLabel}>{label}</div>
      <div style={styles.statValue}>{value}</div>
      {!!sub && <div style={styles.statSub}>{sub}</div>}
    </div>
  );
}

function Pill({ children, tone = "default" }) {
  const palette =
    tone === "good"
      ? styles.pillGood
      : tone === "warn"
      ? styles.pillWarn
      : tone === "bad"
      ? styles.pillBad
      : tone === "soft"
      ? styles.pillSoft
      : styles.pillDefault;

  return <span style={{ ...styles.pill, ...palette }}>{children}</span>;
}

function SectionCard({ eyebrow, title, children, right }) {
  return (
    <div style={styles.sectionCard}>
      <div style={styles.sectionHeader}>
        <div>
          {eyebrow ? <div style={styles.eyebrow}>{eyebrow}</div> : null}
          <div style={styles.sectionTitle}>{title}</div>
        </div>
        {right ? <div>{right}</div> : null}
      </div>
      <div style={styles.sectionBody}>{children}</div>
    </div>
  );
}

function GenePanel({ title, genes, tone = "default", empty = "none" }) {
  return (
    <div style={styles.subPanel}>
      <div style={styles.subPanelTitle}>{title}</div>
      <div style={styles.pillWrap}>
        {genes?.length ? genes.map((g) => <Pill key={g} tone={tone}>{g}</Pill>) : <div style={styles.emptyText}>{empty}</div>}
      </div>
    </div>
  );
}

function SignalListPanel({ title, entries, covered = false, empty = "none" }) {
  return (
    <div style={styles.subPanel}>
      <div style={styles.subPanelTitle}>{title}</div>
      {entries?.length ? (
        <div style={styles.signalList}>
          {entries.map((entry) => (
            <div key={`${entry.gene}_${entry.direction}_${entry.status || "x"}`} style={styles.signalRow}>
              <div style={styles.signalLeft}>
                <Pill tone={directionTone(entry.direction)}>{signalLabel(entry.gene, entry.direction)}</Pill>
              </div>
              <div style={styles.signalArrow}>→</div>
              <div style={styles.signalRight}>
                <span style={styles.signalAction}>{neededAction(entry.direction)}</span>
                {covered ? <span style={styles.signalCovered}>covered</span> : <span style={styles.signalOpen}>open</span>}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={styles.emptyText}>{empty}</div>
      )}
    </div>
  );
}

function CollapsibleBlock({ title, defaultOpen = false, children, compact = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={compact ? styles.subPanel : styles.sectionCompact}>
      <div style={styles.collapseHead}>
        <div style={compact ? styles.subPanelTitle : styles.sectionMiniTitle}>{title}</div>
        <button style={styles.collapseButton} onClick={() => setOpen((v) => !v)}>{open ? 'collapse' : 'expand'}</button>
      </div>
      {open ? <div style={compact ? undefined : styles.collapseBody}>{children}</div> : null}
    </div>
  );
}

function confidenceBand(score) {
  if (score >= 0.75) return 'high';
  if (score >= 0.5) return 'moderate';
  return 'early';
}

function evidenceTierFromItem(item) {
  const explicit = String(item?.evidence_tier || '').trim().toLowerCase();
  if (explicit) return explicit;
  const text = JSON.stringify(item || {}).toLowerCase();
  if (text.includes('guideline') || text.includes('meta') || text.includes('human')) return 'human';
  if (text.includes('listed') || text.includes('approved')) return 'listed';
  if (text.includes('preclinical')) return 'preclinical';
  if (text.includes('mechan')) return 'mechanistic';
  return 'hypothesis';
}

function traceText(trace) {
  return Array.isArray(trace) && trace.length ? trace.join(' · ') : 'none';
}

function computeModelConfidence({ primary, effectiveDiseaseGenes, addons, bundle, spilloverGenes }) {
  const total = Math.max(1, effectiveDiseaseGenes.length || 0);
  const coverage = Number(primary?.coverage_count || 0) / total;
  const evidenceRaw = addons.length ? addons.slice(0, 3).reduce((acc, item) => acc + (evidenceTierFromItem(item) === 'human' ? 1 : evidenceTierFromItem(item) === 'mechanistic' ? 0.65 : 0.35), 0) / Math.min(3, addons.length) : 0.45;
  const bundleSize = Math.max(1, (bundle?.bundle_ids || []).length || 1);
  const bundleScore = bundleSize === 1 ? 1 : bundleSize === 2 ? 0.8 : bundleSize === 3 ? 0.6 : 0.45;
  const spillPenalty = Math.min(0.35, (spilloverGenes?.length || 0) * 0.06);
  const score = Math.max(0.1, Math.min(0.96, coverage * 0.45 + evidenceRaw * 0.25 + bundleScore * 0.18 + (1 - spillPenalty) * 0.12));
  return { score, coverage, evidenceRaw, bundleScore, spillPenalty };
}


function treatmentModeLabel(mode) {
  if (mode === 'mode_1') return 'drugs only';
  if (mode === 'mode_2') return 'drugs + natural compounds';
  return 'drugs + compounds + physiology';
}

function clamp01(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

function buildFactorStrip(plan) {
  const scoreToSign = (v) => {
    const n = Math.max(0, Math.min(1, Number(v || 0)));
    if (n >= 0.75) return '+++';
    if (n >= 0.5) return '++';
    if (n >= 0.25) return '+';
    if (n > 0) return '~';
    return '-';
  };

  const coverage = plan?.coverageRatio || 0;
  const spilloverPenalty = 1 - clamp01((plan?.spilloverCount || 0) / 4);
  const burdenPenalty = 1 - clamp01((plan?.burdenCount || 0) / 6);
  const physiologySupport = clamp01((plan?.physiologyCount || 0) / 6);
  const compoundSupport = clamp01((plan?.compoundCount || 0) / 4);
  const riskPenalty = 1 - clamp01((plan?.riskCount || 0) / 5);

  return [
    { label: 'coverage', val: scoreToSign(coverage) },
    { label: 'spillover', val: scoreToSign(spilloverPenalty) },
    { label: 'burden', val: scoreToSign(burdenPenalty) },
    { label: 'physiology', val: scoreToSign(physiologySupport) },
    { label: 'compound', val: scoreToSign(compoundSupport) },
    { label: 'risk', val: scoreToSign(riskPenalty) },
  ];
}

function summarizeSpecializedPlan(mode, res, totalSignals) {
  if (!res) {
    return {
      mode,
      label: treatmentModeLabel(mode),
      score: 0,
      coverageRatio: 0,
      spilloverCount: 0,
      burdenCount: 0,
      physiologyCount: 0,
      compoundCount: 0,
      riskCount: 0,
      evidenceScore: 0,
      primaryName: 'none',
      bundleNames: [],
      recommendation: 'no output',
      caveat: 'analyze did not return a result',
      notes: [],
    };
  }

  const primary = res?.primary || {};
  const bundle = res?.bundle || {};
  const deviation = res?.deviation || {};
  const addons = Array.isArray(res?.addons) ? res.addons : [];
  const safety = res?.safety_decision || {};
  const bundleIds = Array.isArray(bundle?.bundle_ids) ? bundle.bundle_ids.filter(Boolean) : [];
  const bundleNames = Array.isArray(bundle?.bundle_names) ? bundle.bundle_names.filter(Boolean) : [];
  const coverageRatio = clamp01(bundle?.coverage_ratio || primary?.coverage_ratio || deviation?.coverage_ratio || 0);
  const spilloverCount = Number(bundle?.spillover_count || (bundle?.spillover_genes || []).length || primary?.spillover_count || 0);
  const burdenCount = Math.max(1, bundleIds.length || (primary?.id ? 1 : 0));
  const physiologyCount = addons.filter((item) => item?.kind === 'physiology').length;
  const compoundCount = addons.filter((item) => item?.kind === 'compound').length;
  const riskCount = Array.isArray(safety?.risks) ? safety.risks.length : 0;
  const evidenceWindow = addons.slice(0, 4);
  const evidenceScore = evidenceWindow.length
    ? evidenceWindow.reduce((acc, item) => {
        const tier = evidenceTierFromItem(item);
        return acc + (tier === 'human' ? 1 : tier === 'listed' ? 0.82 : tier === 'preclinical' ? 0.62 : tier === 'mechanistic' ? 0.54 : 0.34);
      }, 0) / evidenceWindow.length
    : 0.4;

  const burdenScore = 1 / burdenCount;
  const spillScore = 1 / (1 + Math.max(0, spilloverCount));
  const physiologyBonus = Math.min(1, physiologyCount / 2);
  const riskScore = Math.max(0, 1 - riskCount * 0.12);
  const score = clamp01(
    coverageRatio * 0.46 +
    spillScore * 0.18 +
    burdenScore * 0.14 +
    evidenceScore * 0.12 +
    physiologyBonus * 0.05 +
    riskScore * 0.05
  );

  const notes = [
    `${Math.round(coverageRatio * 100)}% closure across ${Math.max(1, totalSignals || 0)} signals`,
    `${spilloverCount} spillover signals`,
    `${burdenCount} active treatment items`,
  ];
  if (physiologyCount) notes.push(`${physiologyCount} physiology supports available`);
  if (compoundCount) notes.push(`${compoundCount} compound bridge options available`);
  if (riskCount) notes.push(`${riskCount} lifestyle friction flags entered`);

  let recommendation = 'balanced protocol';
  if (mode === 'mode_1') recommendation = 'lowest-complexity drug path';
  if (mode === 'mode_2') recommendation = 'drug + compound bridge path';
  if (mode === 'mode_3') recommendation = 'full specialized support path';

  let caveat = 'mechanism-first recommendation support only';
  if (spilloverCount >= 3) caveat = 'spillover pressure is still elevated';
  else if (coverageRatio < 0.75) caveat = 'coverage gap still visible';
  else if (riskCount) caveat = 'patient habits may erode protocol stability';

  return {
    mode,
    label: treatmentModeLabel(mode),
    score,
    coverageRatio,
    spilloverCount,
    burdenCount,
    physiologyCount,
    compoundCount,
    riskCount,
    evidenceScore,
    primaryName: primary?.name || 'none',
    bundleNames,
    recommendation,
    caveat,
    notes,
  };
}

function signalStatus(entry, coverageGenes, bundleCoveredEntries) {
  if (coverageGenes.includes(entry.gene)) return 'closed';
  if (bundleCoveredEntries.some((row) => row.gene === entry.gene)) return 'partial';
  return 'open';
}

function signalStatusTone(status) {
  return status === 'closed' ? 'good' : status === 'partial' ? 'warn' : 'bad';
}

function closureAction(status, primaryName, bundleNames) {
  if (status === 'closed') return `primary closes this signal`;
  if (status === 'partial') return `${bundleNames[0] || 'add-on path'} may partially close this`;
  return 'no strong closure yet';
}

function MechanismClosureBar({ entries, coverageGenes, bundleCoveredEntries, primaryName, bundleNames }) {
  const closed = entries.filter((entry) => signalStatus(entry, coverageGenes, bundleCoveredEntries) === 'closed').length;
  const partial = entries.filter((entry) => signalStatus(entry, coverageGenes, bundleCoveredEntries) === 'partial').length;
  const total = Math.max(1, entries.length);
  const progress = ((closed + partial * 0.5) / total) * 100;
  return (
    <div style={styles.subPanel}>
      <div style={styles.subPanelTitle}>mechanism closure score</div>
      <div style={styles.progressBar}><div style={{ ...styles.progressFill, width: `${Math.max(6, progress)}%` }} /></div>
      <div style={styles.progressMeta}>disease neutralization {Math.round(progress)}% · closed {closed} · partial {partial} · open {Math.max(0, total - closed - partial)}</div>
      <div style={styles.progressRows}>
        {entries.map((entry) => {
          const status = signalStatus(entry, coverageGenes, bundleCoveredEntries);
          const percent = status === 'closed' ? 100 : status === 'partial' ? 55 : 12;
          return (
            <div key={`${entry.gene}_${entry.direction}`} style={styles.progressRow}>
              <div style={styles.progressSignal}><Pill tone={directionTone(entry.direction)}>{signalLabel(entry.gene, entry.direction)}</Pill></div>
              <div style={styles.progressTrack}><div style={{ ...styles.progressMiniFill, width: `${percent}%`, background: status === 'closed' ? 'rgba(108,239,164,0.88)' : status === 'partial' ? 'rgba(255,214,120,0.88)' : 'rgba(255,120,120,0.8)' }} /></div>
              <div style={styles.progressStatus}><Pill tone={signalStatusTone(status)}>{status}</Pill></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BundleRankingPanel({ addons, deviationDirections, directionMap, bundleNames }) {
  const ranking = useMemo(() => {
    const rows = (addons || []).map((item) => {
      const covered = (item.covers_deviation_genes || []).length;
      const spill = (item.new_spillover_genes || []).length;
      const evidenceTier = evidenceTierFromItem(item);
      const evidenceScore = evidenceTier === 'human' ? 1 : evidenceTier === 'mechanistic' ? 0.65 : 0.35;
      return { item, covered, spill, evidenceTier, evidenceScore, lowRiskScore: covered - spill * 0.8 + evidenceScore * 0.4 };
    });
    const bestSingle = [...rows].sort((a,b)=>(b.covered - a.covered) || (a.spill - b.spill))[0] || null;
    const bestEvidence = [...rows].sort((a,b)=>(b.evidenceScore - a.evidenceScore) || (b.covered - a.covered))[0] || null;
    const bestLowRisk = [...rows].sort((a,b)=>(b.lowRiskScore - a.lowRiskScore))[0] || null;
    return { bestSingle, bestEvidence, bestLowRisk };
  }, [addons]);

  const renderCard = (label, row) => row ? (
    <div style={styles.proposalCard}>
      <div style={styles.proposalTitle}>{label}</div>
      <div style={styles.proposalLine}><strong>candidate:</strong> {row.item.name}</div>
      <div style={styles.proposalLine}><strong>closure:</strong> {(row.item.covers_deviation_genes || []).map((g) => signalLabel(g, deviationDirections[g] || directionMap[g] || 'unknown')).join(', ') || 'none'}</div>
      <div style={styles.proposalLine}><strong>evidence:</strong> {row.evidenceTier}</div>
      <div style={styles.proposalLine}><strong>interaction / spillover:</strong> {row.spill ? `${row.spill} new spillover genes` : 'low'}</div>
      <div style={styles.proposalLine}><strong>fit:</strong> {bundleNames.includes(row.item.name) ? 'already in selected bundle' : 'available as upgrade path'}</div>
    </div>
  ) : <div style={styles.emptyText}>no bundle ranking yet</div>;

  return (
    <div style={styles.proposalGrid}>
      {renderCard('best single add-on', ranking.bestSingle)}
      {renderCard('best evidence-backed path', ranking.bestEvidence)}
      {renderCard('best low-risk path', ranking.bestLowRisk)}
    </div>
  );
}


function computeRareSynergyRows({ addons, bundleNames, deviationDirections, directionMap }) {
  return (addons || []).map((item) => {
    const covered = (item.covers_deviation_genes || []).map((gene) => ({
      gene,
      direction: deviationDirections[gene] || directionMap[gene] || 'unknown',
    }));
    const directionFitCount = covered.filter((row) => ['down', 'underactive', 'loss of function', 'up', 'overactive', 'gain of function'].includes(normalizeDirection(row.direction))).length;
    const spill = (item.new_spillover_genes || []).length;
    const evidenceTier = evidenceTierFromItem(item);
    const evidenceScore = evidenceTier === 'human' ? 1.0 : evidenceTier === 'mechanistic' ? 0.7 : 0.4;
    const chosen = bundleNames.includes(item.name);
    const score = Number((((item.net_gain || 0) * 1.6) + covered.length * 1.4 + directionFitCount * 0.5 + evidenceScore - spill * 0.9 + (chosen ? 0.35 : 0)).toFixed(2));
    return { item, covered, spill, evidenceTier, evidenceScore, chosen, score };
  }).sort((a, b) => b.score - a.score || b.covered.length - a.covered.length || a.spill - b.spill).slice(0, 6);
}

function RareSynergyPanel({ addons, bundleNames, deviationDirections, directionMap }) {
  const rows = useMemo(
    () => computeRareSynergyRows({ addons, bundleNames, deviationDirections, directionMap }),
    [addons, bundleNames, deviationDirections, directionMap]
  );
  const motifRows = useMemo(() => {
    const map = new Map();
    for (const row of rows) {
      for (const entry of row.covered || []) {
        const key = signalLabel(entry.gene, entry.direction);
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(row.item.name);
      }
    }
    return Array.from(map.entries())
      .map(([signal, names]) => ({ signal, names: Array.from(new Set(names)).slice(0, 4), count: new Set(names).size }))
      .sort((a, b) => b.count - a.count || a.signal.localeCompare(b.signal))
      .slice(0, 6);
  }, [rows]);

  return (
    <SectionCard eyebrow="Synergy layer" title="what complements the primary path, and what creates cross-signal conflict">
      {rows.length ? (
        <>
        {!!motifRows.length && (
          <div style={{...styles.subMiniPanel, marginBottom: 14}}>
            <div style={styles.subMiniTitle}>co-support motifs emerging from the bundle</div>
            <div style={styles.pillWrap}>
              {motifRows.map((row) => (
                <Pill key={row.signal} tone="neutral">{row.signal} · {row.names.join(' + ')}</Pill>
              ))}
            </div>
          </div>
        )}
        <div style={styles.addonGrid}>
          {rows.map((row) => (
            <div key={row.item.id} style={styles.addonCard}>
              <div style={styles.addonName}>{row.item.name}</div>
              <div style={styles.addonScore}>synergy score {num(row.score, 2)} · net gain {num(row.item.net_gain, 2)}</div>

              <div style={styles.subMiniPanel}>
                <div style={styles.subMiniTitle}>helps these disease signals</div>
                <div style={styles.pillWrap}>
                  {row.covered.length ? row.covered.map((entry) => (
                    <Pill key={`${row.item.id}_${entry.gene}`} tone="good">{signalLabel(entry.gene, entry.direction)}</Pill>
                  )) : <div style={styles.emptyText}>none</div>}
                </div>
              </div>

              <div style={styles.subMiniPanel}>
                <div style={styles.subMiniTitle}>cross-signal conflict</div>
                <div style={styles.pillWrap}>
                  {row.item.new_spillover_genes?.length ? row.item.new_spillover_genes.map((g) => <Pill key={g} tone="bad">{g}</Pill>) : <div style={styles.emptyText}>low</div>}
                </div>
              </div>

              <div style={styles.metaGrid}>
                <div style={styles.metaCell}><strong>evidence posture:</strong> {row.evidenceTier}</div>
                <div style={styles.metaCell}><strong>bundle fit:</strong> {row.chosen ? 'already selected in bundle' : 'candidate complement only'}</div>
                <div style={styles.metaCell}><strong>support density:</strong> {row.covered.length} disease signals · spill {row.spill}</div>
                <div style={styles.metaCell}><strong>mechanistic reading:</strong> {row.covered.length >= 2 ? 'multi-signal support' : 'narrow support'}{row.spill ? ' with spillover watch' : ' with low cross-signal pressure'}</div>
              </div>
            </div>
          ))}
        </div>
        </>
      ) : (
        <div style={styles.emptyText}>run analyze first</div>
      )}
    </SectionCard>
  );
}


function classifyBridgeType(item) {
  const kind = String(item?.kind || '').toLowerCase();
  if (kind === 'drug') return 'medicine anchor';
  if (kind === 'compound') return 'natural compound';
  if (kind === 'physiology') return 'physiology support';
  return kind || 'support';
}

function bridgeRiskLabel(score) {
  if (score >= 0.66) return 'high';
  if (score >= 0.34) return 'moderate';
  return 'low';
}

function bridgeDecisionLabel(score) {
  if (score >= 0.72) return 'strong';
  if (score >= 0.5) return 'watch';
  return 'weak';
}

function buildRareBridgeRows({ primary, addons, signedDiseaseEntries, deviationDirections, directionMap, bundleNames }) {
  const diseaseGeneSet = new Set((signedDiseaseEntries || []).map((row) => row.gene));
  const diseaseSignalTotal = Math.max(1, (signedDiseaseEntries || []).length || 0);

  return (addons || []).map((item) => {
    const covered = (item.covers_deviation_genes || []).map((gene) => ({
      gene,
      direction: deviationDirections[gene] || directionMap[gene] || 'unknown',
    }));
    const spillover = uniq(item.new_spillover_genes || []);
    const outside = spillover.filter((gene) => !diseaseGeneSet.has(gene));
    const kind = classifyBridgeType(item);
    const evidenceTier = evidenceTierFromItem(item);
    const evidenceScore = evidenceTier === 'human' ? 1 : evidenceTier === 'listed' ? 0.85 : evidenceTier === 'mechanistic' ? 0.7 : evidenceTier === 'preclinical' ? 0.55 : 0.35;
    const chosen = bundleNames.includes(item.name);
    const netGain = Number(item.net_gain || 0);
    const closureScore = clamp01(covered.length / diseaseSignalTotal);
    const gainScore = clamp01((netGain + 0.15) / 0.65);
    const bundleFitScore = chosen ? 1 : clamp01(0.45 + covered.length * 0.15 - spillover.length * 0.08);
    const completionScore = clamp01(
      kind === 'physiology support'
        ? (covered.length ? 0.82 : 0.62)
        : kind === 'natural compound'
        ? (covered.length ? 0.72 : 0.35)
        : covered.length
        ? 0.68
        : 0.28
    );
    const riskScore = clamp01(outside.length * 0.22 + Math.max(0, spillover.length - outside.length) * 0.12);
    const decisionScore = clamp01(
      closureScore * 0.38 +
      evidenceScore * 0.20 +
      gainScore * 0.16 +
      bundleFitScore * 0.11 +
      completionScore * 0.15 -
      riskScore * 0.24
    );
    const bridgeStrength = Number((covered.length * 1.5 + evidenceScore + (chosen ? 0.4 : 0) - spillover.length * 0.9).toFixed(2));
    const mimicFit = covered.length ? 'usable bridge' : spillover.length ? 'deviation-heavy bridge' : 'dead-end bridge';
    const safeWindow = clamp01(1 - riskScore);
    const completionLabel = kind === 'physiology support' ? 'physiology completion' : covered.length >= 2 ? 'multi-signal completion' : covered.length ? 'partial completion' : 'weak completion';
    return {
      item,
      kind,
      covered,
      spillover,
      outside,
      evidenceTier,
      evidenceScore,
      chosen,
      bridgeStrength,
      mimicFit,
      hasObjectiveSupport: ['human', 'listed', 'mechanistic'].includes(evidenceTier),
      withPrimary: primary?.name ? `${primary.name} -> ${item.name}` : item.name,
      closureScore,
      gainScore,
      bundleFitScore,
      completionScore,
      completionLabel,
      riskScore,
      safeWindow,
      decisionScore,
      decisionLabel: bridgeDecisionLabel(decisionScore),
      riskLabel: bridgeRiskLabel(riskScore),
      doctorDecisionNote: kind === 'physiology support'
        ? 'use as supportive completion layer, not as replacement for the anchor therapy'
        : covered.length && riskScore < 0.34
        ? 'strongest candidate for forward testing first'
        : covered.length
        ? 'usable bridge, but needs deviation review before promotion'
        : 'keep visible as weak path only, not a first-line extension',
    };
  }).sort((a, b) => b.decisionScore - a.decisionScore || b.bridgeStrength - a.bridgeStrength || b.covered.length - a.covered.length || a.spillover.length - b.spillover.length).slice(0, 8);
}

function BridgePathPanel({ title, rows, emptyText, tone = 'good' }) {
  return (
    <div style={styles.subPanel}>
      <div style={styles.subPanelTitle}>{title}</div>
      {rows.length ? (
        <div style={styles.signalList}>
          {rows.map((row) => (
            <div key={`${title}_${row.item.id}`} style={styles.signalRow}>
              <div style={styles.signalLeft}>
                <Pill tone={tone}>{row.withPrimary}</Pill>
              </div>
              <div style={styles.signalArrow}>→</div>
              <div style={styles.signalRight}>
                <span style={styles.signalAction}>{row.covered.length ? row.covered.map((entry) => signalLabel(entry.gene, entry.direction)).join(', ') : row.mimicFit}</span>
              </div>
            </div>
          ))}
        </div>
      ) : <div style={styles.emptyText}>{emptyText}</div>}
    </div>
  );
}

function RareBridgePanel({ primary, addons, signedDiseaseEntries, deviationDirections, directionMap, bundleNames }) {
  const rows = useMemo(
    () => buildRareBridgeRows({ primary, addons, signedDiseaseEntries, deviationDirections, directionMap, bundleNames }),
    [primary, addons, signedDiseaseEntries, deviationDirections, directionMap, bundleNames]
  );

  const directSupport = rows.filter((row) => row.covered.length && row.spillover.length === 0).slice(0, 4);
  const translatedSupport = rows.filter((row) => row.covered.length && row.hasObjectiveSupport).slice(0, 4);
  const outsideSupport = rows.filter((row) => row.outside.length).slice(0, 4);
  const physiologySupport = rows.filter((row) => row.kind === 'physiology support').slice(0, 3);
  const deadEnds = rows.filter((row) => !row.covered.length).slice(0, 4);
  const topDecision = rows[0] || null;
  const safestBridge = [...rows].sort((a, b) => b.safeWindow - a.safeWindow || b.decisionScore - a.decisionScore)[0] || null;
  const bestCompleter = [...rows].sort((a, b) => b.completionScore - a.completionScore || b.decisionScore - a.decisionScore)[0] || null;
  const highRiskCount = rows.filter((row) => row.riskScore >= 0.66).length;
  const auditableRows = rows.slice(0, 4);

  const primaryCoverage = Number(primary?.coverage_ratio || 0);
  const primarySpill = Number(primary?.spillover_count || 0);
  const usableWindow = Math.max(0, Math.min(1, primaryCoverage - Math.min(0.4, primarySpill * 0.08)));

  const topBreakdown = topDecision
    ? [
        { label: 'closure', value: topDecision.closureScore, weight: '38%', note: `${topDecision.covered.length} disease signals closed` },
        { label: 'evidence', value: topDecision.evidenceScore, weight: '20%', note: `${topDecision.evidenceTier} posture` },
        { label: 'net gain', value: topDecision.gainScore, weight: '16%', note: `net gain ${num(topDecision.item.net_gain || 0, 2)}` },
        { label: 'bundle fit', value: topDecision.bundleFitScore, weight: '11%', note: topDecision.chosen ? 'already selected in bundle' : 'candidate extension only' },
        { label: 'completion', value: topDecision.completionScore, weight: '15%', note: topDecision.completionLabel },
        { label: 'risk penalty', value: 1 - topDecision.riskScore, weight: '-24%', note: `${topDecision.outside.length} outside-target activations` },
      ]
    : [];

  const releaseGate = topDecision
    ? {
        summary:
          topDecision.decisionScore >= 0.72 && topDecision.riskScore < 0.34
            ? 'promotable for supervised forward testing'
            : topDecision.decisionScore >= 0.5
            ? 'research-usable, but still review-gated'
            : 'keep as exploratory only',
        blocker:
          topDecision.riskScore >= 0.66
            ? 'outside-target pressure too high'
            : topDecision.evidenceTier === 'hypothesis'
            ? 'evidence posture too early'
            : topDecision.kind === 'physiology support'
            ? 'supportive layer cannot replace anchor therapy'
            : 'human review still required before promotion',
        trustNote:
          topDecision.hasObjectiveSupport
            ? 'objective support exists, but this remains recommendation support rather than autonomous treatment logic'
            : 'mechanism-first bridge only; keep visible, not promoted',
      }
    : null;

  return (
    <SectionCard eyebrow="bridge layer" title="institutional decision surface for primary -> bridge -> completion">
      {primary?.name ? (
        <>
          <div style={styles.decisionBoard}>
            <div style={styles.decisionHero}>
              <div style={styles.eyebrow}>executive summary</div>
              <div style={styles.decisionHeroTitle}>{topDecision ? topDecision.withPrimary : 'no bridge ranked yet'}</div>
              <div style={styles.decisionHeroValue}>{topDecision ? num(topDecision.decisionScore, 2) : '0.00'}</div>
              <div style={styles.decisionHeroSub}>
                {topDecision
                  ? `first bridge now = ${topDecision.decisionLabel} fit · ${topDecision.evidenceTier} evidence · ${pct(topDecision.safeWindow)} safe window`
                  : 'run analyze first'}
              </div>
              {topDecision ? (
                <div style={styles.metaGrid}>
                  <div style={styles.metaCell}><strong>why this won:</strong> closes {topDecision.covered.length} disease signals, keeps risk {topDecision.riskLabel}, and delivers {topDecision.completionLabel}</div>
                  <div style={styles.metaCell}><strong>what blocks promotion:</strong> {releaseGate?.blocker || 'none stated'}</div>
                  <div style={styles.metaCell}><strong>next action:</strong> test this as the first supervised bridge path, then compare against the safest and the system completer variants below</div>
                </div>
              ) : null}
            </div>

            <div style={styles.decisionSplitGrid}>
              <div style={styles.subPanel}>
                <div style={styles.subPanelTitle}>clarity board</div>
                <div style={styles.signalList}>
                  <div style={styles.signalRow}>
                    <div style={styles.signalLeft}><Pill tone="good">primary usable window</Pill></div>
                    <div style={styles.signalArrow}>→</div>
                    <div style={styles.signalRight}><span style={styles.signalAction}>{pct(usableWindow)}</span></div>
                  </div>
                  <div style={styles.signalRow}>
                    <div style={styles.signalLeft}><Pill tone="soft">best bridge</Pill></div>
                    <div style={styles.signalArrow}>→</div>
                    <div style={styles.signalRight}><span style={styles.signalAction}>{topDecision ? topDecision.item.name : 'none'}</span></div>
                  </div>
                  <div style={styles.signalRow}>
                    <div style={styles.signalLeft}><Pill tone="default">safest alternative</Pill></div>
                    <div style={styles.signalArrow}>→</div>
                    <div style={styles.signalRight}><span style={styles.signalAction}>{safestBridge ? `${safestBridge.item.name} · ${pct(safestBridge.safeWindow)}` : 'none'}</span></div>
                  </div>
                  <div style={styles.signalRow}>
                    <div style={styles.signalLeft}><Pill tone="warn">system completer</Pill></div>
                    <div style={styles.signalArrow}>→</div>
                    <div style={styles.signalRight}><span style={styles.signalAction}>{bestCompleter ? `${bestCompleter.item.name} · ${bestCompleter.completionLabel}` : 'none'}</span></div>
                  </div>
                </div>
              </div>

              <div style={styles.subPanel}>
                <div style={styles.subPanelTitle}>trust gate</div>
                <div style={styles.metaGrid}>
                  <div style={styles.metaCell}><strong>release status:</strong> {releaseGate?.summary || 'run analyze first'}</div>
                  <div style={styles.metaCell}><strong>human review:</strong> required before anything moves outside mechanism support mode</div>
                  <div style={styles.metaCell}><strong>evidence posture:</strong> {topDecision ? `${topDecision.evidenceTier} · registry ${topDecision.item.registry_status || '-'}` : 'none'}</div>
                  <div style={styles.metaCell}><strong>trust note:</strong> {releaseGate?.trustNote || 'none'}</div>
                </div>
              </div>
            </div>
          </div>

          <div style={styles.statsRow}>
            <StatCard label="best bridge score" value={topDecision ? num(topDecision.decisionScore, 2) : '0.00'} sub={topDecision ? `${topDecision.item.name} · ${topDecision.decisionLabel}` : 'none yet'} />
            <StatCard label="safest bridge" value={safestBridge ? pct(safestBridge.safeWindow) : '0%'} sub={safestBridge ? `${safestBridge.item.name} · ${safestBridge.riskLabel} risk` : 'none yet'} />
            <StatCard label="system completer" value={bestCompleter ? num(bestCompleter.completionScore, 2) : '0.00'} sub={bestCompleter ? `${bestCompleter.item.name} · ${bestCompleter.completionLabel}` : 'none yet'} />
            <StatCard label="high-risk bridges" value={String(highRiskCount)} sub="paths with strong outside-target pressure" />
          </div>

          <div style={styles.proposalGrid}>
            <div style={styles.proposalCard}>
              <div style={styles.proposalTitle}>audit trail for top bridge</div>
              {topBreakdown.length ? (
                <div style={styles.auditList}>
                  {topBreakdown.map((item) => (
                    <div key={item.label} style={styles.auditRow}>
                      <div style={styles.auditHead}>
                        <span style={styles.rankName}>{item.label}</span>
                        <span style={styles.rankScore}>{pct(item.value)} · {item.weight}</span>
                      </div>
                      <div style={styles.auditTrack}><div style={{ ...styles.auditFill, width: `${Math.max(8, Math.round(item.value * 100))}%` }} /></div>
                      <div style={styles.rankSub}>{item.note}</div>
                    </div>
                  ))}
                </div>
              ) : <div style={styles.emptyText}>run analyze first</div>}
            </div>

            <div style={styles.proposalCard}>
              <div style={styles.proposalTitle}>institutional reading</div>
              {topDecision ? (
                <>
                  <div style={styles.proposalLine}><strong>primary recommendation:</strong> {topDecision.withPrimary}</div>
                  <div style={styles.proposalLine}><strong>why it is not a blind launch:</strong> score is explainable, risk is named, and human review remains explicit</div>
                  <div style={styles.proposalLine}><strong>current limitation:</strong> score is still ui-side composed from returned fields, so backend-native audit logs are still the next institutional step</div>
                  <div style={styles.proposalLine}><strong>best comparison set:</strong> compare against {safestBridge?.item?.name || 'none'} for safety and {bestCompleter?.item?.name || 'none'} for completion before any institutional demo</div>
                </>
              ) : <div style={styles.emptyText}>run analyze first</div>}
            </div>
          </div>

          <div style={styles.dualGrid}>
            <BridgePathPanel title="direct closure bridges" rows={directSupport} emptyText="no clean bridge found yet" tone="good" />
            <BridgePathPanel title="objective bridge translations" rows={translatedSupport} emptyText="no objective bridge found yet" tone="soft" />
          </div>

          <div style={styles.dualGrid}>
            <BridgePathPanel title="outside-target synergy watch" rows={outsideSupport} emptyText="none surfaced" tone="warn" />
            <BridgePathPanel title="physiology complements" rows={physiologySupport} emptyText="run mode 3 to surface physiology paths" tone="default" />
          </div>

          {!!deadEnds.length && (
            <div style={styles.subPanel}>
              <div style={styles.subPanelTitle}>dead-end visibility</div>
              <div style={styles.pillWrap}>
                {deadEnds.map((row) => <Pill key={`dead_${row.item.id}`} tone="bad">{row.item.name}</Pill>)}
              </div>
              <div style={styles.emptyText}>keep weak paths visible so institutional users can see what was considered and why it was not promoted.</div>
            </div>
          )}

          <div style={styles.addonGrid}>
            {auditableRows.map((row, idx) => {
              const factorRows = [
                { label: 'closure', value: row.closureScore },
                { label: 'evidence', value: row.evidenceScore },
                { label: 'completion', value: row.completionScore },
                { label: 'safe window', value: row.safeWindow },
              ];
              return (
                <div key={`bridge_${row.item.id}`} style={styles.addonCard}>
                  <div style={styles.addonName}>#{idx + 1} · {row.withPrimary}</div>
                  <div style={styles.addonScore}>decision {num(row.decisionScore, 2)} · {row.decisionLabel} · risk {pct(row.riskScore)}</div>
                  <div style={styles.heroResultSub}>{row.kind} · {row.mimicFit} · evidence {row.evidenceTier}</div>
                  <div style={styles.heroResultSub}>trace {traceText(row.item.citation_trace || [])}</div>
                  {row.item.notes_excerpt ? <div style={styles.heroResultSub}>{row.item.notes_excerpt}</div> : null}

                  <div style={styles.subMiniPanel}>
                    <div style={styles.subMiniTitle}>score breakdown</div>
                    <div style={styles.auditList}>
                      {factorRows.map((item) => (
                        <div key={`${row.item.id}_${item.label}`} style={styles.auditRowCompact}>
                          <div style={styles.auditHead}>
                            <span style={styles.rankName}>{item.label}</span>
                            <span style={styles.rankScore}>{pct(item.value)}</span>
                          </div>
                          <div style={styles.auditTrack}><div style={{ ...styles.auditFill, width: `${Math.max(8, Math.round(item.value * 100))}%` }} /></div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div style={styles.subMiniPanel}>
                    <div style={styles.subMiniTitle}>disease signals helped</div>
                    <div style={styles.pillWrap}>
                      {row.covered.length ? row.covered.map((entry) => <Pill key={`${row.item.id}_${entry.gene}_bridge`} tone="good">{signalLabel(entry.gene, entry.direction)}</Pill>) : <div style={styles.emptyText}>none</div>}
                    </div>
                  </div>

                  <div style={styles.subMiniPanel}>
                    <div style={styles.subMiniTitle}>outside-target watch</div>
                    <div style={styles.pillWrap}>
                      {row.spillover.length ? row.spillover.map((gene) => <Pill key={`${row.item.id}_${gene}_spill`} tone="bad">{gene}</Pill>) : <div style={styles.emptyText}>low</div>}
                    </div>
                  </div>

                  <div style={styles.metaGrid}>
                    <div style={styles.metaCell}><strong>decision note:</strong> {row.doctorDecisionNote}</div>
                    <div style={styles.metaCell}><strong>objective posture:</strong> {row.hasObjectiveSupport ? 'yes' : 'weak / early'}</div>
                    <div style={styles.metaCell}><strong>outside target count:</strong> {row.outside.length}</div>
                    <div style={styles.metaCell}><strong>bundle state:</strong> {row.chosen ? 'already selected in bundle' : 'candidate extension only'}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {!!rows.slice(4).length && (
            <div style={styles.subPanel}>
              <div style={styles.subPanelTitle}>remaining ranked bridges</div>
              <div style={styles.compactRankList}>
                {rows.slice(4).map((row, idx) => (
                  <div key={`rest_${row.item.id}`} style={styles.compactRankRow}>
                    <div>
                      <div style={styles.rankName}>#{idx + 5} · {row.withPrimary}</div>
                      <div style={styles.rankSub}>{row.kind} · evidence {row.evidenceTier} · completion {pct(row.completionScore)}</div>
                    </div>
                    <div style={styles.rankScore}>{num(row.decisionScore, 2)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div style={styles.emptyText}>run analyze first</div>
      )}
    </SectionCard>
  );
}


export default function RareDiseaseTab() {
  const [diseases, setDiseases] = useState([]);
  const [browseMode, setBrowseMode] = useState("manual");
  const [browseQuery, setBrowseQuery] = useState("");
  const [fillRankings, setFillRankings] = useState([]);
  const [fillRankNote, setFillRankNote] = useState("");
  const [fillRankMeta, setFillRankMeta] = useState({ total_catalog_items: 0, rankable_count: 0, returned_count: 0 });
  const [loadingFillRankings, setLoadingFillRankings] = useState(false);
  const [diseaseId, setDiseaseId] = useState("custom");
  const [geneText, setGeneText] = useState("MTOR up\nBDNF down\nMECP2 down");
  const [spilloverWeight, setSpilloverWeight] = useState("0.12");
  const [maxBundleItems, setMaxBundleItems] = useState("4");
  const [rankDepth, setRankDepth] = useState("8");
  const [plannerMode, setPlannerMode] = useState("mode_a");
  const [bundleStrategy, setBundleStrategy] = useState("dynamic");
  const [treatmentMode, setTreatmentMode] = useState("mode_3");
  const [deviationStrategy, setDeviationStrategy] = useState("drug_first_then_natural_tail");
  const [patientHabitsText, setPatientHabitsText] = useState("smoking relapse risk, sleep disruption");
  const [patientDietText, setPatientDietText] = useState("high sugar, ultra processed food");
  const [protocolBusyId, setProtocolBusyId] = useState("");
  const [specializedPlans, setSpecializedPlans] = useState([]);
  const [specializedLoading, setSpecializedLoading] = useState(false);
  const [specializedError, setSpecializedError] = useState("");

  const [startYear, setStartYear] = useState("1970");
  const [endYear, setEndYear] = useState("2005");
  const [seed, setSeed] = useState("1337");

  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingTrain, setLoadingTrain] = useState(false);
  const [bootError, setBootError] = useState("");
  const [analyzeError, setAnalyzeError] = useState("");
  const [trainError, setTrainError] = useState("");

  const [analyzeData, setAnalyzeData] = useState(null);
  const [memoryData, setMemoryData] = useState({
    trained: false,
    window: null,
    cases_seen: 0,
    hit_ratio: 0,
    pattern_summary: "train first to store general rare-pattern logic",
    trace_sample: [],
  });

  const [historyBank, setHistoryBank] = useState(null);
  const [registrySummary, setRegistrySummary] = useState(null);
  const [replayResult, setReplayResult] = useState(null);
  const [historyTrainResult, setHistoryTrainResult] = useState(null);
  const [historyError, setHistoryError] = useState("");
  const [loadingHistorySeed, setLoadingHistorySeed] = useState(false);
  const [loadingHistoryReplay, setLoadingHistoryReplay] = useState(false);
  const [loadingHistoryTrain, setLoadingHistoryTrain] = useState(false);
  const [loadingStoreHit, setLoadingStoreHit] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showStoredCases, setShowStoredCases] = useState(false);
  const [showTopRefs, setShowTopRefs] = useState(false);

  useEffect(() => {
    let alive = true;

    async function boot() {
      try {
        setBootError("");
        const [diseaseRes, memoryRes, historyRes, registryRes] = await Promise.all([
          apiRareDiseases(),
          apiRareSimMemory(),
          getHistoricalReplayBank().catch(() => null),
          apiRegistrySummary().catch(() => null),
        ]);
        if (!alive) return;

        const diseaseList = Array.isArray(diseaseRes)
          ? diseaseRes
          : Array.isArray(diseaseRes?.diseases)
          ? diseaseRes.diseases
          : [];

        setDiseases(diseaseList);
        setMemoryData(memoryRes || {});
        setHistoryBank(historyRes || null);
        setRegistrySummary(registryRes || null);
      } catch (err) {
        if (!alive) return;
        setBootError(String(err?.message || err || "failed to boot rare tab"));
      }
    }

    boot();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    let alive = true;
    async function loadFillRankings() {
      if (browseMode === "manual") {
        if (!alive) return;
        setFillRankings([]);
        setFillRankNote("");
        return;
      }
      try {
        setLoadingFillRankings(true);
        const res = await apiRareFillRankings({
          mode: browseMode === "catalog" ? "catalog" : "registry",
          query: browseQuery,
          max_results: 40,
          spillover_weight: Number(spilloverWeight || 0.12),
        });
        if (!alive) return;
        setFillRankings(Array.isArray(res?.items) ? res.items : []);
        setFillRankNote(res?.note || "");
        setFillRankMeta({
          total_catalog_items: Number(res?.total_catalog_items || 0),
          rankable_count: Number(res?.rankable_count || 0),
          returned_count: Number(res?.returned_count || 0),
        });
      } catch (err) {
        if (!alive) return;
        setFillRankings([]);
        setFillRankNote(String(err?.message || err || "failed to load fill rankings"));
      } finally {
        if (alive) setLoadingFillRankings(false);
      }
    }
    loadFillRankings();
    return () => {
      alive = false;
    };
  }, [browseMode, browseQuery, spilloverWeight]);

  const selectedDisease = useMemo(() => {
    return diseases.find((d) => d.id === diseaseId) || null;
  }, [diseases, diseaseId]);

  const signedDiseaseEntries = useMemo(() => {
    return signedEntriesFromDisease(selectedDisease, geneText, diseaseId);
  }, [selectedDisease, geneText, diseaseId]);

  const effectiveDiseaseGenes = useMemo(() => {
    return signedDiseaseEntries.map((row) => row.gene);
  }, [signedDiseaseEntries]);

  const directionMap = useMemo(() => {
    const out = {};
    for (const row of signedDiseaseEntries) out[row.gene] = row.direction;
    return out;
  }, [signedDiseaseEntries]);

  const disease = analyzeData?.disease || null;
  const ranked = Array.isArray(analyzeData?.ranked) ? analyzeData.ranked : [];
  const primary = analyzeData?.primary || null;
  const deviation = analyzeData?.deviation || null;
  const rawAddons = Array.isArray(analyzeData?.addons) ? analyzeData.addons : [];
  const addons = useMemo(() => rawAddons.filter((item) => {
    const covers = Array.isArray(item?.covers_deviation_genes) ? item.covers_deviation_genes.length : 0;
    const gain = Number(item?.net_gain || 0);
    if (plannerMode === "mode_b" && item?.kind === "drug") return false;
    return covers > 0 && gain > 0;
  }), [rawAddons, plannerMode]);
  const bundle = analyzeData?.bundle || null;
  const futurePath = analyzeData?.future_path || null;
  const proposals = Array.isArray(analyzeData?.proposals) ? analyzeData.proposals : [];
  const simContext = analyzeData?.sim_context || memoryData || {};
  const institutional = analyzeData?.institutional_assessment || null;
  const safetyDecision = analyzeData?.safety_decision || null;

  const coverageGenes = uniq(primary?.coverage_genes || []);
  const spilloverGenes = uniq(bundle?.spillover_genes || primary?.spillover_genes || []);
  const bundleIds = uniq(bundle?.bundle_ids || []);
  const bundleNames = uniq(bundle?.bundle_names || []);

  const deviationDirections = deviation?.uncovered_directions || {};
  const coverageEntries = coverageGenes.map((gene) => ({ gene, direction: directionMap[gene] || "unknown" }));
  const deviationEntries = uniq(deviation?.uncovered_genes || []).map((gene) => ({ gene, direction: deviationDirections[gene] || directionMap[gene] || "unknown" }));
  const bundleCoveredEntries = uniq(bundle?.covered_genes || []).map((gene) => ({ gene, direction: directionMap[gene] || "unknown" }));
  const bundleUncoveredEntries = uniq(bundle?.uncovered_genes || []).map((gene) => ({ gene, direction: deviationDirections[gene] || directionMap[gene] || "unknown" }));
  const futureRemainingEntries = uniq(futurePath?.remaining_gap_genes || []).map((gene) => ({ gene, direction: deviationDirections[gene] || directionMap[gene] || "unknown" }));
  const modelConfidence = useMemo(() => computeModelConfidence({ primary, effectiveDiseaseGenes, addons, bundle, spilloverGenes }), [primary, effectiveDiseaseGenes, addons, bundle, spilloverGenes]);
  const modelConfidenceLabel = confidenceBand(modelConfidence.score);

  const buildAnalyzePayload = (modeOverride = treatmentMode) => ({
    disease_id: diseaseId || "custom",
    disease_gene_text: geneText,
    disease_genes: [],
    selected_candidates: [],
    max_results: 12,
    max_bundle_items: Number(maxBundleItems || 4),
    rank_depth: Number(rankDepth || 8),
    spillover_weight: Number(spilloverWeight || 0.12),
    planner_mode: plannerMode,
    bundle_strategy: plannerMode === "mode_b" ? "dynamic" : bundleStrategy,
    treatment_mode: modeOverride,
    include_physiology: modeOverride === "mode_3",
    deviation_strategy: deviationStrategy,
    patient_habits_text: patientHabitsText,
    patient_diet_text: patientDietText,
  });

  async function runSpecializedCompare() {
    try {
      setSpecializedLoading(true);
      setSpecializedError("");
      const modes = ["mode_1", "mode_2", "mode_3"];
      const results = await Promise.all(modes.map(async (mode) => ({ mode, res: await apiRareAnalyze(buildAnalyzePayload(mode)) })));
      const plans = results
        .map(({ mode, res }) => summarizeSpecializedPlan(mode, res, effectiveDiseaseGenes.length))
        .sort((a, b) => b.score - a.score);
      setSpecializedPlans(plans);
    } catch (err) {
      setSpecializedPlans([]);
      setSpecializedError(String(err?.message || err || "specialized compare failed"));
    } finally {
      setSpecializedLoading(false);
    }
  }

  async function runAnalyze() {
    try {
      setLoadingAnalyze(true);
      setAnalyzeError("");
      const payload = buildAnalyzePayload();
      const res = await apiRareAnalyze(payload);
      setAnalyzeData(res || null);
      runSpecializedCompare();
    } catch (err) {
      setAnalyzeError(String(err?.message || err || "analyze failed"));
    } finally {
      setLoadingAnalyze(false);
    }
  }

  async function runTrain() {
    try {
      setLoadingTrain(true);
      setTrainError("");
      const res = await apiRareSimTrain({
        start_year: Number(startYear || 1970),
        end_year: Number(endYear || 2005),
        seed: Number(seed || 1337),
      });
      setMemoryData(res?.learned || res || {});
    } catch (err) {
      setTrainError(String(err?.message || err || "training failed"));
    } finally {
      setLoadingTrain(false);
    }
  }



  async function runProposalProtocol(item) {
    try {
      setProtocolBusyId(item?.id || "busy");
      const res = await apiRareProposalProtocol({
        disease_name: disease?.name || selectedDisease?.name || diseaseId || "custom rare disease",
        proposal_id: item?.id || "proposal",
        proposal_title: item?.title || "rare proposal",
        focus: item?.focus || "",
        goal: item?.goal || "",
        cheap_readout: item?.cheap_readout || "",
        stop_rule: item?.stop_rule || "",
        hypothesis_anchor: item?.hypothesis_anchor || "",
        reasoning_trace: Array.isArray(item?.reasoning_trace) ? item.reasoning_trace : [],
        estimated_savings_eur: Number(item?.estimated_savings_eur || 0),
        bundle_names: Array.isArray(bundleNames) ? bundleNames : [],
      });
      if (res?.pdf_url) {
        window.open(res.pdf_url, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      setAnalyzeError(String(err?.message || err || "protocol generation failed"));
    } finally {
      setProtocolBusyId("");
    }
  }

  function handleExport() {
    exportRareDiseaseCase({
      diseaseId,
      geneText,
      patientHabitsText,
      patientDietText,
      deviationStrategy,
      treatmentMode,
      effectiveDiseaseGenes,
      spilloverWeight,
      maxBundleItems,
      rankDepth,
      startYear,
      endYear,
      seed,
      analyzeData,
      memoryData,
    });
  }

  async function refreshHistoryBank() {
    try {
      const bank = await getHistoricalReplayBank();
      setHistoryBank(bank || null);
    } catch (err) {
      setHistoryError(String(err?.message || err || "failed to load historical replay bank"));
    }
  }

  async function runHistorySeed() {
    try {
      setLoadingHistorySeed(true);
      setHistoryError("");
      await seedHistoricalReplayBank();
      await refreshHistoryBank();
    } catch (err) {
      setHistoryError(String(err?.message || err || "failed to seed historical bank"));
    } finally {
      setLoadingHistorySeed(false);
    }
  }

  async function runHistoryReplay() {
    try {
      setLoadingHistoryReplay(true);
      setHistoryError("");
      const genes = effectiveDiseaseGenes.slice(0, 8);
      const diseaseName = disease?.name || disease?.label || selectedDisease?.name || "custom rare disease";

      const res = await replayHistoricalCase({
        disease_name: diseaseName,
        discovery_year: Number(startYear || 1970),
        candidate_features: genes,
        suspected_targets: signedDiseaseEntries.map((row) => ({
          target: row.gene,
          direction: row.direction,
          rationale: "ui replay request",
          confidence: "unknown",
          source_ids: [],
        })),
        notes: "rare disease tab historical replay",
      });
      setReplayResult(res || null);
      await refreshHistoryBank();
    } catch (err) {
      setHistoryError(String(err?.message || err || "historical replay failed"));
    } finally {
      setLoadingHistoryReplay(false);
    }
  }

  async function runHistoryTrain() {
    try {
      setLoadingHistoryTrain(true);
      setHistoryError("");
      const res = await trainHistoricalReplay({
        start_year: Number(startYear || 1970),
        end_year: Number(endYear || 2005),
        seed: Number(seed || 1337),
      });
      setHistoryTrainResult(res || null);
      await refreshHistoryBank();
    } catch (err) {
      setHistoryError(String(err?.message || err || "historical training failed"));
    } finally {
      setLoadingHistoryTrain(false);
    }
  }

  async function runStoreHitLogic() {
    try {
      setLoadingStoreHit(true);
      setHistoryError("");
      const replayId = replayResult?.replay_id || `manual_${Date.now()}`;
      const diseaseName = disease?.name || disease?.label || selectedDisease?.name || "custom rare disease";
      const reusableRule =
        replayResult?.predicted_improvement_logic ||
        replayResult?.predicted_first_medicine_logic ||
        futurePath?.creation_rationale ||
        "preserve hit logic, then add deviation-rescue logic";

      await storeHistoricalHit({
        replay_id: replayId,
        disease_name: diseaseName,
        reusable_rule: reusableRule,
        confidence: "medium",
        source_ids: [],
      });
      await refreshHistoryBank();
    } catch (err) {
      setHistoryError(String(err?.message || err || "failed to store hit logic"));
    } finally {
      setLoadingStoreHit(false);
    }
  }

  function applyRankedDisease(row) {
    if (!row) return;
    if (row.mapped_to_engine && row.disease_id && !String(row.disease_id).startsWith("catalog::")) {
      setDiseaseId(row.disease_id);
      const hit = diseases.find((item) => item.id === row.disease_id);
      if (hit?.genes?.length) {
        const nextGeneText = hit.genes.map((gene) => `${String(gene).toUpperCase()} ${hit?.directions?.[gene] || hit?.directions?.[String(gene).toLowerCase()] || "unknown"}`).join("\n");
        if (nextGeneText) setGeneText(nextGeneText);
      }
      if (row.preferred_mode && row.preferred_mode !== "unmapped") {
        setTreatmentMode(row.preferred_mode);
      }
      return;
    }
    setDiseaseId("custom");
    setGeneText("");
  }

  const proposalText = useMemo(() => {
    if (!primary?.name) return [];
    return [
      `primary first: use ${primary.name} as the current best market-style candidate`,
      deviationEntries.length
        ? `deviation next: unresolved signals are ${deviationEntries.map((row) => signalLabel(row.gene, row.direction)).join(", ")}`
        : "deviation next: no uncovered signals remain after current primary",
      bundleNames.length ? `bundle path: ${bundleNames.join(" + ")}` : "bundle path: no expanded bundle selected yet",
      futurePath?.creation_rationale || "future path path not built yet",
      simContext?.support_note || "simulation context not available yet",
    ];
  }, [primary, deviationEntries, bundleNames, futurePath, simContext]);

  return (
    <div style={styles.page}>
      <div style={styles.gridTop}>
        <SectionCard eyebrow="Rare disease triage" title="find the best covering therapy, inspect deviation, then search add-on path.">
          {bootError ? <div style={styles.errorBox}>boot error: {bootError}</div> : null}
          {analyzeError ? <div style={styles.errorBox}>analyze error: {analyzeError}</div> : null}

          <div style={styles.sectionCompact}>
            <div style={styles.sectionHeader}>
              <div>
                <div style={styles.eyebrow}>input mode</div>
                <div style={styles.sectionTitle}>switch between manual signals, ranked engine-ready diseases, or imported catalog browse.</div>
              </div>
            </div>
            <div style={styles.formRow}>
              <div style={styles.fieldSmall}>
                <label style={styles.label}>surface</label>
                <select style={styles.select} value={browseMode} onChange={(e) => setBrowseMode(e.target.value)}>
                  <option value="manual">manual targets</option>
                  <option value="registry">engine-ranked rare diseases</option>
                  <option value="catalog">pdf catalog browse + mapped ranking</option>
                </select>
              </div>
              <div style={styles.field}>
                <label style={styles.label}>search</label>
                <input style={styles.input} value={browseQuery} onChange={(e) => setBrowseQuery(e.target.value)} placeholder="search disease name or alias" />
              </div>
              <div style={styles.fieldSmall}>
                <label style={styles.label}>catalog loaded</label>
                <div style={styles.helper}>{fillRankMeta.total_catalog_items || 0} rows</div>
              </div>
              <div style={styles.fieldSmall}>
                <label style={styles.label}>rankable now</label>
                <div style={styles.helper}>{fillRankMeta.rankable_count || 0} diseases</div>
              </div>
            </div>
            {browseMode !== "manual" ? (
              <div style={{ ...styles.subPanel, marginTop: 12 }}>
                <div style={styles.subPanelTitle}>{loadingFillRankings ? "loading ranking surface..." : fillRankNote || "ranking surface"}</div>
                <div style={{ maxHeight: 240, overflow: "auto", display: "grid", gap: 10, marginTop: 10 }}>
                  {fillRankings.length ? fillRankings.map((row) => (
                    <button key={row.disease_id} type="button" onClick={() => applyRankedDisease(row)} style={{ ...styles.signalRow, textAlign: "left", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 12, cursor: "pointer" }}>
                      <div style={{ flex: 1 }}>
                        <div style={styles.signalAction}>{row.disease_name}</div>
                        <div style={styles.metaCell}>path {row.preferred_label || 'needs mapping'} · score {num(row.rank_score || 0, 2)} · coverage {pct(row.coverage_ratio || 0)}</div>
                        <div style={styles.metaCell}>{row.rationale}</div>
                        {row.catalog_url ? <div style={styles.metaCell}>{row.catalog_url}</div> : null}
                      </div>
                      <div style={styles.pillWrap}>
                        <Pill tone={row.rankable ? "good" : "soft"}>{row.rankable ? "mapped" : "catalog only"}</Pill>
                        {row.best_primary_name ? <Pill tone="default">{row.best_primary_name}</Pill> : null}
                      </div>
                    </button>
                  )) : <div style={styles.emptyText}>no rows</div>}
                </div>
              </div>
            ) : null}
          </div>

          <div style={styles.formRow}>
            <div style={styles.field}>
              <label style={styles.label}>disease select</label>
              <select style={styles.select} value={diseaseId} onChange={(e) => setDiseaseId(e.target.value)}>
                {(diseases.length ? diseases : [{ id: "custom", name: "custom (paste genes)" }]).map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div style={styles.fieldSmall}>
              <label style={styles.label}>spillover weight</label>
              <input style={styles.input} value={spilloverWeight} onChange={(e) => setSpilloverWeight(e.target.value)} />
            </div>

            <div style={styles.fieldSmall}>
              <label style={styles.label}>treatment mode</label>
              <select style={styles.select} value={treatmentMode} onChange={(e) => setTreatmentMode(e.target.value)}>
                <option value="mode_1">mode 1 · drugs only</option>
                <option value="mode_2">mode 2 · drug + natural compound</option>
                <option value="mode_3">mode 3 · add physiology layer</option>
              </select>
            </div>

            <div style={styles.fieldSmall}>
              <label style={styles.label}>planner mode</label>
              <select style={styles.select} value={plannerMode} onChange={(e) => setPlannerMode(e.target.value)}>
                <option value="mode_a">mode a · rinse with drugs first</option>
                <option value="mode_b">mode b · one drug max</option>
              </select>
            </div>

            <div style={styles.fieldSmall}>
              <label style={styles.label}>mode a strategy</label>
              <select style={styles.select} value={bundleStrategy} onChange={(e) => setBundleStrategy(e.target.value)} disabled={plannerMode === "mode_b"}>
                <option value="dynamic">dynamic cap</option>
                <option value="unlimited">unlimited</option>
              </select>
            </div>

            <div style={styles.fieldSmall}>
              <label style={styles.label}>max bundle items</label>
              <input style={styles.input} value={maxBundleItems} onChange={(e) => setMaxBundleItems(e.target.value)} disabled={plannerMode !== "mode_b" && bundleStrategy === "unlimited"} />
            </div>

            <div style={styles.fieldSmall}>
              <label style={styles.label}>rank depth</label>
              <input style={styles.input} value={rankDepth} onChange={(e) => setRankDepth(e.target.value)} />
            </div>
          </div>

          <div style={styles.field}>
            <label style={styles.label}>disease genes / activators + direction</label>
            <textarea style={styles.textarea} value={geneText} onChange={(e) => setGeneText(e.target.value)} />
            <div style={styles.helper}>paste one per line as gene + disease-side direction. examples: MTOR up, BDNF down, TSC1 loss of function.</div>
          </div>

          <div style={styles.actionsRow}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button style={styles.primaryButton} onClick={runAnalyze} disabled={loadingAnalyze}>
                {loadingAnalyze ? "running analyze..." : "run rare disease analyze"}
              </button>
              <button style={{ ...styles.secondaryButton, width: "auto", minHeight: 44 }} onClick={runSpecializedCompare} disabled={loadingAnalyze || specializedLoading}>
                {specializedLoading ? "comparing modes..." : "run specialized compare"}
              </button>
            </div>
            <div style={styles.geneCount}>gene count {effectiveDiseaseGenes.length}</div>
          </div>

          <div style={styles.statsGrid}>
            <StatCard label="best primary" value={primary?.name || "-"} sub={primary?.id || "no result yet"} />
            <StatCard label="mechanism coverage" value={pct(primary?.coverage_ratio || deviation?.coverage_ratio || 0)} sub={`${primary?.coverage_count || 0} / ${effectiveDiseaseGenes.length} signals neutralized`} />
            <StatCard label="deviation left" value={String(deviation?.uncovered_count || 0)} sub="signals not yet neutralized" />
            <StatCard label="model confidence" value={num(modelConfidence.score, 2)} sub={`${modelConfidenceLabel} confidence`} />
            <StatCard label="add-on options" value={String(addons.length || 0)} sub={addons[0]?.name || "none yet"} />
          </div>


          {(specializedLoading || specializedPlans.length || specializedError) ? (
            <div style={styles.memoryCard}>
              <div style={styles.eyebrow}>specialized treatment comparison</div>
              <div style={styles.metaGrid}>
                <div style={styles.metaCell}><strong>compare logic:</strong> same disease input run through mode 1, mode 2, and mode 3 using the live backend scorer.</div>
                <div style={styles.metaCell}><strong>rank formula:</strong> coverage + spillover restraint + burden restraint + evidence posture + physiology support + lifestyle friction.</div>
              </div>
              {specializedError ? <div style={styles.errorBox}>{specializedError}</div> : null}
              {specializedLoading && !specializedPlans.length ? <div style={styles.emptyText}>running cross-mode comparison...</div> : null}
              {!!specializedPlans.length ? (
                <div style={styles.proposalGrid}>
                  {specializedPlans.map((plan, idx) => {
                    const factors = buildFactorStrip(plan);
                    return (
                    <div key={plan.mode} style={styles.proposalCard}>
                      <div style={styles.proposalTitle}>#{idx + 1} · {plan.label}</div>
                      <div style={styles.proposalLine}><strong>fit score:</strong> {num(plan.score, 2)}</div>
                      <div style={styles.proposalLine}><strong>primary:</strong> {plan.primaryName}</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6, marginBottom: 6 }}>
                        {factors.map((factor) => (
                          <Pill key={`${plan.mode}_${factor.label}`} tone="soft">{factor.label}: {factor.val}</Pill>
                        ))}
                      </div>
                      <div style={styles.proposalLine}><strong>coverage:</strong> {pct(plan.coverageRatio)} · <strong>spillover:</strong> {plan.spilloverCount}</div>
                      <div style={styles.proposalLine}><strong>burden:</strong> {plan.burdenCount} items · <strong>physiology:</strong> {plan.physiologyCount}</div>
                      <div style={styles.proposalLine}><strong>compound bridges:</strong> {plan.compoundCount} · <strong>entered risk flags:</strong> {plan.riskCount}</div>
                      <div style={styles.proposalLine}><strong>recommendation:</strong> {plan.recommendation}</div>
                      <div style={styles.proposalLine}><strong>caveat:</strong> {plan.caveat}</div>
                      <div style={styles.proposalLine}><strong>bundle:</strong> {plan.bundleNames.join(', ') || 'primary only / no addon chosen'}</div>
                      <div style={styles.pillWrap}>
                        {plan.notes.map((note) => <Pill key={`${plan.mode}_${note}`} tone="soft">{note}</Pill>)}
                      </div>
                    </div>
                    );
                  })}
                </div>
              ) : null}
            </div>
          ) : null}

          {institutional ? (
            <div style={styles.memoryCard}>
              <div style={styles.eyebrow}>institutional reality check</div>
              <div style={styles.statsGrid}>
                <StatCard label="readiness" value={institutional.readiness_label || "early"} sub={`score ${num(institutional.readiness_score || 0, 2)}`} />
                <StatCard label="facility fit" value={institutional.facility_fit || "institutional hypothesis support"} sub={institutional.evidence_posture || "mechanism-first"} />
                <StatCard label="treatment mode" value={institutional.treatment_mode || treatmentMode} sub={institutional.provenance_note || "no provenance note"} />
                <StatCard label="registry depth" value={String(institutional.registry_depth?.diseases || 0)} sub={`drugs ${institutional.registry_depth?.drugs || 0} · compounds ${institutional.registry_depth?.compounds || 0} · physiology ${institutional.registry_depth?.physiology || 0}`} />
                <StatCard label="human review" value={institutional.human_review_required ? "required" : "optional"} sub="never standalone clinical output" />
                <StatCard label="source mix" value={Object.keys(institutional.source_mix || {}).length || 0} sub={Object.entries(institutional.source_mix || {}).map(([k, v]) => `${k}:${v}`).join(' · ') || 'none'} />
              </div>

              <div style={styles.metaGrid}>
                <div style={styles.metaCell}><strong>disclaimer:</strong> {institutional.disclaimer || "none"}</div>
                <div style={styles.metaCell}><strong>audit flags:</strong> {(institutional.audit_flags || []).join(', ') || 'none'}</div>
                <div style={styles.metaCell}><strong>fallback used:</strong> {institutional.fallback_used ? "yes" : "no"}</div>
                <div style={styles.metaCell}><strong>provenance:</strong> {institutional.provenance_note || "none"}</div>
                <div style={styles.metaCell}><strong>source mix:</strong> {Object.entries(institutional.source_mix || {}).map(([k, v]) => `${k}:${v}`).join(', ') || "none"}</div>
              </div>

              <div style={styles.proposalGrid}>
                <div style={styles.proposalCard}>
                  <div style={styles.proposalTitle}>strengths</div>
                  {(institutional.strengths || []).length ? institutional.strengths.map((line, idx) => <div key={`s_${idx}`} style={styles.proposalLine}>{line}</div>) : <div style={styles.emptyText}>none</div>}
                </div>
                <div style={styles.proposalCard}>
                  <div style={styles.proposalTitle}>weaknesses</div>
                  {(institutional.weaknesses || []).length ? institutional.weaknesses.map((line, idx) => <div key={`w_${idx}`} style={styles.proposalLine}>{line}</div>) : <div style={styles.emptyText}>none</div>}
                </div>
                <div style={styles.proposalCard}>
                  <div style={styles.proposalTitle}>blockers</div>
                  {(institutional.blockers || []).length ? institutional.blockers.map((line, idx) => <div key={`b_${idx}`} style={styles.proposalLine}>{line}</div>) : <div style={styles.emptyText}>none</div>}
                </div>
                <div style={styles.proposalCard}>
                  <div style={styles.proposalTitle}>registry launch blockers</div>
                  {(registrySummary?.launch_blockers || []).length ? registrySummary.launch_blockers.map((line, idx) => <div key={`rb_${idx}`} style={styles.proposalLine}>{line}</div>) : <div style={styles.emptyText}>none</div>}
                </div>
                <div style={styles.proposalCard}>
                  <div style={styles.proposalTitle}>next steps</div>
                  {(institutional.recommended_next_steps || []).length ? institutional.recommended_next_steps.map((line, idx) => <div key={`n_${idx}`} style={styles.proposalLine}>{line}</div>) : <div style={styles.emptyText}>none</div>}
                </div>
              </div>
            </div>
          ) : null}

          {safetyDecision ? (
            <div style={styles.memoryCard}>
              <div style={styles.eyebrow}>safety decision engine</div>
              <div style={styles.metaGrid}>
                <div style={styles.metaCell}><strong>strategy:</strong> {safetyDecision.deviation_strategy || "n/a"}</div>
                <div style={styles.metaCell}><strong>recommendation:</strong> {safetyDecision.recommendation || "n/a"}</div>
              </div>
              <div style={styles.proposalGrid}>
                {(safetyDecision.risks || []).map((item, idx) => (
                  <div key={`risk_${idx}`} style={styles.proposalCard}>
                    <div style={styles.proposalTitle}>{item.title}</div>
                    <div style={styles.proposalLine}>{item.effect}</div>
                    <div style={styles.proposalLine}>severity: {item.severity} · source: {item.source}</div>
                  </div>
                ))}
                {!(safetyDecision.risks || []).length ? <div style={styles.emptyText}>no obvious lifestyle no-go zone detected from entered text.</div> : null}
              </div>
            </div>
          ) : null}
        </SectionCard>

        <SectionCard eyebrow="Historical replay" title="train from 1970 to 2005">
          {trainError ? <div style={styles.errorBox}>training error: {trainError}</div> : null}

          <div style={styles.formRowTrain}>
            <div style={styles.fieldSmall}>
              <label style={styles.label}>start year</label>
              <input style={styles.inputBig} value={startYear} onChange={(e) => setStartYear(e.target.value)} />
            </div>
            <div style={styles.fieldSmall}>
              <label style={styles.label}>end year</label>
              <input style={styles.inputBig} value={endYear} onChange={(e) => setEndYear(e.target.value)} />
            </div>
            <div style={styles.fieldSmall}>
              <label style={styles.label}>seed</label>
              <input style={styles.inputBig} value={seed} onChange={(e) => setSeed(e.target.value)} />
            </div>
          </div>

          <button style={styles.secondaryButton} onClick={runTrain} disabled={loadingTrain}>
            {loadingTrain ? "training..." : "simulate rare disease history"}
          </button>

          <div style={styles.memoryCard}>
            <div style={styles.eyebrow}>historical model</div>
            <div style={styles.memoryLine}><strong>training window:</strong> {simContext?.window || memoryData?.window || "not trained yet"}</div>
            <div style={styles.memoryLine}><strong>cases analyzed:</strong> {simContext?.cases_seen || 0}</div>
            <div style={styles.memoryLine}><strong>pattern detected:</strong> {simContext?.pattern_summary || "none"}</div>
            <div style={styles.memoryLine}><strong>confidence:</strong> {num(simContext?.hit_ratio || 0, 2)}</div>
            <div style={styles.memoryLine}><strong>support note:</strong> {simContext?.support_note || "none"}</div>
          </div>
        </SectionCard>
      </div>

      <div style={styles.gridBottom}>
        <SectionCard eyebrow="Primary result" title="best fitting market candidate">
          {primary?.name ? (
            <>
              <div style={styles.heroResultCard}>
                <div style={styles.heroResultName}>{primary.name}</div>
                <div style={styles.heroResultSub}>{primary.id} · score {num(primary.score)} · raw {num(primary.raw_score)}</div>
                <div style={styles.heroResultSub}>{primary.rationale}</div>
                <div style={styles.heroResultSub}>evidence {primary.evidence_tier || '-'} · score {num(primary.evidence_score || 0, 2)} · registry {primary.registry_status || '-'}</div>
                <div style={styles.heroResultSub}>trace {traceText(primary.citation_trace || [])}</div>
                {primary.notes_excerpt ? <div style={styles.heroResultSub}>{primary.notes_excerpt}</div> : null}
              </div>

              <MechanismClosureBar entries={signedDiseaseEntries} coverageGenes={coverageGenes} bundleCoveredEntries={bundleCoveredEntries} primaryName={primary?.name} bundleNames={bundleNames} />
              <SignalListPanel title="disease signal neutralized by primary" entries={coverageEntries} covered empty="none" />
              <SignalListPanel title="remaining disease signal not yet neutralized" entries={deviationEntries} empty="none" />
              <GenePanel title="primary spillover" genes={uniq(primary.spillover_genes || [])} tone="bad" />

              <CollapsibleBlock title="rank depth / top references" defaultOpen={showTopRefs} compact>
                <div style={styles.rankList}>
                  {ranked.length ? ranked.slice(0, Number(rankDepth || 8)).map((item) => (
                    <div key={item.id} style={styles.rankRow}>
                      <div>
                        <div style={styles.rankName}>{item.name}</div>
                        <div style={styles.rankSub}>{item.id} · {item.kind}</div>
                        <div style={styles.rankSub}>evidence {item.evidence_tier || '-'} · trace {traceText(item.citation_trace || [])}</div>
                      </div>
                      <div style={styles.rankScore}>{num(item.score)}</div>
                    </div>
                  )) : <div style={styles.emptyText}>run analyze first</div>}
                </div>
              </CollapsibleBlock>
            </>
          ) : (
            <div style={styles.emptyText}>run analyze first</div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Deviation closure" title="mild medicine / natural compound for uncovered genes">
          {addons.length ? (
            <div style={styles.addonGrid}>
              {addons.map((item) => {
                const coverEntries = (item.covers_deviation_genes || []).map((gene) => ({ gene, direction: deviationDirections[gene] || directionMap[gene] || "unknown" }));
                return (
                  <div key={item.id} style={styles.addonCard}>
                    <div style={styles.addonName}>{item.name}</div>
                    <div style={styles.addonScore}>score {num(item.score)} · net gain {num(item.net_gain, 2)}</div>
                    <div style={styles.heroResultSub}>evidence {item.evidence_tier || '-'} · score {num(item.evidence_score || 0, 2)} · registry {item.registry_status || '-'}</div>
                    <div style={styles.heroResultSub}>trace {traceText(item.citation_trace || [])}</div>
                    {item.notes_excerpt ? <div style={styles.heroResultSub}>{item.notes_excerpt}</div> : null}

                    <div style={styles.subMiniPanel}>
                      <div style={styles.subMiniTitle}>covers deviation</div>
                      <div style={styles.pillWrap}>
                        {coverEntries.length ? coverEntries.map((row) => <Pill key={`${item.id}_${row.gene}`} tone="good">{signalLabel(row.gene, row.direction)}</Pill>) : <div style={styles.emptyText}>none</div>}
                      </div>
                    </div>

                    <div style={styles.subMiniPanel}>
                      <div style={styles.subMiniTitle}>new spillover</div>
                      <div style={styles.pillWrap}>
                        {item.new_spillover_genes?.length ? item.new_spillover_genes.map((g) => <Pill key={g} tone="bad">{g}</Pill>) : <div style={styles.emptyText}>none</div>}
                      </div>
                    </div>

                    <div style={styles.metaGrid}>
                      <div style={styles.metaCell}><strong>bundle compatibility:</strong> {item.bundle_compatibility || "-"}</div>
                      <div style={styles.metaCell}><strong>why selected:</strong> {item.why_selected || "-"}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={styles.emptyText}>no add-on candidate returned yet</div>
          )}
        </SectionCard>

        <RareSynergyPanel addons={addons} bundleNames={bundleNames} deviationDirections={deviationDirections} directionMap={directionMap} />

        <RareBridgePanel primary={primary} addons={addons} signedDiseaseEntries={signedDiseaseEntries} deviationDirections={deviationDirections} directionMap={directionMap} bundleNames={bundleNames} />

        <SectionCard eyebrow="Bundle optimizer" title="rank bundle paths by closure, evidence, and safety">
          <BundleRankingPanel addons={addons} deviationDirections={deviationDirections} directionMap={directionMap} bundleNames={bundleNames} />
        </SectionCard>

        <SectionCard eyebrow="Selected minimal bundle" title="bundle chosen to close deviation with least extra noise">
          {bundle ? (
            <>
              <div style={styles.bundleHeader}>
                <div style={styles.bundleNames}>{bundleNames.join(" + ") || "none"}</div>
                <div style={styles.bundleScore}>coverage {pct(bundle.coverage_ratio)} · score {num(bundle.score)}</div>
              </div>

              <SignalListPanel title="bundle covered genes" entries={bundleCoveredEntries} covered empty="none" />
              <SignalListPanel title="bundle uncovered genes" entries={bundleUncoveredEntries} empty="none" />
              <GenePanel title="bundle spillover genes" genes={spilloverGenes} tone="bad" />

              <div style={styles.bundleList}>
                {bundleIds.length ? bundleIds.map((id, idx) => <div key={id} style={styles.bundleItem}>{bundleNames[idx] || id}</div>) : <div style={styles.emptyText}>none</div>}
              </div>
            </>
          ) : (
            <div style={styles.emptyText}>run analyze first</div>
          )}
        </SectionCard>

        <SectionCard eyebrow="future path" title="current coverage vs remaining gap">
          {futurePath ? (
            <>
              <GenePanel title="ideal target set" genes={signedDiseaseEntries.map((row) => signalLabel(row.gene, row.direction))} tone="default" />
              <SignalListPanel title="current coverage" entries={coverageEntries} covered empty="none" />
              <SignalListPanel title="remaining gap" entries={futureRemainingEntries} empty="none" />
              <div style={styles.proposalBox}>
                <div style={styles.proposalLine}><strong>creation justified:</strong> {futurePath.creation_justified ? "yes" : "no"}</div>
                <div style={styles.proposalLine}><strong>rationale:</strong> {futurePath.creation_rationale}</div>
                <div style={styles.proposalLine}><strong>translation note:</strong> {futurePath.translation_note}</div>
              </div>
            </>
          ) : (
            <div style={styles.emptyText}>future path path not available yet</div>
          )}
        </SectionCard>

        <SectionCard eyebrow="Proposal logic" title="early build path from q.pdf">
          {proposals.length ? (
            <div style={styles.proposalGrid}>
              {proposals.map((item) => (
                <div key={item.id} style={styles.proposalCard}>
                  <div style={styles.proposalTitle}>{item.title}</div>
                  <div style={styles.proposalLine}><strong>focus:</strong> {item.focus}</div>
                  <div style={styles.proposalLine}><strong>goal:</strong> {item.goal}</div>
                  <div style={styles.proposalLine}><strong>cheap readout:</strong> {item.cheap_readout}</div>
                  <div style={styles.proposalLine}><strong>stop rule:</strong> {item.stop_rule}</div>
                  <div style={styles.proposalLine}><strong>why this logic:</strong> {item.hypothesis_anchor || "-"}</div>
                  <div style={styles.proposalLine}><strong>estimated savings:</strong> EUR {Math.round(Number(item.estimated_savings_eur || 0)).toLocaleString()}</div>
                  {Array.isArray(item.reasoning_trace) && item.reasoning_trace.length ? (
                    <div style={{ ...styles.proposalLine, marginTop: 8 }}>
                      <strong>logic trace:</strong> {item.reasoning_trace.join(" · ")}
                    </div>
                  ) : null}
                  <div style={{ marginTop: 10 }}>
                    <button style={styles.secondaryButton} onClick={() => runProposalProtocol(item)} disabled={protocolBusyId === item.id}>
                      {protocolBusyId === item.id ? "building protocol..." : "do this experiment (produce safeguard deviation protocol)"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.proposalBox}>
              {proposalText.map((line, idx) => <div key={idx} style={styles.proposalLine}>{line}</div>)}
            </div>
          )}
        </SectionCard>

        <SectionCard eyebrow="trace sample" title="stored simulated hits">
          {(simContext?.matched_traces?.length || simContext?.trace_sample?.length) ? (
            <div style={styles.traceList}>
              {(simContext?.matched_traces?.length ? simContext.matched_traces : simContext.trace_sample).slice(0, 8).map((row, idx) => (
                <div key={`${row.disease_id || row.year || "trace"}_${idx}`} style={styles.traceRow}>
                  <div style={styles.traceYear}>{row.year || "-"}</div>
                  <div style={styles.traceBody}>
                    <div style={styles.traceTitle}>{row.disease_name || row.disease_id || "unknown"}</div>
                    <div style={styles.traceSub}>best primary {row.best_primary_name || "-"} · coverage hits {row.coverage_hits ?? 0} · spillover {row.spillover_count ?? 0}</div>
                    {row.case_match_score ? <div style={styles.traceSub}>case match score {row.case_match_score}</div> : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.emptyText}>no simulation memory yet.</div>
          )}
        </SectionCard>
      </div>

      <SectionCard eyebrow="historical replay" title="train 1970 to 2005" right={<button style={styles.collapseButton} onClick={() => setShowHistory((v) => !v)}>{showHistory ? 'collapse' : 'expand'}</button>}>
        {historyError ? <div style={styles.errorBox}>history error: {historyError}</div> : null}
        {showHistory ? <>

        <div style={styles.actionsRow}>
          <button style={styles.secondaryButton} onClick={runHistorySeed} disabled={loadingHistorySeed}>
            {loadingHistorySeed ? "seeding..." : "seed historical bank"}
          </button>
          <button style={styles.secondaryButton} onClick={runHistoryReplay} disabled={loadingHistoryReplay}>
            {loadingHistoryReplay ? "replaying..." : "run one historical replay"}
          </button>
        </div>

        <div style={styles.actionsRow}>
          <button style={styles.secondaryButton} onClick={runHistoryTrain} disabled={loadingHistoryTrain}>
            {loadingHistoryTrain ? "training..." : "train 1970 → 2005 replay"}
          </button>
          <button style={styles.secondaryButton} onClick={runStoreHitLogic} disabled={loadingStoreHit}>
            {loadingStoreHit ? "storing..." : "store hit logic"}
          </button>
        </div>

        <div style={styles.helper}>replay historical rare-disease thinking and store reusable hit logic.</div>

        <div style={styles.gridBottom}>
          <div style={styles.subPanel}>
            <div style={styles.subPanelTitle}>historical replay bank</div>
            <div style={styles.memoryLine}><strong>schema version:</strong> {historyBank?.schema_version || "-"}</div>
            <div style={styles.memoryLine}><strong>training window:</strong> {historyBank ? `${historyBank.window_start_year || "-"} → ${historyBank.window_end_year || "-"}` : "-"}</div>
            <div style={styles.memoryLine}><strong>cases:</strong> {historyBank?.cases?.length || 0}</div>
            <div style={styles.memoryLine}><strong>replay runs:</strong> {historyBank?.replay_runs?.length || 0}</div>
            <div style={styles.memoryLine}><strong>goal:</strong> {historyBank?.training_goal || "not loaded"}</div>
          </div>

          <div style={styles.subPanel}>
            <div style={styles.subPanelTitle}>historical replay result</div>
            <div style={styles.memoryLine}><strong>replay id:</strong> {replayResult?.replay_id || "-"}</div>
            <div style={styles.memoryLine}><strong>matched case ids:</strong> {(replayResult?.matched_case_ids || []).join(", ") || "-"}</div>
            <div style={styles.memoryLine}><strong>predicted first medicine logic:</strong> {replayResult?.predicted_first_medicine_logic || "-"}</div>
            <div style={styles.memoryLine}><strong>predicted improvement logic:</strong> {replayResult?.predicted_improvement_logic || "-"}</div>
            <div style={styles.memoryLine}><strong>predicted failure logic:</strong> {replayResult?.predicted_failure_logic || "-"}</div>
            <div style={styles.memoryLine}><strong>stored logic note:</strong> {replayResult?.stored_logic_note || "-"}</div>
          </div>
        </div>

        <div style={styles.subPanel}>
          <div style={styles.subPanelTitle}>stored cases</div>
          {historyTrainResult ? (
            <div style={styles.helper}>last train result · runs added {historyTrainResult?.runs_added ?? historyTrainResult?.replay_runs_added ?? "-"} · hit logic stored {historyTrainResult?.hit_logic_stored ?? "-"}</div>
          ) : null}

          <CollapsibleBlock title="stored historical cases" defaultOpen={showStoredCases}>
          {historyBank?.cases?.length ? historyBank.cases.map((item) => (
            <div key={item.case_id} style={styles.addonCard}>
              <div style={styles.addonName}>{item.disease_name}</div>
              <div style={styles.addonScore}>discovery year {item.discovery_year || "-"} · {item.summary || "historical replay case"}</div>

              <div style={styles.metaGrid}>
                <div style={styles.metaCell}><strong>early doctor / researcher view:</strong> {item.discovery?.doctor_researcher_view || "-"}</div>
                <div style={styles.metaCell}><strong>suspected mechanism then:</strong> {item.discovery?.suspected_mechanism || "-"}</div>
                <div style={styles.metaCell}><strong>first medicine:</strong> {item.first_medicine?.medicine_name || "-"}</div>
                <div style={styles.metaCell}><strong>first medicine why:</strong> {item.first_medicine?.why_created || "-"}</div>
                <div style={styles.metaCell}><strong>why later medicines were better:</strong> {(item.later_medicines || []).map((m) => m.why_better_than_previous).filter(Boolean).join(" | ") || "-"}</div>
                <div style={styles.metaCell}><strong>failures / setbacks:</strong> {(item.failures || []).map((f) => `${f.label}: ${f.reason}`).join(" | ") || "-"}</div>
              </div>

              <div style={styles.subMiniPanel}>
                <div style={styles.subMiniTitle}>stored patterns</div>
                {(item.patterns || []).length ? item.patterns.map((pattern) => (
                  <div key={pattern.pattern_id} style={styles.proposalCard}>
                    <div style={styles.proposalTitle}>{pattern.pattern_summary || pattern.pattern_id}</div>
                    <div style={styles.proposalLine}><strong>reusable rule:</strong> {pattern.reusable_rule || "-"}</div>
                    <div style={styles.proposalLine}><strong>first medicine logic:</strong> {pattern.first_medicine_logic || "-"}</div>
                    <div style={styles.proposalLine}><strong>improvement logic:</strong> {pattern.improvement_logic || "-"}</div>
                    <div style={styles.proposalLine}><strong>failure logic:</strong> {pattern.failure_logic || "-"}</div>
                    <div style={styles.proposalLine}><strong>trigger features:</strong> {(pattern.trigger_features || []).join(", ") || "-"}</div>
                  </div>
                )) : <div style={styles.emptyText}>No stored patterns yet.</div>}
              </div>
            </div>
          )) : <div style={styles.emptyText}>No stored cases yet.</div>}
          </CollapsibleBlock>
        </div>
        </> : null}
      </SectionCard>

      <SectionCard eyebrow="Actions" title="export current state">
        <div style={styles.helper}>export saves the full rare-disease workflow object.</div>
        <button style={styles.ghostButton} onClick={handleExport}>export rare case (json)</button>
      </SectionCard>
    </div>
  );
}

const styles = {
  page: {
    display: "flex",
    flexDirection: "column",
    gap: 14,
    color: "#edf0ff",
  },
  gridTop: {
    display: "grid",
    gridTemplateColumns: "1.56fr 0.74fr",
    gap: 16,
    alignItems: "stretch",
  },
  gridBottom: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 16,
    alignItems: "stretch",
  },
  dualGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 14,
    alignItems: "start",
    marginBottom: 14,
  },
  sectionCard: {
    borderRadius: 18,
    border: "1px solid rgba(180, 190, 255, 0.14)",
    background: "linear-gradient(180deg, rgba(16, 20, 50, 0.72), rgba(10, 14, 30, 0.62))",
    boxShadow: "0 16px 60px rgba(0,0,0,0.45)",
    backdropFilter: "blur(10px)",
    overflow: "hidden",
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: 14,
    padding: "14px 16px 10px 16px",
    borderBottom: "1px solid rgba(180, 190, 255, 0.14)",
    background: "rgba(10, 14, 30, 0.25)",
  },
  sectionBody: {
    padding: 14,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  eyebrow: {
    fontSize: 10,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "rgba(240, 245, 255, 0.62)",
    marginBottom: 5,
    fontWeight: 600,
  },
  sectionTitle: {
    fontSize: 13,
    lineHeight: 1.22,
    fontWeight: 650,
    letterSpacing: "0.02em",
    textTransform: "lowercase",
    maxWidth: 520,
  },
  formRow: {
    display: "grid",
    gridTemplateColumns: "1.2fr 0.8fr 0.8fr 0.8fr",
    gap: 12,
    alignItems: "end",
  },
  formRowTrain: {
    display: "grid",
    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
    gap: 12,
    alignItems: "end",
  },
  field: { display: "flex", flexDirection: "column", gap: 7 },
  fieldSmall: { display: "flex", flexDirection: "column", gap: 7, minWidth: 0 },
  label: { fontSize: 11, color: "rgba(232,236,255,0.78)", textTransform: "lowercase", fontWeight: 500 },
  select: {
    height: 44,
    borderRadius: 14,
    border: "1px solid rgba(180, 190, 255, 0.14)",
    background: "rgba(10, 14, 30, 0.42)",
    color: "#eef0ff",
    padding: "0 14px",
    fontSize: 13,
    outline: "none",
    fontWeight: 500,
  },
  input: {
    height: 44,
    borderRadius: 14,
    border: "1px solid rgba(180, 190, 255, 0.14)",
    background: "rgba(10, 14, 30, 0.42)",
    color: "#eef0ff",
    padding: "0 14px",
    fontSize: 13,
    outline: "none",
    minWidth: 0,
    fontWeight: 500,
  },
  inputBig: {
    height: 48,
    borderRadius: 14,
    border: "1px solid rgba(180, 190, 255, 0.14)",
    background: "rgba(10, 14, 30, 0.42)",
    color: "#eef0ff",
    padding: "0 14px",
    fontSize: 14,
    fontWeight: 600,
    outline: "none",
    minWidth: 0,
  },
  textarea: {
    minHeight: 142,
    borderRadius: 14,
    border: "1px solid rgba(180, 190, 255, 0.14)",
    background: "rgba(10, 14, 30, 0.42)",
    color: "#eef0ff",
    padding: 14,
    fontSize: 13,
    lineHeight: 1.45,
    resize: "vertical",
    outline: "none",
    fontWeight: 500,
  },
  helper: { fontSize: 11, color: "rgba(225,229,255,0.58)", lineHeight: 1.45 },
  actionsRow: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 },
  primaryButton: {
    border: "1px solid rgba(154, 163, 255, 0.34)",
    background: "linear-gradient(180deg, rgba(131,95,255,0.90), rgba(105,84,250,0.82))",
    color: "#fff",
    borderRadius: 16,
    height: 44,
    padding: "0 20px",
    fontSize: 13,
    fontWeight: 650,
    cursor: "pointer",
    boxShadow: "0 8px 20px rgba(93,82,255,0.20)",
  },
  secondaryButton: {
    border: "1px solid rgba(154, 163, 255, 0.24)",
    background: "rgba(68,78,165,0.22)",
    color: "#f4f6ff",
    borderRadius: 16,
    minHeight: 48,
    padding: "10px 16px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    width: "100%",
  },
  ghostButton: {
    alignSelf: "flex-start",
    border: "1px solid rgba(154, 163, 255, 0.24)",
    background: "rgba(255,255,255,0.03)",
    color: "#eef0ff",
    borderRadius: 14,
    height: 40,
    padding: "0 16px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  },
  geneCount: { fontSize: 13, color: "rgba(234,238,255,0.78)", fontWeight: 500 },
  statsGrid: { display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 },
  statCard: {
    borderRadius: 16,
    border: "1px solid rgba(130,145,255,0.14)",
    background: "rgba(255,255,255,0.018)",
    padding: 14,
    minHeight: 104,
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
  },
  statLabel: { fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(228,231,255,0.66)", fontWeight: 600 },
  statValue: { fontSize: 15, lineHeight: 1.1, fontWeight: 650, letterSpacing: "-0.01em" },
  statSub: { fontSize: 12, lineHeight: 1.35, color: "rgba(231,236,255,0.68)" },
  errorBox: {
    borderRadius: 14,
    padding: "11px 13px",
    background: "rgba(120,22,52,0.16)",
    border: "1px solid rgba(255,110,160,0.24)",
    color: "#ffd7e4",
    fontSize: 13,
    lineHeight: 1.45,
  },
  memoryCard: {
    borderRadius: 18,
    border: "1px solid rgba(130,145,255,0.15)",
    background: "radial-gradient(circle at top right, rgba(118,102,255,0.12), transparent 26%), rgba(255,255,255,0.02)",
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  memoryLine: { fontSize: 13, lineHeight: 1.45, color: "#eef0ff" },
  heroResultCard: {
    borderRadius: 18,
    border: "1px solid rgba(130,145,255,0.16)",
    background: "radial-gradient(circle at top right, rgba(111, 92, 255, 0.14), transparent 24%), rgba(255,255,255,0.02)",
    padding: 16,
  },
  heroResultName: { fontSize: 15, lineHeight: 1.15, fontWeight: 650, letterSpacing: "-0.01em" },
  heroResultSub: { marginTop: 7, fontSize: 12, color: "rgba(231,236,255,0.74)", lineHeight: 1.45 },
  subPanel: {
    borderRadius: 16,
    border: "1px solid rgba(130,145,255,0.14)",
    background: "rgba(255,255,255,0.018)",
    padding: 14,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  subPanelTitle: { fontSize: 11, color: "rgba(230,234,255,0.70)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 },
  pillWrap: { display: "flex", flexWrap: "wrap", gap: 8 },
  pill: {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    padding: "6px 10px",
    border: "1px solid rgba(255,255,255,0.08)",
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: "0.01em",
  },
  pillDefault: { background: "rgba(90,98,180,0.16)", color: "#ecefff" },
  pillGood: { background: "rgba(61,148,113,0.16)", color: "#d9fff0", border: "1px solid rgba(84,191,147,0.20)" },
  pillWarn: { background: "rgba(167,129,52,0.18)", color: "#ffe8b3", border: "1px solid rgba(234,191,94,0.20)" },
  pillSoft: { background: "rgba(84,125,199,0.18)", color: "#d8e7ff", border: "1px solid rgba(111,154,231,0.22)" },
  pillBad: { background: "rgba(143,74,112,0.18)", color: "#ffd8ef", border: "1px solid rgba(188,98,144,0.22)" },
  signalList: { display: "flex", flexDirection: "column", gap: 8 },
  signalRow: {
    display: "grid",
    gridTemplateColumns: "minmax(0, auto) 18px minmax(0, 1fr)",
    alignItems: "center",
    gap: 8,
    padding: "8px 10px",
    borderRadius: 14,
    background: "rgba(255,255,255,0.015)",
    border: "1px solid rgba(130,145,255,0.10)",
  },
  signalLeft: { display: "flex", alignItems: "center", minWidth: 0 },
  signalArrow: { color: "rgba(227,232,255,0.45)", fontSize: 12, textAlign: "center" },
  signalRight: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" },
  signalAction: { fontSize: 12, color: "rgba(229,233,255,0.72)", fontWeight: 500 },
  signalCovered: { fontSize: 11, color: "#d9fff0", background: "rgba(61,148,113,0.14)", border: "1px solid rgba(84,191,147,0.18)", borderRadius: 999, padding: "4px 8px" },
  signalOpen: { fontSize: 11, color: "#ffe8b3", background: "rgba(167,129,52,0.14)", border: "1px solid rgba(234,191,94,0.18)", borderRadius: 999, padding: "4px 8px" },
  addonGrid: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 },
  addonCard: {
    borderRadius: 18,
    border: "1px solid rgba(130,145,255,0.14)",
    background: "rgba(255,255,255,0.018)",
    padding: 14,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  addonName: { fontSize: 14, fontWeight: 650, lineHeight: 1.2 },
  addonScore: { fontSize: 12, color: "rgba(230,234,255,0.66)" },
  subMiniPanel: {
    borderRadius: 14,
    border: "1px solid rgba(130,145,255,0.12)",
    background: "rgba(255,255,255,0.015)",
    padding: 12,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  subMiniTitle: { fontSize: 10, textTransform: "uppercase", letterSpacing: "0.06em", color: "rgba(230,234,255,0.60)", fontWeight: 600 },
  metaGrid: { display: "grid", gridTemplateColumns: "1fr", gap: 8 },
  metaCell: { fontSize: 12, lineHeight: 1.45, color: "rgba(232,236,255,0.78)" },
  bundleHeader: { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", borderRadius: 16, padding: "12px 14px", background: "rgba(255,255,255,0.018)", border: "1px solid rgba(130,145,255,0.12)" },
  bundleNames: { fontSize: 14, fontWeight: 650 },
  bundleScore: { fontSize: 12, color: "rgba(230,234,255,0.66)" },
  bundleList: { display: "flex", flexWrap: "wrap", gap: 8 },
  bundleItem: { borderRadius: 999, padding: "7px 11px", background: "rgba(255,255,255,0.035)", border: "1px solid rgba(130,145,255,0.14)", fontSize: 12, fontWeight: 600 },
  proposalBox: { borderRadius: 16, border: "1px solid rgba(130,145,255,0.12)", background: "rgba(255,255,255,0.018)", padding: 14, display: "flex", flexDirection: "column", gap: 8 },
  proposalGrid: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 },
  proposalCard: { borderRadius: 16, border: "1px solid rgba(130,145,255,0.12)", background: "rgba(255,255,255,0.018)", padding: 14, display: "flex", flexDirection: "column", gap: 8 },
  proposalTitle: { fontSize: 13, fontWeight: 650 },
  proposalLine: { fontSize: 12, lineHeight: 1.45, color: "rgba(232,236,255,0.78)" },
  decisionBoard: {
    borderRadius: 18,
    border: "1px solid rgba(130,145,255,0.15)",
    background: "radial-gradient(circle at top right, rgba(111, 92, 255, 0.16), transparent 24%), rgba(255,255,255,0.02)",
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  decisionHero: {
    borderRadius: 16,
    border: "1px solid rgba(130,145,255,0.14)",
    background: "rgba(255,255,255,0.02)",
    padding: 16,
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  decisionHeroTitle: { fontSize: 16, lineHeight: 1.2, fontWeight: 700, letterSpacing: "-0.01em" },
  decisionHeroValue: { fontSize: 28, lineHeight: 1, fontWeight: 750, letterSpacing: "-0.03em" },
  decisionHeroSub: { fontSize: 13, lineHeight: 1.45, color: "rgba(232,236,255,0.72)" },
  decisionSplitGrid: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 },
  auditList: { display: "flex", flexDirection: "column", gap: 10 },
  auditRow: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    padding: "10px 12px",
    borderRadius: 14,
    border: "1px solid rgba(130,145,255,0.10)",
    background: "rgba(255,255,255,0.015)",
  },
  auditRowCompact: { display: "flex", flexDirection: "column", gap: 6 },
  auditHead: { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" },
  auditTrack: {
    height: 8,
    borderRadius: 999,
    background: "rgba(255,255,255,0.06)",
    overflow: "hidden",
    border: "1px solid rgba(130,145,255,0.10)",
  },
  auditFill: {
    height: "100%",
    borderRadius: 999,
    background: "linear-gradient(90deg, rgba(121,99,255,0.92), rgba(106,198,255,0.82))",
  },
  compactRankList: { display: "flex", flexDirection: "column", gap: 8 },
  compactRankRow: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "center",
    padding: "10px 12px",
    borderRadius: 14,
    background: "rgba(255,255,255,0.015)",
    border: "1px solid rgba(130,145,255,0.10)",
  },
  rankList: { display: "flex", flexDirection: "column", gap: 8, maxHeight: 360, overflow: "auto" },
  rankRow: { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: "10px 12px", borderRadius: 14, background: "rgba(255,255,255,0.015)", border: "1px solid rgba(130,145,255,0.10)" },
  rankName: { fontSize: 13, fontWeight: 600 },
  rankSub: { fontSize: 11, color: "rgba(232,236,255,0.60)", marginTop: 4 },
  rankScore: { fontSize: 12, fontWeight: 650, color: "#eef0ff" },
  traceList: { display: "flex", flexDirection: "column", gap: 10 },
  traceRow: { display: "grid", gridTemplateColumns: "72px minmax(0, 1fr)", gap: 12, borderRadius: 16, border: "1px solid rgba(130,145,255,0.12)", background: "rgba(255,255,255,0.018)", padding: 12 },
  traceYear: { fontSize: 13, fontWeight: 650, color: "#eef0ff" },
  traceBody: { display: "flex", flexDirection: "column", gap: 5 },
  traceTitle: { fontSize: 13, fontWeight: 600 },
  traceSub: { fontSize: 12, color: "rgba(232,236,255,0.70)" },
  emptyText: { fontSize: 12, lineHeight: 1.45, color: "rgba(226,230,255,0.54)" },
};

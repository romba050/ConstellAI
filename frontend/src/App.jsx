import React, { useEffect, useMemo, useState } from "react";
import SpaceBackground from "./SpaceBackground.jsx";
import RareDiseaseTab from "./RareDiseaseTab.jsx";
import RareDiseasePredictorTab from "./RareDiseasePredictorTab.jsx";
import RegistryBrowserPanel from "./RegistryBrowserPanel.jsx";
import SelfLLMTab from "./SelfLLMTab.jsx";
import { downloadJSON, buildExportEnvelope } from "./exportUtils.js";
import {
  DISEASE_UNIVERSE,
  getDrugsForSubcategory,
  EVIDENCE_STARTERS,
  DRUG_LIBRARY,
  getObjectiveEvidenceForId,
  SIDE_EFFECT_SUPPORT_INDEX,
  NEGATIVE_HABIT_LIBRARY,
} from "./mockData.js";
import {
  compoundsForTarget,
  compoundsForDrug,
  interactionReport,
  optimizeStack,
  generateEarlyKillExperiments,
  rankMimicCandidates,
  targetHitCount,
  normalizeTargetLabel,
  setRuntimeMimicLibrary,
} from "./logic.js";
import { safeguardAnalyze } from "./safeguardLogic.js";
import { apiCompoundAnalyze, apiDrugMimicDrugs, apiRegistryDiseaseDrugs, apiSafeguardAnalyze, apiSafeguardMemoryAdd, apiSystemMemorySummary, apiRegistrySummary, apiRegistryHydrateAll, apiBiomedManifest, apiRareCompounds, apiRarePhysiology } from "./apiClient.js";
import "./styles.css";
import "./clinicalLaunch.css";

function TabButton({ id, active, onClick, children }) {
  return (
    <button className={`tabbtn ${active ? "active" : ""}`} onClick={() => onClick(id)}>
      {children}
    </button>
  );
}

function Breadcrumb({ disease, subcat, drug, onJump }) {
  return (
    <div className="breadcrumb">
      <div className={`crumb ${!disease ? "crumbStrong" : ""}`} onClick={() => onJump({ level: "root" })}>
        diseases
      </div>
      {disease && (
        <div className={`crumb ${disease && !subcat ? "crumbStrong" : ""}`} onClick={() => onJump({ level: "disease" })}>
          {disease.label}
        </div>
      )}
      {subcat && (
        <div className={`crumb ${subcat && !drug ? "crumbStrong" : ""}`} onClick={() => onJump({ level: "subcat" })}>
          {subcat.label}
        </div>
      )}
      {drug && <div className="crumb crumbStrong">{drug.name}</div>}
    </div>
  );
}

function isProvisionalTargetLabel(label) {
  const raw = String(label || "").trim();
  if (!raw) return false;
  return /\b(starter|secondary\s+starter|light\s+signal|context)\b/i.test(raw);
}

function cleanTargetBucket(items = []) {
  const seen = new Set();
  const clean = [];
  for (const item of items || []) {
    if (isProvisionalTargetLabel(item)) continue;
    const norm = normalizeTargetLabel(item);
    if (!norm || seen.has(norm)) continue;
    seen.add(norm);
    clean.push(norm);
  }
  return clean;
}

function sanitizeDrugActivates(activates = {}) {
  return {
    genes: cleanTargetBucket(activates.genes || []),
    receptors: cleanTargetBucket(activates.receptors || []),
    sirtuins: cleanTargetBucket(activates.sirtuins || []),
    pathways: cleanTargetBucket(activates.pathways || []),
  };
}

function PlanetGrid({ items, onPick, metaFn }) {
  return (
    <div className="planetGrid">
      {items.map((x) => (
        <div key={x.id} className="planet" onClick={() => onPick(x)}>
          <div className="planetLabel">{x.label || x.name}</div>
          <div className="planetMeta">{metaFn ? metaFn(x) : "open"}</div>
        </div>
      ))}
    </div>
  );
}

function WelcomeLanding({ onOpen, onQuickOpen }) {
  const entries = [
    { id: "rare", label: "rare diseases", meta: "triage, mechanism review, therapy comparison" },
    { id: "drug", label: "drug mimicking", meta: "target surfaces, stack design, mimic supports" },
    { id: "safeguard", label: "safeguard deviation", meta: "protocol drift, failure prevention, checklisting" },
    { id: "predictor", label: "rare disease predictor", meta: "historical replay, pattern detection, frontier search" },
    { id: "more", label: "research ops", meta: "memory, evidence, registry, self-llm" },
  ];

  return (
    <div className="welcomeShell">
      <div className="welcomeHero">
        <div className="welcomeEyebrow">med-r5 institutional workspace</div>
        <div className="welcomeTitle">welcome</div>
        <div className="welcomeSub">
          clinical rare disease research workspace for disease triage, drug mimic design, safeguard control, and registry-backed exploration.
        </div>
        <div className="welcomeActions">
          <button className="btn" onClick={() => onQuickOpen("rare")}>open rare disease triage</button>
          <button className="btn btnGhost" onClick={() => onQuickOpen("drug")}>open drug mimicking</button>
        </div>
      </div>
      <div className="welcomeOrbitWrap">
        <div className="welcomeOrbitGrid">
          {entries.map((entry) => (
            <div key={entry.id} className="planet welcomePlanet" onClick={() => onOpen(entry.id)}>
              <div className="planetLabel">{entry.label}</div>
              <div className="planetMeta">{entry.meta}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TargetSection({ title, items, selected, onToggle }) {
  return (
    <div className="card bubbleCard">
      <div className="cardTitle">{title}</div>
      <div className="bubbleRow">
        {items.map((t) => (
          <div key={t} className={`bubblePill ${selected.has(t) ? "on" : ""}`} onClick={() => onToggle(t)}>
            {normalizeTargetLabel(t)}
          </div>
        ))}
        {!items.length && <div className="small">no targets available.</div>}
      </div>
    </div>
  );
}

function MimicPicker({ drug, targetsSelected, selectedCompounds, onToggleCompound, mimicMode, onChangeMode }) {
  const [query, setQuery] = useState("");

  const candidates = useMemo(() => {
    const set = new Map();
    for (const t of targetsSelected) {
      for (const c of compoundsForTarget(t)) set.set(c.id, c);
    }
    for (const c of compoundsForDrug(drug)) {
      if (!set.has(c.id)) set.set(c.id, c);
    }
    let rows = Array.from(set.values());
    if (mimicMode === "compound") rows = rows.filter((x) => (x.kind || "compound") === "compound");
    if (mimicMode === "diet") rows = rows.filter((x) => (x.kind || "compound") === "diet");
    if (mimicMode === "physiology") rows = rows.filter((x) => (x.kind || "compound") === "physiology");
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      rows = rows.filter((x) => String(x.name || "").toLowerCase().includes(q) || String((x.targets || []).join(" ")).toLowerCase().includes(q));
    }
    return rankMimicCandidates(targetsSelected, rows);
  }, [drug, targetsSelected, mimicMode, query]);

  const selectionCount = targetsSelected.length;

  return (
    <div className="card bubbleCard">
      <div className="cardTitle">mimic support</div>
      <div className="cardSub">compound, diet, and physiology supports ranked against selected medicinal targets and the anchor drug profile.</div>
      <div className="bubbleRow" style={{ marginBottom: 10 }}>
        {[
          ["hybrid", "all"],
          ["compound", "compound"],
          ["diet", "diet"],
          ["physiology", "physiology"],
        ].map(([value, label]) => (
          <div key={value} className={`bubblePill ${mimicMode === value ? "on" : ""}`} onClick={() => onChangeMode(value)}>
            {label}
          </div>
        ))}
      </div>
      <input className="softInput" placeholder="search mimic items or targets" value={query} onChange={(e) => setQuery(e.target.value)} style={{ marginBottom: 10 }} />
      <div className="small" style={{ marginBottom: 10 }}>selected targets {selectionCount} • anchor drug {drug?.name || "none"} • candidates {candidates.length}</div>
      <div className="list">
        {candidates.map((c) => {
          const on = selectedCompounds.some((x) => x.id === c.id);
          const refs = (getObjectiveEvidenceForId(c.id)?.refs || []).length;
          const hits = targetHitCount(c, targetsSelected);
          return (
            <div key={c.id} className={`card subcard mimicCard ${on ? "cardSelected" : ""}`} onClick={() => onToggleCompound(c)} style={{ cursor: "pointer" }}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                <div>
                  <div className="cardTitle">{c.name}</div>
                  <div className="cardSub">[{c.kind || "compound"}] • target hits {hits} • refs {refs}</div>
                </div>
                <div className={`bubblePill ${on ? "on" : ""}`}>{on ? "selected" : "pick"}</div>
              </div>
              <div className="bubbleRow" style={{ marginTop: 8 }}>
                {(c.targets || []).slice(0, 6).map((t) => <div key={t} className="bubblePill">{normalizeTargetLabel(t)}</div>)}
              </div>
            </div>
          );
        })}
        {!candidates.length && <div className="small">select targets first.</div>}
      </div>
    </div>
  );
}


function computeDrugSynergyRows({ selectedTargets, selectedCompounds, currentDrug }) {
  const targetList = Array.from(new Set((selectedTargets || []).map((t) => normalizeTargetLabel(t)).filter(Boolean)));
  const selectedIds = new Set((selectedCompounds || []).map((item) => item.id));
  const selectedTargetHits = new Set();
  for (const item of selectedCompounds || []) {
    for (const t of item.targets || []) selectedTargetHits.add(normalizeTargetLabel(t));
  }

  const pool = new Map();
  for (const target of targetList) {
    for (const item of compoundsForTarget(target)) {
      if (!item || selectedIds.has(item.id)) continue;
      pool.set(item.id, item);
    }
  }

  return Array.from(pool.values())
    .map((item) => {
      const hitTargets = (item.targets || [])
        .map((t) => normalizeTargetLabel(t))
        .filter((t) => targetList.includes(t));
      const newCoverage = hitTargets.filter((t) => !selectedTargetHits.has(t));
      const overlapWithSelected = hitTargets.filter((t) => selectedTargetHits.has(t));
      const simReport = interactionReport([...(selectedCompounds || []), item]);
      const warnings = simReport?.warnings || [];
      const highWarnings = warnings.filter((w) => String(w.level || '').toUpperCase() === 'HIGH').length;
      const medWarnings = warnings.filter((w) => String(w.level || '').toUpperCase() === 'MED').length;
      const evidenceRefs = (getObjectiveEvidenceForId(item.id)?.refs || []).length;
      const conflictPenalty = highWarnings * 1.8 + medWarnings * 0.8;
      const score = Number((newCoverage.length * 2.6 + overlapWithSelected.length * 1.1 + evidenceRefs * 0.25 - conflictPenalty).toFixed(2));
      return {
        item,
        hitTargets,
        newCoverage,
        overlapWithSelected,
        warnings,
        highWarnings,
        medWarnings,
        evidenceRefs,
        score,
      };
    })
    .filter((row) => row.hitTargets.length)
    .sort((a, b) => b.score - a.score || b.newCoverage.length - a.newCoverage.length || a.highWarnings - b.highWarnings)
    .slice(0, 6);
}

function DrugSynergyPanel({ drug, selectedTargets, selectedCompounds }) {
  const rows = useMemo(
    () => computeDrugSynergyRows({ selectedTargets, selectedCompounds, currentDrug: drug }),
    [drug, selectedTargets, selectedCompounds]
  );

  return (
    <div className="panel">
      <div className="panelHead">
        <div className="panelTitle">synergy layer</div>
        <div className="small">what best complements the current mimic stack without creating obvious stack noise.</div>
      </div>
      <div className="panelBody">
        {!drug ? (
          <div className="small">pick a drug first.</div>
        ) : !selectedTargets.length ? (
          <div className="small">select targets first to unlock synergy ranking.</div>
        ) : !rows.length ? (
          <div className="small">no clear complement candidate yet from the current target set.</div>
        ) : (
          <div className="list">
            {rows.map((row) => (
              <div key={row.item.id} className="card subcard">
                <div className="row" style={{ justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <div>
                    <div className="cardTitle">{row.item.name}</div>
                    <div className="cardSub">
                      [{row.item.kind || "compound"}] • synergy score {row.score} • refs {row.evidenceRefs}
                    </div>
                  </div>
                  <div className={`bubblePill ${row.highWarnings ? "badTone" : row.newCoverage.length >= 2 ? "on" : ""}`}>
                    {row.highWarnings ? "watch conflicts" : row.newCoverage.length ? "good complement" : "overlap support"}
                  </div>
                </div>

                <div className="kv compactKv" style={{ marginTop: 10 }}>
                  <div>new target closure</div>
                  <div>{row.newCoverage.map(normalizeTargetLabel).join(", ") || "none"}</div>
                  <div>shared reinforcement</div>
                  <div>{row.overlapWithSelected.map(normalizeTargetLabel).join(", ") || "none"}</div>
                  <div>risk signal</div>
                  <div>{row.highWarnings ? `${row.highWarnings} high` : row.medWarnings ? `${row.medWarnings} medium` : "low"}</div>
                </div>

                {!!row.warnings.length && (
                  <div className="warnBox" style={{ marginTop: 10 }}>
                    {row.warnings.slice(0, 2).map((w, idx) => (
                      <div key={idx} className={`warn ${w.level === "HIGH" ? "high" : ""}`}>
                        <div className="warnTitle">{w.level} • {w.title}</div>
                        <div className="warnDetail">{w.detail}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


function confidenceTone(v) {
  const n = Number(v || 0);
  if (n >= 0.75) return "on";
  if (n >= 0.5) return "";
  return "badTone";
}

function SideEffectSupportPanel({ drug }) {
  const meta = useMemo(() => {
    if (!drug) return null;
    const key = String(drug.id || "").toLowerCase();
    return SIDE_EFFECT_SUPPORT_INDEX[key] || SIDE_EFFECT_SUPPORT_INDEX[String(drug.name || "").toLowerCase()] || null;
  }, [drug]);

  if (!drug) return null;

  return (
    <div className="panel">
      <div className="panelHead">
        <div className="panelTitle">side-effect support</div>
        <div className="small">structured mitigation logic with evidence anchors.</div>
      </div>
      <div className="panelBody">
        {!meta ? (
          <div className="card">
            <div className="cardTitle">support frame pending</div>
            <div className="cardSub">no seeded mitigation logic yet for {drug.name}.</div>
          </div>
        ) : (
          <div className="list">
            <div className="card">
              <div className="cardTitle">drug support frame</div>
              <div className="kv compactKv">
                <div>drug</div><div>{meta.drug}</div>
                <div>class</div><div>{meta.className}</div>
                <div>common effects</div><div>{(meta.commonEffects || []).join(', ')}</div>
                <div>confidence</div><div>{meta.confidenceLabel} ({meta.confidence})</div>
              </div>
            </div>
            {(meta.effects || []).map((effect) => (
              <div key={effect.label} className="card subcard">
                <div className="row" style={{justifyContent:'space-between', alignItems:'center', gap:8}}>
                  <div>
                    <div className="cardTitle">{effect.label}</div>
                    <div className="cardSub">{effect.mechanism}</div>
                  </div>
                  <div className={`bubblePill ${confidenceTone(effect.confidence)}`}>{effect.evidenceTier} · {effect.confidence}</div>
                </div>
                <div className="sideEffectGrid">
                  <div className="sideEffectCell"><div className="smallLabel">physiology</div><div className="small">{effect.physiology}</div></div>
                  <div className="sideEffectCell"><div className="smallLabel">diet</div><div className="small">{effect.diet}</div></div>
                  <div className="sideEffectCell"><div className="smallLabel">compound</div><div className="small">{effect.compound}</div></div>
                  <div className="sideEffectCell"><div className="smallLabel">supportive medication</div><div className="small">{effect.medication}</div></div>
                  <div className="sideEffectCell"><div className="smallLabel">interaction risk</div><div className="small">{effect.interactionRisk}</div></div>
                </div>
                <div className="list" style={{marginTop:10}}>
                  {(effect.refs || []).map((ref, idx) => (
                    <a key={idx} className="small evidenceLink" href={ref.url} target="_blank" rel="noreferrer">~ {ref.label}</a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function HabitOffsetTab() {
  const [habitId, setHabitId] = useState(NEGATIVE_HABIT_LIBRARY[0]?.id || '');
  const [severity, setSeverity] = useState('moderate');
  const habit = useMemo(() => NEGATIVE_HABIT_LIBRARY.find((x) => x.id === habitId) || NEGATIVE_HABIT_LIBRARY[0], [habitId]);
  const scaleMap = { low: 0.85, moderate: 1.0, heavy: 1.18 };
  const scaledConfidence = Math.max(0.25, Math.min(0.95, Number((habit?.confidence || 0.6) * (severity === 'heavy' ? 0.94 : 1.0)).toFixed(2)));

  return (
    <div className="grid rareSoloGrid">
      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">negative habits</div>
          <div className="small">map habit damage into offset functions.</div>
        </div>
        <div className="panelBody">
          <div className="planetGrid" style={{gridTemplateColumns:'repeat(2, minmax(0, 1fr))'}}>
            {NEGATIVE_HABIT_LIBRARY.map((item) => (
              <div key={item.id} className={`planet ${item.id === habit?.id ? 'planetActive' : ''}`} onClick={() => setHabitId(item.id)}>
                <div className="planetLabel">{item.name}</div>
                <div className="planetMeta">{item.summary}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="list">
        <div className="panel">
          <div className="panelHead">
            <div className="panelTitle">habit damage map</div>
            <div className="small">{habit?.name || '-'} </div>
          </div>
          <div className="panelBody">
            <div className="card">
              <div className="row" style={{justifyContent:'space-between', alignItems:'center', gap:8}}>
                <div>
                  <div className="cardTitle">exposure severity</div>
                  <div className="cardSub">scale offsets to real-world burden.</div>
                </div>
                <div className="bubbleRow">
                  {['low','moderate','heavy'].map((level) => <div key={level} className={`bubblePill ${severity === level ? 'on' : ''}`} onClick={() => setSeverity(level)}>{level}</div>)}
                </div>
              </div>
            </div>
            <div className="card">
              <div className="cardTitle">signals under pressure</div>
              <div className="bubbleRow" style={{marginTop:8}}>{(habit?.signals || []).map((s) => <div key={s} className="bubblePill">{s}</div>)}</div>
              <div className="small" style={{marginTop:10}}>{habit?.impact}</div>
            </div>
            <div className="card">
              <div className="cardTitle">offset frame</div>
              <div className="kv compactKv">
                <div>physiology</div><div>{habit?.offsets?.physiology}</div>
                <div>diet</div><div>{habit?.offsets?.diet}</div>
                <div>compound</div><div>{habit?.offsets?.compound}</div>
                <div>medication</div><div>{habit?.offsets?.medication}</div>
                <div>model confidence</div><div>{scaledConfidence}</div>
              </div>
            </div>
          </div>
        </div>
        <div className="panel">
          <div className="panelHead">
            <div className="panelTitle">objective anchors</div>
            <div className="small">evidence-backed offset items.</div>
          </div>
          <div className="panelBody">
            <div className="list">
              {(habit?.refs || []).map((ref, idx) => (
                <div key={idx} className="card subcard">
                  <div className="row" style={{justifyContent:'space-between', alignItems:'center', gap:8}}>
                    <div>
                      <div className="cardTitle">{ref.title}</div>
                      <div className="cardSub">{ref.note}</div>
                    </div>
                    <div className={`bubblePill ${confidenceTone((ref.confidence || 0.6) * (scaleMap[severity] || 1))}`}>{ref.evidenceTier}</div>
                  </div>
                  <a className="small evidenceLink" href={ref.url} target="_blank" rel="noreferrer">~ {ref.label}</a>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ObjectiveEvidencePanel({ drug, selectedTargets, selectedCompounds }) {
  const rows = useMemo(() => {
    const unique = [];
    const seen = new Set();
    for (const item of selectedCompounds || []) {
      if (seen.has(item.id)) continue;
      seen.add(item.id);
      const evidence = getObjectiveEvidenceForId(item.id);
      if (evidence) unique.push({ item, evidence });
    }
    return unique;
  }, [selectedCompounds]);

  const drugMeta = useMemo(() => {
    if (!drug) return null;
    return DRUG_LIBRARY.find((x) => x.id === drug.id || String(x.name || '').toLowerCase() === String(drug.name || '').toLowerCase()) || null;
  }, [drug]);

  return (
    <div className="panel">
      <div className="panelHead">
        <div className="panelTitle">objective evidence</div>
        <div className="small">citation anchors for selected mimic items.</div>
      </div>
      <div className="panelBody">
        {!!drugMeta && (
          <div className="card">
            <div className="cardTitle">drug anchor</div>
            <div className="cardSub">{drugMeta.name} • {drugMeta.class}</div>
            <div className="small" style={{ marginTop: 8 }}>targets: {(drugMeta.targets || []).join(', ') || 'none'}</div>
            <div className="small" style={{ marginTop: 8 }}>selected targets: {(selectedTargets || []).map(normalizeTargetLabel).join(', ') || 'none selected'}</div>
          </div>
        )}
        <div className="list" style={{ marginTop: 12 }}>
          {rows.map(({ item, evidence }) => (
            <div key={item.id} className="card subcard">
              <div className="cardTitle">{item.name}</div>
              <div className="cardSub">[{item.kind || 'compound'}] • covers {(item.targets || []).slice(0, 5).map(normalizeTargetLabel).join(', ') || 'none'}</div>
              <div className="small" style={{ marginTop: 8 }}>{evidence.mechanism}</div>
              <div className="list" style={{ marginTop: 10 }}>
                {(evidence.refs || []).map((ref, idx) => (
                  <a key={idx} className="small evidenceLink" href={ref.url} target="_blank" rel="noreferrer">~ {ref.label}</a>
                ))}
              </div>
            </div>
          ))}
          {!rows.length && <div className="small">pick at least one mimic item to surface objective citations.</div>}
        </div>
      </div>
    </div>
  );
}

function StackPanel({ selectedCompounds, mandatoryIds, setMandatoryIds, selectedTargets, drug }) {
  const report = useMemo(() => interactionReport(selectedCompounds), [selectedCompounds]);

  function toggleMandatory(id) {
    setMandatoryIds((prev) => {
      const s = new Set(prev);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      return Array.from(s);
    });
  }

  return (
    <div className="panel">
      <div className="panelHead">
        <div className="panelTitle">stack control</div>
        <div className="small">general medicinal review for useful anchors, overlap burden, and avoidable redundancy.</div>
      </div>
      <div className="panelBody">
        <div className="card">
          <div className="cardTitle">selected stack</div>
          <div className="row">
            {selectedCompounds.map((c) => (
              <div key={c.id} className={`pill ${mandatoryIds.includes(c.id) ? "on" : ""}`} onClick={() => toggleMandatory(c.id)}>
                {c.name}
              </div>
            ))}
            {!selectedCompounds.length && <div className="small">no medicinal supports selected.</div>}
          </div>
          <div className="kv compactKv">
            <div>hepatic burden</div>
            <div>{report.score.liverLoad}</div>
            <div>metabolic push</div>
            <div>{report.score.nadBoost}</div>
            <div>same-axis items</div>
            <div>{report.score.nadBoosterCount}</div>
            <div>redundancy watch</div>
            <div>{report.score.b3DerivativeCount}</div>
          </div>
          <div className="warnBox">
            {report.warnings.map((w, idx) => (
              <div key={idx} className={`warn ${w.level === "HIGH" ? "high" : ""}`}>
                <div className="warnTitle">{w.level} • {w.title}</div>
                <div className="warnDetail">{w.detail}</div>
              </div>
            ))}
            {!report.warnings.length && <div className="small">no major warnings detected.</div>}
          </div>
          <div className="small" style={{ marginTop: 10 }}>selected targets: {(selectedTargets || []).map(normalizeTargetLabel).join(', ') || "none"} • anchor drug: {drug?.name || "none"}</div>
        </div>
      </div>
    </div>
  );
}

function EarlyKillPanel({ drug, chosenTargets, selectedCompounds }) {
  const experiments = useMemo(() => {
    if (!drug) return [];
    return generateEarlyKillExperiments({ drug, chosenTargets, selectedCompounds });
  }, [drug, chosenTargets, selectedCompounds]);

  const summary = useMemo(() => {
    const costTotal = experiments.reduce((a, e) => a + Number(e.costEUR || 0), 0);
    const upsideTotal = experiments.reduce((a, e) => a + Number(e.profitEUR || 0), 0);
    const avgRisk = experiments.length ? Math.round(experiments.reduce((a, e) => a + Number(e.failProb || 0), 0) / experiments.length) : 0;
    const best = [...experiments].sort((a, b) => (b.profitEUR - b.costEUR) - (a.profitEUR - a.costEUR))[0] || null;
    const tierCounts = experiments.reduce((acc, e) => {
      const key = String(e.tier || 'cheap').toLowerCase();
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {});
    return { costTotal, upsideTotal, avgRisk, best, tierCounts };
  }, [experiments]);

  return (
    <div className="panel">
      <div className="panelHead">
        <div className="panelTitle">early-kill hypotheses</div>
        <div className="small">cheap, medium, and heavy assay paths with stop rules.</div>
      </div>
      <div className="panelBody">
        {!drug && <div className="small">select a drug first.</div>}
        {!!drug && (
          <div className="list">
            <div className="card">
              <div className="cardTitle">portfolio view</div>
              <div className="kv compactKv">
                <div>total cost</div>
                <div>{fmtMoney(summary.costTotal)}</div>
                <div>total upside</div>
                <div>{fmtMoney(summary.upsideTotal)}</div>
                <div>avg risk</div>
                <div>{summary.avgRisk}%</div>
                <div>best candidate</div>
                <div>{summary.best?.title || "none"}</div>
                <div>cheap / medium / heavy</div>
                <div>{summary.tierCounts.cheap || 0} / {summary.tierCounts.medium || 0} / {summary.tierCounts.heavy || 0}</div>
              </div>
            </div>
            {experiments.map((e) => (
              <div key={e.id} className="card earlyKillCard">
                <div className="earlyKillTop">
                  <div>
                    <div className="cardTitle">{e.title}</div>
                    <div className="cardSub">{e.hypothesis}</div>
                  </div>
                  <div className={`tierBadge tier_${String(e.tier || 'cheap').toLowerCase()}`}>{e.tier}</div>
                </div>
                <div className="hr" />
                <div className="small">{e.why}</div>
                <div className="kv compactKv">
                  <div>assay type</div>
                  <div>{e.assayType}</div>
                  <div>target family</div>
                  <div>{e.targetFamily}</div>
                  <div>cost</div>
                  <div>{fmtMoney(e.costEUR)}</div>
                  <div>upside</div>
                  <div>{fmtMoney(e.profitEUR)}</div>
                  <div>risk</div>
                  <div>{e.failProb}%</div>
                  <div>days</div>
                  <div>{e.days}</div>
                </div>
                <div className="stopBox">stop signal: {e.stopSignal}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SafeguardTab() {
  const [experimentText, setExperimentText] = useState("we will freeze cells for long-term storage using dmso and ln2.");
  const [outcomeText, setOutcomeText] = useState("we freezed cells but x happened so we lost this amount of cost");
  const [estimatedSavingsEUR, setEstimatedSavingsEUR] = useState(30000);
  const [failureReductionPct, setFailureReductionPct] = useState(3);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saveNote, setSaveNote] = useState("");

  async function runAnalyze() {
    try {
      setLoading(true);
      setError("");
      const res = await apiSafeguardAnalyze({ experiment_text: experimentText });
      setResult(res || null);
    } catch (err) {
      setError(String(err?.message || err || "safeguard analyze failed"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { runAnalyze(); }, []);

  async function storeOutcome() {
    try {
      setSaving(true);
      setSaveNote("");
      await apiSafeguardMemoryAdd({
        items: [{
          text: experimentText.trim() || "safeguard run",
          tags: (result?.tags || []).slice(0, 6),
          protocol_used: true,
          estimated_savings_eur: Number(estimatedSavingsEUR || 0),
          failure_reduction_pct: Number(failureReductionPct || 0),
          outcome_text: outcomeText,
        }],
      });
      setSaveNote("stored to backend safeguard memory");
    } catch (err) {
      setError(String(err?.message || err || "failed to store safeguard outcome"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid">
      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">safeguard input</div>
          <div className="small">describe experiment + store free-text deviations to train memory.</div>
        </div>
        <div className="panelBody">
          <div className="card">
            <div className="cardTitle">experiment description</div>
            <textarea className="softTextarea" value={experimentText} onChange={(e) => setExperimentText(e.target.value)} rows={7} />
            <div className="row">
              <button className="btn" onClick={runAnalyze} disabled={loading}>{loading ? "running..." : "run safeguard"}</button>
            </div>
          </div>

          <div className="card" style={{ marginTop: 12 }}>
            <div className="cardTitle">experiment outcome / deviation memory</div>
            <textarea className="softTextarea" value={outcomeText} onChange={(e) => setOutcomeText(e.target.value)} rows={6} />
            <div className="split2" style={{ marginTop: 12 }}>
              <div>
                <div className="cardTitle">estimated savings (eur)</div>
                <input className="softInput" type="number" value={estimatedSavingsEUR} onChange={(e) => setEstimatedSavingsEUR(Number(e.target.value))} />
              </div>
              <div>
                <div className="cardTitle">failure reduction %</div>
                <input className="softInput" type="number" value={failureReductionPct} onChange={(e) => setFailureReductionPct(Number(e.target.value))} />
              </div>
            </div>
            <div className="row">
              <button className="btn" onClick={storeOutcome} disabled={saving || !outcomeText.trim()}>{saving ? "storing..." : "store to memory"}</button>
              {saveNote ? <div className="small">{saveNote}</div> : null}
            </div>
          </div>

          {!!error && <div className="warn high" style={{ marginTop: 12 }}><div className="warnDetail">{error}</div></div>}
        </div>
      </div>

      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">safeguard output</div>
          <div className="small">backend tags + failure modes + preventable safeguards.</div>
        </div>
        <div className="panelBody">
          {!result && <div className="small">run safeguard to load output.</div>}
          {!!result && (
            <>
              <div className="card">
                <div className="cardTitle">tag scan</div>
                <div className="row">
                  {(result.tags || []).map((tag) => <div key={tag} className="pill">{tag}</div>)}
                </div>
                <div className="cardSub" style={{ marginTop: 8 }}>estimated savings eur {Number(result.estimated_savings_eur || 0).toLocaleString()}</div>
              </div>

              <div className="card" style={{ marginTop: 12 }}>
                <div className="cardTitle">top failure causes</div>
                <div className="list">
                  {(result.matches || []).map((x, idx) => (
                    <div key={idx} className="warn">
                      <div className="warnTitle">{x.summary}</div>
                      <div className="warnDetail">avoidable {String(x.avoidable)} · cost eur {Number(x.cost_eur || 0).toLocaleString()} · time weeks {x.time_weeks}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card" style={{ marginTop: 12 }}>
                <div className="cardTitle">deviation checklist</div>
                <div className="list">
                  {(result.safeguards || []).map((c, idx) => (
                    <div key={idx} className="card subcard">
                      <div className="cardSub">{c}</div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}



function RegistryAdminPanel() {
  const [summary, setSummary] = useState(null);
  const [manifest, setManifest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hydrating, setHydrating] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  async function loadSummary() {
    try {
      setLoading(true);
      setError("");
      const [sum, man] = await Promise.all([apiRegistrySummary(), apiBiomedManifest().catch(() => null)]);
      setSummary(sum || null);
      setManifest(man || null);
    } catch (err) {
      setError(String(err?.message || err || "failed to load registry summary"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSummary();
  }, []);

  async function hydrateBreadth() {
    try {
      setHydrating(true);
      setError("");
      setNote("");
      const res = await apiRegistryHydrateAll({ include_fda: true, include_mondo_rare: true, include_mondo_all: true, include_rxterms: true, include_pubchem_seed_compounds: true });
      const stepText = (res?.steps || []).map((x) => `${x.source}: ${x.stored || 0}`).join(" • ");
      setNote(stepText || "hydration finished");
      await loadSummary();
    } catch (err) {
      setError(String(err?.message || err || "registry hydration failed"));
    } finally {
      setHydrating(false);
    }
  }

  return (
    <div className="panel">
      <div className="panelHead">
        <div className="panelTitle">registry breadth</div>
        <div className="row">
          <div className="small">starter registry vs hydrated biomedical ingestion breadth.</div>
          <button className="btn btnGhost" onClick={loadSummary} disabled={loading}>{loading ? "refreshing..." : "refresh"}</button>
        </div>
      </div>
      <div className="panelBody">
        {!!error && <div className="warn high"><div className="warnDetail">{error}</div></div>}
        {!error && summary && (
          <>
            <div className="memoryHeroGrid">
              <div className="memoryHeroCard"><div className="memoryHeroLabel">diseases</div><div className="memoryHeroValue">{summary?.diseases?.total || 0}</div></div>
              <div className="memoryHeroCard"><div className="memoryHeroLabel">drugs</div><div className="memoryHeroValue">{summary?.drugs?.total || 0}</div></div>
              <div className="memoryHeroCard"><div className="memoryHeroLabel">compounds</div><div className="memoryHeroValue">{summary?.compounds?.total || 0}</div></div>
              <div className="memoryHeroCard"><div className="memoryHeroLabel">physiology</div><div className="memoryHeroValue">{summary?.physiology?.total || 0}</div></div>
            </div>
            <div className="card" style={{ marginTop: 12 }}>
              <div className="cardTitle">biomedical ingestion control</div>
              <div className="cardSub">{summary?.note || "no registry note"}</div>
              <div className="row" style={{ marginTop: 12, gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <button className="btn" onClick={hydrateBreadth} disabled={hydrating}>{hydrating ? "hydrating..." : "run full biomedical ingest"}</button>
                {note ? <div className="small">{note}</div> : null}
              </div>
              {manifest?.manifest ? (
                <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
                  <div className="subPanel">
                    <div className="subPanelTitle">disease sources</div>
                    <div className="small">starter {manifest?.manifest?.disease_sources?.starter || 0} • mondo rare {manifest?.manifest?.disease_sources?.mondo_rare || 0} • mondo all {manifest?.manifest?.disease_sources?.mondo_all || 0}</div>
                  </div>
                  <div className="subPanel">
                    <div className="subPanelTitle">drug sources</div>
                    <div className="small">starter {manifest?.manifest?.drug_sources?.starter || 0} • openfda {manifest?.manifest?.drug_sources?.openfda || 0} • rxterms {manifest?.manifest?.drug_sources?.rxterms || 0}</div>
                  </div>
                  <div className="subPanel">
                    <div className="subPanelTitle">compound sources</div>
                    <div className="small">starter {manifest?.manifest?.compound_sources?.starter || 0} • pubchem seed {manifest?.manifest?.compound_sources?.pubchem_seed || 0}</div>
                  </div>
                  <div className="subPanel">
                    <div className="subPanelTitle">physiology sources</div>
                    <div className="small">starter {manifest?.manifest?.physiology_sources?.starter || 0}</div>
                  </div>
                </div>
              ) : null}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function fmtMs(ms) {
  if (!ms) return "not yet";
  const d = new Date(ms);
  return d.toLocaleDateString();
}

function fmtAgo(ms) {
  if (!ms) return "not yet";
  const diff = Math.max(0, Date.now() - Number(ms));
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins || 1}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 48) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function fmtMoney(v) {
  return Number(v || 0).toLocaleString();
}

function MemoryTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEngineId, setSelectedEngineId] = useState("rare");

  async function load() {
    try {
      setLoading(true);
      setError("");
      const res = await apiSystemMemorySummary();
      setData(res || null);
    } catch (err) {
      setError(String(err?.message || err || "failed to load memory summary"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const engines = Array.isArray(data?.engines) ? data.engines : [];
  const recentUpdates = Array.isArray(data?.recent_updates) ? data.recent_updates : [];
  const recentQueries = Array.isArray(data?.recent_evidence_queries) ? data.recent_evidence_queries : [];

  useEffect(() => {
    if (!engines.length) return;
    if (!engines.some((x) => x.id === selectedEngineId)) setSelectedEngineId(engines[0].id);
  }, [engines, selectedEngineId]);

  const selectedEngine = engines.find((x) => x.id === selectedEngineId) || engines[0] || null;

  return (
    <div className="grid">
      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">memory mission control</div>
          <div className="row">
            <div className="small">live backend summary across engines.</div>
            <button className="btn btnGhost" onClick={load} disabled={loading}>{loading ? "refreshing..." : "refresh"}</button>
          </div>
        </div>
        <div className="panelBody">
          {loading && <div className="small">loading memory summary...</div>}
          {!!error && (
            <div className="warn high">
              <div className="warnTitle">memory endpoint not reachable</div>
              <div className="warnDetail">{error}</div>
            </div>
          )}
          {!loading && !error && (
            <>
              <div className="memoryHeroGrid">
                <div className="memoryHeroCard">
                  <div className="memoryHeroLabel">rare window</div>
                  <div className="memoryHeroValue">{data?.rare_window || "not trained"}</div>
                </div>
                <div className="memoryHeroCard">
                  <div className="memoryHeroLabel">rare hit ratio</div>
                  <div className="memoryHeroValue">{Math.round((Number(data?.rare_hit_ratio || 0) || 0) * 100)}%</div>
                </div>
                <div className="memoryHeroCard">
                  <div className="memoryHeroLabel">recent evidence</div>
                  <div className="memoryHeroValue">{recentQueries.length}</div>
                </div>
                <div className="memoryHeroCard">
                  <div className="memoryHeroLabel">engines tracked</div>
                  <div className="memoryHeroValue">{engines.length}</div>
                </div>
                <div className="memoryHeroCard">
                  <div className="memoryHeroLabel">protocols used</div>
                  <div className="memoryHeroValue">{data?.safeguard_protocols_created || 0}</div>
                </div>
                <div className="memoryHeroCard">
                  <div className="memoryHeroLabel">eur saved</div>
                  <div className="memoryHeroValue">{fmtMoney(data?.safeguard_estimated_savings_eur || 0)}</div>
                </div>
              </div>

              <div className="memorySectionLabel">engine drilldown</div>
              <div className="memoryEngineGrid">
                {engines.map((engine) => (
                  <button key={engine.id} className={`memoryEngineCard ${selectedEngineId === engine.id ? "active" : ""}`} onClick={() => setSelectedEngineId(engine.id)}>
                    <div className="memoryEngineTop">
                      <div>
                        <div className="memoryEngineName">{engine.name}</div>
                        <div className="memoryEngineConfidence">{engine.confidence}</div>
                      </div>
                      <div className="memoryEngineDate">{fmtAgo(engine.last_updated_ms)}</div>
                    </div>
                    <div className="memoryEngineStats">
                      <div><span>runs</span><strong>{engine.runs || 0}</strong></div>
                      <div><span>stored</span><strong>{engine.stored_cases || 0}</strong></div>
                    </div>
                    <div className="memoryEngineBlock">
                      <div className="memoryEngineBlockLabel">top pattern</div>
                      <div>{engine.top_pattern || "none yet"}</div>
                    </div>
                  </button>
                ))}
              </div>

              {!!selectedEngine && (
                <div className="memoryDetailCard">
                  <div className="memoryDetailTop">
                    <div>
                      <div className="memoryDetailTitle">{selectedEngine.name}</div>
                      <div className="memoryDetailMeta">last updated {fmtMs(selectedEngine.last_updated_ms)} • confidence {selectedEngine.confidence}</div>
                    </div>
                  </div>
                  <div className="memoryDetailGrid">
                    <div className="memoryDetailBlock">
                      <div className="memoryEngineBlockLabel">summary</div>
                      <div>{selectedEngine.summary || "no summary yet"}</div>
                    </div>
                    <div className="memoryDetailBlock">
                      <div className="memoryEngineBlockLabel">improved</div>
                      <div>{selectedEngine.improved || "waiting for next run"}</div>
                    </div>
                    <div className="memoryDetailBlock wide">
                      <div className="memoryEngineBlockLabel">detail</div>
                      <div className="memoryBulletList">
                        {(selectedEngine.details || []).map((item, idx) => <div key={idx}>~ {item}</div>)}
                        {!(selectedEngine.details || []).length && <div>~ no extra detail yet.</div>}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">recent updates</div>
          <div className="small">what the system has learned lately.</div>
        </div>
        <div className="panelBody">
          {loading && <div className="small">building update trail...</div>}
          {!loading && !error && (
            <div className="list">
              {recentUpdates.map((item, idx) => (
                <div key={`${item.engine}_${idx}`} className="updateCard">
                  <div className="updateEngine">{item.engine}</div>
                  <div className="updateNote">{item.note}</div>
                </div>
              ))}
              {!recentUpdates.length && <div className="small">no updates yet.</div>}
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">recent subj _ obj searches</div>
          <div className="small">saved automatically when compare runs.</div>
        </div>
        <div className="panelBody">
          {loading && <div className="small">loading evidence trail...</div>}
          {!loading && !error && (
            <div className="list">
              {recentQueries.map((q, idx) => (
                <div key={`${q.compound}_${idx}`} className="updateCard">
                  <div className="updateEngine">{q.compound} • {q.context || "general"}</div>
                  <div className="updateNote">targets: {(q.targets || []).join(", ") || "none"} • {fmtAgo(q.saved_at_ms)}</div>
                </div>
              ))}
              {!recentQueries.length && <div className="small">no saved evidence searches yet.</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EvidenceTab() {
  const [queryType, setQueryType] = useState("compound");
  const [compound, setCompound] = useState(EVIDENCE_STARTERS?.[0]?.compound || "berberine");
  const [context, setContext] = useState(EVIDENCE_STARTERS?.[0]?.context || "metabolic syndrome");
  const [targetsText, setTargetsText] = useState((EVIDENCE_STARTERS?.[0]?.targets || []).join(", "));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function runAnalyze(nextCompound = compound, nextContext = context, nextTargetsText = targetsText) {
    try {
      setLoading(true);
      setError("");
      const targets = String(nextTargetsText || "")
        .split(/[\n,;|]+/)
        .map((x) => x.trim())
        .filter(Boolean);
      const res = await apiCompoundAnalyze({
        compound: nextCompound,
        context: `${queryType}: ${nextContext}` ,
        targets,
        max_papers: 8,
        use_llm: true,
      });
      setResult(res || null);
    } catch (err) {
      setError(String(err?.message || err || "compound analysis failed"));
    } finally {
      setLoading(false);
    }
  }

  function applyStarter(starter) {
    setCompound(starter.compound);
    setContext(starter.context || "");
    setTargetsText((starter.targets || []).join(", "));
    runAnalyze(starter.compound, starter.context || "", (starter.targets || []).join(", "));
  }

  useEffect(() => {
    runAnalyze(compound, context, targetsText);
  }, []);

  return (
    <div className="grid">
      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">subj _ obj</div>
          <div className="small">compare literature signal and real-world signal side by side.</div>
        </div>
        <div className="panelBody">
          <div className="card">
            <div className="cardTitle">starter compounds</div>
            <div className="starterGrid">
              {EVIDENCE_STARTERS.map((starter) => (
                <button key={starter.compound} className="starterCard" onClick={() => applyStarter(starter)}>
                  <div className="starterTitle">{starter.compound}</div>
                  <div className="starterMeta">{starter.context}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="card" style={{ marginTop: 12 }}>
            <div className="cardTitle">analyze medicine / compound / physiology / diet</div>
            <div className="evidenceForm">
              <select className="softInput" value={queryType} onChange={(e) => setQueryType(e.target.value)}>
                <option value="medicine">medicine</option>
                <option value="compound">compound</option>
                <option value="physiology">physiology</option>
                <option value="diet">diet</option>
              </select>
              <input className="softInput" value={compound} onChange={(e) => setCompound(e.target.value)} placeholder="compound" />
              <input className="softInput" value={context} onChange={(e) => setContext(e.target.value)} placeholder="context / disease" />
              <input className="softInput" value={targetsText} onChange={(e) => setTargetsText(e.target.value)} placeholder="targets, optional" />
              <button className="btn" onClick={() => runAnalyze()} disabled={loading || !compound.trim()}>
                {loading ? "running..." : "run compare"}
              </button>
            </div>
            {!!error && <div className="warn high" style={{ marginTop: 10 }}><div className="warnDetail">{error}</div></div>}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">evidence output</div>
          <div className="small">objective vs subjective engine result.</div>
        </div>
        <div className="panelBody">
          {!result && <div className="small">pick a starter or run a query.</div>}
          {!!result && (
            <div className="list">
              <div className="compareGrid">
                <div className="compareCard">
                  <div className="compareLabel">objective</div>
                  <div className="compareText">{result.objective_summary || "no objective summary returned."}</div>
                </div>
                <div className="compareCard">
                  <div className="compareLabel">subjective</div>
                  <div className="compareText">{result.subjective_summary || "no subjective summary returned."}</div>
                </div>
              </div>

              <div className="card">
                <div className="cardTitle">pmids</div>
                <div className="row">
                  {(result.pmids || []).map((pmid) => (
                    <div key={pmid} className="pill">{pmid}</div>
                  ))}
                  {!(result.pmids || []).length && <div className="small">no pmids returned.</div>}
                </div>
              </div>

              <div className="card">
                <div className="cardTitle">last compare</div>
                <div className="kv compactKv">
                  <div>query type</div>
                  <div>{queryType}</div>
                  <div>query</div>
                  <div>{result.compound || compound}</div>
                  <div>context</div>
                  <div>{result._context || context || "general"}</div>
                  <div>targets</div>
                  <div>{(result._targets || []).join(", ") || "none"}</div>
                </div>
              </div>

              <div className="card">
                <div className="cardTitle">notes</div>
                <div className="cardSub">{result.notes || "no extra notes."}</div>
                {result.report_pdf_url ? (
                  <div className="row" style={{ marginTop: 10 }}>
                    <a className="btn btnGhost" href={result.report_pdf_url} target="_blank" rel="noreferrer">open report pdf</a>
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("rare");
  const [moreTab, setMoreTab] = useState("habit");
  const [diseaseId, setDiseaseId] = useState(null);
  const [subcatId, setSubcatId] = useState(null);
  const [drugId, setDrugId] = useState(null);
  const [selectedTargets, setSelectedTargets] = useState(new Set());
  const [selectedCompounds, setSelectedCompounds] = useState([]);
  const [mandatoryIds, setMandatoryIds] = useState([]);
  const [mimicMode, setMimicMode] = useState("hybrid");
  const [registryDrugs, setRegistryDrugs] = useState([]);
  const [registryDiseaseDrugs, setRegistryDiseaseDrugs] = useState([]);
  const [runtimeLibraryReady, setRuntimeLibraryReady] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);

  const disease = useMemo(() => DISEASE_UNIVERSE.find((d) => d.id === diseaseId) || null, [diseaseId]);
  const subcat = useMemo(() => (!disease ? null : (disease.children || []).find((c) => c.id === subcatId) || null), [disease, subcatId]);

  useEffect(() => {
    let alive = true;
    Promise.all([
      apiDrugMimicDrugs().catch(() => []),
      apiRareCompounds().catch(() => []),
      apiRarePhysiology().catch(() => []),
    ]).then(([drugRows, compoundRows, physiologyRows]) => {
      if (!alive) return;
      setRegistryDrugs(Array.isArray(drugRows) ? drugRows : []);
      setRuntimeMimicLibrary(Array.isArray(compoundRows) ? compoundRows : [], Array.isArray(physiologyRows) ? physiologyRows : []);
      setRuntimeLibraryReady(true);
    }).catch(() => {
      if (!alive) return;
      setRegistryDrugs([]);
      setRuntimeLibraryReady(false);
    });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    let alive = true;
    if (!subcat?.label) {
      setRegistryDiseaseDrugs([]);
      return () => { alive = false; };
    }
    apiRegistryDiseaseDrugs(subcat.label, 24)
      .then((res) => {
        if (!alive) return;
        setRegistryDiseaseDrugs(Array.isArray(res?.items) ? res.items : []);
      })
      .catch(() => { if (alive) setRegistryDiseaseDrugs([]); });
    return () => { alive = false; };
  }, [subcat?.label]);

  const drugsForSubcat = useMemo(() => {
    if (!disease || !subcat) return [];
    const seeded = getDrugsForSubcategory({ diseaseId: disease.id, subcat });
    const diseaseMatched = (Array.isArray(registryDiseaseDrugs) ? registryDiseaseDrugs : [])
      .map((item) => {
        const drugRow = item?.drug || {};
        const overlapGenes = Array.isArray(item?.overlap_genes) ? item.overlap_genes : [];
        const targetGenes = Array.isArray(drugRow?.targets)
          ? drugRow.targets.map((target) => typeof target === "string" ? target : target?.gene).filter(Boolean)
          : [];
        return {
          id: drugRow.id,
          name: drugRow.name,
          summary: overlapGenes.length
            ? `disease-matched registry drug · overlap ${overlapGenes.slice(0, 6).join(", ")}`
            : `registry-backed drug candidate · ${(targetGenes || []).slice(0, 6).join(", ") || "mapped target set"}`,
          activates: { genes: targetGenes, receptors: [], sirtuins: [], pathways: [] },
          _score: Number(item?.score || 0),
          _mappedCount: targetGenes.length,
        };
      })
      .filter((item) => item.id && item.name && item._mappedCount > 0)
      .sort((a, b) => (b._score - a._score) || (b._mappedCount - a._mappedCount) || String(a.name || "").localeCompare(String(b.name || "")));

    const registryRows = Array.isArray(registryDrugs) ? registryDrugs : [];
    const globalMapped = registryRows
      .map((row) => ({
        id: row.id,
        name: row.name,
        summary: `registry-backed drug candidate · ${(row.targets || []).slice(0, 8).join(", ") || "no mapped targets yet"}`,
        activates: { genes: row.targets || [], receptors: [], sirtuins: [], pathways: [] },
        _mappedCount: Array.isArray(row.targets) ? row.targets.length : 0,
      }))
      .filter((item) => item.id && item.name && item._mappedCount > 0)
      .sort((a, b) => (b._mappedCount - a._mappedCount) || String(a.name || "").localeCompare(String(b.name || "")));

    const combined = [];
    const seen = new Set();
    for (const item of [...seeded, ...diseaseMatched, ...globalMapped]) {
      if (!item?.id || seen.has(item.id)) continue;
      seen.add(item.id);
      combined.push(item);
    }
    return combined;
  }, [disease, subcat, registryDiseaseDrugs, registryDrugs]);
  const drug = useMemo(() => {
    if (!subcat) return null;
    const base = (drugsForSubcat || []).find((x) => x.id === drugId) || null;
    if (!base) return null;
    const meta = DRUG_LIBRARY.find((x) => x.id === base.id || String(x.name || "").toLowerCase() === String(base.name || "").toLowerCase()) || null;
    return meta ? { ...meta, ...base, candidateMimics: meta.candidateMimics || base.candidateMimics || [] } : base;
  }, [subcat, drugsForSubcat, drugId]);
  const drugTargets = useMemo(() => {
    if (!drug) return { genes: [], receptors: [], sirtuins: [], pathways: [] };
    return sanitizeDrugActivates(drug.activates || {});
  }, [drug]);
  const stackReport = useMemo(() => interactionReport(selectedCompounds), [selectedCompounds]);

  function resetDownstream() {
    setDiseaseId(null);
    setSubcatId(null);
    setDrugId(null);
    setSelectedTargets(new Set());
    setSelectedCompounds([]);
    setMandatoryIds([]);
    setMimicMode("hybrid");
  }

  function pickDisease(d) {
    setDiseaseId(d.id);
    setSubcatId(null);
    setDrugId(null);
    setSelectedTargets(new Set());
    setSelectedCompounds([]);
    setMandatoryIds([]);
    setMimicMode("hybrid");
  }

  function pickSubcat(c) {
    setSubcatId(c.id);
    setDrugId(null);
    setSelectedTargets(new Set());
    setSelectedCompounds([]);
    setMandatoryIds([]);
    setMimicMode("hybrid");
  }

  function pickDrug(x) {
    setDrugId(x.id);
    setSelectedTargets(new Set());
    setSelectedCompounds([]);
    setMandatoryIds([]);
  }

  function jump({ level }) {
    if (level === "root") return resetDownstream();
    if (level === "disease") {
      setSubcatId(null);
      setDrugId(null);
      setSelectedTargets(new Set());
      setSelectedCompounds([]);
      setMandatoryIds([]);
      return;
    }
    if (level === "subcat") {
      setDrugId(null);
      setSelectedTargets(new Set());
      setSelectedCompounds([]);
      setMandatoryIds([]);
    }
  }

  function toggleTarget(t) {
    setSelectedTargets((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  function toggleCompound(c) {
    setSelectedCompounds((prev) => {
      const on = prev.some((x) => x.id === c.id);
      if (on) {
        setMandatoryIds((m) => m.filter((id) => id !== c.id));
        return prev.filter((x) => x.id !== c.id);
      }
      return [...prev, c];
    });
  }

  function optimize() {
    const optimized = optimizeStack({ selected: selectedCompounds, mandatoryIds });
    const keep = new Set(optimized.map((c) => c.id));
    setMandatoryIds((m) => m.filter((id) => keep.has(id)));
    setSelectedCompounds(optimized);
  }

  function exportDrugRun() {
    const payload = buildExportEnvelope({
      tabId: "drug",
      title: "drug mimic run export",
      data: {
        navigation: {
          diseaseId,
          subcatId,
          drugId,
          diseaseLabel: disease?.label || null,
          subcatLabel: subcat?.label || null,
          drugName: drug?.name || null,
        },
        targets: { selected: Array.from(selectedTargets), all: drugTargets },
        stack: {
          selectedCompounds: selectedCompounds.map((c) => ({ id: c.id, name: c.name, liverLoad: c.liverLoad || 0, nadBoost: c.nadBoost || 0 })),
          mandatoryIds,
          report: stackReport,
          mimicMode,
        },
      },
    });
    downloadJSON("medr5_drug_mimic", payload);
  }

  const leftTitle = !disease ? "category map" : !subcat ? "subcategory map" : !drug ? "drug map" : "target map";

  return (
    <div className="space-root">
      <SpaceBackground />
      <div className="shell">
        <div className="topbar">
          <div className="brand" style={{ cursor: "pointer" }} onClick={() => setShowWelcome(true)}>
            <div className="title">~ med-r5</div>
            <div className="sub">rare disease workspace</div>
          </div>
          <div className="tabs">
            <button className={`tabbtn ${showWelcome ? "active" : ""}`} onClick={() => setShowWelcome(true)}>home</button>
            <TabButton id="rare" active={tab === "rare"} onClick={setTab}>rare diseases</TabButton>
            <TabButton id="drug" active={tab === "drug"} onClick={setTab}>drug mimicking</TabButton>
            <TabButton id="safeguard" active={tab === "safeguard"} onClick={setTab}>safeguard deviation</TabButton>
            <TabButton id="predictor" active={tab === "predictor"} onClick={setTab}>rare disease predictor</TabButton>
            <TabButton id="more" active={tab === "more"} onClick={setTab}>more tools</TabButton>
          </div>
        </div>

        {showWelcome && <WelcomeLanding onOpen={(nextTab) => { setTab(nextTab); setShowWelcome(false); if (nextTab === "more") setMoreTab("admin"); }} onQuickOpen={(nextTab) => { setTab(nextTab); setShowWelcome(false); }} />}

        {!showWelcome && tab === "rare" && (
          <div className="grid rareSoloGrid">
            <div className="panel">
              <div className="panelHead">
                <div className="panelTitle">rare disease triage</div>
                <div className="small">find the best covering therapy, inspect deviation, search add-on path.</div>
              </div>
              <div className="panelBody">
                <RareDiseaseTab />
              </div>
            </div>
          </div>
        )}

        {!showWelcome && tab === "predictor" && <RareDiseasePredictorTab />}
        {!showWelcome && tab === "safeguard" && <SafeguardTab />}
        {!showWelcome && tab === "more" && (
          <div className="grid rareSoloGrid">
            <div className="panel">
              <div className="panelHead">
                <div className="panelTitle">support tools</div>
                <div className="small">keep the main navigation focused while still exposing the remaining engines.</div>
              </div>
              <div className="panelBody">
                <div className="subtabs">
                  <button className={`subtabbtn ${moreTab === "habit" ? "active" : ""}`} onClick={() => setMoreTab("habit")}>habit offset</button>
                  <button className={`subtabbtn ${moreTab === "evidence" ? "active" : ""}`} onClick={() => setMoreTab("evidence")}>subj obj</button>
                  <button className={`subtabbtn ${moreTab === "admin" ? "active" : ""}`} onClick={() => setMoreTab("admin")}>memory</button>
                  <button className={`subtabbtn ${moreTab === "selfllm" ? "active" : ""}`} onClick={() => setMoreTab("selfllm")}>self llm</button>
                </div>
                <div className="subtabPane">
                  {moreTab === "habit" && <HabitOffsetTab />}
                  {moreTab === "evidence" && <EvidenceTab />}
                  {moreTab === "admin" && <>
                    <MemoryTab />
                    <RegistryAdminPanel />
                    <RegistryBrowserPanel title="biomedical registry browser" />
                  </>}
                  {moreTab === "selfllm" && <SelfLLMTab />}
                </div>
              </div>
            </div>
          </div>
        )}

        {!showWelcome && tab === "drug" && (
          <div className="grid">
            <div className="panel">
              <div className="panelHead">
                <div className="panelTitle">{leftTitle}</div>
                <Breadcrumb disease={disease} subcat={subcat} drug={drug} onJump={jump} />
              </div>
              <div className="panelBody">
                {!disease && <PlanetGrid items={DISEASE_UNIVERSE} onPick={pickDisease} metaFn={(d) => `${(d.children || []).length} subcategories`} />}
                {disease && !subcat && <PlanetGrid items={disease.children || []} onPick={pickSubcat} metaFn={(c) => `${(c.drugs || []).length ? (c.drugs || []).length : 3} drugs`} />}
                {subcat && !drug && <><div className="small" style={{ marginBottom: 10 }}>registry-backed drug surface {drugsForSubcat.length} • runtime mimic library {runtimeLibraryReady ? "loaded" : "starter fallback"}</div><PlanetGrid items={drugsForSubcat} onPick={pickDrug} metaFn={(x) => x.summary || "open drug"} /></>}
                {drug && (
                  <div className="split2">
                    <div className="list">
                      <TargetSection title="genes" items={drugTargets.genes} selected={selectedTargets} onToggle={toggleTarget} />
                      <TargetSection title="receptors" items={drugTargets.receptors} selected={selectedTargets} onToggle={toggleTarget} />
                      <TargetSection title="sirtuins" items={drugTargets.sirtuins} selected={selectedTargets} onToggle={toggleTarget} />
                      <TargetSection title="pathways" items={drugTargets.pathways} selected={selectedTargets} onToggle={toggleTarget} />
                    </div>
                    <div className="list">
                      <MimicPicker drug={drug} targetsSelected={Array.from(selectedTargets)} selectedCompounds={selectedCompounds} onToggleCompound={toggleCompound} mimicMode={mimicMode} onChangeMode={setMimicMode} />
                      <div className="card">
                        <div className="cardTitle">actions</div>
                        <div className="row">
                          <button className="btn" onClick={optimize} disabled={!selectedCompounds.length}>optimize stack</button>
                          <button className="btn btnGhost" onClick={() => { setSelectedTargets(new Set()); setSelectedCompounds([]); setMandatoryIds([]); }}>clear</button>
                          <button className="btn" onClick={exportDrugRun} disabled={!drug}>export json</button>
                        </div>
                      </div>
                      <div className="card drugCanvasCard bubbleCard">
                        <div className="cardTitle">drug canvas</div>
                        <div className="drugCanvasTitle">{drug.name}</div>
                        <div className="cardSub">{drug.summary}</div>
                        <div className="row drugCanvasTags">
                          <div className="bubblePill on">{disease?.label || 'disease'}</div>
                          <div className="bubblePill">{subcat?.label || 'subcategory'}</div>
                          <div className="bubblePill">{selectedCompounds.length} mimic items</div>
                        </div>
                      </div>
                      {(() => {
                        const meta = DRUG_LIBRARY.find((x) => x.id === drug.id || x.name.toLowerCase() === String(drug.name || '').toLowerCase());
                        if (!meta) return null;
                        return (
                          <div className="card">
                            <div className="cardTitle">drug intelligence</div>
                            <div className="kv compactKv">
                              <div>class</div>
                              <div>{meta.class}</div>
                              <div>targets</div>
                              <div>{(meta.targets || []).join(', ') || 'none'}</div>
                              <div>pathways</div>
                              <div>{(meta.pathways || []).join(', ') || 'none'}</div>
                              <div>mimic ideas</div>
                              <div>{(meta.candidateMimics || []).join(', ') || 'none'}</div>
                            </div>
                            <div className="small" style={{ marginTop: 8 }}>common effects: {(meta.commonEffects || []).join(', ') || 'none'}</div>
                          </div>
                        );
                      })()}
                      <SideEffectSupportPanel drug={drug} />
                    </div>
                  </div>
                )}
              </div>
            </div>
            <div className="list">
              <StackPanel selectedCompounds={selectedCompounds} mandatoryIds={mandatoryIds} setMandatoryIds={setMandatoryIds} selectedTargets={Array.from(selectedTargets)} drug={drug} />
              <DrugSynergyPanel drug={drug} selectedTargets={Array.from(selectedTargets)} selectedCompounds={selectedCompounds} />
              <ObjectiveEvidencePanel drug={drug} selectedTargets={Array.from(selectedTargets)} selectedCompounds={selectedCompounds} />
              <EarlyKillPanel drug={drug} chosenTargets={Array.from(selectedTargets)} selectedCompounds={selectedCompounds} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

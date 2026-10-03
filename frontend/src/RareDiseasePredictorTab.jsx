import React, { useEffect, useMemo, useState } from "react";
import { apiPredictorMemory, apiPredictorPredict, apiPredictorTrain, apiRegistrySummary } from "./apiClient";

function clampInt(v, lo, hi, fallback) {
  const n = parseInt(v, 10);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(lo, Math.min(hi, n));
}

function prettyJson(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

export default function RareDiseasePredictorTab() {
  const [mode, setMode] = useState("rare_disease");

  const [startYear, setStartYear] = useState(1900);
  const [endYear, setEndYear] = useState(2025);
  const [seed, setSeed] = useState(1337);
  const [includeRegistry, setIncludeRegistry] = useState(true);

  const [mem, setMem] = useState(null);
  const [trainLoading, setTrainLoading] = useState(false);
  const [trainErr, setTrainErr] = useState("");

  const [targetYear, setTargetYear] = useState(2030);
  const [horizonYears, setHorizonYears] = useState(10);
  const [topK, setTopK] = useState(8);

  const [pred, setPred] = useState(null);
  const [predLoading, setPredLoading] = useState(false);
  const [predErr, setPredErr] = useState("");
  const [registrySummary, setRegistrySummary] = useState(null);

  useEffect(() => {
    let alive = true;
    apiPredictorMemory(mode)
      .then((m) => {
        if (!alive) return;
        setMem(m);
      })
      .catch(() => {
        if (!alive) return;
        setMem(null);
      });
    apiRegistrySummary()
      .then((summary) => {
        if (!alive) return;
        setRegistrySummary(summary);
      })
      .catch(() => {
        if (!alive) return;
        setRegistrySummary(null);
      });
    return () => {
      alive = false;
    };
  }, [mode]);

  const onTrain = async () => {
    setTrainErr("");
    setTrainLoading(true);
    try {
      const payload = {
        mode,
        start_year: clampInt(startYear, 1500, 2100, 1900),
        end_year: clampInt(endYear, 1500, 2100, 2025),
        seed: clampInt(seed, 0, 999999, 1337),
        include_registry: Boolean(includeRegistry),
      };
      const m = await apiPredictorTrain(payload);
      setMem(m);
      setPred(null);
    } catch (e) {
      setTrainErr(String(e?.message || e));
    } finally {
      setTrainLoading(false);
    }
  };

  const onPredict = async () => {
    setPredErr("");
    setPredLoading(true);
    try {
      const payload = {
        mode,
        target_year: clampInt(targetYear, 1500, 2200, 2030),
        horizon_years: clampInt(horizonYears, 1, 50, 10),
        top_k: clampInt(topK, 1, 50, 8),
        seed: clampInt(seed, 0, 999999, 1337),
      };
      const out = await apiPredictorPredict(payload);
      setPred(out);
    } catch (e) {
      setPredErr(String(e?.message || e));
    } finally {
      setPredLoading(false);
    }
  };

  const trained = Boolean(mem?.trained);

  const headline = useMemo(() => {
    if (!mem) return "";
    if (!mem?.trained) return "not trained yet";
    return `${mem?.summary || "trained"}`;
  }, [mem]);

  return (
    <div className="panelBody">
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div className="card">
          <div className="muted">mode</div>
          <div className="row" style={{ marginTop: 8, gap: 10 }}>
            <select className="select" value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="rare_disease">rare disease predictor</option>
              <option value="pandemic">pandemic predictor</option>
            </select>
            <span className="pill">planning surface</span>
          </div>

          <div className="muted" style={{ marginTop: 12 }}>training window</div>
          <div className="row" style={{ marginTop: 8, gap: 10 }}>
            <input className="input" value={startYear} onChange={(e) => setStartYear(e.target.value)} placeholder="start" />
            <input className="input" value={endYear} onChange={(e) => setEndYear(e.target.value)} placeholder="end" />
            <input className="input" value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="seed" />
          </div>

          {mode === "rare_disease" ? (
            <label className="row" style={{ marginTop: 10, gap: 10, alignItems: "center" }}>
              <input type="checkbox" checked={includeRegistry} onChange={(e) => setIncludeRegistry(e.target.checked)} />
              <span className="muted">include internal registry diseases (more breadth and less starter-only bias)</span>
            </label>
          ) : null}

          <div className="row" style={{ marginTop: 12, gap: 10 }}>
            <button className="btn" onClick={onTrain} disabled={trainLoading}>
              {trainLoading ? "training…" : "train"}
            </button>
            <div className="muted" style={{ alignSelf: "center" }}>{headline}</div>
          </div>

          {trainErr ? <div className="error" style={{ marginTop: 10 }}>{trainErr}</div> : null}

          <div className="muted" style={{ marginTop: 14 }}>predict</div>
          <div className="row" style={{ marginTop: 8, gap: 10 }}>
            <input className="input" value={targetYear} onChange={(e) => setTargetYear(e.target.value)} placeholder="target year" />
            {mode === "rare_disease" ? (
              <>
                <input className="input" value={horizonYears} onChange={(e) => setHorizonYears(e.target.value)} placeholder="horizon years" />
                <input className="input" value={topK} onChange={(e) => setTopK(e.target.value)} placeholder="top k" />
              </>
            ) : null}
            <button className="btn" onClick={onPredict} disabled={!trained || predLoading}>
              {predLoading ? "predicting…" : "predict"}
            </button>
          </div>

          {!trained ? (
            <div className="muted" style={{ marginTop: 10 }}>
              train first. this uses historical heuristics and registry breadth checks, not a real-world medical forecast.
            </div>
          ) : null}

          {predErr ? <div className="error" style={{ marginTop: 10 }}>{predErr}</div> : null}
        </div>

        <div className="card">
          <div className="muted">memory snapshot</div>
          <div style={{ marginTop: 8 }} className="stack">
            <div className="kvRow"><div>trained</div><div>{String(Boolean(mem?.trained))}</div></div>
            <div className="kvRow"><div>window</div><div>{mem?.window || "—"}</div></div>
            <div className="kvRow"><div>cases seen</div><div>{mem?.cases_seen ?? 0}</div></div>
            {mode === "pandemic" ? (
              <>
                <div className="kvRow"><div>last event year</div><div>{mem?.last_event_year ?? "—"}</div></div>
                <div className="kvRow"><div>avg gap</div><div>{mem?.avg_gap_years ? `${Number(mem.avg_gap_years).toFixed(1)}y` : "—"}</div></div>
              </>
            ) : null}
          </div>

          {mode === "rare_disease" ? (
            <>
              <div className="muted" style={{ marginTop: 12 }}>top categories</div>
              <div className="pills" style={{ marginTop: 6 }}>
                {(mem?.top_categories || []).slice(0, 10).map((c) => <span key={c} className="pill">{c}</span>)}
              </div>
              <div className="muted" style={{ marginTop: 12 }}>top genes</div>
              <div className="pills" style={{ marginTop: 6 }}>
                {(mem?.top_genes || []).slice(0, 16).map((g) => <span key={g} className="pill">{g}</span>)}
              </div>
            </>
          ) : (
            <>
              <div className="muted" style={{ marginTop: 12 }}>top families</div>
              <div className="pills" style={{ marginTop: 6 }}>
                {(mem?.top_categories || []).slice(0, 10).map((f) => <span key={f} className="pill">{f}</span>)}
              </div>
            </>
          )}

          {registrySummary ? (
            <div style={{ marginTop: 14, padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 12 }}>
              <div className="muted">registry posture</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 10, marginTop: 10 }}>
                <div><strong>launch label:</strong> {registrySummary.launch_label || "starter"}</div>
                <div><strong>launch ready:</strong> {registrySummary.launch_ready ? "yes" : "no"}</div>
                <div><strong>diseases:</strong> {registrySummary.diseases?.total ?? 0}</div>
                <div><strong>drugs:</strong> {registrySummary.drugs?.total ?? 0}</div>
                <div><strong>compounds:</strong> {registrySummary.compounds?.total ?? 0}</div>
                <div><strong>physiology:</strong> {registrySummary.physiology?.total ?? 0}</div>
                <div><strong>drug evidence-ready share:</strong> {Math.round(Number(registrySummary.drugs?.evidence_ready_share || 0) * 100)}%</div>
                <div><strong>compound evidence-ready share:</strong> {Math.round(Number(registrySummary.compounds?.evidence_ready_share || 0) * 100)}%</div>
              </div>
              {(registrySummary.launch_blockers || []).length ? (
                <>
                  <div className="muted" style={{ marginTop: 10 }}>current launch blockers</div>
                  <div className="stack" style={{ marginTop: 6 }}>
                    {(registrySummary.launch_blockers || []).slice(0, 4).map((item, idx) => (
                      <div key={`rb_${idx}`} className="kvRow"><div>{idx + 1}</div><div>{item}</div></div>
                    ))}
                  </div>
                </>
              ) : null}
            </div>
          ) : null}

          {pred ? (
            <>
              {mode === "rare_disease" && pred?.operations_snapshot ? (
                <div style={{ marginTop: 14, padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 12 }}>
                  <div className="muted">center operations snapshot</div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 10, marginTop: 10 }}>
                    <div><strong>expected quarterly cases:</strong> {pred.operations_snapshot.expected_quarterly_cases ?? "-"}</div>
                    <div><strong>expected annual cases:</strong> {pred.operations_snapshot.expected_annual_cases ?? "-"}</div>
                    <div><strong>annual range:</strong> {pred.operations_snapshot.annual_range || "-"}</div>
                    <div><strong>load band:</strong> {pred.operations_snapshot.load_band || "-"}</div>
                    <div><strong>staffing note:</strong> {pred.operations_snapshot.staffing_note || "-"}</div>
                    <div><strong>top service lines:</strong> {(pred.operations_snapshot.top_service_lines || []).join(", ") || "-"}</div>
                  </div>
                </div>
              ) : null}
              <div className="muted" style={{ marginTop: 14 }}>prediction output</div>
              <pre className="code" style={{ marginTop: 8, maxHeight: 320, overflow: "auto" }}>{prettyJson(pred)}</pre>
            </>
          ) : (
            <div className="muted" style={{ marginTop: 14 }}>no prediction yet</div>
          )}
        </div>
      </div>

      <div className="muted" style={{ marginTop: 14 }}>
        note: this tab is a planning surface for center-load and discovery forecasting. check registry posture, launch blockers, and evidence depth before using the output for institution-facing planning.
      </div>
    </div>
  );
}

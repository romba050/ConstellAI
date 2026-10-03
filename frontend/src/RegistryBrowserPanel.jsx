import React, { useEffect, useMemo, useState } from "react";
import {
  apiRegistrySummary,
  apiRegistrySearch,
  apiRegistryDiseaseDrugs,
} from "./apiClient";

function fmtInt(n) {
  const x = Number.isFinite(Number(n)) ? Number(n) : 0;
  return x.toLocaleString();
}

function short(s, n = 140) {
  const t = String(s || "").trim();
  if (!t) return "";
  if (t.length <= n) return t;
  return t.slice(0, n - 1) + "…";
}

export default function RegistryBrowserPanel({ title = "all data registry", compact = false }) {
  const [summary, setSummary] = useState(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [selected, setSelected] = useState(null);
  const [diseaseDrugMap, setDiseaseDrugMap] = useState(null);

  useEffect(() => {
    let alive = true;
    apiRegistrySummary()
      .then((s) => {
        if (alive) setSummary(s);
      })
      .catch(() => {
        // non-fatal; the rest can still work
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const qq = q.trim();
    if (!qq) {
      setResults([]);
      setErr("");
      return;
    }

    let alive = true;
    setLoading(true);
    setErr("");

    const t = setTimeout(() => {
      apiRegistrySearch(qq, 30)
        .then((res) => {
          if (!alive) return;
          setResults(Array.isArray(res?.results) ? res.results : []);
        })
        .catch((e) => {
          if (!alive) return;
          setErr(String(e?.message || e));
          setResults([]);
        })
        .finally(() => {
          if (!alive) return;
          setLoading(false);
        });
    }, 250);

    return () => {
      alive = false;
      clearTimeout(t);
    };
  }, [q]);

  useEffect(() => {
    if (!selected || selected.type !== "disease") {
      setDiseaseDrugMap(null);
      return;
    }
    let alive = true;
    apiRegistryDiseaseDrugs(selected.item?.id, 25)
      .then((m) => {
        if (!alive) return;
        setDiseaseDrugMap(m);
      })
      .catch(() => {
        if (!alive) return;
        setDiseaseDrugMap(null);
      });
    return () => {
      alive = false;
    };
  }, [selected]);

  const headerCounts = useMemo(() => {
    if (!summary) return null;
    const d = summary?.diseases || {};
    const dr = summary?.drugs || {};
    const c = summary?.compounds || {};
    const p = summary?.physiology || {};
    return {
      diseases: d.total || d.count || 0,
      drugs: dr.total || dr.count || 0,
      compounds: c.total || c.count || 0,
      physiology: p.total || p.count || 0,
    };
  }, [summary]);

  return (
    <div className="panel">
      <div className="panelHeader">
        <div>
          <div className="panelTitle">{title}</div>
          {headerCounts && (
            <div className="muted small" style={{ marginTop: 4 }}>
              diseases {fmtInt(headerCounts.diseases)} • drugs {fmtInt(headerCounts.drugs)} • compounds {fmtInt(headerCounts.compounds)}
              {!compact ? ` • physiology ${fmtInt(headerCounts.physiology)}` : ""}
            </div>
          )}
        </div>
        <div className="panelMeta">search everything</div>
      </div>

      <div className="panelBody">
        <div className="row" style={{ gap: 10, alignItems: "center" }}>
          <input
            className="input"
            placeholder="search disease / drug / compound / physiology…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {loading ? <span className="pill">loading</span> : null}
        </div>

        {err ? <div className="error" style={{ marginTop: 10 }}>{err}</div> : null}

        {results?.length ? (
          <div className="card" style={{ marginTop: 12 }}>
            <div className="muted" style={{ marginBottom: 8 }}>
              results ({results.length}) — click to expand
            </div>
            <div className="stack" style={{ gap: 8 }}>
              {results.map((r, idx) => {
                const it = r?.item || {};
                const type = r?.type || "unknown";
                const label = it?.name || it?.id || "unknown";
                const sub = type === "disease" ? it?.category : type === "drug" ? it?.drug_class : it?.category;
                return (
                  <button
                    key={`${type}-${it?.id || idx}`}
                    className="starterCard"
                    style={{ textAlign: "left" }}
                    onClick={() => setSelected({ type, item: it })}
                    title="open details"
                  >
                    <div className="starterTitle">
                      <span className="pill" style={{ marginRight: 8 }}>{type}</span>
                      {label}
                    </div>
                    <div className="starterHint">{[sub ? short(sub, 90) : "", it?.source ? `source ${it.source}` : ""].filter(Boolean).join(" • ")}</div>
                  </button>
                );
              })}
            </div>
          </div>
        ) : q.trim() ? (
          !loading && <div className="muted" style={{ marginTop: 10 }}>no results</div>
        ) : null}

        {selected ? (
          <div className="card" style={{ marginTop: 12 }}>
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div className="panelTitle" style={{ marginBottom: 4 }}>
                  {selected.type}: {selected.item?.name || selected.item?.id}
                </div>
                <div className="muted small">id: {selected.item?.id || "—"} {selected.item?.source ? `• source: ${selected.item.source}` : ""}</div>
              </div>
              <button className="btn" onClick={() => setSelected(null)}>close</button>
            </div>

            {selected.type === "disease" ? (
              <div style={{ marginTop: 10 }}>
                <div className="muted">category</div>
                <div style={{ marginTop: 4 }}>{selected.item?.category || "—"}</div>

                <div className="muted" style={{ marginTop: 10 }}>genes</div>
                <div className="pills" style={{ marginTop: 6 }}>
                  {(selected.item?.genes || []).slice(0, compact ? 14 : 24).map((g) => (
                    <span key={g} className="pill">{g}</span>
                  ))}
                  {!(selected.item?.genes || []).length ? <span className="muted">—</span> : null}
                </div>

                <div className="muted" style={{ marginTop: 12 }}>top matching drugs</div>
                {diseaseDrugMap?.items?.length ? (
                  <div className="stack" style={{ gap: 8, marginTop: 6 }}>
                    {diseaseDrugMap.items.slice(0, compact ? 6 : 12).map((x) => (
                      <div key={x?.drug?.id} className="kvRow">
                        <div>
                          <div><strong>{x?.drug?.name || x?.drug?.id}</strong> <span className="muted">(score {x?.score})</span></div>
                          <div className="muted small">
                            overlap: {(x?.overlap_genes || []).slice(0, 8).join(", ") || "—"}
                            {x?.indication_match ? " • indication match" : ""}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="muted" style={{ marginTop: 6 }}>no high-signal drug matches found in current registry</div>
                )}
              </div>
            ) : null}

            {selected.type === "drug" ? (
              <div style={{ marginTop: 10 }}>
                <div className="muted">drug class</div>
                <div style={{ marginTop: 4 }}>{selected.item?.drug_class || "—"}</div>

                <div className="muted" style={{ marginTop: 10 }}>indications</div>
                <div style={{ marginTop: 4 }}>{(selected.item?.indications || []).join("; ") || "—"}</div>

                <div className="muted" style={{ marginTop: 10 }}>targets</div>
                <div className="pills" style={{ marginTop: 6 }}>
                  {(selected.item?.targets || []).slice(0, compact ? 12 : 24).map((t, i) => (
                    <span key={`${t?.gene || i}`} className="pill">{t?.gene || "?"}</span>
                  ))}
                  {!(selected.item?.targets || []).length ? <span className="muted">—</span> : null}
                </div>
              </div>
            ) : null}

            {selected.type === "compound" ? (
              <div style={{ marginTop: 10 }}>
                <div className="muted">targets</div>
                <div className="pills" style={{ marginTop: 6 }}>
                  {(selected.item?.targets || []).slice(0, compact ? 12 : 24).map((t, i) => (
                    <span key={`${t?.gene || i}`} className="pill">{t?.gene || "?"}</span>
                  ))}
                  {!(selected.item?.targets || []).length ? <span className="muted">—</span> : null}
                </div>
              </div>
            ) : null}

            {selected.type === "physiology" ? (
              <div style={{ marginTop: 10 }}>
                <div className="muted">category</div>
                <div style={{ marginTop: 4 }}>{selected.item?.category || "—"}</div>

                <div className="muted" style={{ marginTop: 10 }}>targets</div>
                <div className="pills" style={{ marginTop: 6 }}>
                  {(selected.item?.targets || []).slice(0, compact ? 12 : 24).map((t, i) => (
                    <span key={`${t?.gene || i}`} className="pill">{t?.gene || "?"}</span>
                  ))}
                  {!(selected.item?.targets || []).length ? <span className="muted">—</span> : null}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {!compact ? (
          <div className="muted" style={{ marginTop: 12 }}>
            note: “matches” are heuristic (gene overlap + loose indication string). swap in your real knowledge graphs / ontologies when ready.
          </div>
        ) : null}
      </div>
    </div>
  );
}

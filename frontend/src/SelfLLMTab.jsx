import { useMemo, useState } from 'react';
import { apiSelfLLMRunLoop, apiSelfLLMStart, apiSelfLLMSuggestPatch } from './apiClient.js';

function ScorePill({ label, value }) {
  return (
    <div className="bubblePill on" style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function SelfLLMTab() {
  const [hint, setHint] = useState('');
  const [loading, setLoading] = useState(false);
  const [loopLoading, setLoopLoading] = useState(false);
  const [patchLoading, setPatchLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [loopResults, setLoopResults] = useState([]);
  const [patch, setPatch] = useState('');

  const activeProposalText = useMemo(() => {
    if (result?.proposal) return result.proposal;
    if (loopResults[0]?.proposal) return loopResults[0].proposal;
    return '';
  }, [result, loopResults]);

  async function runSingle() {
    try {
      setLoading(true);
      setError('');
      setPatch('');
      const data = await apiSelfLLMStart({ hint });
      setResult(data || null);
    } catch (err) {
      setError(String(err?.message || err || 'failed to generate proposal'));
    } finally {
      setLoading(false);
    }
  }

  async function runLoop() {
    try {
      setLoopLoading(true);
      setError('');
      setPatch('');
      const data = await apiSelfLLMRunLoop({ hint, iterations: 5 });
      const proposals = Array.isArray(data?.proposals) ? data.proposals : [];
      setLoopResults(proposals);
      if (proposals[0]?.proposal) setResult(proposals[0]);
    } catch (err) {
      setError(String(err?.message || err || 'failed to run self llm loop'));
    } finally {
      setLoopLoading(false);
    }
  }

  async function runPatchSuggestion() {
    if (!activeProposalText) {
      setError('generate a proposal first.');
      return;
    }
    try {
      setPatchLoading(true);
      setError('');
      const data = await apiSelfLLMSuggestPatch({ proposal: activeProposalText });
      setPatch(data?.patch || 'no patch returned');
    } catch (err) {
      setError(String(err?.message || err || 'failed to generate patch suggestion'));
    } finally {
      setPatchLoading(false);
    }
  }

  return (
    <div className="grid rareSoloGrid">
      <div className="panel">
        <div className="panelHead">
          <div className="panelTitle">self llm</div>
          <div className="small">proposal engine aimed at making med-r more sellable to institutional buyers.</div>
        </div>
        <div className="panelBody">
          <div className="card">
            <div className="cardTitle">improvement goal</div>
            <div className="cardSub">target: move toward a state where 25 / 50 medical facilities would consider buying it.</div>
            <textarea
              className="softTextarea"
              rows={6}
              placeholder="optional guidance. example: improve auditability for rare disease outputs"
              value={hint}
              onChange={(e) => setHint(e.target.value)}
            />
            <div className="row" style={{ marginTop: 12, gap: 10, flexWrap: 'wrap' }}>
              <button className="btn" onClick={runSingle} disabled={loading || loopLoading}>
                {loading ? 'generating...' : 'generate proposal'}
              </button>
              <button className="btn btnGhost" onClick={runLoop} disabled={loading || loopLoading}>
                {loopLoading ? 'running loop...' : 'run loop x5'}
              </button>
              <button className="btn btnGhost" onClick={runPatchSuggestion} disabled={patchLoading || !activeProposalText}>
                {patchLoading ? 'building patch...' : 'suggest patch'}
              </button>
            </div>
            {!!error && (
              <div className="warn high" style={{ marginTop: 12 }}>
                <div className="warnTitle">self llm error</div>
                <div className="warnDetail">{error}</div>
              </div>
            )}
          </div>

          {!!result && (
            <div className="card" style={{ marginTop: 12 }}>
              <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                <div>
                  <div className="cardTitle">latest proposal</div>
                  <div className="cardSub">saved to: {result.file || 'not saved'}</div>
                </div>
                <ScorePill label="institution score" value={result.institutional_score ?? '-'} />
              </div>

              <pre style={{ whiteSpace: 'pre-wrap', marginTop: 12 }}>{result.proposal}</pre>

              {!!result.institution_breakdown && (
                <div style={{ marginTop: 12 }}>
                  <div className="cardTitle">institution simulation</div>
                  <div className="bubbleRow" style={{ marginTop: 8 }}>
                    {Object.entries(result.institution_breakdown).map(([key, value]) => (
                      <ScorePill key={key} label={key.replace(/_/g, ' ')} value={value} />
                    ))}
                  </div>
                </div>
              )}

              {!!result.system_maturity && (
                <div style={{ marginTop: 12 }}>
                  <div className="cardTitle">system maturity</div>
                  <div className="bubbleRow" style={{ marginTop: 8 }}>
                    <ScorePill label="ui" value={result.system_maturity.ui_score} />
                    <ScorePill label="backend" value={result.system_maturity.backend_score} />
                    <ScorePill label="api" value={result.system_maturity.api_score} />
                    <ScorePill label="overall" value={result.system_maturity.system_maturity} />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="list">
        <div className="panel">
          <div className="panelHead">
            <div className="panelTitle">loop proposals</div>
            <div className="small">top-ranked proposals from the latest x5 run.</div>
          </div>
          <div className="panelBody">
            <div className="list">
              {loopResults.map((item, idx) => (
                <div key={`${item.file || idx}`} className="card subcard" onClick={() => item?.proposal && setResult(item)} style={{ cursor: item?.proposal ? 'pointer' : 'default' }}>
                  <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
                    <div>
                      <div className="cardTitle">proposal {idx + 1}</div>
                      <div className="cardSub">{item.file || item.error || 'no file'}</div>
                    </div>
                    {'institutional_score' in item ? <ScorePill label="score" value={item.institutional_score} /> : null}
                  </div>
                  {item.error ? <div className="warnDetail" style={{ marginTop: 8 }}>{item.error}</div> : null}
                </div>
              ))}
              {!loopResults.length && <div className="small">no loop proposals yet.</div>}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panelHead">
            <div className="panelTitle">patch suggestion</div>
            <div className="small">human review gate stays in place. no code is auto-applied.</div>
          </div>
          <div className="panelBody">
            {!patch && <div className="small">generate a proposal, then click suggest patch.</div>}
            {!!patch && <pre style={{ whiteSpace: 'pre-wrap' }}>{patch}</pre>}
          </div>
        </div>
      </div>
    </div>
  );
}

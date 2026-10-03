const DEV_PROXY_BASE = "";
const API_CANDIDATES = [DEV_PROXY_BASE, import.meta.env.VITE_API_BASE].filter((x, i, a) => x !== undefined && x !== null && a.indexOf(x) === i);
function withTimeout(ms = 30000) { const ctrl = new AbortController(); const timer = setTimeout(() => ctrl.abort(new Error(`request timed out after ${ms}ms`)), ms); return { signal: ctrl.signal, clear: () => clearTimeout(timer) }; }
async function jfetchAgainst(base, path, opts = {}) { const url = path.startsWith("http") ? path : `${base}${path}`; const timeoutMs = Number(opts.timeoutMs || 30000); const { signal, clear } = withTimeout(timeoutMs); const headers = { ...(opts.headers || {}) }; const hasBody = opts.body !== undefined && opts.body !== null; if (hasBody && !headers['Content-Type']) headers['Content-Type'] = 'application/json'; try { const res = await fetch(url, { credentials: 'include', ...opts, headers, signal }); if (!res.ok) { let detail = `HTTP ${res.status} ${res.statusText}`; try { const ct = res.headers.get('content-type') || ''; if (ct.includes('application/json')) { const j = await res.json(); detail = j?.detail || JSON.stringify(j); } else { detail = await res.text(); } } catch {} throw new Error(detail || `HTTP ${res.status}`); } if (res.status === 204) return null; const ct = res.headers.get('content-type') || ''; if (ct.includes('application/json')) return res.json(); return res.text(); } finally { clear(); } }
async function jfetch(path, opts = {}) { let lastErr = null; for (const base of API_CANDIDATES) { try { return await jfetchAgainst(base, path, opts); } catch (err) { lastErr = err; } } throw lastErr || new Error('api request failed'); }
export async function apiHealth() { return jfetch('/api/health'); }
export async function apiHypothesisBundle(payload) { return jfetch('/api/hypothesis/bundle', { method: 'POST', body: JSON.stringify(payload || {}) }); }
export async function apiSafeguardAnalyze(payload) { return jfetch('/api/safeguard/analyze', { method: 'POST', body: JSON.stringify(payload || {}) }); }
export async function apiSafeguardMemoryAdd(payload) { return jfetch('/api/safeguard/memory/add', { method: 'POST', body: JSON.stringify(payload || {}) }); }
export async function apiSafeguardMemoryList() { return jfetch('/api/safeguard/memory/list'); }
export async function apiRareDiseases() { return jfetch('/api/rare/diseases'); }
export async function apiRareFillRankings(payload) { return jfetch('/api/rare/fill-rankings', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiRareDrugs() { return jfetch('/api/rare/drugs'); }
export async function apiDrugMimicDrugs() { return jfetch('/api/drug-mimic/drugs'); }
export async function apiRareCompounds() { return jfetch('/api/rare/compounds'); }
export async function apiRareAnalyze(payload) { const res = await jfetch('/api/rare/analyze', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); return { ...res, disease: res?.disease || null, ranked: Array.isArray(res?.ranked) ? res.ranked : [], summary: res?.summary || {}, primary: res?.primary || null, deviation: res?.deviation || null, addons: Array.isArray(res?.addons) ? res.addons : [], bundle: res?.bundle || null, future_path: res?.future_path || null, proposals: Array.isArray(res?.proposals) ? res.proposals : [], sim_context: res?.sim_context || null }; }
export async function apiRareSimTrain(payload) { return jfetch('/api/rare/sim/train', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiRareSimMemory() { return jfetch('/api/rare/sim/memory'); }
export async function apiCompoundReports() { return jfetch('/api/compound/reports'); }
export async function apiCompoundAnalyze(payload) { return jfetch('/api/compound/analyze', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiSystemMemorySummary() { return jfetch('/api/system/memory/summary'); }
export async function apiSelfLLMStart(payload) { return jfetch('/api/self_llm/start', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiSelfLLMRunLoop(payload) { return jfetch('/api/self_llm/run_loop', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiSelfLLMSuggestPatch(payload) { return jfetch('/api/self_llm/suggest_patch', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiRarePhysiology() { return jfetch('/api/rare/physiology'); }
export async function apiRareProposalProtocol(payload) { return jfetch('/api/rare/proposal/protocol', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiRegistryHydrateFda() { return jfetch('/api/registry/fda/hydrate', { method: 'POST', timeoutMs: 600000 }); }
export async function apiPredictorMemory(mode = 'rare_disease') { return jfetch(`/api/predictor/memory/${encodeURIComponent(mode)}`); }
export async function apiPredictorTrain(payload) { return jfetch('/api/predictor/train', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiPredictorPredict(payload) { return jfetch('/api/predictor/predict', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 120000 }); }
export async function apiRegistrySummary() { return jfetch('/api/registry/summary'); }
export async function apiRegistryHydrateMondo(payload) { return jfetch('/api/registry/mondo/hydrate', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 600000 }); }
export async function apiRegistryHydrateAll(payload) { return jfetch('/api/registry/hydrate/all', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 30000 }); }
export async function apiRegistryHydrateStatus(jobId) { try { return await jfetch(jobId ? `/api/registry/hydrate/status/${encodeURIComponent(jobId)}` : '/api/registry/hydrate/status'); } catch (err) { const msg = String(err?.message || err || ''); if (msg.includes('no hydration job found') || msg.includes('hydration job not found') || msg.includes('HTTP 404')) return null; throw err; } }
export async function apiRegistrySearch(query, limit = 25) { return jfetch(`/api/registry/search?q=${encodeURIComponent(query || '')}&limit=${encodeURIComponent(limit)}`); }
export async function apiRegistryDiseaseDrugs(diseaseId, limit = 25) { return jfetch(`/api/registry/disease-drugs/${encodeURIComponent(diseaseId)}?limit=${encodeURIComponent(limit)}`); }
export async function apiBiomedManifest() { return jfetch('/api/biomed/manifest'); }
export async function apiBiomedIngestFull(payload) { return jfetch('/api/biomed/ingest/full', { method: 'POST', body: JSON.stringify(payload || {}), timeoutMs: 600000 }); }

# Therapeutic flow implementation

Base: latest ConstellAI main, ad86a0a00ae870b604253b723f0acf766a41cb3f.
New branch: therapeutic-hypotheses-demo. Original atlas, Reactome/HPO graph, cached dataset,
search, CPLX1/STXBP1 connection and source-ledger logic remain reusable downstream.

Frozen contract: atlas/analysis/models.py, schema version constellai-analysis-v2.
POST /api/v1/analyze_disease accepts disease, optional gene, optional variant, and use_openai.
Frontend starts against a JSON fixture from precisely this contract; live integration swaps transport.

Planned files:
- atlas/server.py: analysis, health and schema endpoints; therapeutic root; atlas at /atlas.
- atlas/llm.py: Responses API strict text.format JSON schema; bounded timeout, sanitized fallback.
- atlas/analysis/models.py, weights.json, ranking.py, service.py, explain.py, evidence.json:
  typed contract, evidence curation, deterministic score and source-bound optional OpenAI extraction.
- atlas/analysis/graph.py: deterministic reviewed evidence graph, source/endpoint validation,
  observed/inferred confidence and scope, contrasting evidence, and original referenced HPO rows.
- web/research.html, research.js, research.css, demo-analysis.json: dark Maria journey.
- web/index.html, app.js, style.css: link back to the therapeutic journey and a
  Maria-only atlas audience, without other persona controls or stored-choice restoration.
- tests/test_analysis.py and tests/test_analysis_api.py: deterministic scoring, source integrity,
  variant abstention, unsupported disease, Responses validation, API/mock parity and original graph.
- README.md, .env.example, START_DEMO.cmd, docs/THERAPEUTIC_DEMO.md: runnable submission handoff.
- docs/EVIDENCE_REVIEW.md, LITERATURE_REVIEW_TRACEABILITY.md, JUDGING_READINESS.md, CHALLENGE_SUBMISSION.md,
  VERIFICATION.md: native literature-tab coverage, evidence corrections and scoped submission checks.

Hero: STXBP1 only after primary evidence checks. 4-PB, levetiracetam and phenytoin are not
accepted from draft examples. Phenylbutyrate formulation and species/variant contexts stay explicit.
The Literature reviews tab supplies foundational papers and corrects levetiracetam's
preclinical assessment. CPLX1 receives a sourced mechanism profile with no drug candidates.
Unknown variants do not inherit a gene-wide LOF/GOF classification or automatic drug eligibility.
Graph similarity never creates therapy efficacy or safety evidence.

Score: configured positive sum minus explicit risks, clamped 0-100. Missing positive evidence
receives zero; unknown risks receive their full configured penalty. Toxicity/organ burden share
one penalty using the worse rating. These ordinal curator ratings are an auditable research
priority heuristic, not a clinical probability or validated efficacy model.

Parallel ownership after contract freeze: backend, frontend, source verification. Integrate and
verify one cached end-to-end path, mock transport, unknown disease/variant paths, desktop/mobile,
and Responses request behavior. Live OpenAI verification requires an available server-side key.
Upload a new branch only after the complete software and delivery verification are finished.
The revised judging prompt adds an inspectable therapeutic graph before prioritisation,
downstream validation resources, an expandable literature-to-claim review, and an honest
unmeasured acceleration thesis. A subsequent explicit user request adds the six-hour
Pulse scope below. Eligibility and outreach ideas from the reference tab remain outside
the implementation.

Six-hour Pulse extension:
- atlas/pulse/models.py freezes constellai-pulse-v1 separately from reviewed analysis.
- atlas/pulse/service.py provides bounded public Europe PMC and ClinicalTrials.gov
  discovery, record diffs, source-specific attempt/success/error status and persistent cache.
- atlas/pulse/sources.py implements bounded JSON adapters and pagination;
  atlas/pulse/__main__.py offers explicit one-shot checks and discovery-snapshot export.
- atlas/server.py runs the due-time scheduler during server lifespan and serves cached
  GET /api/v1/pulse responses, optionally filtered by gene.
- web/research.* provides a dark unreviewed discovery feed, source links and provider dates.
- docs/PULSE.md and README document runtime, coverage and review boundaries.

Watch STXBP1, CPLX1, MUNC18-1 and complexin-1, including exact historical study identifiers
NCT05462054 and NCT06983158. The paper search uses a rolling 90-day publication window;
bounded pagination is not a comprehensive literature or trial monitor. The server must
remain running and awake for six-hour checks. Saved cache supports a truthful prior
snapshot when a provider fails; source-specific dates/errors remain visible.

Discoveries and optional quote-checked AI drafts remain unreviewed. They never update
reviewed evidence, graph claims, score inputs or ranks automatically. Pulse AI is disabled
by default, requires its separate opt-in plus a server-side key, and is limited to three
paper abstracts per run. No foundation/news fetchers, grants, standalone preprint feeds,
monthly ontology refresh, eligibility screening, weekly emails or external messaging
are added by this extension. Final verification and screenshots are recorded separately.

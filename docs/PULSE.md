# Six-hour discovery Pulse

Pulse is a bounded public-source discovery feed for STXBP1/CPLX1 research. Its records and optional AI drafts are **unreviewed**. They never change the reviewed source ledger, evidence graph, score inputs or candidate ranks automatically.

## Run it

Start the normal application with `START_DEMO.cmd` on Windows, or:

```bash
python -m uvicorn atlas.server:app --port 8800
```

Open the dark research journey at http://127.0.0.1:8800 and its Pulse panel. The server starts the scheduler during application lifespan. A due check runs in the background; a six-hour due time is persisted. Browser reads serve the saved snapshot and do not trigger source or model requests.

The server and host must remain running and awake. Shutdown, sleep or a stopped hosting instance pauses checks. This is an application scheduler, not a guarantee that a stopped laptop or hosting instance keeps running. The interval is six hours; short scheduler wake-ups only check whether that interval is due.

The public providers need no API key. To disable scheduling, set `CONSTELLAI_PULSE_ENABLED=0` in `.env` or the server environment and restart. The reviewed analysis remains available from its curated snapshot.

For an operator's one-shot check from the repository:

```bash
python -m atlas.pulse --once
```

This obeys the persisted six-hour interval. `--export <path>` writes a discovery
snapshot containing up to 5,000 saved items. The explicit `--once --force` CLI option bypasses timing and enablement checks,
but cannot bypass an active process lease. Use it deliberately for bootstrap or recovery;
ordinary/manual service refresh retains a one-hour throttle. No public refresh endpoint
is documented; GET remains a saved-state read.

Optional abstract-draft processing is disabled by default. Enable it only with both:

```dotenv
CONSTELLAI_PULSE_AI_ENABLED=1
OPENAI_API_KEY=<server-side key>
```

Keep the real key out of source control, browser code and screenshots. At most three paper abstracts are selected per run. Accepted draft quotes must match the fetched text; the resulting drafts still require review. AI does not supply efficacy points, individual variant classification or autonomous source approval.

## API and separate contract

`GET /api/v1/pulse` reads cached discovery state. Optional parameters:

| Parameter | Meaning |
| --- | --- |
| gene | STXBP1 or CPLX1 filters the returned discovery items. |
| limit | Number of displayed items; default 50, accepted range 1–200. |

For example, open `http://127.0.0.1:8800/api/v1/pulse?gene=STXBP1&limit=50`.

The frozen response schema is `constellai-pulse-v1` in `atlas/pulse/models.py`. It is separate from `constellai-analysis-v2`; a discovery is not a reviewed analysis claim.

The response exposes scheduler enablement/running state, the six-hour interval, last attempt/success and next check, watchlist, per-provider state, bounded items and coverage limitations. An item identifies its provider, record type, public URL, matched genes, source date, local first/last seen/change times, differences, unreviewed status and any draft claims.

## Coverage and limits

The watchlist uses **STXBP1**, **CPLX1**, **MUNC18-1** and **complexin-1**, plus exact historical study IDs **NCT05462054** and **NCT06983158**. Term matches establish discovery relevance only; they do not establish a drug response or shared clinical eligibility.

| Provider | Fetch design | Coverage boundary |
| --- | --- | --- |
| Europe PMC | Public REST search, JSON core metadata/abstracts, cursor pagination; a rolling 90-day first-publication window repeated at every check. | At most two search pages of 50 records. Late indexing, older work, synonyms beyond this watchlist and records beyond the cap can be missed. MED, PMC and PPR records can be discovered; a preprint is unreviewed discovery, not validated evidence. |
| ClinicalTrials.gov | Public v2 gene/synonym search and exact study reads; page-token pagination. | At most two search pages of 50, plus the watched exact study reads. Search matching and caps are not an exhaustive registry search. Status is the dated sponsor registry entry, not a site-access or eligibility decision. |

Pulse does not add foundation/company-news fetchers, grant feeds, standalone bioRxiv/medRxiv connectors, monthly ontology refresh, weekly emails, case finding or eligibility screening. Existing Atlas enrichment and the curated therapeutic evidence retain their separate behavior and review scope.

Each source request has a 10-second timeout, a two-megabyte response bound and a shared
60-second provider budget. Validation or pagination failures produce partial/error
coverage rather than a complete-success claim. A record absent from a bounded search
is never inferred to have been removed.

A first successful bootstrap labels matching records **discovered** because they are new to the local watchlist. It must not claim they were just published, first discovered scientifically or absent from all prior literature. Subsequent changes are comparisons against the saved local record; a new first-seen time is not a publication event.

Historical terminated or withdrawn trials can appear as discoveries on initial import. That is not evidence of a newly terminated or withdrawn trial event.

## Read the dates correctly

| Field or displayed date | Meaning |
| --- | --- |
| reviewed evidence date | Human curation of the therapeutic source ledger; Pulse fetches do not advance it. |
| provider last_attempt_at | Most recent attempt to contact that source, including failures. |
| provider last_success_at | Most recent check completing within that provider's configured query/window. A partial fetch can yield records while leaving this complete-success date unchanged. |
| first_seen_at / last_seen_at | First/most recent appearance in the local Pulse watchlist. |
| changed_at | When the local comparison recorded a discovery or change. |
| paper source_updated_on | Source dateOfRevision when supplied, otherwise firstPublicationDate. The summary separately identifies first publication: earliest electronic/print date, potentially derived from partial dates. This is not a Pulse fetch timestamp. |
| trial source_updated_on | Registry last-update-posted date. It is not the Pulse fetch time. |
| next_check_at | Persisted due time for a subsequent scheduler check while the server runs. |

Provider states are pending, ok, partial or error. A partial result or error must retain its coverage/error information alongside the corresponding attempt and last-success dates. A network block, timeout or failed page must not be rendered as “no relevant research exists.” Previously saved records are historical cache, not proof that a failed source was freshly checked.

Use the provider rows when judging freshness; a global fetch timestamp does not establish that every source succeeded. No numerical half-life is used to certify clinical validity.

## Review boundary

Human review must verify the primary record, exact disease/gene/variant/model, endpoint, formulation, safety limitations, contradictions and current study status before adding a supported claim. Public source URLs are preserved for that work.

A literal quote match checks provenance of the quoted words. It does not establish that a draft interpretation is correct, that an experimental effect transfers to humans or that two related genes share treatment response. Accepted AI drafts remain unreviewed and do not enter the reviewed graph or scoring.

Persistent state is `data/cache/pulse/state.sqlite3`, excluded from Git. Saved provider
statuses and records survive a restart; records are retained when they leave the
rolling publication window. On a fresh cache, `data/curated/pulse-bootstrap.json`,
when present and valid, supplies a dated public-source discovery baseline. Its original
timestamps and unreviewed status are preserved; import does not claim a new fetch.
The shipped paper bootstrap contains metadata and source links, without full
abstracts. Subsequent source retrieval may store returned excerpts locally.
Missing bootstrap abstracts do not create a fabricated change on the first retrieval.

The API returns newest local changes up to its requested display limit. Its record
counts describe saved/filtered watchlist records, not the size of all relevant research.
A reviewer curates evidence explicitly through the reviewed source library; Pulse
does not overwrite that file. No patient data, outreach, enrollment or external
messaging is part of the feed.

## Technical source verification

Reviewed 4 October 2026 against primary provider interfaces:

- [Europe PMC REST documentation](https://europepmc.org/RestfulWebService) describes JSON versus default XML, core metadata and sorting. Its [official development-host documentation](https://dev.europepmc.org/RestfulWebService) was readable when the production documentation page returned HTTP 403.
- [Europe PMC field metadata](https://www.ebi.ac.uk/europepmc/webservices/rest/fields?format=json) lists FIRST_PDATE and FIRST_IDATE separately. [Search help](https://europepmc.org/help) distinguishes first publication from first indexing. The [official reference guide](https://europepmc.org/docs/EBI_Europe_PMC_Web_Service_Reference.pdf) specifies cursorMark/nextCursorMark pagination.
- [ClinicalTrials.gov v2 API documentation](https://clinicaltrials.gov/data-api/api) and [study data structure](https://clinicaltrials.gov/data-api/about-api/study-data-structure) are the primary technical references. Some documentation pages depend on JavaScript and expose little text to a static reader.

A bounded live transport probe confirmed Europe PMC JSON core search with a first-publication date range, a returned abstract and next cursor. A ClinicalTrials.gov gene/synonym query returned a nextPageToken; using it returned a distinct study on the next page. Fresh individual-study reads also succeeded through the public API.

These probes establish the source interfaces and one transport's access on the review date. Provider access can differ by host, network or request client; HTTP 403/bot protection and network restrictions must remain visible failures. Successful probes do not replace the application's own live bootstrap check. Delivery verification records the implemented adapter, scheduler and UI checks separately.

The application's approved live bootstrap on 2026-10-04 fetched **102 unreviewed
records: 90 Europe PMC papers and 12 ClinicalTrials.gov studies**. The attempt was
2026-10-04T12:07:31Z, complete success 12:07:33Z and persisted next due time
18:07:31Z. Both providers reported ok for their configured coverage. These are
actual discovery-snapshot counts, not comprehensive field counts or reviewed claims.
The six-hour due-time behavior was checked with injected clocks; a full six-hour
wall-clock observation had not occurred at delivery.

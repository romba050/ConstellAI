"use strict";

(() => {
  const $ = (selector) => document.querySelector(selector);
  const content = $("#pulse-content");
  if (!content) return;
  const status = $("#pulse-status");
  const errorBox = $("#pulse-error");
  const refreshButton = $("#pulse-refresh");
  const downloadButton = $("#pulse-download");
  const snapshotMode = new URLSearchParams(location.search).get("data") === "mock";
  const providers = {
    europe_pmc: { name: "Europe PMC", hosts: new Set(["europepmc.org", "www.europepmc.org", "pubmed.ncbi.nlm.nih.gov"]) },
    clinicaltrials_gov: { name: "ClinicalTrials.gov", hosts: new Set(["clinicaltrials.gov", "www.clinicaltrials.gov"]) },
  };
  const feedStates = {
    pending: "First retrieval pending", running: "Retrieval in progress", ok: "Last check completed",
    partial: "Partial retrieval", error: "Retrieval error", disabled: "Monitoring disabled",
  };
  const providerStates = { pending: "Pending", ok: "Retrieved", partial: "Partial", error: "Error" };
  const evidenceLabels = {
    human_clinical: "Human clinical", preclinical: "Preclinical", mechanistic_inference: "Mechanistic inference", unknown: "Unknown",
  };
  const trialStatuses = {
    RECRUITING: "Recruiting", NOT_YET_RECRUITING: "Not yet recruiting", ACTIVE_NOT_RECRUITING: "Active, not recruiting",
    COMPLETED: "Completed", TERMINATED: "Terminated", WITHDRAWN: "Withdrawn", SUSPENDED: "Suspended",
    ENROLLING_BY_INVITATION: "Enrolling by invitation", AVAILABLE: "Available", NO_LONGER_AVAILABLE: "No longer available",
    TEMPORARILY_NOT_AVAILABLE: "Temporarily not available", APPROVED_FOR_MARKETING: "Approved for marketing", UNKNOWN: "Unknown",
  };
  const dateFormatter = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Stockholm", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short" });
  let selectedGene = "STXBP1";
  let currentData = null;
  let lastSignature = "";
  let activeController = null;
  let requestSequence = 0;

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
  }

  function timestamp(value, empty = "Not recorded") {
    if (!value) return `<span class="pulse-muted">${esc(empty)}</span>`;
    const parsed = new Date(value);
    return Number.isFinite(parsed.getTime()) ? `<time datetime="${esc(value)}" title="${esc(value)}">${esc(dateFormatter.format(parsed))}</time>` : esc(value);
  }

  function sourceLink(item) {
    let safe = null;
    try {
      const url = new URL(item.url);
      if (url.protocol === "https:" && !url.username && !url.password && providers[item.provider].hosts.has(url.hostname)) safe = url.href;
    } catch (_) { /* An unsafe or unavailable source URL remains plain text. */ }
    return safe ? `<a href="${esc(safe)}" target="_blank" rel="noopener noreferrer">${esc(item.title)} <span aria-hidden="true">↗</span></a>` : `<span>${esc(item.title)}</span><span class="pulse-link-unavailable">Source link unavailable</span>`;
  }

  function validate(data) {
    const textOrNull = (value) => value === null || typeof value === "string";
    const textArray = (value) => Array.isArray(value) && value.every((item) => typeof item === "string");
    const count = (value) => Number.isInteger(value) && value >= 0;
    if (!data || data.schema_version !== "constellai-pulse-v1" || !Object.prototype.hasOwnProperty.call(feedStates, data.state) ||
        typeof data.scheduler_enabled !== "boolean" || typeof data.scheduler_running !== "boolean" ||
        !Number.isInteger(data.interval_hours) || data.interval_hours < 1 ||
        ![data.last_attempt_at, data.last_success_at, data.next_check_at].every(textOrNull) ||
        !textArray(data.watchlist) || !textArray(data.limitations) || !Array.isArray(data.providers) || !Array.isArray(data.items) ||
        !count(data.unreviewed_count) || !count(data.total_records)) throw new Error("The saved Pulse response is incomplete. The research analysis remains available.");
    for (const provider of data.providers) {
      if (!Object.prototype.hasOwnProperty.call(providers, provider.id) || !Object.prototype.hasOwnProperty.call(providerStates, provider.state) ||
          typeof provider.name !== "string" || typeof provider.coverage !== "string" || !count(provider.record_count) ||
          ![provider.last_attempt_at, provider.last_success_at, provider.error].every(textOrNull)) throw new Error("A Pulse provider status is incomplete.");
    }
    for (const item of data.items) {
      if (!Object.prototype.hasOwnProperty.call(providers, item.provider) || !["paper", "trial"].includes(item.kind) ||
          !["discovered", "updated"].includes(item.change_type) || item.review_status !== "unreviewed" ||
          ![item.id, item.title, item.url, item.summary, item.first_seen_at, item.last_seen_at, item.changed_at].every((value) => typeof value === "string") ||
          !textOrNull(item.source_updated_on) || !textOrNull(item.excerpt) || !textArray(item.matched_genes) ||
          !Array.isArray(item.changes) || !Array.isArray(item.draft_claims) ||
          !item.changes.every((change) => typeof change.field === "string" && textOrNull(change.before) && textOrNull(change.after)) ||
          !item.draft_claims.every((claim) => claim.review_status === "unreviewed" && typeof claim.statement === "string" && typeof claim.quote === "string" && Object.prototype.hasOwnProperty.call(evidenceLabels, claim.evidence_type))) throw new Error("An unreviewed Pulse record is incomplete; it has not been displayed.");
    }
    return data;
  }

  function monitored(data = currentData) {
    return Boolean(selectedGene && (data ? data.watchlist.some((term) => term.toUpperCase() === selectedGene) : ["STXBP1", "CPLX1"].includes(selectedGene)));
  }

  function providerCard(provider) {
    return `<article class="pulse-provider"><div class="pulse-provider-heading"><h4>${esc(provider.name)}</h4><span class="pulse-state ${provider.state}">${esc(providerStates[provider.state])}</span></div><dl><dt>Last attempt</dt><dd>${timestamp(provider.last_attempt_at)}</dd><dt>Last successful retrieval</dt><dd>${timestamp(provider.last_success_at)}</dd><dt>Records reported</dt><dd>${provider.record_count}</dd></dl>${provider.error ? `<p class="pulse-provider-error">${esc(provider.error)}</p>` : ""}<p class="pulse-coverage"><strong>Coverage &amp; retrieval limits</strong>${esc(provider.coverage)}</p></article>`;
  }

  function changeValue(value, field) {
    if (value === null) return '<span class="pulse-muted">Not recorded</span>';
    let actual = value;
    try { const parsed = JSON.parse(value); if (typeof parsed === "string") actual = parsed; } catch (_) { /* Most field values are ordinary text. */ }
    const readable = /status/i.test(field) ? trialStatuses[actual] : null;
    return readable ? `${esc(readable)}<span class="pulse-raw-value">${esc(actual)}</span>` : esc(value);
  }

  function changes(item) {
    if (!item.changes.length) return `<p class="pulse-record-note">${item.change_type === "discovered" ? "New to the local watchlist; this does not mean newly published." : "The source record was updated; no field-level difference is recorded in this snapshot."}</p>`;
    return `<div class="pulse-diff-wrap"><table class="pulse-diff"><caption>Recorded changes · awaiting review</caption><thead><tr><th scope="col">Field</th><th scope="col">Before</th><th scope="col">After</th></tr></thead><tbody>${item.changes.map((change) => `<tr><th scope="row">${esc(change.field === "source_updated_on" ? item.kind === "paper" ? "Source revised / published" : "Registry updated" : change.field.replace(/([a-z])([A-Z])/g, "$1 $2").replaceAll("_", " "))}</th><td>${changeValue(change.before, change.field)}</td><td>${changeValue(change.after, change.field)}</td></tr>`).join("")}</tbody></table></div>`;
  }

  function sourceDetails(item) {
    const drafts = item.draft_claims.map((draft) => {
      const matched = Boolean(draft.quote && draft.quote.length <= 300 && item.excerpt?.includes(draft.quote));
      return `<div class="pulse-draft"><div class="pulse-draft-label">AI draft · unreviewed<span>${esc(evidenceLabels[draft.evidence_type])}</span></div><p>${esc(draft.statement)}</p>${draft.quote ? `<blockquote>${esc(draft.quote)}</blockquote>` : ""}<p class="pulse-quote-state">${matched ? "Exact quote found in the source excerpt. The claim still requires review." : "Quote check unresolved in this displayed excerpt. The claim requires review."}</p></div>`;
    }).join("");
    return `<details class="pulse-item-details" data-pulse-key="${esc(`record:${item.id}:source`)}"><summary>Source record &amp; review details<span>Unreviewed</span></summary><div><dl class="pulse-item-times"><dt>First seen on watchlist</dt><dd>${timestamp(item.first_seen_at)}</dd><dt>Last seen in retrieval</dt><dd>${timestamp(item.last_seen_at)}</dd><dt>${item.kind === "paper" ? "Source revised / published" : "Registry updated"}</dt><dd>${item.source_updated_on ? esc(item.source_updated_on) : "Not supplied by source"}</dd></dl>${item.excerpt ? `<h4>Source excerpt</h4><p class="pulse-excerpt">${esc(item.excerpt)}</p>` : '<p class="pulse-muted">No source excerpt is stored for this record.</p>'}${drafts}${item.draft_claims.length ? '<p class="pulse-record-note">Quote matching checks provenance only. Draft claims await curator adjudication.</p>' : ""}</div></details>`;
  }

  function itemCard(item) {
    const preview = item.kind === "paper" ? "Paper record awaiting curator review. Open the source to assess relevance, study type and limitations." : item.summary;
    return `<article class="pulse-item"><div class="pulse-item-meta"><span class="pulse-change ${item.change_type}">${item.change_type === "discovered" ? "New to watchlist" : "Record updated"}</span><span class="pulse-unreviewed">Unreviewed</span><span>${esc(providers[item.provider].name)} · ${item.kind === "paper" ? "Paper" : "Trial"}</span></div><h4>${sourceLink(item)}</h4><p class="pulse-detected">Detected ${timestamp(item.changed_at)} · ${esc(item.matched_genes.join(", "))}</p>${item.source_updated_on ? `<p class="pulse-source-date">${item.kind === "paper" ? "Source revised / published" : "Registry updated"}: ${esc(item.source_updated_on)}</p>` : ""}<p class="pulse-item-summary">${esc(preview)}</p>${changes(item)}${sourceDetails(item)}</article>`;
  }

  function feed(data) {
    if (!monitored(data)) return `<div class="pulse-empty"><h4>${selectedGene ? `${esc(selectedGene)} is not monitored` : "No watched gene selected"}</h4><p>Pulse currently follows the configured watchlist shown above. This query has no monitored feed; its research analysis is handled separately.</p></div>`;
    const items = data.items.filter((item) => item.matched_genes.some((gene) => gene.toUpperCase() === selectedGene));
    if (!items.length) {
      const explanation = data.state === "pending" ? "The first retrieval has not completed." : ["error", "partial"].includes(data.state) ? "Review provider status and coverage above." : "No new or updated records are present in this saved feed for the selected gene.";
      return `<div class="pulse-empty"><h4>No watchlist changes to show for ${esc(selectedGene)}</h4><p>${esc(explanation)} This is a bounded source watchlist, with the recorded coverage and retrieval limits.</p></div>`;
    }
    const first = items.slice(0, 5);
    const remaining = items.slice(5);
    return `<p class="pulse-feed-count">${items.length} ${items.length === 1 ? "feed entry" : "feed entries"} shown for ${esc(selectedGene)} · all unreviewed</p><div class="pulse-feed">${first.map(itemCard).join("")}</div>${remaining.length ? `<details class="pulse-more" data-pulse-key="more:${esc(selectedGene)}"><summary>Show ${remaining.length} more watchlist ${remaining.length === 1 ? "entry" : "entries"}</summary><div class="pulse-feed">${remaining.map(itemCard).join("")}</div></details>` : ""}`;
  }

  function render(data) {
    const opened = new Set([...document.querySelectorAll("#pulse-content details[data-pulse-key]")].filter((detail) => detail.open).map((detail) => detail.getAttribute("data-pulse-key")));
    const schedulerPrefix = snapshotMode ? "Recorded " : "";
    const running = data.scheduler_running ? "worker running" : "worker stopped";
    const enabled = data.scheduler_enabled ? "enabled" : "disabled";
    const nextNote = data.scheduler_enabled && data.scheduler_running ? "" : '<p class="pulse-schedule-note">The worker is not active; a recorded next-check timestamp does not indicate a running schedule.</p>';
    content.innerHTML = `<div class="pulse-schedule"><div><h3>${snapshotMode ? "Saved six-hour monitoring setup" : `Background checks every ${data.interval_hours} hours`}</h3><p>${snapshotMode ? "Snapshot only. Scheduler and provider states below reflect the saved record; this page does not refresh Pulse or control background retrieval." : "Source retrieval follows the background schedule. This page reads the saved feed; refreshing the display does not trigger a source search."}</p></div><div class="pulse-worker-states"><span class="pulse-state ${data.scheduler_enabled ? "ok" : "pending"}">${schedulerPrefix}${enabled}</span><span class="pulse-state ${data.scheduler_running ? "ok" : "pending"}">${schedulerPrefix}${running}</span></div></div><dl class="pulse-times"><div><dt>Last source-check attempt</dt><dd>${timestamp(data.last_attempt_at)}</dd></div><div><dt>Last successful retrieval</dt><dd>${timestamp(data.last_success_at)}</dd></div><div><dt>Next scheduled check</dt><dd>${timestamp(data.next_check_at, "Not scheduled")}</dd></div></dl>${nextNote}<div class="pulse-retrieval-state"><span class="pulse-state ${data.state}">${esc(feedStates[data.state])}</span><span>${data.total_records} stored source records · ${data.unreviewed_count} unreviewed records reported</span></div><details class="pulse-source-status" data-pulse-key="providers"><summary>Source status &amp; coverage<span>${data.providers.length} providers</span></summary><div class="pulse-providers">${data.providers.map(providerCard).join("")}</div></details><details class="pulse-watchlist" data-pulse-key="watchlist"><summary>Watched genes, synonyms &amp; identifiers<span>${data.watchlist.length} terms</span></summary><div class="pulse-watch-terms">${data.watchlist.map((term) => `<span>${esc(term)}</span>`).join("")}</div></details><div class="pulse-feed-heading"><h3>Unreviewed research feed</h3><p>Changes are discoveries for this watchlist, with their source dates and recorded differences.</p></div>${feed(data)}<details class="pulse-limitations" data-pulse-key="limitations"><summary>Pulse scope &amp; limitations</summary><ul>${data.limitations.map((limitation) => `<li>${esc(limitation)}</li>`).join("")}</ul></details>`;
    document.querySelectorAll("#pulse-content details[data-pulse-key]").forEach((detail) => { detail.open = opened.has(detail.getAttribute("data-pulse-key")); });
    $("#pulse-gene").textContent = selectedGene || "No watched gene";
    $("#pulse-summary-state").textContent = snapshotMode ? "Snapshot only · unreviewed" : monitored(data) ? feedStates[data.state] : "Gene not monitored";
    downloadButton.disabled = !monitored(data);
  }

  function absentSnapshot() {
    $("#pulse-summary-state").textContent = "Snapshot only";
    status.textContent = "Mock mode · no live Pulse requests or polling";
    content.innerHTML = '<div class="pulse-empty"><h4>Snapshot-only mode</h4><p>No saved Pulse snapshot has been included. The analysis fixture remains available; open cached analysis to inspect the saved live watchlist.</p><a class="small-action" href="/">Open cached analysis →</a></div>';
    downloadButton.disabled = true;
  }

  async function loadPulse(force = false) {
    if (document.hidden || (activeController && !force)) return;
    if (activeController) activeController.abort();
    const sequence = ++requestSequence;
    const controller = new AbortController();
    activeController = controller;
    const timeout = setTimeout(() => controller.abort(), 12000);
    content.setAttribute("aria-busy", "true");
    refreshButton.disabled = true;
    errorBox.hidden = true;
    try {
      const query = selectedGene && ["STXBP1", "CPLX1"].includes(selectedGene) ? `?gene=${encodeURIComponent(selectedGene)}` : "";
      const response = await fetch(snapshotMode ? "/pulse-snapshot.json" : `/api/v1/pulse${query}`, { signal: controller.signal, cache: "no-store" });
      if (snapshotMode && response.status === 404) { if (sequence === requestSequence) absentSnapshot(); return; }
      if (!response.ok) throw new Error(`The saved Pulse feed could not be read (HTTP ${response.status}).`);
      const data = validate(await response.json());
      if (sequence !== requestSequence) return;
      const signature = `${selectedGene || ""}\u0000${JSON.stringify(data)}`;
      currentData = data;
      if (signature !== lastSignature) {
        render(data);
        lastSignature = signature;
      }
      $("#pulse-summary-state").textContent = snapshotMode ? "Snapshot only · unreviewed" : monitored(data) ? feedStates[data.state] : "Gene not monitored";
      status.textContent = snapshotMode ? "Saved snapshot · no live Pulse requests or polling" : !monitored(data) ? "This gene is not on the Pulse watchlist" : force ? "Saved feed loaded · source retrieval times are shown below" : "Saved watchlist loaded · source retrieval times are shown below";
    } catch (error) {
      if (sequence !== requestSequence) return;
      if (snapshotMode && !currentData) { absentSnapshot(); return; }
      errorBox.textContent = error.name === "AbortError" ? "The saved Pulse feed took longer than expected to load." : error instanceof TypeError ? "The saved Pulse feed could not be reached." : error.message;
      if (currentData) errorBox.textContent += " The last displayed snapshot is retained.";
      errorBox.hidden = false;
      status.textContent = "Pulse unavailable · the research analysis remains available";
      if (!currentData) content.innerHTML = '<p class="pulse-muted">Pulse status and source records will appear when the saved feed is available.</p>';
      $("#pulse-summary-state").textContent = "Feed unavailable";
    } finally {
      clearTimeout(timeout);
      if (sequence === requestSequence) {
        activeController = null;
        content.setAttribute("aria-busy", "false");
        refreshButton.disabled = snapshotMode;
      }
    }
  }

  refreshButton.addEventListener("click", () => { if (!snapshotMode) loadPulse(true); });
  downloadButton.addEventListener("click", () => {
    if (!currentData || !monitored()) return;
    const url = URL.createObjectURL(new Blob([`${JSON.stringify(currentData, null, 2)}\n`], { type: "application/json" }));
    const anchor = document.createElement("a");
    const date = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Stockholm", dateStyle: "short" }).format(new Date());
    anchor.href = url;
    anchor.download = `constellai-pulse-review-feed-${date}.json`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.addEventListener("constellai:analysis", (event) => {
    const gene = typeof event.detail?.gene === "string" ? event.detail.gene.trim().toUpperCase() : null;
    if (gene === selectedGene) return;
    selectedGene = gene;
    $("#pulse-gene").textContent = selectedGene || "No watched gene";
    downloadButton.disabled = true;
    if (snapshotMode) { if (currentData) render(currentData); return; }
    if (currentData && !monitored(currentData)) render(currentData);
    status.textContent = monitored() ? `Loading the saved watchlist for ${selectedGene}…` : "This gene is not on the Pulse watchlist";
    loadPulse(true);
  });
  if (!snapshotMode) {
    setInterval(() => { if (!document.hidden) loadPulse(); }, 60000);
  } else refreshButton.disabled = true;
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && (!snapshotMode || requestSequence === 0)) loadPulse();
  });
  loadPulse();
})();

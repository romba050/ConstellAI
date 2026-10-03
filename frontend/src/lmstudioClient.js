export async function callLmStudioJSON({
  baseUrl,
  apiKey,
  model,
  system,
  user,
  timeoutMs = 25000
}) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = `${baseUrl.replace(/\/$/, "")}/v1/chat/completions`;
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {})
      },
      body: JSON.stringify({
        model,
        temperature: 0.2,
        messages: [
          { role: "system", content: system },
          { role: "user", content: user }
        ],
        response_format: { type: "json_object" }
      }),
      signal: controller.signal
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`LM STUDIO HTTP ${res.status}: ${txt.slice(0, 300)}`);
    }

    const data = await res.json();
    const content = data?.choices?.[0]?.message?.content ?? "";
    let parsed = null;
    try { parsed = JSON.parse(content); } catch { parsed = null; }

    return { ok: true, raw: content, json: parsed };
  } finally {
    clearTimeout(t);
  }
}

export function randomHypothesisBundle(seedLabel = "MOCK") {
  const ideas = [
    {
      hypothesis: `IMMUNE GENE OVERLAP SIGNAL SUGGESTS ONCOLOGY RELEVANCE (${seedLabel}).`,
      why: [
        "TARGET/GENE LANGUAGE CLUSTER LOOKS SIMILAR ACROSS TWO DOMAINS (MOCK).",
        "DOWNSTREAM PATHWAY WORDS CO-OCCUR IN ABSTRACTS (MOCK)."
      ]
    },
    {
      hypothesis: `SIRTUIN-LEANING SIGNAL MAY MODULATE TUMOR MICROENVIRONMENT (${seedLabel}).`,
      why: [
        "SIRT NODE CONNECTS METABOLIC + IMMUNE TERMS (MOCK).",
        "PRIOR ART SHOWS MIXED BUT TESTABLE SIGNALS (MOCK)."
      ]
    },
    {
      hypothesis: `COMPOUND COMBINATION COULD CREATE AN UNEXPECTED SYNERGY (${seedLabel}).`,
      why: [
        "OVERLAP IS WEAK INDIVIDUALLY BUT STRONG AS A SET (MOCK).",
        "CHEAP EARLY KILL CAN DISPROVE FAST (MOCK)."
      ]
    }
  ];

  const pick = ideas[Math.floor(Math.random() * ideas.length)];

  const experiments = [
    { name: "IN VITRO MARKER SHIFT SCREEN", cost_eur: 4500, days: 10, early_kill: "NO SHIFT IN PRIMARY MARKERS." },
    { name: "DOSE-RANGE TOX / VIABILITY", cost_eur: 2500, days: 7, early_kill: "TOX WINDOW TOO NARROW." },
    { name: "PATHWAY REPORTER ASSAY", cost_eur: 6500, days: 14, early_kill: "REPORTER DOES NOT MOVE." },
    { name: "SIMPLE CO-CULTURE IMMUNE READOUT", cost_eur: 9000, days: 18, early_kill: "NO DELTA VS CONTROL." },
    { name: "MINI-PK / STABILITY CHECK", cost_eur: 5000, days: 12, early_kill: "UNSTABLE / DEGRADES FAST." }
  ];

  const profit = {
    scenario: "IF SIGNAL HOLDS, THIS COULD OPEN A NEW INDICATION OR A LICENSABLE ASSAY WORKFLOW (MOCK).",
    range_eur: "250K–2.5M (MOCK PLACEHOLDER)"
  };

  return {
    hypothesis: pick.hypothesis,
    why: pick.why,
    early_kill_experiments: experiments,
    cost_total_eur: experiments.reduce((s, x) => s + x.cost_eur, 0),
    profit_potential: profit
  };
}

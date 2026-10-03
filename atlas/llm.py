"""OpenAI-backed steps: Extract, Reconcile, Explain.

Every function returns None (or leaves its input untouched) when no key is
configured or the call fails, and the callers fall back to deterministic logic.
Model output is never trusted blindly: quotes must appear verbatim in the
source abstract, and citations must point at evidence ids we supplied.
"""
import json
import re

from .config import OPENAI_API_KEY, OPENAI_MODEL

_client = None


def available():
    return bool(OPENAI_API_KEY)


def status():
    return {"enabled": available(), "model": OPENAI_MODEL if available() else None}


def _json(system, user, name, schema):
    global _client
    if not available():
        return None
    try:
        if _client is None:
            from openai import OpenAI
            _client = OpenAI(api_key=OPENAI_API_KEY, timeout=60)
        r = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_schema",
                             "json_schema": {"name": name, "strict": True, "schema": schema}},
        )
        return json.loads(r.choices[0].message.content)
    except Exception as e:  # network, quota, bad model name: degrade to template mode
        print(f"[llm] {name} failed: {e}")
        return None


def _obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def extract_claims(gene, abstracts):
    """Extract variant-effect and research-asset claims from abstracts.

    abstracts: [{"pmid": str, "text": str}]. Returns claims whose quote is
    verified to be a verbatim span of the cited abstract, or None.
    """
    if not abstracts:
        return None
    schema = _obj({"claims": {"type": "array", "items": _obj({
        "pmid": {"type": "string"},
        "kind": {"type": "string", "enum": ["variant_effect", "asset"]},
        "effect": {"type": "string", "enum": ["loss_of_function", "gain_of_function", "dominant_negative", "none"]},
        "asset_type": {"type": "string", "enum": ["animal_model", "cell_model", "biomarker", "natural_history", "registry", "therapy", "none"]},
        "statement": {"type": "string"},
        "quote": {"type": "string"},
    })}})
    system = (
        "You extract evidence from biomedical abstracts for a rare-disease knowledge graph. "
        f"Focus on the gene {gene}. Extract (a) variant_effect claims: what the abstract itself says about "
        "how pathogenic variants in this gene act (loss of function / haploinsufficiency, gain of function, "
        "dominant negative), and (b) asset claims: reusable research assets the abstract reports (animal model, "
        "cell/iPSC model, biomarker, natural history study, registry, therapy candidate). "
        "For each claim give a one-sentence plain statement and a `quote` copied EXACTLY, character for "
        "character, from that abstract (max 300 characters). Do not infer beyond the text. "
        "Use effect='none' for asset claims and asset_type='none' for variant_effect claims. "
        "Return an empty list if nothing qualifies."
    )
    user = "\n\n".join(f"PMID {a['pmid']}:\n{a['text']}" for a in abstracts)
    out = _json(system, user, "claims", schema)
    if out is None:
        return None
    texts = {a["pmid"]: _norm(a["text"]) for a in abstracts}
    verified = []
    for c in out["claims"]:
        if c["pmid"] in texts and _norm(c["quote"]) and _norm(c["quote"]) in texts[c["pmid"]]:
            verified.append(c)
    return verified


def resolve_query(query):
    """Reconcile a free-text or lay query into candidate vocabulary strings."""
    schema = _obj({"candidates": {"type": "array", "items": {"type": "string"}}})
    system = (
        "A family member or researcher typed a search into a rare-disease atlas and it matched nothing. "
        "Return up to 6 candidate search strings it most likely refers to: official disease names, "
        "HGNC gene symbols, or HPO phenotype names. Correct misspellings and expand lay descriptions. "
        "Only real, established names; no explanations."
    )
    out = _json(system, query, "resolve", schema)
    return out["candidates"] if out else None


def explain(context, evidence_ids, audience):
    """Plain-language explanation of a connection. Every sentence cites [E#] ids."""
    schema = _obj({"paragraphs": {"type": "array", "items": {"type": "string"}}})
    tone = {
        "devon": "a newly diagnosed family with no medical background (short sentences, no jargon, warm but honest)",
        "maria": "a patient-organisation leader deciding whether to contact another community",
        "priya": "a biotech scout assessing therapeutic opportunity",
        "osei": "an academic researcher looking for collaborators on a shared mechanism",
    }.get(audience, "a patient-organisation leader")
    system = (
        f"You explain a link between two rare diseases to {tone}. Use ONLY the evidence items provided; each "
        "has an id like E3. After every factual sentence cite the supporting ids in square brackets, e.g. [E3]. "
        "Clearly separate what is observed data from what is an inferred hypothesis, state what is still "
        "uncertain or contradictory, and finish with what should be checked next. Never suggest that a "
        "treatment exists or will work. 3 short paragraphs, under 170 words total."
    )
    out = _json(system, json.dumps(context), "explanation", schema)
    if not out:
        return None
    text = "\n\n".join(out["paragraphs"])
    cited = set(re.findall(r"E\d+", text))
    if not cited or not cited <= set(evidence_ids):
        return None  # uncited or mis-cited explanations are discarded
    return text


def name_groups(groups, hpo, path_names):
    """Give colour groups short human names; keeps the enrichment label on failure."""
    payload = [{"id": g["id"],
                "phenotypes": [hpo[h["hp"]]["name"] for h in g["phenotypes"]],
                "pathways": [path_names.get(p["id"], "") for p in g["pathways"]],
                "pathway_class": g["top_pathway_class"]}
               for g in groups if g["id"] >= 0]
    schema = _obj({"names": {"type": "array", "items": _obj({"id": {"type": "integer"}, "name": {"type": "string"}})}})
    system = ("Each item describes a cluster of rare monogenic diseases by its most enriched phenotypes and "
              "pathways. Give each a distinct, accurate name of 2-4 words that a patient family could "
              "understand (e.g. 'Retinal degeneration', 'Lysosomal storage'). Do not overclaim.")
    out = _json(system, json.dumps(payload), "group_names", schema)
    if out:
        names = {x["id"]: x["name"] for x in out["names"]}
        for g in groups:
            if g["id"] in names:
                g["enrichment_label"], g["label"] = g["label"], names[g["id"]]

"""Explain one disease-to-disease connection: evidence, contradictions, checks, actions."""
from concurrent.futures import ThreadPoolExecutor

from . import enrich, llm

ACTIVE = ("RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING")
REUSABLE_KINDS = ("Natural history study", "Registry", "Biomarker study", "Biobank")
EFFECT_LABEL = {"loss": "loss of function", "gain": "gain of function", "mixed": "variant-dependent (loss and gain both reported)",
                "unknown": "not established"}


def effect_profile(atlas, disease, enr):
    """Combine curated, variant-level and literature signals into a variant-effect call per disease."""
    signals, lof, gof = [], 0, 0
    for s in disease["genes"][:2]:
        cg = atlas.genes[s]["clingen"]
        if cg and cg["haploinsufficiency"].startswith("Sufficient"):
            lof += 2
            signals.append({"text": f"ClinGen: sufficient evidence that losing one copy of {s} causes disease (haploinsufficiency)",
                            "source": "ClinGen dosage sensitivity", "url": cg["url"], "date": cg["date"],
                            "kind": "curated", "confidence": 0.95})
    if any("recessive" in i.lower() for i in disease["inheritance"]):
        lof += 1
        signals.append({"text": "Recessive inheritance: both gene copies are affected, which usually means loss of function",
                        "source": "HPO annotations (inheritance)", "url": "", "date": "", "kind": "inferred", "confidence": 0.6})
    for v in (enr or {}).get("clinvar", []):
        known = v["truncating"] + v["missense"]
        if known >= 10:
            share = v["truncating"] / known
            if share > 0.5:
                lof += 1
            signals.append({"text": f"ClinVar: {v['truncating']} protein-truncating vs {v['missense']} missense pathogenic variants in {v['gene']} "
                                    f"({share:.0%} truncating)",
                            "source": "ClinVar", "url": v["url"], "date": (enr or {}).get("fetched", ""),
                            "kind": "observed", "confidence": 0.7})
    lit = {"loss_of_function": set(), "gain_of_function": set(), "dominant_negative": set()}
    for c in (enr or {}).get("pubmed", {}).get("claims", []):
        if c["kind"] == "variant_effect" and c["effect"] in lit:
            lit[c["effect"]].add(c["pmid"])
    lof += min(2, len(lit["loss_of_function"]))
    gof += min(3, len(lit["gain_of_function"]))
    if lof >= 2 and gof >= 2:
        direction = "mixed"
    elif gof >= 2:
        direction = "gain"
    elif lof >= 2:
        direction = "loss"
    else:
        direction = "unknown"
    return {"direction": direction, "label": EFFECT_LABEL[direction], "signals": signals,
            "literature": {k: sorted(v) for k, v in lit.items()},
            "dominant_negative": len(lit["dominant_negative"]) >= 2}


def shared_phenotypes(atlas, a, b):
    """Most specific phenotypes both diseases share, exact or through a common ancestor term."""
    ann_a = {x["hp"]: x for x in a["phenotypes"]}
    ann_b = {x["hp"]: x for x in b["phenotypes"]}
    prop_a = set().union(*(atlas.anc(h) for h in ann_a)) if ann_a else set()
    prop_b = set().union(*(atlas.anc(h) for h in ann_b)) if ann_b else set()
    common = prop_a & prop_b
    covered = set()
    for t in common:
        covered |= atlas.anc(t) - {t}
    out = []
    for t in sorted(common - covered, key=lambda t: -atlas.hpo[t]["ic"]):
        if atlas.hpo[t]["ic"] < 1.0:
            continue
        term = atlas.hpo[t]
        via_a = ann_a.get(t) or next(x for h, x in ann_a.items() if t in atlas.anc(h))
        via_b = ann_b.get(t) or next(x for h, x in ann_b.items() if t in atlas.anc(h))
        out.append({"hp": t, "name": term["name"], "lay": term["lay"], "ic": term["ic"], "n": term["n"],
                    "specificity": atlas.informative(t), "exact": t in ann_a and t in ann_b,
                    "a": atlas.pheno_view(via_a), "b": atlas.pheno_view(via_b),
                    "url": f"https://hpo.jax.org/browse/term/{t}"})
    return out, prop_a, prop_b


def distinct_phenotypes(atlas, d, other_prop, n=6):
    out = [atlas.pheno_view(x) for x in d["phenotypes"] if x["hp"] not in other_prop]
    return [p for p in out if p["specificity"] != "broad"][:n]


def people_overlap(ea, eb):
    pa = {p["key"]: p for p in ea["investigators"]}
    out = []
    for p in eb["investigators"]:
        if p["key"] in pa:
            q = pa[p["key"]]
            out.append({"name": q["name"], "affiliation": q["affiliation"] or p["affiliation"],
                        "a": {"papers": q["papers"][:3], "trials": q["trials"], "grants": q["grants"]},
                        "b": {"papers": p["papers"][:3], "trials": p["trials"], "grants": p["grants"]},
                        "score": q["score"] + p["score"]})
    return sorted(out, key=lambda p: -p["score"])[:8]


def sponsor_overlap(ea, eb):
    def names(e):
        out = {}
        for s in e["trials"]["studies"]:
            if s["specific"]:
                for nm in [s["sponsor"]] + s["collaborators"]:
                    out.setdefault(nm, s["nct"])
        return out
    na, nb = names(ea), names(eb)
    return [{"name": k, "a": na[k], "b": nb[k]} for k in na if k in nb and k][:8]


def connection(atlas, aid, bid, audience="maria"):
    a, b = atlas.diseases[aid], atlas.diseases[bid]
    with ThreadPoolExecutor(3) as ex:
        fa, fb = ex.submit(enrich.enrich, a), ex.submit(enrich.enrich, b)
        fc = ex.submit(lambda: enrich.comention(a, b))
        ea, eb = fa.result(), fb.result()
        try:
            co = fc.result()
        except Exception:
            co = None

    shared_ph, prop_a, prop_b = shared_phenotypes(atlas, a, b)
    shared_pa = [atlas.pathways[p] for p in atlas.shared_pathway_ids(a, b)]
    same_gene = sorted(set(a["genes"]) & set(b["genes"]))
    nb = next((n for n in a["neighbors"] if n["id"] == bid), None) or next((n for n in b["neighbors"] if n["id"] == aid), None)
    eff_a, eff_b = effect_profile(atlas, a, ea), effect_profile(atlas, b, eb)
    informative = [p for p in shared_ph if p["specificity"] == "informative"]

    # ---- evidence ledger: every statement in the UI points at one of these
    evidence = []

    def ev(relation, text, source, url, kind, confidence, date=""):
        evidence.append({"id": f"E{len(evidence) + 1}", "relation": relation, "text": text, "source": source,
                         "url": url, "kind": kind, "confidence": round(confidence, 2), "date": date})
        return evidence[-1]["id"]

    path = {"a_gene": [], "b_gene": [], "pathways": [], "phenotypes": []}
    for d, key in ((a, "a_gene"), (b, "b_gene")):
        omim = next((x for x in d["xrefs"] if x.startswith("OMIM:")), None)
        for s in d["genes"]:
            path[key].append({"gene": s, "e": ev(
                "gene causes disease", f"Pathogenic variants in {s} cause {d['name']}", "OMIM gene–disease map (via HPO)",
                f"https://omim.org/entry/{omim.split(':')[1]}" if omim else "", "observed", 0.9, atlas.meta["sources"][0]["version"])})
    for p in shared_pa[:5]:
        ga = [s for s in a["genes"] if any(pid == p["id"] for pid, _ in atlas.genes[s]["pathways"])]
        gb = [s for s in b["genes"] if any(pid == p["id"] for pid, _ in atlas.genes[s]["pathways"])]
        evs = {e for s in ga + gb for pid, e in atlas.genes[s]["pathways"] if pid == p["id"]}
        path["pathways"].append({**p, "genes_a": ga, "genes_b": gb, "e": ev(
            "genes take part in the same pathway",
            f"{', '.join(ga)} and {', '.join(gb)} both take part in “{p['name']}” ({p['n_genes']} genes in the pathway)",
            "Reactome", p["url"], "observed", 0.9 if "TAS" in evs else 0.6, atlas.meta["built"])})
    for p in shared_ph[:10]:
        refs = (p["a"]["refs"][:1] + p["b"]["refs"][:1])
        p["e"] = ev("diseases share a symptom",
                    f"Both show {p['name'].lower()}" + ("" if p["exact"] else f" ({a['name']}: {p['a']['name']}; {b['name']}: {p['b']['name']})")
                    + f" — seen in {p['n']} of {atlas.background} annotated diseases",
                    "HPO annotations " + " / ".join(refs), p["url"], "observed",
                    min(p["a"]["confidence"], p["b"]["confidence"]), max(p["a"]["date"], p["b"]["date"]))
        path["phenotypes"].append(p["hp"])
    link_e = ev("inferred mechanistic similarity",
                f"Similarity score {nb['score'] if nb else 'below threshold'} "
                f"(phenotype {nb['pheno'] if nb else '–'}, pathway {nb['path'] if nb and nb['path'] is not None else 'n/a'}) "
                "computed by ConstellAI from the observations above; this is a hypothesis, not clinical proof",
                "ConstellAI graph analytics", "", "inferred", nb["score"] if nb else 0.1, atlas.meta["built"])
    for d, eff, tag in ((a, eff_a, "a"), (b, eff_b, "b")):
        eff["e"] = [ev(f"variant effect ({d['name']})", s["text"], s["source"], s["url"], s["kind"], s["confidence"], s["date"])
                    for s in eff["signals"]]

    # ---- contradictions and what must be checked
    contradictions, checks = [], []
    for d, eff, enr in ((a, eff_a, ea), (b, eff_b, eb)):
        if eff["direction"] == "mixed":
            claims = [c for c in enr["pubmed"]["claims"] if c["kind"] == "variant_effect"]
            contradictions.append({
                "title": f"{'/'.join(d['genes'])}: both loss- and gain-of-function variants are reported",
                "detail": "Papers disagree by variant, so families in one community may need opposite therapeutic strategies.",
                "quotes": [{"pmid": c["pmid"], "effect": c["effect"], "quote": c["quote"], "url": c["url"], "year": c["year"]}
                           for c in claims[:4]]})
    conflicts = [atlas.hpo[h]["name"] for h in a["excluded"] if h in prop_b] + [atlas.hpo[h]["name"] for h in b["excluded"] if h in prop_a]
    if conflicts:
        contradictions.append({"title": "A symptom of one disease is explicitly excluded in the other",
                               "detail": ", ".join(sorted(set(conflicts))[:6]), "quotes": []})
    if same_gene:
        checks.append({"level": "warn", "text": f"Same gene ({', '.join(same_gene)}) does not mean same mechanism. Confirm whether the "
                       "variants in each community reduce, abolish or alter the protein before sharing a therapeutic strategy."})
    if {eff_a["direction"], eff_b["direction"]} == {"loss", "gain"}:
        checks.append({"level": "stop", "text": f"Opposite variant effects: {a['name']} looks like {eff_a['label']}, {b['name']} like {eff_b['label']}. "
                       "Registries and natural-history tools can be shared; a therapy designed for one could harm the other."})
    elif "unknown" in (eff_a["direction"], eff_b["direction"]) or "mixed" in (eff_a["direction"], eff_b["direction"]):
        checks.append({"level": "warn", "text": f"Variant effect is {eff_a['label']} for {a['name']} and {eff_b['label']} for {b['name']}. "
                       "Ask a geneticist to confirm both act in the same direction on the shared pathway."})
    else:
        checks.append({"level": "ok", "text": f"Both diseases point to {eff_a['label']} — a shared therapeutic logic is plausible but unproven."})
    if set(a["inheritance"]) and set(b["inheritance"]) and not set(a["inheritance"]) & set(b["inheritance"]):
        checks.append({"level": "warn", "text": f"Inheritance differs ({', '.join(a['inheritance'])} vs {', '.join(b['inheritance'])}); "
                       "trial eligibility and genetic counselling will not transfer directly."})
    if a["onset"] and b["onset"] and not set(a["onset"]) & set(b["onset"]):
        checks.append({"level": "warn", "text": f"Age of onset differs ({', '.join(a['onset'][:2])} vs {', '.join(b['onset'][:2])}); "
                       "outcome measures validated in one age group may not fit the other."})
    if a["sparse"] or b["sparse"]:
        thin = a if a["sparse"] else b
        checks.append({"level": "warn", "text": f"{thin['name']} has only {len(thin['phenotypes'])} recorded symptoms, so the overlap is "
                       "measured on thin data. Deep phenotyping of a few patients would firm this up."})
    if not shared_pa:
        checks.append({"level": "warn", "text": "No shared curated pathway: the link rests on symptoms alone, which can arise from different causes."
                       if a["has_pathway"] and b["has_pathway"] else
                       "At least one gene has no curated Reactome pathway yet, so mechanistic overlap could not be tested."})
    only_a, only_b = distinct_phenotypes(atlas, a, prop_b), distinct_phenotypes(atlas, b, prop_a)
    if only_b:
        checks.append({"level": "info", "text": f"Symptoms recorded only in {b['name']}: {', '.join(p['name'] for p in only_b[:4])}. "
                       "Check whether a shared registry needs extra modules for them."})

    # ---- verdict
    if nb is None or nb["score"] < atlas.meta["params"]["min_score"]:
        grade, why = "unsupported", "The overlap is below the atlas threshold; treat this as an unsupported link."
    elif (shared_pa and len(informative) >= 2) or (nb["score"] >= 0.45 and len(informative) >= 3):
        grade, why = "viable", "Shared pathway and unusually informative shared symptoms." if shared_pa else "Several unusually informative shared symptoms."
    else:
        grade, why = "speculative", "Overlap rests mostly on broad symptoms or a single line of evidence."
    if a["sparse"] or b["sparse"]:
        grade = "speculative" if grade == "viable" else grade
    if co and not same_gene:
        if co["count"] == 0:
            novelty = "No PubMed paper mentions both together — a connection nobody has written down yet."
        elif co["count"] < 5:
            novelty = f"Only {co['count']} PubMed paper(s) mention both — a barely explored connection."
        else:
            novelty = f"{co['count']} PubMed papers already mention both — a recognised relationship you can build on."
    else:
        novelty = ""

    # ---- reusable assets and network overlap
    def assets(enr):
        specific = [s for s in enr["trials"]["studies"] if s["specific"]]
        models = {}
        for c in enr["pubmed"]["claims"]:
            if c["kind"] == "asset":
                models.setdefault(c["asset_type"], []).append(c)
        return {"reusable": [s for s in specific if s["kind"] in REUSABLE_KINDS],
                "interventional": [s for s in specific if s["type"] == "INTERVENTIONAL"],
                "literature": {k: v[:3] for k, v in models.items()},
                "grants": enr["grants"]["grants"][:6], "grant_count": enr["grants"]["count"],
                "organizations": enr["organizations"], "registries": enr["registries"]}
    assets_a, assets_b = assets(ea), assets(eb)
    people, sponsors = people_overlap(ea, eb), sponsor_overlap(ea, eb)
    reg_shared = [r for r in assets_a["registries"] if r.get("genes") and r in assets_b["registries"]]

    # ---- actions a group leader can take this week
    actions = []
    org_b = next((o for o in assets_b["organizations"] if o.get("source") == "curated"), None) or \
        (assets_b["organizations"][0] if assets_b["organizations"] else None)
    lead_b = eb["investigators"][0] if eb["investigators"] else None
    if org_b:
        actions.append({"who": org_b["name"], "url": org_b.get("url", ""),
                        "text": f"Write to {org_b['name']} with the sourced proposal below and ask for a 30-minute call "
                                "between the two scientific leads."})
    elif lead_b:
        actions.append({"who": lead_b["name"], "url": "",
                        "text": f"No patient group found for {b['name']}. Contact {lead_b['name']} ({lead_b['affiliation'][:80] or 'affiliation in PubMed'}), "
                                "the most active investigator, and ask who represents families."})
    else:
        actions.append({"who": "", "url": "", "text": f"No patient group or active investigator found for {b['name']}. "
                        "List both diseases in a cross-disease registry so future families can be linked."})
    reuse = (assets_b["reusable"] or assets_b["interventional"])[:1]
    if reuse:
        s = reuse[0]
        pi = s["officials"][0]["name"] if s["officials"] else s["sponsor"]
        actions.append({"who": pi, "url": s["url"],
                        "text": f"Ask {pi} for the protocol and outcome measures of {s['nct']} (“{s['title']}”, {s['kind'].lower()}, "
                                f"{s['status'].replace('_', ' ').lower()}"
                                + (f", n={s['enrollment']}" if s["enrollment"] else "") + ") and whether your families could use the same instruments."})
    if people:
        actions.append({"who": people[0]["name"], "url": "",
                        "text": f"{people[0]['name']} already appears in both communities' research — ask them to introduce the two groups "
                                "(name-level match: verify it is the same person)."})
    if reg_shared:
        actions.append({"who": reg_shared[0]["name"], "url": reg_shared[0]["url"],
                        "text": f"Both genes are covered by {reg_shared[0]['name']}: ask for a combined data request rather than building a new registry."})
    elif not assets_a["reusable"]:
        r = ea["registries"][-3] if len(ea["registries"]) >= 3 else None
        if r:
            actions.append({"who": r["name"], "url": r["url"],
                            "text": f"No registry or natural-history study found for {a['name']}. {r['name']} accepts any rare disease — "
                                    "start collecting the shared symptoms there so the data are comparable."})
    question = (f"Do variants in {'/'.join(a['genes'])} and {'/'.join(b['genes'])} change “{shared_pa[0]['name']}” in the same direction?"
                if shared_pa else
                f"Is there a common cause behind {', '.join(p['name'].lower() for p in (informative or shared_ph)[:3])} in both diseases?")
    models_b = assets_b["literature"].get("animal_model") or assets_b["literature"].get("cell_model")
    experiment = {"question": question,
                  "design": (f"Measure the same pathway readout side by side in a {'/'.join(a['genes'])} and a {'/'.join(b['genes'])} model"
                             if shared_pa else "Run a standardised deep-phenotyping (HPO) survey in both communities and compare")
                            + (f"; a model for {'/'.join(b['genes'])} is already reported (PMID {models_b[0]['pmid']})." if models_b else "."),
                  "decides": "A matching readout justifies shared assays, a shared natural-history protocol and joint outreach to therapy developers; "
                             "a mismatch tells both groups to share infrastructure only."}

    context = {
        "disease_a": a["name"], "genes_a": a["genes"], "disease_b": b["name"], "genes_b": b["genes"],
        "verdict": grade, "novelty": novelty, "evidence": [{k: e[k] for k in ("id", "relation", "text", "kind", "source")} for e in evidence],
        "checks": [c["text"] for c in checks], "contradictions": [c["title"] for c in contradictions],
    }
    narrative = llm.explain(context, [e["id"] for e in evidence], audience) if llm.available() else None
    if narrative is None:
        narrative = template_narrative(a, b, path, shared_ph, informative, link_e, checks, grade)

    out = {
        "a": atlas.card(aid), "b": atlas.card(bid), "score": nb, "same_gene": same_gene,
        "verdict": {"grade": grade, "why": why, "novelty": novelty},
        "path": path, "shared_phenotypes": shared_ph[:14], "shared_pathways": shared_pa[:6],
        "only_a": only_a, "only_b": only_b,
        "effects": {"a": eff_a, "b": eff_b}, "contradictions": contradictions, "checks": checks,
        "comention": co, "people": people, "sponsors": sponsors,
        "assets_a": assets_a, "assets_b": assets_b, "actions": actions, "experiment": experiment,
        "evidence": evidence, "narrative": narrative, "narrative_by": "openai" if llm.available() and narrative else "template",
        "coverage": coverage(atlas, ea, eb),
    }
    out["brief"] = brief(atlas, a, b, out)
    return out


def template_narrative(a, b, path, shared_ph, informative, link_e, checks, grade):
    ga, gb = "/".join(a["genes"]), "/".join(b["genes"])
    parts = [f"{a['name']} is caused by changes in {ga} [{path['a_gene'][0]['e']}], and {b['name']} by changes in {gb} [{path['b_gene'][0]['e']}]."]
    if path["pathways"]:
        p = path["pathways"][0]
        parts.append(f"Both genes work in the same cellular process, “{p['name']}” [{p['e']}].")
    if shared_ph:
        top = (informative or shared_ph)[:3]
        cites = "".join(f"[{p['e']}]" for p in top if "e" in p)
        parts.append(f"Patients in both groups show {', '.join(p['name'].lower() for p in top)} {cites}"
                     + (" — symptoms rare enough to be a meaningful signal." if informative else " — common symptoms, so weak evidence on their own."))
    second = (f"Putting these observations together, the atlas infers a {grade} link [{link_e}]. "
              "That inference is a hypothesis: it has not been tested in patients.")
    third = "Before joining forces: " + " ".join(c["text"] for c in checks if c["level"] in ("stop", "warn"))[:420]
    return "\n\n".join([" ".join(parts), second, third])


def coverage(atlas, ea, eb):
    return {"searched": [
        f"{atlas.meta['counts']['diseases']} monogenic diseases compared on {atlas.meta['counts']['phenotype_annotations']:,} HPO annotations (release {atlas.meta['sources'][0]['version']})",
        f"{atlas.meta['counts']['pathways']} Reactome pathways for {atlas.meta['counts']['genes']} genes",
        f"PubMed: “{ea['pubmed']['query']}” ({ea['pubmed']['count']} papers) and “{eb['pubmed']['query']}” ({eb['pubmed']['count']})",
        f"ClinicalTrials.gov: {ea['trials']['count']} and {eb['trials']['count']} studies",
        f"NIH RePORTER {'/'.join(str(y) for y in ea['grants'].get('years', []))}: {ea['grants']['count']} and {eb['grants']['count']} projects",
    ], "fetched": ea["fetched"], "errors": ea["errors"] + eb["errors"]}


def brief(atlas, a, b, c):
    """A sourced collaboration proposal the group leader can send as-is."""
    ga, gb = "/".join(a["genes"]), "/".join(b["genes"])
    L = [f"# Proposal: shared research between the {a['name']} and {b['name']} communities", "",
         f"*Prepared with ConstellAI on {enrich.today()}. Every statement below links to its source; items marked "
         "“inferred” are hypotheses to be reviewed by a scientific advisor.*", "",
         "## Why we are writing",
         f"Our community is affected by **{a['name']}** ({ga}). The rare-disease atlas indicates a **{c['verdict']['grade']}** "
         f"connection to **{b['name']}** ({gb}). {c['verdict']['novelty']}", "", "## The evidence"]
    for p in c["path"]["pathways"][:3]:
        L.append(f"- **Shared pathway (observed):** {', '.join(p['genes_a'])} and {', '.join(p['genes_b'])} both take part in "
                 f"“{p['name']}” — Reactome {p['id']}, {p['url']}")
    for p in c["shared_phenotypes"][:6]:
        refs = ", ".join(dict.fromkeys(p["a"]["refs"][:1] + p["b"]["refs"][:1]))
        L.append(f"- **Shared symptom (observed):** {p['name']} ({p['hp']}; {p['n']} of {atlas.background} diseases) — {refs}")
    if c["score"]:
        L.append(f"- **Overall similarity (inferred):** {c['score']['score']} on a 0–1 scale (phenotype {c['score']['pheno']}, "
                 f"pathway {c['score']['path'] if c['score']['path'] is not None else 'n/a'}).")
    if c["comention"]:
        L.append(f"- **Existing literature:** {c['comention']['count']} PubMed paper(s) mention both — {c['comention']['url']}")
    L += ["", "## What already exists that we could share"]
    listed = False
    for label, assets in ((b["name"], c["assets_b"]), (a["name"], c["assets_a"])):
        for s in (assets["reusable"] + assets["interventional"])[:4]:
            listed = True
            L.append(f"- {label}: {s['kind']} **{s['nct']}** — {s['title']} ({s['status'].replace('_', ' ').lower()}"
                     f"{', n=' + str(s['enrollment']) if s['enrollment'] else ''}; sponsor {s['sponsor']}) {s['url']}")
        for g in assets["grants"][:2]:
            listed = True
            L.append(f"- {label}: NIH project {g['num']} — {g['title']} ({g['org']}, FY{g['year']}) {g['url']}")
    if not listed:
        L.append("- No registry, natural-history study or funded project was found for either disease. Building one together avoids duplicating it.")
    if c["people"]:
        L += ["", "## People who already bridge both communities (name-level match, to be verified)"]
        L += [f"- {p['name']} — {p['affiliation'][:100]}" for p in c["people"][:4]]
    L += ["", "## What must be checked before we join forces"]
    L += [f"- {x['text']}" for x in c["checks"]]
    L += [f"- Contradictory evidence: {x['title']}. {x['detail']}" for x in c["contradictions"]]
    L += ["", "## Proposed first step",
          f"**Question:** {c['experiment']['question']}", "", f"**How:** {c['experiment']['design']}", "",
          f"**What it decides:** {c['experiment']['decides']}", "",
          "## What we ask of you",
          "A 30-minute call between our scientific leads to review this evidence, and — if it holds — agreement to share "
          "protocols, outcome measures and registry structure rather than build them twice.", "",
          "---", "*ConstellAI connects public data (HPO, MONDO, OMIM, Reactome, ClinGen, ClinVar, PubMed, ClinicalTrials.gov, "
          "NIH RePORTER). It does not give medical advice and does not claim that any treatment exists or will work.*"]
    return "\n".join(L)

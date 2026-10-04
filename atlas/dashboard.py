"""Maria's dashboard: a typed knowledge graph around the focus disease, plus the search ledger.

Nodes are diseases, genes, variants, mechanisms, symptoms, patient groups, papers,
studies and research assets. Every edge carries a plain-language relation, an
evidence level and its source:

    observed    a database record, registry entry or published statement
    inferred    computed by ConstellAI from observed data
    hypothesis  proposed by the team's curation, not confirmed by a source we query
    nodata      we searched and found nothing
"""
import json
import time
from collections import Counter

from . import enrich, trials
from .config import CURATED
from .sources import EVIDENCE_LABEL

N_NEIGHBORS = 5
N_SYMPTOMS = 8
N_PATHWAYS = 3
_cache = {}


def seed():
    return json.loads((CURATED / "stxbp1_seed.json").read_text())


def build(atlas, did, force=False):
    if not force and did in _cache and time.time() - _cache[did][0] < 1800:
        return _cache[did][1]
    out = _build(atlas, did)
    _cache[did] = (time.time(), out)
    return out


def _build(atlas, did):
    d = atlas.diseases[did]
    gene = d["genes"][0]
    sd = seed()
    enr = enrich.enrich(d)
    studies = trials.all_studies(gene, sd["studies"])
    hpoa = atlas.meta["sources"][0]["version"]
    nodes, edges = {}, []

    def node(nid, typ, label, **kw):
        nodes.setdefault(nid, {"id": nid, "type": typ, "label": label, **kw})
        return nid

    def edge(s, t, relation, level, text, source, url="", date="", contradiction=""):
        edges.append({"id": f"e{len(edges) + 1}", "source": s, "target": t, "relation": relation, "level": level,
                      "text": text, "evidence_source": source, "url": url, "date": date, "contradiction": contradiction})

    def gene_node(sym, **kw):
        return node(f"g:{sym}", "gene", sym, url=f"https://www.ncbi.nlm.nih.gov/gene/?term={sym}%5Bsym%5D+AND+human%5Borgn%5D", **kw)

    def disease_edge(sym, x):
        omim = next((r for r in x["xrefs"] if r.startswith("OMIM:")), None)
        edge(f"g:{sym}", f"d:{x['id']}" if x["id"] != did else "d:focus", "causes", "observed",
             f"Pathogenic variants in {sym} cause {x['name']}.", "OMIM gene–disease map (via HPO)",
             f"https://omim.org/entry/{omim.split(':')[1]}" if omim else "", hpoa)

    # ---- the focus disease and its gene
    node("d:focus", "disease", f"{gene}-related disorder", sub=d["name"], focus=True,
         detail=d["def"], url=f"https://monarchinitiative.org/{did}")
    gene_node(gene)
    disease_edge(gene, d)

    # ---- variants and how they act
    cv = next((v for v in enr["clinvar"] if v["gene"] == gene), None)
    cg = atlas.genes[gene]["clingen"]
    if cg and cg["haploinsufficiency"].startswith("Sufficient"):
        node("m:haploinsufficiency", "mechanism", "Haploinsufficiency",
             detail="One working copy of the gene does not make enough protein.")
        edge(f"g:{gene}", "m:haploinsufficiency", "acts through", "observed",
             f"ClinGen: sufficient evidence that losing one copy of {gene} causes disease.",
             "ClinGen dosage sensitivity", cg["url"], cg["date"])
    if cv:
        node("v:truncating", "variant", f"Truncating variants · {cv['truncating']}",
             detail="Nonsense, frameshift and splice-site variants classified pathogenic or likely pathogenic.")
        node("v:missense", "variant", f"Missense variants · {cv['missense']}",
             detail="Single amino-acid changes classified pathogenic or likely pathogenic.")
        for v, n in (("v:truncating", cv["truncating"]), ("v:missense", cv["missense"])):
            edge(v, f"g:{gene}", "found in", "observed", f"{n} pathogenic or likely pathogenic variants of this kind in {gene}.",
                 "ClinVar", cv["url"], enr["fetched"])
        if "m:haploinsufficiency" in nodes:
            edge("v:truncating", "m:haploinsufficiency", "leads to", "inferred",
                 "Truncating variants usually stop the protein being made, which fits haploinsufficiency.",
                 "ConstellAI, from ClinVar and ClinGen", "", enr["fetched"])
    claims = [c for c in enr["pubmed"]["claims"] if c["kind"] == "variant_effect"]
    dn = [c for c in claims if c["effect"] == "dominant_negative"]
    if dn or any(p["supports"] == "m:dominant_negative" for p in sd["papers"]):
        node("m:dominant_negative", "mechanism", "Dominant-negative effect",
             detail="Some altered proteins interfere with the healthy copy instead of simply being absent.")
        edge("v:missense" if cv else f"g:{gene}", "m:dominant_negative", "can lead to", "observed" if dn else "hypothesis",
             (f"“{dn[0]['quote']}”" if dn else "Reported for some variants in the literature curated by the team."),
             f"PubMed {dn[0]['pmid']} ({dn[0]['year']})" if dn else "Team curation", dn[0]["url"] if dn else "",
             dn[0]["year"] if dn else sd["verified"],
             contradiction="Same gene, two mechanisms: a therapy that raises protein levels may not suit dominant-negative variants.")

    # ---- neighbouring diseases: closest by similarity, plus the curated release-machinery genes
    chosen = {}
    for nb in d["neighbors"]:
        if len(chosen) < N_NEIGHBORS and not nb["same_gene"]:
            chosen[nb["id"]] = nb
    by_id = {nb["id"]: nb for nb in d["neighbors"]}
    snare_missing = []
    for sym in sd["snare_genes"]:
        if sym not in atlas.genes:
            snare_missing.append(sym)
            continue
        ids = atlas.genes[sym]["diseases"]
        best = max(ids, key=lambda i: by_id.get(i, {}).get("score", 0))
        chosen.setdefault(best, by_id.get(best))
    for oid, nb in chosen.items():
        o = atlas.diseases[oid]
        node(f"d:{oid}", "disease", o["name"], sub=", ".join(o["genes"]), atlas_id=oid,
             detail=o["def"], inheritance=o["inheritance"])
        for sym in o["genes"][:1]:
            gene_node(sym)
            disease_edge(sym, o)
        if nb:
            shared = atlas.shared_pathway_ids(d, o)
            why = (f"shares the pathway “{atlas.pathways[shared[0]]['name']}” and overlapping symptoms" if shared
                   else "overlapping symptoms; no shared curated pathway")
            contra = ""
            if d["inheritance"] and o["inheritance"] and not set(d["inheritance"]) & set(o["inheritance"]):
                contra = (f"Inheritance differs: {', '.join(o['inheritance'])} here vs {', '.join(d['inheritance'])} for {gene}. "
                          "Eligibility and trial design will not transfer directly.")
            edge("d:focus", f"d:{oid}", "resembles", "inferred",
                 f"Similarity {nb['score']} (symptoms {nb['pheno']}, pathway {nb['path'] if nb['path'] is not None else 'n/a'}): {why}. "
                 "A hypothesis to validate, not proof.", "ConstellAI graph analytics", "", atlas.meta["built"], contra)

    # ---- mechanisms: curated SNARE node plus the Reactome pathways most shared with neighbours
    neighbour_genes = [atlas.diseases[i]["genes"][0] for i in chosen]
    own = {p for p, _ in atlas.genes[gene]["pathways"]}
    usage = Counter(p for s in neighbour_genes for p, _ in atlas.genes[s]["pathways"] if p in own)
    for pid, _ in sorted(usage.items(), key=lambda kv: (-kv[1], -atlas.pathways[kv[0]]["ic"]))[:N_PATHWAYS]:
        p = atlas.pathways[pid]
        node(f"m:{pid}", "mechanism", p["name"], url=p["url"], detail=f"Reactome pathway with {p['n_genes']} genes.")
        for sym in [gene] + neighbour_genes:
            if any(x == pid for x, _ in atlas.genes[sym]["pathways"]):
                edge(f"g:{sym}", f"m:{pid}", "takes part in", "observed",
                     f"{sym} is annotated to “{p['name']}”.", "Reactome", p["url"], atlas.meta["built"])
    review = next((p for p in sd["papers"] if p["supports"] == "m:snare"), None)
    if review:
        node("m:snare", "mechanism", "SNARE-mediated vesicle fusion",
             detail="The machinery that releases neurotransmitter at the synapse.")
        edge(f"g:{gene}", "m:snare", "takes part in", "observed", review["claim"],
             f"{review['label']}, {review['journal']} (PMID {review['pmid']})", review["url"], review["year"])
        for sym in sd["snare_genes"]:
            if sym in atlas.genes:
                confirmed = bool(own & {p for p, _ in atlas.genes[sym]["pathways"]})
                edge(f"g:{sym}", "m:snare", "takes part in", "observed" if confirmed else "hypothesis",
                     (f"{sym} shares a Reactome release pathway with {gene}, consistent with the review."
                      if confirmed else f"{sym} is on the team's curated list of release-machinery genes; no shared Reactome pathway with {gene} confirms it."),
                     "Reactome + team curation" if confirmed else "Team curation (from the SNAREopathies review)",
                     review["url"], review["year"] if not confirmed else atlas.meta["built"])
        for sym in snare_missing:
            gene_node(sym, gap=True, detail="No monogenic disease with recorded symptoms for this gene in the atlas sources.")
            edge(f"g:{sym}", "m:snare", "may take part in", "nodata",
                 f"{sym} is on the team's curated list, but the atlas sources hold no disease record for it.",
                 "HPO annotations and OMIM gene map searched", "", hpoa)

    # ---- symptoms, with frequency and reference, and which neighbours share them
    views = [atlas.pheno_view(a) for a in d["phenotypes"]]
    def shared_by(v):
        return sum(any(v["hp"] in atlas.anc(x["hp"]) for x in atlas.diseases[oid]["phenotypes"]) for oid in chosen)

    # prefer distinctive symptoms that neighbours also show: those are the ones that tie the graph together
    top = sorted((v for v in views if v["specificity"] != "broad"), key=lambda v: (-shared_by(v), -v["ic"]))[:N_SYMPTOMS]
    for v in top:
        node(f"s:{v['hp']}", "symptom", v["name"], url=v["url"],
             detail=f"Seen in {v['n']} of {atlas.background} annotated diseases.")
        freq = f" Frequency {v['freq_raw']}." if v["freq_raw"] and not v["freq_raw"].startswith("HP:") else (
            f" Frequency about {round(v['freq'] * 100)}%." if v["freq"] is not None else "")
        edge("d:focus", f"s:{v['hp']}", "patients show", "observed",
             f"{v['name']} is recorded for this disease.{freq} Evidence: {EVIDENCE_LABEL.get(v['ev'], v['ev'])}.",
             "HPO annotations · " + ", ".join(v["refs"][:2]), v["url"], v["date"])
        for oid in chosen:
            o = atlas.diseases[oid]
            hit = next((a for a in o["phenotypes"] if v["hp"] in atlas.anc(a["hp"])), None)
            if hit:
                edge(f"d:{oid}", f"s:{v['hp']}", "patients show", "observed",
                     f"{atlas.hpo[hit['hp']]['name']} is recorded for {o['name']}.",
                     "HPO annotations · " + ", ".join(hit["refs"][:2]), v["url"], hit["date"])

    # ---- patient groups, for the focus disease and its neighbours
    for o in enr["organizations"]:
        gid = node(f"p:{o['name']}", "group", o["name"], url=o.get("url", ""))
        curated = o.get("source") == "curated"
        edge(gid, "d:focus", "serves", "observed",
             (f"Listed for {gene} in the curated patient-organisation list; website reachable." if curated
              else f"Sponsor or collaborator of {o.get('via', 'a registered study')}."),
             "Curated list, website checked" if curated else "ClinicalTrials.gov", o.get("url", ""),
             o.get("verified", enr["fetched"]))
    for oid in chosen:
        o = atlas.diseases[oid]
        own_groups = [m for m in enrich.match_orgs(o) if m["scope"] == "gene"]
        for m in own_groups[:1]:
            gid = node(f"p:{m['name']}", "group", m["name"], url=m["url"])
            edge(gid, f"d:{oid}", "serves", "observed", f"Listed for {', '.join(o['genes'])} in the curated patient-organisation list.",
                 "Curated list, website checked", m["url"], m["verified"])
        if not own_groups and oid in list(chosen)[:2]:
            gid = node(f"p:none:{oid}", "group", "No group found", gap=True,
                       detail="This does not mean none exists: only the sources listed were searched.")
            edge(gid, f"d:{oid}", "searched for", "nodata",
                 f"No dedicated patient group for {', '.join(o['genes'])} in the sources we searched.",
                 f"{len(enrich.curated()['organizations'])} curated organisations", "", enrich.curated()["verified"])

    # ---- studies (trials) and research assets (registries, natural-history studies, models)
    group_ids = {n["label"]: nid for nid, n in nodes.items() if n["type"] == "group"}
    for t in studies:
        is_asset = t["type"] != "INTERVENTIONAL"
        if is_asset and gene.lower() not in (t["title"] + " ".join(t["conditions"])).lower() and t["nct"] not in sd["studies"]:
            continue  # broad registries that only mention the gene in passing stay in the trials list
        nid = node(f"t:{t['nct']}", "asset" if is_asset else "study", t["title"], sub=t["nct"], url=t["url"],
                   status=t["status"], flags=t["flags"], updated=t["updated"], kind=t["kind"],
                   enrollment=t["enrollment"], enrollment_type=t["enrollment_type"], sponsor=t["sponsor"])
        state = t["status"].replace("_", " ").lower()
        edge(nid, "d:focus", "is a registry or natural-history study for" if is_asset else "tests a treatment in", "observed",
             f"{t['kind']}, registered as {state}; last updated {t['updated']}; "
             f"{t['enrollment'] if t['enrollment'] is not None else '?'} participants ({t['enrollment_type'].lower() or 'not stated'}).",
             "ClinicalTrials.gov", t["url"], t["updated"], contradiction=" · ".join(t["flags"]))
        if t["sponsor"] in group_ids:
            edge(group_ids[t["sponsor"]], nid, "sponsors", "observed", f"{t['sponsor']} is the lead sponsor.",
                 "ClinicalTrials.gov", t["url"], t["updated"])
    assets = {}
    for c in enr["pubmed"]["claims"]:
        if c["kind"] == "asset" and c["asset_type"] in ("animal_model", "cell_model", "biomarker"):
            assets.setdefault(c["asset_type"], c)
    labels = {"animal_model": ("a:mouse", "Animal model"), "cell_model": ("a:cell", "Cell model"), "biomarker": ("a:biomarker", "Biomarker")}
    for typ, c in assets.items():
        nid = node(labels[typ][0], "asset", labels[typ][1], detail="Reported in the literature read for this gene.")
        edge(nid, f"g:{gene}", "models" if "model" in typ else "measures", "observed", f"“{c['quote']}”",
             f"PubMed {c['pmid']} ({c['year']})", c["url"], c["year"])
    for r in enr["registries"][:2]:
        nid = node(f"a:{r['name']}", "asset", r["name"], url=r["url"], detail=r["what"])
        edge(nid, "d:focus", "is open to", "observed", r["what"], "Curated list, website checked", r["url"],
             enrich.curated()["verified"])

    # ---- papers: the team's verified seed, attached to what each supports
    for p in sd["papers"]:
        target = p["supports"]
        if target == "a:mouse":
            node("a:mouse", "asset", "Animal model", detail="Reported in the literature read for this gene.")
        if target not in nodes:
            continue
        nid = node(f"r:{p['pmid']}", "paper", p["label"], sub=f"{p['journal']} {p['year']}", url=p["url"], detail=p["title"])
        edge(nid, target, p["relation"], "observed", p["claim"],
             f"{p['label']}, {p['journal']} (PMID {p['pmid']}; summary by the team, PMID verified)", p["url"], p["year"])

    # ---- what we searched
    drug_named = [t for t in studies if t["type"] == "INTERVENTIONAL" and t["status"] in
                  ("RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION") and gene.lower() in (t["title"] + " ".join(t["conditions"])).lower()]
    ledger = [
        {"what": f"Studies mentioning {gene}, any status", "where": "ClinicalTrials.gov", "found": len(studies), "date": studies[0]["updated"] if studies else "", "url": f"https://clinicaltrials.gov/search?term={gene}"},
        {"what": f"Open treatment trials that name {gene}", "where": "ClinicalTrials.gov", "found": len(drug_named), "date": enr["fetched"], "url": f"https://clinicaltrials.gov/search?term={gene}&aggFilters=status:rec%20not"},
        {"what": f"Papers with {gene} in title or abstract", "where": "PubMed", "found": enr["pubmed"]["count"], "date": enr["fetched"], "url": enr["pubmed"]["url"]},
        {"what": f"NIH projects mentioning {gene}, {'–'.join(str(y) for y in enr['grants'].get('years', [])[::2])}", "where": "NIH RePORTER", "found": enr["grants"]["count"], "date": enr["fetched"], "url": "https://reporter.nih.gov"},
        {"what": f"Pathogenic or likely pathogenic {gene} variants", "where": "ClinVar", "found": cv["total"] if cv else 0, "date": enr["fetched"], "url": cv["url"] if cv else ""},
        {"what": f"Patient groups for {gene}", "where": f"{len(enrich.curated()['organizations'])} curated organisations and trial sponsors", "found": len(enr["organizations"]), "date": enrich.curated()["verified"], "url": ""},
    ]
    for oid in list(chosen)[:1]:
        o = atlas.diseases[oid]
        try:
            eo = enrich.enrich(o)
            g2 = ", ".join(o["genes"])
            ledger += [
                {"what": f"Registered studies for {g2} (closest disease)", "where": "ClinicalTrials.gov", "found": eo["trials"]["count"], "date": eo["fetched"], "url": eo["trials"]["url"]},
                {"what": f"NIH projects mentioning {g2}", "where": "NIH RePORTER", "found": eo["grants"]["count"], "date": eo["fetched"], "url": "https://reporter.nih.gov"},
                {"what": f"Dedicated patient group for {g2}", "where": "curated organisations and trial sponsors", "found": sum(1 for x in eo["organizations"] if x.get("scope") == "gene" or x.get("source") != "curated"), "date": eo["fetched"], "url": ""},
                {"what": f"Papers with {g2} in title or abstract", "where": "PubMed", "found": eo["pubmed"]["count"], "date": eo["fetched"], "url": eo["pubmed"]["url"]},
            ]
        except Exception as e:  # the ledger still shows the focus-disease searches
            print(f"[dashboard] neighbour ledger failed: {e}")

    counts = Counter(n["type"] for n in nodes.values())
    return {"focus": did, "gene": gene, "nodes": list(nodes.values()), "edges": edges, "counts": counts,
            "levels": Counter(e["level"] for e in edges), "studies": studies, "ledger": ledger,
            "seed": {"verified": sd["verified"], "papers": len(sd["papers"]), "unresolved": sd["unresolved"]},
            "built": enr["fetched"]}

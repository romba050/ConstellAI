"""In-memory atlas: lookups, global search with synonym resolution, entity views."""
import gzip
import json
import re
from collections import defaultdict

from . import enrich, sources
from .config import ATLAS_FILE, CONTRIBUTIONS_FILE

INFORMATIVE_SHARE = 0.02   # a phenotype seen in <2% of annotated diseases is "unusually informative"
BROAD_SHARE = 0.10


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


class Atlas:
    def __init__(self):
        with gzip.open(ATLAS_FILE, "rt", encoding="utf-8") as f:
            data = json.load(f)
        self.meta, self.diseases, self.hpo = data["meta"], data["diseases"], data["hpo"]
        self.genes, self.pathways = data["genes"], data["pathways"]
        self.clusters, self.groups = data["clusters"], {g["id"]: g for g in data["groups"]}
        self.background = self.meta["counts"]["background_diseases"]
        self._anc = {}
        self.pheno_diseases = defaultdict(set)
        for d in self.diseases.values():
            for a in d["phenotypes"]:
                for t in self.anc(a["hp"]):
                    self.pheno_diseases[t].add(d["id"])
        self.pathway_diseases = defaultdict(set)
        for g in self.genes.values():
            for pid, _ in g["pathways"]:
                self.pathway_diseases[pid].update(g["diseases"])
        self.cluster_members = defaultdict(list)
        for d in self.diseases.values():
            self.cluster_members[d["cluster"]].append(d["id"])
        self._build_index()

    # ---------------------------------------------------------------- ontology helpers
    def anc(self, hp):
        if hp not in self._anc:
            out = {hp}
            for p in self.hpo.get(hp, {}).get("parents", []):
                out |= self.anc(p)
            self._anc[hp] = out
        return self._anc[hp]

    def informative(self, hp):
        share = self.hpo[hp]["n"] / self.background
        return "informative" if share < INFORMATIVE_SHARE else ("broad" if share > BROAD_SHARE else "moderate")

    def pheno_view(self, a):
        t = self.hpo[a["hp"]]
        return {**a, "name": t["name"], "lay": t["lay"], "ic": t["ic"], "n": t["n"],
                "specificity": self.informative(a["hp"]),
                "ev_label": sources.EVIDENCE_LABEL.get(a["ev"], a["ev"]),
                "confidence": sources.EVIDENCE_CONFIDENCE.get(a["ev"], 0.5),
                "url": f"https://hpo.jax.org/browse/term/{a['hp']}"}

    # ---------------------------------------------------------------- views
    def card(self, did):
        d = self.diseases[did]
        return {"id": did, "name": d["name"], "genes": d["genes"], "cluster": d["cluster"], "group": d["group"],
                "sparse": d["sparse"]}

    def grade(self, d, nb):
        """Cheap triage of a similarity edge; the connection view refines it with live evidence."""
        other = self.diseases[nb["id"]]
        if d["sparse"] or other["sparse"]:
            return "thin"
        if nb["score"] >= 0.4 and ((nb["path"] or 0) >= 0.3 or nb["pheno"] >= 0.5):
            return "viable"
        return "speculative"

    def gene_view(self, symbol, exclude=None):
        g = self.genes[symbol]
        return {"symbol": symbol, "ncbi": g["ncbi"], "clingen": g["clingen"],
                "url": f"https://www.ncbi.nlm.nih.gov/gene/{g['ncbi']}",
                "pathways": [{**self.pathways[p], "ev": ev} for p, ev in g["pathways"]],
                "other_diseases": [self.card(x) for x in g["diseases"] if x != exclude]}

    def detail(self, did):
        d = self.diseases[did]
        c = self.clusters[d["cluster"]]
        neighbors = []
        for nb in d["neighbors"]:
            o = self.diseases[nb["id"]]
            shared = [self.pathways[p]["name"] for p in self.shared_pathway_ids(d, o)[:1]]
            neighbors.append({**self.card(nb["id"]), **nb, "grade": self.grade(d, nb),
                              "cross_group": o["group"] != d["group"], "shared_pathway": shared[0] if shared else None,
                              "orgs": [m["name"] for m in enrich.match_orgs(o) if m["scope"] == "gene"]})
        return {
            **{k: d[k] for k in ("id", "name", "synonyms", "xrefs", "def", "inheritance", "onset", "sparse",
                                 "has_pathway", "group", "x", "y")},
            "cluster": {**c, "phenotypes": [{**p, "name": self.hpo[p["hp"]]["name"]} for p in c["phenotypes"]],
                        "pathways": [{**p, "name": self.pathways[p["id"]]["name"]} for p in c["pathways"]]},
            "group_label": self.groups[d["group"]]["label"],
            "genes": [self.gene_view(s, did) for s in d["genes"]],
            "phenotypes": [self.pheno_view(a) for a in d["phenotypes"]],
            "excluded": [{"hp": h, "name": self.hpo[h]["name"]} for h in d["excluded"] if h in self.hpo],
            "neighbors": neighbors,
            "contributions": [c for c in load_contributions() if c["disease"] == did],
            "links": self.links(d),
        }

    def links(self, d):
        out = [{"label": d["id"], "url": f"https://monarchinitiative.org/{d['id']}"}] if d["id"].startswith("MONDO") else []
        for x in d["xrefs"]:
            db, code = x.split(":")
            if db == "OMIM":
                out.append({"label": x, "url": f"https://omim.org/entry/{code}"})
            elif db == "ORPHA":
                out.append({"label": x, "url": f"https://www.orpha.net/en/disease/detail/{code}"})
        return out

    def shared_pathway_ids(self, a, b):
        pa = {p for s in a["genes"] for p, _ in self.genes[s]["pathways"]}
        pb = {p for s in b["genes"] for p, _ in self.genes[s]["pathways"]}
        return sorted(pa & pb, key=lambda p: -self.pathways[p]["ic"])

    def map_points(self):
        return [[d["id"], d["name"], d["x"], d["y"], d["group"], d["cluster"], ",".join(d["genes"]),
                 len(d["neighbors"])] for d in self.diseases.values()]

    def map_edges(self):
        ids = {did: i for i, did in enumerate(self.diseases)}
        seen = set()
        for d in self.diseases.values():
            for nb in d["neighbors"][:4]:
                e = (min(ids[d["id"]], ids[nb["id"]]), max(ids[d["id"]], ids[nb["id"]]))
                seen.add(e)
        return sorted(seen)

    # ---------------------------------------------------------------- search
    def _build_index(self):
        idx = []  # (normalised text, type, id, label, matched synonym or None)
        for d in self.diseases.values():
            idx.append((norm(d["name"]), "disease", d["id"], d["name"], None))
            for s in d["synonyms"]:
                idx.append((norm(s), "disease", d["id"], d["name"], s))
            for x in [d["id"]] + d["xrefs"]:
                idx.append((norm(x), "disease", d["id"], d["name"], x))
        for s, g in self.genes.items():
            idx.append((norm(s), "gene", s, s, None))
        for hp, n in self.pheno_diseases.items():
            t = self.hpo[hp]
            idx.append((norm(t["name"]), "phenotype", hp, t["name"], None))
            for s in t["synonyms"]:
                idx.append((norm(s), "phenotype", hp, t["name"], s))
        for pid, p in self.pathways.items():
            idx.append((norm(p["name"]), "mechanism", pid, p["name"], None))
        for o in enrich.curated()["organizations"]:
            if o.get("reachable", True):
                idx.append((norm(o["name"]), "group", o["name"], o["name"], None))
        self.index = idx

    def search(self, q, limit=12):
        nq = norm(q)
        if not nq:
            return []
        type_rank = {"disease": 0, "gene": 0, "group": 1, "mechanism": 2, "phenotype": 2}
        best = {}
        words = nq.split()
        for text, typ, eid, label, syn in self.index:
            if text == nq:
                tier = 0
            elif text.startswith(nq):
                tier = 1
            elif (" " + nq) in (" " + text):
                tier = 2
            elif nq in text and len(nq) >= 3:
                tier = 3
            elif len(words) > 1 and all(w in text for w in words):
                tier = 4
            else:
                continue
            key = (typ, eid)
            score = (tier, type_rank[typ], len(text))
            if key not in best or score < best[key][0]:
                best[key] = (score, {"type": typ, "id": eid, "label": label, "matched": syn})
        hits = [h for _, h in sorted(best.values(), key=lambda x: x[0])[:limit]]
        for h in hits:
            if h["type"] == "gene":
                h["sub"] = f"{len(self.genes[h['id']]['diseases'])} disease(s)"
            elif h["type"] == "disease":
                h["sub"] = ", ".join(self.diseases[h["id"]]["genes"])
            elif h["type"] == "phenotype":
                h["sub"] = f"{len(self.pheno_diseases[h['id']])} diseases"
            elif h["type"] == "mechanism":
                h["sub"] = f"{len(self.pathway_diseases[h['id']])} diseases"
        return hits

    # ---------------------------------------------------------------- entity views (gene / phenotype / mechanism / group)
    def entity(self, typ, eid):
        if typ == "gene":
            ids = self.genes[eid]["diseases"]
            head = {"title": eid, "kind": "Gene", "gene": self.gene_view(eid),
                    "note": "A gene name is only the starting point: each disease below can follow a different variant effect."}
        elif typ == "phenotype":
            ids = self.pheno_diseases[eid]
            t = self.hpo[eid]
            head = {"title": t["name"], "kind": "Symptom (HPO)", "def": t["def"], "lay": t["lay"],
                    "specificity": self.informative(eid), "url": f"https://hpo.jax.org/browse/term/{eid}",
                    "note": f"Annotated in {t['n']} of {self.background} diseases with HPO annotations."}
        elif typ == "mechanism":
            ids = self.pathway_diseases[eid]
            p = self.pathways[eid]
            head = {"title": p["name"], "kind": "Mechanism (Reactome pathway)", "url": p["url"],
                    "note": f"{p['n_genes']} genes take part in this pathway; part of “{p['root']}”."}
        elif typ == "group":
            o = next(o for o in enrich.curated()["organizations"] if o["name"] == eid)
            ids = [d["id"] for d in self.diseases.values() if any(m["name"] == eid for m in enrich.match_orgs(d))]
            head = {"title": o["name"], "kind": "Patient organisation", "url": o["url"],
                    "note": f"Curated entry; website reachable on {enrich.curated()['verified']}."}
        else:
            raise KeyError(typ)
        by_cluster = defaultdict(list)
        for did in ids:
            by_cluster[self.diseases[did]["cluster"]].append(did)
        ranked = []
        for cid, members in by_cluster.items():
            c = self.clusters[cid]
            genes = sorted({g for m in members for g in self.diseases[m]["genes"]})
            orgs = sorted({o["name"] for m in members for o in enrich.match_orgs(self.diseases[m])})
            ranked.append({
                "cluster": cid, "label": c["label"], "sub": c["sub"], "group": c["group"], "size": c["size"],
                "matching": len(members), "share": round(len(members) / c["size"], 2),
                "diseases": [self.card(m) for m in members], "genes": genes,
                "haploinsufficient": [g for g in genes if (self.genes[g]["clingen"] or {}).get("haploinsufficiency", "").startswith("Sufficient")],
                "organizations": orgs,
            })
        ranked.sort(key=lambda r: (-r["matching"], -r["share"]))
        return {**head, "type": typ, "id": eid, "count": len(ids), "ids": sorted(ids), "clusters": ranked[:40]}


def load_contributions():
    if CONTRIBUTIONS_FILE.exists():
        return json.loads(CONTRIBUTIONS_FILE.read_text())
    return []

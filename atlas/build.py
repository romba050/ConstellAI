"""Graph builder: reconcile vocabularies, connect the evidence, cluster by mechanism.

    uv run python -m atlas.build            # download bulk sources if missing, then build
    uv run python -m atlas.build --refresh  # re-download sources first
"""
import datetime
import gzip
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict

import igraph as ig
import numpy as np
from scipy import sparse

from . import llm, sources
from .config import (ATLAS_FILE, KNN, MIN_SCORE, NO_PATHWAY_DISCOUNT,
                     PHENO_GATE, SPARSE_PHENOTYPES,
                     W_PATH, W_PHENO)

PHENO_ROOT = "HP:0000118"
N_GROUP_COLORS = 14


def display_name(name):
    return name[:1].upper() + name[1:] if name else name


def ic_cosine(M, ic):
    """IC-weighted cosine between all rows of a binary sparse matrix.

    Cosine rather than Jaccard so that a deeply phenotyped disease is not
    penalised against a sparsely annotated one.
    """
    W = M.multiply(ic.astype(np.float32)).tocsr()
    inter = (W @ M.T).toarray().astype(np.float32)
    s = np.asarray(W.sum(axis=1)).ravel()
    norm = np.sqrt(s[:, None] * s[None, :])
    with np.errstate(divide="ignore", invalid="ignore"):
        sim = np.where(norm > 0, inter / norm, 0).astype(np.float32)
    return sim


def reconcile():
    """Merge OMIM / Orphanet / DECIPHER records into stable MONDO disease nodes."""
    print("Reconciling vocabularies (MONDO, HPO, OMIM, Orphanet)")
    hpo, alt = sources.load_hpo()
    anc = sources.ancestors_fn(hpo)
    mondo, xmap = sources.load_mondo()
    hpoa, hpoa_version = sources.load_hpoa()

    def did(raw):
        return xmap.get(raw, raw)

    diseases = {}

    def node(raw, fallback_name=""):
        d = did(raw)
        if d not in diseases:
            m = mondo.get(d)
            diseases[d] = {
                "id": d,
                "name": display_name(m["name"] if m else fallback_name),
                "synonyms": list(m["synonyms"]) if m else [],
                "xrefs": list(m["xrefs"]) if m else [raw],
                "def": m["def"] if m else "",
                "genes": [], "pheno": {}, "excluded": set(),
                "inheritance": set(), "onset": set(),
            }
        return diseases[d]

    for r in hpoa:
        hp = alt.get(r["hpo_id"], r["hpo_id"])
        if hp not in hpo:
            continue
        d = node(r["database_id"], r["disease_name"])
        nm = r["disease_name"]
        if nm and nm.lower() != d["name"].lower() and nm not in d["synonyms"]:
            d["synonyms"].append(nm)
        if r["aspect"] == "I":
            d["inheritance"].add(hpo[hp]["name"])
        elif r["aspect"] == "C":
            if "onset" in hpo[hp]["name"].lower():
                d["onset"].add(hpo[hp]["name"])
        elif r["aspect"] == "P":
            freq = sources.parse_frequency(r["frequency"])
            if r["qualifier"] == "NOT" or freq == 0.0:
                d["excluded"].add(hp)
                continue
            m = re.search(r"\[(\d{4}-\d{2}-\d{2})\]", r["biocuration"])
            a = d["pheno"].setdefault(hp, {"hp": hp, "freq": None, "freq_raw": "", "refs": [],
                                           "ev": r["evidence"], "date": "", "src": []})
            if freq is not None and (a["freq"] is None or freq > a["freq"]):
                a["freq"], a["freq_raw"] = round(freq, 3), r["frequency"]
            for ref in r["reference"].split(";"):
                if ref and ref not in a["refs"] and len(a["refs"]) < 4:
                    a["refs"].append(ref)
            if sources.EVIDENCE_CONFIDENCE.get(r["evidence"], 0) > sources.EVIDENCE_CONFIDENCE.get(a["ev"], 0):
                a["ev"] = r["evidence"]
            if m and m.group(1) > a["date"]:
                a["date"] = m.group(1)
            if r["database_id"] not in a["src"]:
                a["src"].append(r["database_id"])

    gene_ncbi = {}
    for r in sources.load_gene_disease():
        d = did(r["disease_id"])
        if d in diseases and r["gene_symbol"] not in diseases[d]["genes"]:
            diseases[d]["genes"].append(r["gene_symbol"])
            gene_ncbi[r["gene_symbol"]] = r["ncbi_gene_id"].split(":")[1]
    return hpo, anc, diseases, gene_ncbi, hpoa_version


def top_terms(frac, ic, min_frac, n, is_ancestor=None):
    score = frac * ic
    score[frac < min_frac] = 0
    picked = []
    for j in np.argsort(-score):
        if score[j] <= 0 or len(picked) >= n:
            break
        if is_ancestor and any(is_ancestor(j, p) or is_ancestor(p, j) for p in picked):
            continue
        picked.append(int(j))
    return picked


def build():
    hpo, anc, all_diseases, gene_ncbi, hpoa_version = reconcile()
    pheno_terms = sorted(t for t in hpo if PHENO_ROOT in anc(t))
    tix = {t: i for i, t in enumerate(pheno_terms)}

    # --- information content over every annotated disease, monogenic or not
    with_pheno = [d for d in all_diseases.values() if d["pheno"]]
    rows, cols = [], []
    for i, d in enumerate(with_pheno):
        prop = set()
        for hp in d["pheno"]:
            prop |= anc(hp)
        d["_prop"] = [tix[t] for t in prop if t in tix]
        rows += [i] * len(d["_prop"])
        cols += d["_prop"]
    A_all = sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)),
                              shape=(len(with_pheno), len(pheno_terms)))
    df = np.asarray(A_all.sum(axis=0)).ravel()
    ic = np.where(df > 0, -np.log(np.maximum(df, 1) / len(with_pheno)), 0).astype(np.float32)

    # --- the atlas: monogenic diseases with at least one phenotype annotation
    keep = [i for i, d in enumerate(with_pheno) if 1 <= len(d["genes"]) <= 4]
    ds = [with_pheno[i] for i in keep]
    A = A_all[keep]
    n = len(ds)
    print(f"Atlas: {n} monogenic diseases, {len(gene_ncbi)} genes, "
          f"{sum(len(d['pheno']) for d in ds)} phenotype annotations")

    print("Phenotype similarity (IC-weighted over HPO)")
    S_ph = ic_cosine(A, ic)

    print("Pathway similarity (Reactome)")
    gene_paths, path_ev, path_names, path_roots = sources.load_reactome()
    n_reactome_genes = len(gene_paths)
    path_genes = Counter(p for ps in gene_paths.values() for p in ps)
    used_paths = sorted({p for d in ds for g in d["genes"] for p in gene_paths.get(gene_ncbi[g], ())})
    pix = {p: i for i, p in enumerate(used_paths)}
    ic_p = np.array([-math.log(path_genes[p] / n_reactome_genes) for p in used_paths], np.float32)
    rows, cols = [], []
    for i, d in enumerate(ds):
        ps = {pix[p] for g in d["genes"] for p in gene_paths.get(gene_ncbi[g], ())}
        rows += [i] * len(ps)
        cols += list(ps)
    P = sparse.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=(n, len(used_paths)))
    S_pa = ic_cosine(P, ic_p)
    has_path = np.asarray(P.sum(axis=1)).ravel() > 0
    both = has_path[:, None] & has_path[None, :]
    # A shared pathway only counts once the patients also look alike: this keeps
    # "same gene, different effect" diseases apart instead of merging them by name.
    gate = np.minimum(1, S_ph / PHENO_GATE)
    S = np.where(both, W_PHENO * S_ph + W_PATH * S_pa * gate, NO_PATHWAY_DISCOUNT * S_ph)
    np.fill_diagonal(S, 0)

    print("k-nearest-neighbour graph, Leiden clustering, layout")
    edges = {}
    order = np.argsort(-S, axis=1)[:, :KNN]
    neighbors = [[] for _ in range(n)]
    for i in range(n):
        for j in order[i]:
            if S[i, j] < MIN_SCORE:
                break
            j = int(j)
            neighbors[i].append(j)
            edges[(min(i, j), max(i, j))] = float(S[i, j])
    g = ig.Graph(n=n, edges=list(edges), edge_attrs={"weight": list(edges.values())})
    random.seed(7)
    coarse = g.community_leiden(objective_function="modularity", weights="weight",
                                resolution=0.6, n_iterations=20).membership
    group_sizes = Counter(coarse)
    # isolated stars and tiny components share one "unconnected" group
    group_rank = {c: r for r, (c, s) in enumerate(group_sizes.most_common()) if s >= 25}
    group_of = [group_rank.get(c, -1) for c in coarse]

    cluster_of = [None] * n
    for c in set(coarse):
        members = [i for i in range(n) if coarse[i] == c]
        if len(members) < 4:
            for i in members:
                cluster_of[i] = f"c{c}"
            continue
        sub = g.subgraph(members)
        fine = sub.community_leiden(objective_function="modularity", weights="weight",
                                    resolution=1.5, n_iterations=20).membership
        for i, f in zip(members, fine):
            cluster_of[i] = f"c{c}.{f}"

    # Layout: UMAP on the similarity matrix, so neighbours on the map are neighbours in the evidence.
    import umap
    dist = np.clip(1 - S, 0, 1).astype(np.float32)
    np.fill_diagonal(dist, 0)
    layout = umap.UMAP(n_neighbors=KNN, min_dist=0.3, spread=1.2, metric="precomputed",
                       random_state=7).fit_transform(dist)
    layout -= np.median(layout, axis=0)
    layout /= np.percentile(np.abs(layout), 99.5)
    layout = np.clip(layout, -1.05, 1.05)

    # --- label clusters by what their members disproportionately share
    def hp_is_ancestor(a, b):
        return pheno_terms[a] in anc(pheno_terms[b])

    def describe(members):
        frac_h = np.asarray(A[members].mean(axis=0)).ravel()
        frac_p = np.asarray(P[members].mean(axis=0)).ravel()
        small = len(members) < 3
        hps = top_terms(frac_h, ic, 0.0 if small else 0.5, 4, hp_is_ancestor)
        pas = top_terms(frac_p, ic_p, 0.0 if small else 0.3, 3)
        return ([{"hp": pheno_terms[j], "frac": round(float(frac_h[j]), 2)} for j in hps],
                [{"id": used_paths[j], "frac": round(float(frac_p[j]), 2)} for j in pas])

    clusters = {}
    by_cluster = defaultdict(list)
    for i, c in enumerate(cluster_of):
        by_cluster[c].append(i)
    for c, members in by_cluster.items():
        hps, pas = describe(members)
        label = path_names[pas[0]["id"]] if pas else (hpo[hps[0]["hp"]]["name"] if hps else "Unlabelled")
        sub = hpo[hps[0]["hp"]]["name"] if (pas and hps) else (hpo[hps[1]["hp"]]["name"] if len(hps) > 1 else "")
        clusters[c] = {"id": c, "label": label, "sub": sub, "group": group_of[members[0]],
                       "size": len(members), "phenotypes": hps, "pathways": pas}

    groups = []
    for c, rank in sorted(group_rank.items(), key=lambda kv: kv[1]):
        members = [i for i in range(n) if coarse[i] == c]
        hps, pas = describe(members)
        root_counts = Counter(path_roots.get(used_paths[j], "") for i in members for j in P[i].indices)
        root = root_counts.most_common(1)[0][0] if root_counts else ""
        groups.append({"id": rank, "size": len(members),
                       "label": " · ".join(hpo[h["hp"]]["name"] for h in hps[:2]) or "Mixed",
                       "phenotypes": hps, "pathways": pas,
                       "top_pathway_class": path_names.get(root, ""),
                       "color": rank if rank < N_GROUP_COLORS else -1})
    n_unconnected = sum(1 for x in group_of if x == -1)
    groups.append({"id": -1, "size": n_unconnected, "label": "Small or unconnected constellations",
                   "phenotypes": [], "pathways": [], "top_pathway_class": "", "color": -1})

    if llm.available():
        print("Naming clusters with OpenAI")
        llm.name_groups(groups, hpo, path_names)

    # --- serialise
    clingen = sources.load_clingen()
    used_hp = set()
    out_diseases = {}
    ids = [d["id"] for d in ds]
    for i, d in enumerate(ds):
        used_hp |= set(d["pheno"]) | d["excluded"]
        out_diseases[d["id"]] = {
            "id": d["id"], "name": d["name"], "synonyms": d["synonyms"][:25], "xrefs": d["xrefs"],
            "def": d["def"], "genes": d["genes"],
            "inheritance": sorted(d["inheritance"]), "onset": sorted(d["onset"]),
            "phenotypes": sorted(d["pheno"].values(), key=lambda a: -ic[tix[a["hp"]]] if a["hp"] in tix else 0),
            "excluded": sorted(d["excluded"]),
            "sparse": len(d["pheno"]) < SPARSE_PHENOTYPES,
            "has_pathway": bool(has_path[i]),
            "x": round(float(layout[i, 0]), 4), "y": round(float(layout[i, 1]), 4),
            "group": group_of[i], "cluster": cluster_of[i],
            "neighbors": [{"id": ids[j], "score": round(float(S[i, j]), 3),
                           "pheno": round(float(S_ph[i, j]), 3),
                           "path": round(float(S_pa[i, j]), 3) if both[i, j] else None,
                           "same_gene": bool(set(d["genes"]) & set(ds[j]["genes"]))}
                          for j in neighbors[i]],
        }
    closure = set()
    for hp in used_hp:
        closure |= anc(hp)
    for c in clusters.values():
        closure |= {h["hp"] for h in c["phenotypes"]}
    out_hpo = {t: {"name": hpo[t]["name"], "lay": hpo[t]["lay"], "parents": hpo[t]["parents"],
                   "synonyms": hpo[t]["synonyms"][:8], "def": hpo[t]["def"][:300],
                   "ic": round(float(ic[tix[t]]), 2) if t in tix else 0,
                   "n": int(df[tix[t]]) if t in tix else 0}
               for t in closure}
    gene_diseases = defaultdict(list)
    for d in ds:
        for s in d["genes"]:
            gene_diseases[s].append(d["id"])
    out_genes = {s: {"symbol": s, "ncbi": gene_ncbi[s], "diseases": dl,
                     "pathways": [[p, path_ev.get((gene_ncbi[s], p), "")]
                                  for p in sorted(gene_paths.get(gene_ncbi[s], ()), key=lambda p: -ic_p[pix[p]])],
                     "clingen": clingen.get(s)}
                 for s, dl in gene_diseases.items()}
    out_paths = {p: {"id": p, "name": path_names.get(p, p), "ic": round(float(ic_p[pix[p]]), 2),
                     "n_genes": path_genes[p], "root": path_names.get(path_roots.get(p, ""), ""),
                     "url": f"https://reactome.org/content/detail/{p}"}
                 for p in used_paths}
    today = datetime.date.today().isoformat()
    atlas = {
        "meta": {
            "built": today,
            "counts": {"diseases": n, "genes": len(out_genes), "phenotype_terms": len(used_hp),
                       "phenotype_annotations": sum(len(d["phenotypes"]) for d in out_diseases.values()),
                       "pathways": len(out_paths), "similarity_edges": len(edges),
                       "clusters": len(clusters), "background_diseases": len(with_pheno)},
            "sources": [
                {"name": "HPO annotations (phenotype.hpoa)", "version": hpoa_version, "url": "https://hpo.jax.org/data/annotations"},
                {"name": "MONDO disease ontology", "version": today, "url": "https://mondo.monarchinitiative.org"},
                {"name": "OMIM gene-disease (via HPO genes_to_disease)", "version": hpoa_version, "url": "https://omim.org"},
                {"name": "Reactome pathways", "version": today, "url": "https://reactome.org"},
                {"name": "ClinGen dosage sensitivity", "version": today, "url": "https://search.clinicalgenome.org/kb/gene-dosage"},
            ],
            "params": {"w_pheno": W_PHENO, "w_path": W_PATH, "no_pathway_discount": NO_PATHWAY_DISCOUNT,
                       "knn": KNN, "min_score": MIN_SCORE, "pheno_gate": PHENO_GATE},
        },
        "diseases": out_diseases, "hpo": out_hpo, "genes": out_genes, "pathways": out_paths,
        "clusters": clusters, "groups": groups,
    }
    with gzip.open(ATLAS_FILE, "wt", encoding="utf-8") as f:
        json.dump(atlas, f, separators=(",", ":"))
    sizes = sorted((c["size"] for c in clusters.values()), reverse=True)
    print(f"Wrote {ATLAS_FILE} ({ATLAS_FILE.stat().st_size / 1e6:.1f} MB): {len(edges)} similarity edges, "
          f"{len(groups) - 1} colour groups, {len(clusters)} clusters (largest {sizes[:5]}, "
          f"median {sizes[len(sizes) // 2]}), {n_unconnected} diseases in small/unconnected groups")
    for gr in groups[:N_GROUP_COLORS]:
        print(f"   group {gr['id']:>2} n={gr['size']:<4} {gr['label']}  [{gr['top_pathway_class']}]")


if __name__ == "__main__":
    sources.download_all(force="--refresh" in sys.argv)
    build()

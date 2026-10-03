"""Parsers for the bulk biology sources (HPO, HPOA, MONDO, Reactome, ClinGen)."""
import csv
import re
import urllib.request
from collections import defaultdict

from .config import BULK_SOURCES, RAW

FREQ_TERMS = {
    "HP:0040280": 1.0,   # Obligate
    "HP:0040281": 0.9,   # Very frequent
    "HP:0040282": 0.55,  # Frequent
    "HP:0040283": 0.17,  # Occasional
    "HP:0040284": 0.025, # Very rare
    "HP:0040285": 0.0,   # Excluded
}
EVIDENCE_CONFIDENCE = {"PCS": 0.9, "TAS": 0.8, "IEA": 0.5}
EVIDENCE_LABEL = {
    "PCS": "published clinical study",
    "TAS": "traceable author statement",
    "IEA": "inferred from electronic annotation",
}


def download_all(force=False):
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in BULK_SOURCES.items():
        dest = RAW / name
        if dest.exists() and not force:
            continue
        print(f"  downloading {name}")
        req = urllib.request.Request(url, headers={"User-Agent": "ConstellAI/0.1"})
        with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)


def parse_obo(path):
    """Yield each [Term] stanza as {tag: [values]}."""
    stanza, in_term = None, False
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("["):
                if in_term and stanza:
                    yield stanza
                in_term = line == "[Term]"
                stanza = defaultdict(list)
            elif in_term and ": " in line:
                tag, value = line.split(": ", 1)
                stanza[tag].append(value)
    if in_term and stanza:
        yield stanza


def _quoted(value):
    m = re.match(r'"((?:[^"\\]|\\.)*)"', value)
    return m.group(1).replace('\\"', '"') if m else value


def load_hpo():
    terms, alt = {}, {}
    for s in parse_obo(RAW / "hp.obo"):
        if "is_obsolete" in s:
            continue
        tid = s["id"][0]
        synonyms, lay = [], None
        for syn in s.get("synonym", []):
            text = _quoted(syn)
            synonyms.append(text)
            if "layperson" in syn and "EXACT" in syn and lay is None:
                lay = text
        terms[tid] = {
            "name": s["name"][0],
            "synonyms": synonyms,
            "lay": lay,
            "parents": [p.split(" ")[0] for p in s.get("is_a", [])],
            "def": _quoted(s["def"][0]) if "def" in s else "",
        }
        for a in s.get("alt_id", []):
            alt[a] = tid
    return terms, alt


def ancestors_fn(terms):
    cache = {}

    def anc(t):
        if t in cache:
            return cache[t]
        out = {t}
        for p in terms.get(t, {}).get("parents", []):
            out |= anc(p)
        cache[t] = out
        return out

    return anc


def load_mondo():
    """Return (terms, xref->MONDO) using only equivalence-grade xrefs."""
    terms, xmap = {}, {}
    for s in parse_obo(RAW / "mondo.obo"):
        if "is_obsolete" in s or not s["id"][0].startswith("MONDO:"):
            continue
        mid = s["id"][0]
        xrefs = []
        for x in s.get("xref", []):
            if "MONDO:equivalentTo" not in x:
                continue
            ref = x.split(" ")[0]
            if ref.startswith("Orphanet:"):
                ref = "ORPHA:" + ref.split(":")[1]
            if ref.startswith(("OMIM:", "ORPHA:")):
                xrefs.append(ref)
                xmap.setdefault(ref, mid)
        synonyms = []
        for syn in s.get("synonym", []):
            if " EXACT " in syn or " RELATED " in syn:
                text = _quoted(syn)
                if text not in synonyms:
                    synonyms.append(text)
        terms[mid] = {
            "name": s["name"][0],
            "synonyms": synonyms,
            "xrefs": xrefs,
            "def": _quoted(s["def"][0]) if "def" in s else "",
            "parents": [p.split(" ")[0] for p in s.get("is_a", [])],
        }
    return terms, xmap


def parse_frequency(raw):
    if not raw:
        return None
    if raw in FREQ_TERMS:
        return FREQ_TERMS[raw]
    m = re.match(r"(\d+)/(\d+)$", raw)
    if m and int(m.group(2)):
        return int(m.group(1)) / int(m.group(2))
    m = re.match(r"([\d.]+)%$", raw)
    if m:
        return float(m.group(1)) / 100
    return None


def load_hpoa():
    """Yield annotation rows as dicts; also returns the release version."""
    rows, version = [], ""
    with open(RAW / "phenotype.hpoa", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#version:"):
                version = line.split(":", 1)[1].strip()
            if line.startswith("#"):
                continue
            if line.startswith("database_id"):
                header = line.rstrip("\n").split("\t")
                continue
            rows.append(dict(zip(header, line.rstrip("\n").split("\t"))))
    return rows, version


def load_gene_disease():
    out = []
    with open(RAW / "genes_to_disease.txt", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["association_type"] == "MENDELIAN":
                out.append(row)
    return out


def load_reactome():
    """gene (NCBI id) -> lowest-level human pathways, plus names and top-level roots."""
    names = {}
    with open(RAW / "ReactomePathways.txt", encoding="utf-8") as f:
        for line in f:
            pid, name, species = line.rstrip("\n").split("\t")
            if species == "Homo sapiens":
                names[pid] = name.strip()
    parent = defaultdict(list)
    with open(RAW / "ReactomePathwaysRelation.txt", encoding="utf-8") as f:
        for line in f:
            p, c = line.split()
            if c in names:
                parent[c].append(p)

    def root(pid, seen=()):
        while parent.get(pid) and pid not in seen:
            seen += (pid,)
            pid = parent[pid][0]
        return pid

    gene_paths, evidence = defaultdict(set), {}
    with open(RAW / "NCBI2Reactome.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6 or parts[5] != "Homo sapiens":
                continue
            gene_paths[parts[0]].add(parts[1])
            evidence[(parts[0], parts[1])] = parts[4]
    roots = {pid: root(pid) for pid in names}
    return gene_paths, evidence, names, roots


def load_clingen():
    out = {}
    with open(RAW / "clingen_dosage.csv", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 6 and row[1].startswith("HGNC:"):
                out[row[0]] = {
                    "haploinsufficiency": row[2],
                    "triplosensitivity": row[3],
                    "url": row[4],
                    "date": row[5][:10],
                }
    return out

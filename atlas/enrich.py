"""Live evidence layer: papers, investigators, studies, funding, variants, communities.

Fetched on demand per disease from public APIs and cached on disk, so the atlas
covers every disease in the map rather than a hand-prepared slice.
"""
import datetime
import json
import re
import threading
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import httpx

from . import llm
from .config import CACHE, CURATED, NCBI_API_KEY

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CACHE_DAYS = 7
HTTP = httpx.Client(timeout=25, headers={"User-Agent": "ConstellAI/0.1 (rare disease atlas; hackathon prototype)"},
                    follow_redirects=True)

_ncbi_lock = threading.Lock()
_ncbi_last = [0.0]


def today():
    return datetime.date.today().isoformat()


def ncbi(endpoint, **params):
    """E-utilities call, throttled to NCBI's published rate limit."""
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    gap = 0.11 if NCBI_API_KEY else 0.36
    for attempt in range(3):
        with _ncbi_lock:
            wait = _ncbi_last[0] + gap - time.time()
            if wait > 0:
                time.sleep(wait)
            _ncbi_last[0] = time.time()
        r = HTTP.post(f"{EUTILS}/{endpoint}.fcgi", data=params)
        if r.status_code == 429:
            time.sleep(1 + attempt)
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()


def person_key(last, first):
    last = re.sub(r"[^a-z]", "", last.lower())
    return f"{last} {first[:1].lower()}" if last and first else ""


def split_name(full):
    """'Matthijs Verhage, MD, PhD' -> ('Verhage', 'Matthijs')."""
    full = re.sub(r"^(dr|prof|professor)\.?\s+", "", full.split(",")[0].strip(), flags=re.I)
    parts = [p for p in full.split() if not re.fullmatch(r"(MD|PhD|MSc|MBBS|DO|Jr\.?|Sr\.?|II|III)", p, re.I)]
    return (parts[-1], parts[0]) if len(parts) >= 2 else ("", "")


def pubmed_term(disease):
    terms = [f"{g}[Title/Abstract]" for g in disease["genes"]]
    name = disease["name"]
    if not re.search(r"\d", name) and len(name) < 60:  # skip numbered OMIM-style series names
        terms.append(f'"{name}"[Title/Abstract]')
    return "(" + " OR ".join(terms) + ")"


# ------------------------------------------------------------------ PubMed

EFFECT_PATTERNS = {
    "loss_of_function": r"loss[- ]of[- ]function|haploinsufficien|\bLoF\b|null (?:allele|variant|mutation)s?",
    "gain_of_function": r"gain[- ]of[- ]function|\bGoF\b",
    "dominant_negative": r"dominant[- ]negative",
}
ASSET_PATTERNS = {
    "animal_model": r"mouse model|mice\b|knock-?in|knock-?out|zebrafish|drosophila|C\. elegans|rat model",
    "cell_model": r"iPSC|induced pluripotent|organoid|patient-derived (?:neurons|fibroblasts|cells)",
    "biomarker": r"biomarker",
    "natural_history": r"natural history",
    "registry": r"\bregistry\b",
    "therapy": r"antisense oligonucleotide|\bASOs?\b|gene therapy|\bAAV\d?\b|enzyme replacement|"
               r"gene replacement|drug repurposing|repurposed|small[- ]molecule",
}


def pattern_claims(genes, papers):
    """Deterministic claim extraction: sentences that state a variant effect or an asset."""
    claims = []
    gene_re = re.compile("|".join(re.escape(g) for g in genes), re.I)
    for p in papers:
        seen = set()
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z])", p["abstract"]):
            for effect, pat in EFFECT_PATTERNS.items():
                if re.search(pat, sent, re.I) and (gene_re.search(sent) or gene_re.search(p["title"])) and effect not in seen:
                    seen.add(effect)
                    claims.append({"pmid": p["pmid"], "kind": "variant_effect", "effect": effect,
                                   "asset_type": "none", "statement": "", "quote": sent[:400], "method": "pattern"})
            for asset, pat in ASSET_PATTERNS.items():
                if re.search(pat, sent, re.I) and asset not in seen:
                    seen.add(asset)
                    claims.append({"pmid": p["pmid"], "kind": "asset", "effect": "none", "asset_type": asset,
                                   "statement": "", "quote": sent[:400], "method": "pattern"})
    return claims


def fetch_pubmed(disease):
    term = pubmed_term(disease)
    gene_term = "(" + " OR ".join(f"{g}[Title/Abstract]" for g in disease["genes"]) + ")"
    mech = (gene_term + ' AND ("loss of function"[tiab] OR "gain of function"[tiab] OR '
            'haploinsufficiency[tiab] OR "dominant negative"[tiab])')
    main = ncbi("esearch", db="pubmed", term=term, retmode="json", retmax=30, sort="relevance").json()["esearchresult"]
    extra = ncbi("esearch", db="pubmed", term=mech, retmode="json", retmax=12, sort="relevance").json()["esearchresult"]
    ids = list(dict.fromkeys(main.get("idlist", []) + extra.get("idlist", [])))
    papers = []
    if ids:
        root = ET.fromstring(ncbi("efetch", db="pubmed", id=",".join(ids), retmode="xml").content)
        for art in root.iter("PubmedArticle"):
            pmid = art.findtext(".//PMID")
            authors = []
            for a in art.iter("Author"):
                last, first = a.findtext("LastName") or "", a.findtext("ForeName") or a.findtext("Initials") or ""
                if last:
                    authors.append({"last": last, "first": first, "aff": (a.findtext(".//Affiliation") or "")[:160]})
            abstract = " ".join("".join(t.itertext()) for t in art.iter("AbstractText"))
            papers.append({
                "pmid": pmid,
                "title": "".join(art.find(".//ArticleTitle").itertext()) if art.find(".//ArticleTitle") is not None else "",
                "journal": art.findtext(".//Journal/ISOAbbreviation") or art.findtext(".//Journal/Title") or "",
                "year": art.findtext(".//JournalIssue/PubDate/Year") or (art.findtext(".//JournalIssue/PubDate/MedlineDate") or "")[:4],
                "authors": authors, "abstract": abstract,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
    claims = None
    if llm.available():
        claims = llm.extract_claims("/".join(disease["genes"]),
                                    [{"pmid": p["pmid"], "text": p["abstract"][:2500]} for p in papers[:24] if p["abstract"]])
        if claims is not None:
            for c in claims:
                c["method"] = "llm"
    if claims is None:
        claims = pattern_claims(disease["genes"], papers)
    by_pmid = {p["pmid"]: p for p in papers}
    for c in claims:
        c["year"], c["title"], c["url"] = by_pmid[c["pmid"]]["year"], by_pmid[c["pmid"]]["title"], by_pmid[c["pmid"]]["url"]
    return {
        "query": term, "count": int(main.get("count", 0)),
        "url": "https://pubmed.ncbi.nlm.nih.gov/?" + str(httpx.QueryParams({"term": term})),
        "papers": [{k: v for k, v in p.items() if k != "abstract"} | {"authors": p["authors"][:1] + p["authors"][-1:] if len(p["authors"]) > 1 else p["authors"],
                                                                     "n_authors": len(p["authors"])} for p in papers],
        "claims": claims,
        "claim_method": "llm" if any(c["method"] == "llm" for c in claims) else "pattern",
        "_authors": [(p["pmid"], p["year"], p["authors"]) for p in papers],
    }


# ------------------------------------------------------------------ ClinVar

def fetch_clinvar(disease):
    out = []
    path = '("clinsig pathogenic"[Properties] OR "clinsig likely pathogenic"[Properties])'
    classes = {
        "total": "",
        "truncating": ' AND ("nonsense"[Molecular consequence] OR "frameshift variant"[Molecular consequence] OR '
                      '"splice donor variant"[Molecular consequence] OR "splice acceptor variant"[Molecular consequence])',
        "missense": ' AND "missense variant"[Molecular consequence]',
    }
    for g in disease["genes"][:2]:
        counts = {}
        for k, extra in classes.items():
            r = ncbi("esearch", db="clinvar", term=f"{g}[gene] AND {path}{extra}", retmode="json", retmax=0)
            counts[k] = int(r.json()["esearchresult"]["count"])
        out.append({"gene": g, **counts, "url": f"https://www.ncbi.nlm.nih.gov/clinvar/?term={g}%5Bgene%5D"})
    return out


# ------------------------------------------------------------------ ClinicalTrials.gov

CT_FIELDS = ("NCTId,BriefTitle,OverallStatus,StartDate,StudyType,Phase,EnrollmentCount,PatientRegistry,"
             "LeadSponsorName,LeadSponsorClass,CollaboratorName,Condition,InterventionType,InterventionName,"
             "OverallOfficialName,OverallOfficialAffiliation,PrimaryOutcomeMeasure,MinimumAge,MaximumAge")


def classify_study(title, study_type, registry, itypes):
    t = title.lower()
    if study_type == "INTERVENTIONAL":
        if "GENETIC" in itypes:
            return "Genetic therapy trial"
        return "Interventional trial"
    if "natural history" in t or "trial readiness" in t or "longitudinal" in t:
        return "Natural history study"
    if registry or "registry" in t or "registries" in t:
        return "Registry"
    if "biomarker" in t:
        return "Biomarker study"
    if "biobank" in t or "repository" in t:
        return "Biobank"
    return "Observational study"


def fetch_trials(disease):
    names = [disease["name"]] if not re.search(r"\d", disease["name"]) else []
    cond = " OR ".join(disease["genes"] + [f'"{n}"' for n in names])
    for field in ("query.cond", "query.term"):
        r = HTTP.get("https://clinicaltrials.gov/api/v2/studies",
                     params={field: cond, "pageSize": 40, "fields": CT_FIELDS, "countTotal": "true"})
        r.raise_for_status()
        data = r.json()
        if data.get("studies"):
            break
    needles = [g.lower() for g in disease["genes"]] + [n.lower() for n in names]
    studies = []
    for s in data.get("studies", []):
        p = s["protocolSection"]
        ident, design = p["identificationModule"], p.get("designModule", {})
        spons = p.get("sponsorCollaboratorsModule", {})
        arms = p.get("armsInterventionsModule", {}).get("interventions", [])
        conditions = p.get("conditionsModule", {}).get("conditions", [])
        itypes = sorted({i.get("type", "") for i in arms})
        elig = p.get("eligibilityModule", {})
        hay = (ident.get("briefTitle", "") + " " + " ".join(conditions)).lower()
        studies.append({
            "nct": ident["nctId"], "title": ident.get("briefTitle", ""),
            "status": p.get("statusModule", {}).get("overallStatus", ""),
            "start": p.get("statusModule", {}).get("startDateStruct", {}).get("date", ""),
            "type": design.get("studyType", ""), "phase": ", ".join(design.get("phases", [])),
            "enrollment": design.get("enrollmentInfo", {}).get("count"),
            "kind": classify_study(ident.get("briefTitle", ""), design.get("studyType", ""),
                                   design.get("patientRegistry"), itypes),
            "sponsor": spons.get("leadSponsor", {}).get("name", ""),
            "sponsor_class": spons.get("leadSponsor", {}).get("class", ""),
            "collaborators": [c["name"] for c in spons.get("collaborators", [])],
            "conditions": conditions[:6],
            "interventions": [{"type": i.get("type", ""), "name": i.get("name", "")} for i in arms[:4]],
            "officials": [{"name": o.get("name", ""), "affiliation": o.get("affiliation", "")}
                          for o in p.get("contactsLocationsModule", {}).get("overallOfficials", [])],
            "outcomes": [o.get("measure", "") for o in p.get("outcomesModule", {}).get("primaryOutcomes", [])][:3],
            "ages": " – ".join(x for x in (elig.get("minimumAge"), elig.get("maximumAge")) if x),
            "specific": any(n in hay for n in needles),
            "url": f"https://clinicaltrials.gov/study/{ident['nctId']}",
        })
    studies.sort(key=lambda s: (not s["specific"], s["status"] not in ("RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"), -int(s["start"][:4]) if s["start"] else 0))
    return {"query": cond, "count": data.get("totalCount", len(studies)), "studies": studies,
            "url": "https://clinicaltrials.gov/search?" + str(httpx.QueryParams({"cond": cond}))}


# ------------------------------------------------------------------ NIH RePORTER

def fetch_grants(disease):
    year = datetime.date.today().year
    body = {
        "criteria": {
            "advanced_text_search": {"operator": "or", "search_field": "projecttitle,terms",
                                     "search_text": " ".join(disease["genes"])},
            "fiscal_years": [year - 2, year - 1, year],
        },
        "limit": 60, "sort_field": "fiscal_year", "sort_order": "desc",
        "include_fields": ["ProjectNum", "CoreProjectNum", "ProjectTitle", "PrincipalInvestigators", "Organization",
                           "FiscalYear", "AwardAmount", "ProjectStartDate", "ProjectEndDate", "AgencyIcAdmin",
                           "ProjectDetailUrl"],
    }
    r = HTTP.post("https://api.reporter.nih.gov/v2/projects/search", json=body)
    r.raise_for_status()
    data = r.json()
    grants, seen = [], set()
    for g in data.get("results", []):
        core = g.get("core_project_num") or g.get("project_num")
        if core in seen:
            continue
        seen.add(core)
        grants.append({
            "num": core, "title": (g.get("project_title") or "").strip(), "year": g.get("fiscal_year"),
            "amount": g.get("award_amount"),
            "org": ((g.get("organization") or {}).get("org_name") or "").title(),
            "ic": (g.get("agency_ic_admin") or {}).get("abbreviation", ""),
            "end": (g.get("project_end_date") or "")[:10],
            "pis": [{"last": p.get("last_name", "").title(), "first": p.get("first_name", "").title()}
                    for p in g.get("principal_investigators") or []],
            "url": g.get("project_detail_url", ""),
        })
    return {"query": " OR ".join(disease["genes"]), "count": data.get("meta", {}).get("total", len(grants)),
            "grants": grants, "years": body["criteria"]["fiscal_years"]}


# ------------------------------------------------------------------ communities

_curated = None
ORG_WORDS = re.compile(r"foundation|alliance|association|society|\bfund\b|trust|consortium|\bcure\b|"
                       r"patient|families|\bhope\b|charity|coalition|network", re.I)
NOT_ORG = re.compile(r"universit|hospital|institut|college|clinic|medical cent|pharma|therapeutics|\binc\b|"
                     r"national institutes|\bnih\b|\bllc\b|\bltd\b|gmbh|biosciences|health system", re.I)


def curated():
    global _curated
    if _curated is None:
        _curated = json.loads((CURATED / "patient_orgs.json").read_text())
    return _curated


def match_orgs(disease):
    genes = set(disease["genes"])
    names = [disease["name"].lower()] + [s.lower() for s in disease["synonyms"]]
    out = []
    for o in curated()["organizations"]:
        if not o.get("reachable", True):
            continue
        by_gene = genes & set(o.get("genes", []))
        by_name = [k for k in o.get("keywords", []) if any(k.lower() in n for n in names)]
        if by_gene or by_name:
            out.append({**o, "matched_on": (f"gene {', '.join(sorted(by_gene))}" if by_gene else f"name “{by_name[0]}”"),
                        "source": "curated", "verified": curated()["verified"]})
    return out


def directories(disease):
    orpha = next((x.split(":")[1] for x in disease["xrefs"] if x.startswith("ORPHA:")), None)
    omim = next((x.split(":")[1] for x in disease["xrefs"] if x.startswith("OMIM:")), None)
    q = str(httpx.QueryParams({"s": disease["name"]}))
    out = [{"name": "NORD rare disease database", "url": f"https://rarediseases.org/?{q}"},
           {"name": "Global Genes RARE Portal", "url": f"https://globalgenes.org/?{q}"},
           {"name": "Genetic Alliance", "url": "https://geneticalliance.org"},
           {"name": "EURORDIS member directory", "url": "https://www.eurordis.org/who-we-are/our-members/"},
           {"name": "RareConnect communities", "url": "https://www.rareconnect.org"}]
    if orpha:
        out.insert(0, {"name": f"Orphanet (ORPHA:{orpha}) — patient organisations tab",
                       "url": f"https://www.orpha.net/en/disease/detail/{orpha}"})
    if omim:
        out.append({"name": f"OMIM entry {omim}", "url": f"https://omim.org/entry/{omim}"})
    return out


# ------------------------------------------------------------------ assemble

def investigators(pub, trials, grants):
    people = defaultdict(lambda: {"name": "", "affiliation": "", "papers": [], "last_author": 0,
                                  "trials": [], "grants": [], "score": 0.0})
    for pmid, year, authors in pub.get("_authors", []):
        for i, a in enumerate(authors):
            key = person_key(a["last"], a["first"])
            if not key:
                continue
            p = people[key]
            p["name"] = p["name"] or f"{a['first']} {a['last']}"
            is_last = i == len(authors) - 1 and len(authors) > 1
            p["papers"].append(pmid)
            p["last_author"] += is_last
            p["score"] += 1.0 if is_last else (0.5 if i == 0 else 0.15)
            if a["aff"] and (is_last or not p["affiliation"]):
                p["affiliation"] = a["aff"]
    for s in trials.get("studies", []):
        if not s["specific"]:
            continue
        for o in s["officials"]:
            key = person_key(*split_name(o["name"]))
            if key:
                p = people[key]
                p["name"] = p["name"] or o["name"].split(",")[0]
                p["affiliation"] = p["affiliation"] or o["affiliation"]
                p["trials"].append(s["nct"])
                p["score"] += 2.0
    for g in grants.get("grants", []):
        for pi in g["pis"]:
            key = person_key(pi["last"], pi["first"])
            if key:
                p = people[key]
                p["name"] = p["name"] or f"{pi['first']} {pi['last']}"
                p["affiliation"] = p["affiliation"] or g["org"]
                p["grants"].append(g["num"])
                p["score"] += 1.5
    ranked = sorted(({"key": k, **v, "score": round(v["score"], 2)} for k, v in people.items()),
                    key=lambda p: -p["score"])
    return [p for p in ranked if p["score"] >= 1][:25]


def sponsor_orgs(trials):
    seen, out = set(), []
    for s in trials.get("studies", []):
        if not s["specific"]:
            continue
        for name in [s["sponsor"]] + s["collaborators"]:
            if name and name not in seen and ORG_WORDS.search(name) and not NOT_ORG.search(name):
                seen.add(name)
                out.append({"name": name, "source": "ClinicalTrials.gov sponsor/collaborator", "via": s["nct"],
                            "url": s["url"]})
    return out


def _safe(fn, disease, label, errors):
    try:
        return fn(disease)
    except Exception as e:
        errors.append(f"{label}: {type(e).__name__}")
        return None


def enrich(disease, force=False):
    path = CACHE / "enrich" / (disease["id"].replace(":", "_") + ".json")
    if path.exists() and not force:
        cached = json.loads(path.read_text())
        age = (datetime.date.today() - datetime.date.fromisoformat(cached["fetched"])).days
        if age <= CACHE_DAYS and not cached.get("errors"):
            return cached
    errors = []
    with ThreadPoolExecutor(4) as ex:
        f_pub = ex.submit(_safe, fetch_pubmed, disease, "PubMed", errors)
        f_var = ex.submit(_safe, fetch_clinvar, disease, "ClinVar", errors)
        f_tri = ex.submit(_safe, fetch_trials, disease, "ClinicalTrials.gov", errors)
        f_gra = ex.submit(_safe, fetch_grants, disease, "NIH RePORTER", errors)
        pub = f_pub.result() or {"papers": [], "claims": [], "count": 0, "query": pubmed_term(disease), "url": "", "claim_method": "pattern"}
        trials = f_tri.result() or {"studies": [], "count": 0, "query": "", "url": ""}
        grants = f_gra.result() or {"grants": [], "count": 0, "query": "", "years": []}
        clinvar = f_var.result() or []
    people = investigators(pub, trials, grants)
    pub.pop("_authors", None)
    orgs = match_orgs(disease)
    known = {o["name"].lower() for o in orgs}
    orgs += [o for o in sponsor_orgs(trials) if o["name"].lower() not in known]
    out = {
        "id": disease["id"], "fetched": today(), "errors": errors,
        "pubmed": pub, "clinvar": clinvar, "trials": trials, "grants": grants,
        "investigators": people, "organizations": orgs,
        "registries": [r for r in curated()["cross_disease_registries"]
                       if not r.get("genes") or set(r["genes"]) & set(disease["genes"])],
        "directories": directories(disease),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def comention(a, b):
    """How often the literature already mentions both diseases together."""
    term = f"{pubmed_term(a)} AND {pubmed_term(b)}"
    r = ncbi("esearch", db="pubmed", term=term, retmode="json", retmax=5, sort="relevance").json()["esearchresult"]
    return {"count": int(r.get("count", 0)), "pmids": r.get("idlist", []), "query": term,
            "url": "https://pubmed.ncbi.nlm.nih.gov/?" + str(httpx.QueryParams({"term": term}))}

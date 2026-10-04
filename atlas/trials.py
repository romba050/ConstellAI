"""Trials a family affected by the focus disease could ask to join.

Pulls open studies from ClinicalTrials.gov for the gene itself and for the broader
conditions its patients present with, then screens every eligibility text with
gpt-oss-120b (or rules when no model is configured).
"""
import datetime
import json
import re

from . import llm
from .config import CACHE
from .enrich import HTTP

OPEN = "RECRUITING,NOT_YET_RECRUITING,ENROLLING_BY_INVITATION"
FIELDS = ("NCTId,BriefTitle,BriefSummary,OverallStatus,StudyType,Phase,Condition,InterventionType,InterventionName,"
          "LeadSponsorName,EligibilityCriteria,MinimumAge,MaximumAge,Sex,LocationFacility,LocationCity,"
          "LocationCountry,LocationStatus,CentralContactName,CentralContactPhone,CentralContactEMail,LastUpdatePostDate")
CACHE_HOURS = 24
FOCUS_SUMMARY = ("early-onset epilepsy, often infantile spasms or drug-resistant seizures, developmental delay and "
                 "intellectual disability, movement disorders; usually de novo loss-of-function variants")
# Broad conditions STXBP1 patients present with; trials here may accept them without naming the gene.
BROAD = ["developmental and epileptic encephalopathy", "epileptic encephalopathy", "infantile spasms",
         "drug resistant epilepsy", "Lennox-Gastaut syndrome"]
BATCH = 8
SCREENS = CACHE / "trial_screens.json"  # verdicts keyed by NCT id + last update, kept across refreshes


def years(age):
    """'18 Months' -> 1.5; None when absent."""
    if not age:
        return None
    m = re.match(r"([\d.]+)\s*(\w+)", age)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2).lower()
    return round(n / {"y": 1, "m": 12, "w": 52, "d": 365}.get(unit[0], 1), 2)


def kind(t):
    """Plain category so a family sees medicines first and research procedures last."""
    if t["type"] != "INTERVENTIONAL":
        return "Registry or natural-history study"
    types = {i["type"] for i in t["interventions"]}
    if types & {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}:
        return "Medicine or gene therapy"
    if "DIETARY_SUPPLEMENT" in types or any("diet" in i["name"].lower() for i in t["interventions"]):
        return "Diet or supplement"
    if "DEVICE" in types:
        return "Device or brain stimulation"
    if "PROCEDURE" in types or "RADIATION" in types:
        return "Surgery or procedure"
    return "Other research study"


KIND_ORDER = ["Medicine or gene therapy", "Diet or supplement", "Registry or natural-history study",
              "Device or brain stimulation", "Surgery or procedure", "Other research study"]


def search(params):
    r = HTTP.get("https://clinicaltrials.gov/api/v2/studies",
                 params={**params, "filter.overallStatus": OPEN, "fields": FIELDS, "pageSize": 100})
    r.raise_for_status()
    return r.json().get("studies", [])


def parse(s, found_by):
    p = s["protocolSection"]
    ident, design = p["identificationModule"], p.get("designModule", {})
    elig, cl = p.get("eligibilityModule", {}), p.get("contactsLocationsModule", {})
    arms = p.get("armsInterventionsModule", {}).get("interventions", [])
    return {
        "nct": ident["nctId"], "title": ident.get("briefTitle", ""),
        "summary": p.get("descriptionModule", {}).get("briefSummary", "")[:600],
        "status": p.get("statusModule", {}).get("overallStatus", ""),
        "updated": p.get("statusModule", {}).get("lastUpdatePostDateStruct", {}).get("date", ""),
        "type": design.get("studyType", ""), "phases": design.get("phases", []),
        "conditions": p.get("conditionsModule", {}).get("conditions", [])[:8],
        "interventions": [{"type": i.get("type", ""), "name": i.get("name", "")} for i in arms[:5]],
        "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
        "criteria": elig.get("eligibilityCriteria", ""),
        "min_age": years(elig.get("minimumAge")), "max_age": years(elig.get("maximumAge")),
        "ages": " – ".join(x for x in (elig.get("minimumAge"), elig.get("maximumAge")) if x) or "any age",
        "sex": elig.get("sex", "ALL"),
        "sites": [{"facility": l.get("facility", ""), "city": l.get("city", ""), "country": l.get("country", ""),
                   "status": l.get("status", "")} for l in cl.get("locations", [])],
        "contacts": [{"name": c.get("name", ""), "phone": c.get("phone", ""), "email": c.get("email", "")}
                     for c in cl.get("centralContacts", [])][:2],
        "found_by": found_by,
        "url": f"https://clinicaltrials.gov/study/{ident['nctId']}",
    }


GENE_RESTRICTED = re.compile(r"\b(SCN1A|SCN2A|SCN8A|KCNT1|KCNQ2|CDKL5|SLC6A1|SLC13A5|GNAO1|PCDH19|SYNGAP1|FOXG1|"
                             r"CACNA1A|GRIN2[AB]|UBE3A|TSC[12]|Dravet|Angelman|Rett)\b", re.I)


def rule_screen(gene, t):
    text = " ".join([t["title"], " ".join(t["conditions"]), t["criteria"]])
    if re.search(gene, text, re.I):
        return {"verdict": "names_disease", "reason": f"The study mentions {gene} directly.", "quote": "",
                "requirements": [], "method": "rules"}
    hit = GENE_RESTRICTED.search(t["title"] + " " + " ".join(t["conditions"]))
    if hit:
        return {"verdict": "other_gene_only", "reason": f"The study is limited to {hit.group(0)}.", "quote": "",
                "requirements": [], "method": "rules"}
    return {"verdict": "could_include", "reason": "Not limited to another gene; eligibility must be checked by the study team.",
            "quote": "", "requirements": [], "method": "rules"}


def screen_all(focus, items):
    """Rules first; the model only sees trials the rules cannot settle. Verdicts are cached per trial version."""
    cache = json.loads(SCREENS.read_text()) if SCREENS.exists() else {}
    todo = []
    for t in items:
        key = f"{focus['gene']}|{t['nct']}|{t['updated']}"
        rule = rule_screen(focus["gene"], t)
        if key in cache:
            t["screen"] = cache[key]
        elif rule["verdict"] == "other_gene_only" or not llm.available():
            t["screen"] = rule
        else:
            todo.append((key, t))
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        res = llm.screen_trials(focus, [t for _, t in chunk]) or {}
        for key, t in chunk:
            if t["nct"] in res:
                t["screen"] = {**res[t["nct"]], "method": "llm"}
                if rule_screen(focus["gene"], t)["verdict"] == "names_disease":
                    t["screen"]["verdict"] = "names_disease"  # the gene is in the text, even if past the excerpt
                cache[key] = t["screen"]
            else:
                t["screen"] = rule_screen(focus["gene"], t)
        SCREENS.parent.mkdir(parents=True, exist_ok=True)
        SCREENS.write_text(json.dumps(cache))


def find(disease, force=False):
    gene = disease["genes"][0]
    path = CACHE / "trials" / f"{gene}.json"
    if path.exists() and not force:
        cached = json.loads(path.read_text())
        age = datetime.datetime.now() - datetime.datetime.fromisoformat(cached["fetched"])
        if age.total_seconds() < CACHE_HOURS * 3600:
            return cached
    queries = [({"query.term": gene}, f"mentions {gene}")]
    queries += [({"query.cond": c, "filter.advanced": "AREA[StudyType]INTERVENTIONAL AND AREA[StdAge]CHILD"},
                 f"children's interventional trials: {c}") for c in BROAD]
    trials, errors = {}, []
    for params, label in queries:
        try:
            for s in search(params):
                t = parse(s, label)
                trials.setdefault(t["nct"], t)
        except Exception as e:
            errors.append(f"{label}: {type(e).__name__}")
    focus = {"name": disease["name"], "gene": gene, "summary": FOCUS_SUMMARY}
    items = list(trials.values())
    screen_all(focus, items)
    for t in items:
        t.pop("criteria")
        t["kind"] = kind(t)
    order = {"names_disease": 0, "could_include": 1, "excludes": 2, "other_gene_only": 3}
    items.sort(key=lambda t: (order[t["screen"]["verdict"]], KIND_ORDER.index(t["kind"]), t["nct"]))
    out = {"gene": gene, "fetched": datetime.datetime.now().isoformat(timespec="seconds"),
           "queries": [label for _, label in queries], "errors": errors,
           "model": f"{llm.MODEL} via {llm.PROVIDER}" if llm.available() else "rules",
           "trials": items}
    path.parent.mkdir(parents=True, exist_ok=True)
    if not errors:
        path.write_text(json.dumps(out))
    return out

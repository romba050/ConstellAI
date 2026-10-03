from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "data" / "registry"
DISEASES_PATH = REGISTRY_DIR / "diseases.json"
DRUGS_PATH = REGISTRY_DIR / "drugs.json"
COMPOUNDS_PATH = REGISTRY_DIR / "compounds.json"
PHYSIOLOGY_PATH = REGISTRY_DIR / "physiology.json"
FDA_HYDRATED_PATH = REGISTRY_DIR / "drugs_fda_hydrated.json"
RXTERMS_HYDRATED_PATH = REGISTRY_DIR / "drugs_rxterms_hydrated.json"
MONDO_RARE_HYDRATED_PATH = REGISTRY_DIR / "diseases_mondo_rare_hydrated.json"
MONDO_ALL_HYDRATED_PATH = REGISTRY_DIR / "diseases_mondo_all_hydrated.json"
PUBCHEM_SEED_HYDRATED_PATH = REGISTRY_DIR / "compounds_pubchem_seed_hydrated.json"
OPENFDA_BASE = "https://api.fda.gov/drug/drugsfda.json"
DEFAULT_MONDO_RARE_URL = "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo-rare.json"
DEFAULT_MONDO_ALL_URL = "https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.json"
RXTERMS_ALLCONCEPTS_URL = "https://rxnav.nlm.nih.gov/REST/RxTerms/allconcepts.json"
PUBCHEM_AUTOCOMPLETE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/autocomplete/compound/{query}/JSON?limit={limit}"
PUBCHEM_PROPERTY_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/property/Title,MolecularFormula,MolecularWeight/JSON"
PUBCHEM_SYNONYM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/synonyms/JSON"


def _read_json_any(path: Path) -> Any:
    if not path.exists():
        print(f"[registry] missing: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data in (None, {}, []):
            print(f"[registry] empty data: {path}")
        return data
    except Exception as e:
        print(f"[registry] failed to load {path}: {e}")
        return None


def _read_json_list(path: Path) -> List[Dict[str, Any]]:
    raw = _read_json_any(path)
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        items = raw.get("items", [])
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


def _write_items(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"items": items}, indent=2, ensure_ascii=False), encoding="utf-8")


def _fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "med-r5/biomedical-ingestion"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_json_retry(url: str, retries: int = 3, delay_sec: float = 1.2) -> Any:
    last_exc: Optional[Exception] = None
    for attempt in range(max(1, int(retries or 1))):
        try:
            return _fetch_json(url)
        except Exception as exc:
            last_exc = exc
            if attempt >= max(1, int(retries or 1)) - 1:
                break
            import time
            time.sleep(delay_sec * (attempt + 1))
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("failed to fetch json")


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm_text(value).lower()


def _norm_gene(value: Any) -> str:
    return _norm_text(value).upper().replace(" ", "").replace("-", "")


def _norm_gene_list(values: Any) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values or []:
        gene = _norm_gene(value)
        if gene and gene not in seen:
            out.append(gene)
            seen.add(gene)
    return out


def _copy_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(item))


def _merge_unique_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in rows:
        key = (_norm_lower(item.get("id") or item.get("name")), _norm_lower(item.get("kind") or item.get("class") or item.get("type") or item.get("category")))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _normalize_target_records(values: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for value in values or []:
        if not isinstance(value, dict):
            continue
        gene = _norm_gene(value.get("gene") or value.get("target"))
        if not gene:
            continue
        direction = _norm_lower(value.get("direction") or value.get("effect") or "modulate")
        key = (gene, direction)
        if key in seen:
            continue
        seen.add(key)
        try:
            strength = float(value.get("strength", 0.6) or 0.6)
        except Exception:
            strength = 0.6
        out.append({
            "gene": gene,
            "direction": direction,
            "effect": direction,
            "strength": strength,
            "confidence": _norm_lower(value.get("confidence") or "starter"),
            "spillover": bool(value.get("spillover", False)),
            "note": _norm_text(value.get("note")),
        })
    return out


def _deep_find_graph_items(node: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(node, dict):
        graphs = node.get("graphs")
        if isinstance(graphs, list):
            for graph in graphs:
                if isinstance(graph, dict) and isinstance(graph.get("nodes"), list):
                    out.extend([x for x in graph.get("nodes") if isinstance(x, dict)])
        if isinstance(node.get("nodes"), list):
            out.extend([x for x in node.get("nodes") if isinstance(x, dict)])
        for value in node.values():
            out.extend(_deep_find_graph_items(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(_deep_find_graph_items(value))
    return out


def _extract_mondo_synonyms(node: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    meta = node.get("meta", {}) or {}
    for raw in meta.get("synonyms", []) or []:
        if isinstance(raw, dict):
            val = _norm_text(raw.get("val") or raw.get("value") or raw.get("synonym"))
        else:
            val = _norm_text(raw)
        if val and val not in out:
            out.append(val)
    return out


def _extract_mondo_xrefs(node: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    meta = node.get("meta", {}) or {}
    for raw in meta.get("xrefs", []) or []:
        if isinstance(raw, dict):
            val = _norm_text(raw.get("val") or raw.get("value") or raw.get("id"))
        else:
            val = _norm_text(raw)
        if val and val not in out:
            out.append(val)
    return out


def _extract_mondo_subsets(node: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    meta = node.get("meta", {}) or {}
    for raw in (meta.get("subsets") or meta.get("in_subset") or []):
        if isinstance(raw, dict):
            val = _norm_text(raw.get("val") or raw.get("value") or raw.get("id"))
        else:
            val = _norm_text(raw)
        if val and val not in out:
            out.append(val)
    return out


def _normalize_mondo_node(node: Dict[str, Any], source_tag: str, force_rare: Optional[bool] = None) -> Optional[Dict[str, Any]]:
    node_id = _norm_text(node.get("id"))
    label = _norm_text(node.get("lbl") or node.get("label") or node.get("name"))
    if not node_id or not label:
        return None
    if not (node_id.startswith("MONDO:") or node_id.startswith("MONDO_")):
        return None
    if label.lower().startswith("obsolete "):
        return None
    subsets = _extract_mondo_subsets(node)
    xrefs = _extract_mondo_xrefs(node)
    synonyms = _extract_mondo_synonyms(node)
    meta = node.get("meta", {}) or {}
    definition = _norm_text((meta.get("definition") or {}).get("val"))
    category = "rare_disease" if force_rare else "disease"
    rare_flag = bool(force_rare)
    if force_rare is None:
        lowered = [x.lower() for x in subsets]
        rare_flag = any("rare" in x for x in lowered) or "rare" in label.lower()
        category = "rare_disease" if rare_flag else "disease"
    return {
        "id": node_id.replace("_", ":") if node_id.startswith("MONDO_") else node_id,
        "name": label,
        "category": category,
        "rare": rare_flag,
        "aliases": synonyms[:20],
        "genes": [],
        "directions": {},
        "status": "hydrated",
        "source": source_tag,
        "subsets": subsets,
        "xrefs": xrefs,
        "notes": definition,
    }


def hydrate_mondo_rare_diseases(download_url: Optional[str] = None) -> Dict[str, Any]:
    url = download_url or DEFAULT_MONDO_RARE_URL
    payload = _fetch_json(url)
    rows: List[Dict[str, Any]] = []
    seen = set()
    for node in _deep_find_graph_items(payload):
        row = _normalize_mondo_node(node, source_tag="mondo_rare", force_rare=True)
        if not row:
            continue
        key = (_norm_lower(row.get("id")), _norm_lower(row.get("name")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    _write_items(MONDO_RARE_HYDRATED_PATH, rows)
    clear_registry_cache()
    return {"ok": True, "stored": len(rows), "path": str(MONDO_RARE_HYDRATED_PATH), "source": "mondo_rare", "download_url": url}


def hydrate_mondo_all_diseases(download_url: Optional[str] = None) -> Dict[str, Any]:
    url = download_url or DEFAULT_MONDO_ALL_URL
    payload = _fetch_json(url)
    rows: List[Dict[str, Any]] = []
    seen = set()
    for node in _deep_find_graph_items(payload):
        row = _normalize_mondo_node(node, source_tag="mondo_all", force_rare=None)
        if not row:
            continue
        key = (_norm_lower(row.get("id")), _norm_lower(row.get("name")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    _write_items(MONDO_ALL_HYDRATED_PATH, rows)
    clear_registry_cache()
    return {"ok": True, "stored": len(rows), "path": str(MONDO_ALL_HYDRATED_PATH), "source": "mondo_all", "download_url": url}


def _normalize_fda_product(application: Dict[str, Any], product: Dict[str, Any]) -> Dict[str, Any]:
    brand = _norm_text(product.get("brand_name"))
    generic = _norm_text(product.get("generic_name"))
    ingredients = []
    for item in product.get("active_ingredients") or []:
        if isinstance(item, dict):
            name = _norm_text(item.get("name"))
            if name:
                ingredients.append(name)
    route = [_norm_text(x) for x in (product.get("route") or []) if _norm_text(x)]
    app_no = _norm_text(application.get("application_number")) or _norm_text(product.get("application_number"))
    slug = (brand or generic or app_no or "drug").lower().replace(" ", "_").replace("/", "_")
    return {
        "id": f"fda_{slug}_{app_no.lower()}".strip("_"),
        "name": brand or generic or app_no or "unknown drug",
        "class": "approved_drug",
        "kind": "drug",
        "targets": [],
        "indications": [x for x in [generic, brand] if x],
        "rare_relevant": False,
        "status": "hydrated",
        "approval_status": _norm_lower(product.get("marketing_status") or "approved"),
        "source": "openfda_drugsfda",
        "active_ingredients": ingredients,
        "brand_name": brand,
        "generic_name": generic,
        "application_number": app_no,
        "routes": route,
        "notes": " | ".join([x for x in [
            f"dosage form: {_norm_text(product.get('dosage_form'))}" if _norm_text(product.get("dosage_form")) else "",
            f"sponsor: {_norm_text(application.get('sponsor_name'))}" if _norm_text(application.get("sponsor_name")) else "",
            f"status: {_norm_text(product.get('marketing_status'))}" if _norm_text(product.get("marketing_status")) else "",
        ] if x]),
        "xrefs": [app_no] if app_no else [],
    }


def hydrate_fda_approved_drugs(page_size: int = 99) -> Dict[str, Any]:
    skip = 0
    seen = set()
    all_rows: List[Dict[str, Any]] = []
    step = max(1, min(int(page_size or 99), 99))
    max_skip = 25000
    total_applications = None
    pages = 0
    truncated = False
    failed_pages: List[Dict[str, Any]] = []

    while skip <= max_skip:
        q = urllib.parse.urlencode({"limit": step, "skip": skip})
        page_url = f"{OPENFDA_BASE}?{q}"
        try:
            payload = _fetch_json_retry(page_url, retries=3, delay_sec=1.0)
        except Exception as exc:
            failed_pages.append({"skip": skip, "limit": step, "error": str(exc)})
            next_skip = skip + step
            if next_skip > max_skip:
                truncated = True
                break
            skip = next_skip
            continue

        meta = payload.get("meta") or {}
        results_meta = meta.get("results") or {}
        if total_applications is None:
            try:
                total_applications = int(results_meta.get("total"))
            except Exception:
                total_applications = None
        results = payload.get("results") or []
        if not isinstance(results, list) or not results:
            break
        pages += 1
        for application in results:
            if not isinstance(application, dict):
                continue
            for product in application.get("products") or []:
                if not isinstance(product, dict):
                    continue
                row = _normalize_fda_product(application, product)
                key = (_norm_lower(row.get("application_number")), _norm_lower(row.get("name")), _norm_lower(row.get("generic_name")))
                if key in seen:
                    continue
                seen.add(key)
                all_rows.append(row)
        if len(results) < step:
            break
        next_skip = skip + step
        if next_skip > max_skip:
            truncated = True
            break
        skip = next_skip

    _write_items(FDA_HYDRATED_PATH, all_rows)
    clear_registry_cache()
    partial = bool(truncated or failed_pages)
    note_parts = []
    if truncated:
        note_parts.append("openfda pagination capped at official skip ceiling")
    if failed_pages:
        note_parts.append(f"{len(failed_pages)} page windows failed but retained partial results")
    if not note_parts:
        note_parts.append("openfda hydration complete")
    return {
        "ok": len(all_rows) > 0 or not failed_pages,
        "stored": len(all_rows),
        "path": str(FDA_HYDRATED_PATH),
        "source": "openfda_drugsfda",
        "page_size": step,
        "pages": pages,
        "max_skip": max_skip,
        "truncated": bool(partial),
        "partial": bool(partial),
        "failed_pages": failed_pages[:12],
        "total_applications": total_applications,
        "note": " • ".join(note_parts),
    }

def hydrate_rxterms_drugs() -> Dict[str, Any]:
    payload = _fetch_json(RXTERMS_ALLCONCEPTS_URL)
    groups = (((payload or {}).get("rxtermsdata") or {}).get("conceptGroup") or {}).get("conceptProperties") or []
    rows: List[Dict[str, Any]] = []
    seen = set()
    for item in groups:
        if not isinstance(item, dict):
            continue
        rxcui = _norm_text(item.get("rxcui"))
        name = _norm_text(item.get("name"))
        if not (rxcui and name):
            continue
        key = (_norm_lower(rxcui), _norm_lower(name))
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "id": f"rxterms_{rxcui}",
            "name": name,
            "class": _norm_lower(item.get("tty") or "rxterms"),
            "kind": "drug",
            "targets": [],
            "indications": [],
            "rare_relevant": False,
            "status": "hydrated",
            "approval_status": "listed",
            "source": "rxterms",
            "active_ingredients": [],
            "brand_name": name if str(item.get("tty") or "").upper() == "BN" else "",
            "generic_name": name if str(item.get("tty") or "").upper() != "BN" else "",
            "application_number": "",
            "routes": [],
            "notes": f"rxcui: {rxcui} | tty: {_norm_text(item.get('tty'))}",
            "xrefs": [rxcui],
        })
    _write_items(RXTERMS_HYDRATED_PATH, rows)
    clear_registry_cache()
    return {"ok": True, "stored": len(rows), "path": str(RXTERMS_HYDRATED_PATH), "source": "rxterms"}


def _extract_seed_compound_names(seed_names: Optional[List[str]] = None) -> List[str]:
    seeds: List[str] = []
    for item in _read_json_list(COMPOUNDS_PATH):
        name = _norm_text(item.get("name"))
        if name:
            seeds.append(name)
    for item in _read_json_list(DRUGS_PATH) + _read_json_list(FDA_HYDRATED_PATH):
        for name in (item.get("active_ingredients") or []):
            token = _norm_text(name)
            if token:
                seeds.append(token)
        for name in [item.get("generic_name"), item.get("brand_name"), item.get("name")]:
            token = _norm_text(name)
            if token:
                seeds.append(token)
    for name in seed_names or []:
        token = _norm_text(name)
        if token:
            seeds.append(token)
    out: List[str] = []
    seen = set()
    for name in seeds:
        low = name.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(name)
    return out[:250]


def _pubchem_lookup_name(name: str) -> Optional[Dict[str, Any]]:
    token = urllib.parse.quote(name)
    try:
        prop_payload = _fetch_json(PUBCHEM_PROPERTY_URL.format(query=token))
    except Exception:
        prop_payload = None
    try:
        syn_payload = _fetch_json(PUBCHEM_SYNONYM_URL.format(query=token))
    except Exception:
        syn_payload = None
    props = (((prop_payload or {}).get("PropertyTable") or {}).get("Properties") or [])
    syns = (((syn_payload or {}).get("InformationList") or {}).get("Information") or [])
    prop = props[0] if props else {}
    syn = syns[0] if syns else {}
    cid = _norm_text(prop.get("CID") or syn.get("CID"))
    title = _norm_text(prop.get("Title")) or _norm_text(name)
    if not title:
        return None
    synonyms = [
        _norm_text(x)
        for x in (syn.get("Synonym") or [])[:20]
        if _norm_text(x)
    ]
    mw = prop.get("MolecularWeight")
    formula = _norm_text(prop.get("MolecularFormula"))
    notes = []
    if formula:
        notes.append(f"formula: {formula}")
    if mw not in (None, ""):
        notes.append(f"mw: {mw}")
    return {
        "id": f"pubchem_{cid or title.lower().replace(' ', '_')}",
        "name": title,
        "type": "compound_reference",
        "kind": "compound",
        "targets": [],
        "interaction_notes": [],
        "status": "hydrated",
        "source": "pubchem_seed",
        "notes": " | ".join(notes),
        "xrefs": [x for x in [f"CID:{cid}" if cid else ""] if x],
        "aliases": synonyms,
    }


def hydrate_pubchem_seed_compounds(seed_names: Optional[List[str]] = None) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    for name in _extract_seed_compound_names(seed_names):
        row = _pubchem_lookup_name(name)
        if not row:
            continue
        key = (_norm_lower(row.get("id")), _norm_lower(row.get("name")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
    _write_items(PUBCHEM_SEED_HYDRATED_PATH, rows)
    clear_registry_cache()
    return {"ok": True, "stored": len(rows), "path": str(PUBCHEM_SEED_HYDRATED_PATH), "source": "pubchem_seed"}


def load_diseases() -> List[Dict[str, Any]]:
    items = _read_json_list(DISEASES_PATH) + _read_json_list(MONDO_RARE_HYDRATED_PATH) + _read_json_list(MONDO_ALL_HYDRATED_PATH)
    items = _merge_unique_rows(items)
    out: List[Dict[str, Any]] = []
    for item in items:
        out.append({
            "id": _norm_text(item.get("id")),
            "name": _norm_text(item.get("name")),
            "category": _norm_lower(item.get("category") or "disease"),
            "rare": bool(item.get("rare", False)),
            "aliases": [_norm_text(x) for x in (item.get("aliases") or []) if _norm_text(x)],
            "genes": _norm_gene_list(item.get("genes") or []),
            "directions": {_norm_gene(k): _norm_lower(v) for k, v in (item.get("directions") or {}).items() if _norm_gene(k)},
            "status": _norm_lower(item.get("status") or "starter"),
            "source": _norm_lower(item.get("source") or "starter_registry"),
            "notes": _norm_text(item.get("notes")),
            "xrefs": [_norm_text(x) for x in (item.get("xrefs") or []) if _norm_text(x)],
        })
    return out


def load_drugs() -> List[Dict[str, Any]]:
    items = _read_json_list(DRUGS_PATH) + _read_json_list(FDA_HYDRATED_PATH) + _read_json_list(RXTERMS_HYDRATED_PATH)
    items = _merge_unique_rows(items)
    out: List[Dict[str, Any]] = []
    for item in items:
        out.append({
            "id": _norm_text(item.get("id")),
            "name": _norm_text(item.get("name")),
            "class": _norm_lower(item.get("class")),
            "kind": "drug",
            "targets": _normalize_target_records(item.get("targets") or []),
            "indications": [_norm_text(x) for x in (item.get("indications") or []) if _norm_text(x)],
            "rare_relevant": bool(item.get("rare_relevant", False)),
            "status": _norm_lower(item.get("status") or "starter"),
            "approval_status": _norm_lower(item.get("approval_status") or item.get("status") or "starter"),
            "source": _norm_lower(item.get("source") or "starter_registry"),
            "active_ingredients": [_norm_text(x) for x in (item.get("active_ingredients") or []) if _norm_text(x)],
            "brand_name": _norm_text(item.get("brand_name")),
            "generic_name": _norm_text(item.get("generic_name")),
            "application_number": _norm_text(item.get("application_number")),
            "routes": [_norm_text(x) for x in (item.get("routes") or []) if _norm_text(x)],
            "notes": _norm_text(item.get("notes")),
            "xrefs": [_norm_text(x) for x in (item.get("xrefs") or []) if _norm_text(x)],
        })
    return out


def load_compounds() -> List[Dict[str, Any]]:
    items = _read_json_list(COMPOUNDS_PATH) + _read_json_list(PUBCHEM_SEED_HYDRATED_PATH)
    items = _merge_unique_rows(items)
    out: List[Dict[str, Any]] = []
    for item in items:
        out.append({
            "id": _norm_text(item.get("id")),
            "name": _norm_text(item.get("name")),
            "type": _norm_lower(item.get("type") or "compound"),
            "kind": "compound",
            "targets": _normalize_target_records(item.get("targets") or []),
            "interaction_notes": [_norm_text(x) for x in (item.get("interaction_notes") or []) if _norm_text(x)],
            "status": _norm_lower(item.get("status") or "starter"),
            "source": _norm_lower(item.get("source") or "starter_registry"),
            "notes": _norm_text(item.get("notes")),
            "xrefs": [_norm_text(x) for x in (item.get("xrefs") or []) if _norm_text(x)],
            "aliases": [_norm_text(x) for x in (item.get("aliases") or []) if _norm_text(x)],
        })
    return out


def load_physiology() -> List[Dict[str, Any]]:
    items = _read_json_list(PHYSIOLOGY_PATH)
    out: List[Dict[str, Any]] = []
    for item in items:
        out.append({
            "id": _norm_text(item.get("id")),
            "name": _norm_text(item.get("name")),
            "type": _norm_lower(item.get("type") or "physiology"),
            "kind": "physiology",
            "targets": _normalize_target_records(item.get("targets") or []),
            "modalities": [_norm_text(x) for x in (item.get("modalities") or []) if _norm_text(x)],
            "status": _norm_lower(item.get("status") or "starter"),
            "source": _norm_lower(item.get("source") or "starter_registry"),
            "notes": _norm_text(item.get("notes")),
            "xrefs": [_norm_text(x) for x in (item.get("xrefs") or []) if _norm_text(x)],
        })
    return out


def get_all_diseases() -> List[Dict[str, Any]]:
    return [_copy_item(x) for x in load_diseases()]


def get_rare_diseases() -> List[Dict[str, Any]]:
    return [_copy_item(x) for x in load_diseases() if bool(x.get("rare"))]


def get_all_drugs() -> List[Dict[str, Any]]:
    return [_copy_item(x) for x in load_drugs()]


def get_all_compounds() -> List[Dict[str, Any]]:
    return [_copy_item(x) for x in load_compounds()]


def get_all_physiology() -> List[Dict[str, Any]]:
    return [_copy_item(x) for x in load_physiology()]


def get_all_candidates(include_physiology: bool = False) -> List[Dict[str, Any]]:
    rows = get_all_drugs() + get_all_compounds()
    if include_physiology:
        rows += get_all_physiology()
    return rows


def get_candidates(kind: Optional[str] = None, include_physiology: bool = False) -> List[Dict[str, Any]]:
    kind_l = _norm_lower(kind)
    if not kind_l:
        return get_all_candidates(include_physiology=include_physiology)
    if kind_l == "drug":
        return get_all_drugs()
    if kind_l == "compound":
        return get_all_compounds()
    if kind_l == "physiology":
        return get_all_physiology()
    return []


def find_disease_by_id(disease_id: str) -> Optional[Dict[str, Any]]:
    needle = _norm_text(disease_id)
    for item in load_diseases():
        if item.get("id") == needle:
            return _copy_item(item)
    return None


def find_disease_by_name(name: str) -> Optional[Dict[str, Any]]:
    needle = _norm_lower(name)
    for item in load_diseases():
        if _norm_lower(item.get("name")) == needle:
            return _copy_item(item)
        aliases = item.get("aliases") or []
        if needle in {_norm_lower(x) for x in aliases}:
            return _copy_item(item)
    return None


def _search_blob(item: Dict[str, Any]) -> str:
    parts = [item.get("id"), item.get("name"), item.get("notes"), item.get("category"), item.get("class"), item.get("type")]
    parts.extend(item.get("aliases") or [])
    parts.extend(item.get("xrefs") or [])
    parts.extend(item.get("indications") or [])
    parts.extend(item.get("active_ingredients") or [])
    parts.extend(item.get("genes") or [])
    for t in item.get("targets") or []:
        if isinstance(t, dict):
            parts.append(t.get("gene"))
    return " | ".join([_norm_text(x) for x in parts if _norm_text(x)]).lower()


def search_registry(query: str, limit: int = 25) -> Dict[str, Any]:
    q = _norm_lower(query)
    if not q:
        return {"ok": True, "results": []}
    rows = []
    buckets = [("disease", load_diseases()), ("drug", load_drugs()), ("compound", load_compounds()), ("physiology", load_physiology())]
    for bucket, items in buckets:
        for item in items:
            blob = _search_blob(item)
            if q not in blob:
                continue
            score = 1
            if q == _norm_lower(item.get("name")):
                score += 6
            elif _norm_lower(item.get("name")).startswith(q):
                score += 4
            elif q in _norm_lower(item.get("name")):
                score += 3
            if q == _norm_lower(item.get("id")):
                score += 5
            if any(q == _norm_lower(x) for x in (item.get("aliases") or [])):
                score += 4
            rows.append({"type": bucket, "score": score, "item": _copy_item(item)})
    rows.sort(key=lambda x: (-int(x.get("score", 0)), _norm_lower((x.get("item") or {}).get("name"))))
    return {"ok": True, "results": rows[: max(1, min(int(limit or 25), 100))]}


def get_disease_drug_matches(disease_id: str, limit: int = 25) -> Dict[str, Any]:
    disease = find_disease_by_id(disease_id) or find_disease_by_name(disease_id)
    if not disease:
        return {"ok": False, "disease": None, "items": []}
    disease_genes = {_norm_gene(x) for x in (disease.get("genes") or []) if _norm_gene(x)}
    disease_name_l = _norm_lower(disease.get("name"))
    disease_aliases = {_norm_lower(x) for x in (disease.get("aliases") or []) if _norm_text(x)}
    scored = []
    for drug in load_drugs():
        overlap = []
        for target in drug.get("targets") or []:
            gene = _norm_gene((target or {}).get("gene"))
            if gene and gene in disease_genes:
                overlap.append(gene)
        indication_match = False
        for ind in drug.get("indications") or []:
            low = _norm_lower(ind)
            if disease_name_l and disease_name_l in low:
                indication_match = True
                break
            if any(alias and alias in low for alias in disease_aliases):
                indication_match = True
                break
        score = len(set(overlap)) * 3 + (2 if indication_match else 0)
        if score <= 0:
            continue
        scored.append({
            "drug": _copy_item(drug),
            "score": score,
            "overlap_genes": sorted(set(overlap)),
            "indication_match": indication_match,
        })
    scored.sort(key=lambda x: (-int(x.get("score", 0)), _norm_lower((x.get("drug") or {}).get("name"))))
    return {"ok": True, "disease": _copy_item(disease), "items": scored[: max(1, min(int(limit or 25), 100))]}


def clear_registry_cache() -> None:
    return None


def registry_data_depth() -> Dict[str, int]:
    return {
        "starter_diseases": len(_read_json_list(DISEASES_PATH)),
        "starter_drugs": len(_read_json_list(DRUGS_PATH)),
        "starter_compounds": len(_read_json_list(COMPOUNDS_PATH)),
        "starter_physiology": len(_read_json_list(PHYSIOLOGY_PATH)),
        "hydrated_fda_drugs": len(_read_json_list(FDA_HYDRATED_PATH)),
        "hydrated_rxterms_drugs": len(_read_json_list(RXTERMS_HYDRATED_PATH)),
        "hydrated_mondo_rare_diseases": len(_read_json_list(MONDO_RARE_HYDRATED_PATH)),
        "hydrated_mondo_all_diseases": len(_read_json_list(MONDO_ALL_HYDRATED_PATH)),
        "hydrated_pubchem_seed_compounds": len(_read_json_list(PUBCHEM_SEED_HYDRATED_PATH)),
    }


def registry_source_manifest() -> Dict[str, Any]:
    return {
        "disease_sources": {
            "starter": len(_read_json_list(DISEASES_PATH)),
            "mondo_rare": len(_read_json_list(MONDO_RARE_HYDRATED_PATH)),
            "mondo_all": len(_read_json_list(MONDO_ALL_HYDRATED_PATH)),
        },
        "drug_sources": {
            "starter": len(_read_json_list(DRUGS_PATH)),
            "openfda": len(_read_json_list(FDA_HYDRATED_PATH)),
            "rxterms": len(_read_json_list(RXTERMS_HYDRATED_PATH)),
        },
        "compound_sources": {
            "starter": len(_read_json_list(COMPOUNDS_PATH)),
            "pubchem_seed": len(_read_json_list(PUBCHEM_SEED_HYDRATED_PATH)),
        },
        "physiology_sources": {
            "starter": len(_read_json_list(PHYSIOLOGY_PATH)),
        },
    }

from functools import lru_cache
import json
from pathlib import Path

EDITION = Path(__file__).resolve().parents[1]
REPO = EDITION.parents[1]

@lru_cache(maxsize=1)
def dataset():
    return json.loads((EDITION / 'data' / 'pilot_evidence.json').read_text(encoding='utf-8'))

def sources():
    return {s['id']: s for s in dataset()['sources']}

def valid_refs(refs):
    known = sources()
    return bool(refs) and all(r in known and all(known[r].get(k) for k in
        ('source', 'source_url', 'evidence_type', 'evidence_level', 'retrieved_at')) for r in refs)

def provenance(refs):
    if not valid_refs(refs):
        raise ValueError('Missing or unknown provenance')
    return [sources()[r] for r in dict.fromkeys(refs)]

def disease_by_id(id):
    return next((d for d in dataset()['diseases'] if d['id'] == id), None)

@lru_cache(maxsize=1)
def catalog():
    path = REPO / 'backend' / 'data' / 'registry' / 'rare_diseases_catalog_gard_2026.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []

def search(query='', limit=20):
    q = query.strip().casefold()
    curated = [dict(id=d['id'], name=d['name'], gene=d['gene'], curated=True, evidence_depth=d['evidence_depth'])
               for d in dataset()['diseases'] if q in (d['name']+' '+d['gene']).casefold()]
    names = {d['name'].casefold() for d in dataset()['diseases']}
    discovered = []
    if q:
        for i, d in enumerate(catalog()):
            if d.get('disease_name','').casefold() in names:
                continue
            if q in (d.get('disease_name','')+' '+d.get('other_names','')).casefold():
                discovered.append(dict(id=f'catalog:{i}', name=d['disease_name'], gene=None, curated=False,
                                       source_url=d.get('disease_url'), evidence_depth='Discovery only; mechanism not curated'))
    return dict(results=(curated+discovered)[:limit], total=len(curated)+len(discovered),
                catalog_entries=len(catalog()), curated_diseases=4,
                breadth_note='The inherited GARD discovery catalog includes non-monogenic conditions. Catalog breadth is not validated therapeutic coverage.')

def discovery(id):
    if not id.startswith('catalog:'):
        raise ValueError('Unknown discovery record')
    index = int(id.split(':')[1])
    if index < 0 or index >= len(catalog()):
        raise ValueError('Unknown discovery record')
    row = catalog()[index]
    return dict(id=id, name=row['disease_name'], source_url=row.get('disease_url'), evidence_depth='Discovery only',
                ranking_allowed=False, rankings=[], graph=dict(nodes=[],edges=[]),
                reason='No curated causal direction or candidate evidence. No therapeutic ranking generated.',
                next_step='Use the linked GARD resource, then obtain a sourced causal gene, variant direction and intervention evidence.')

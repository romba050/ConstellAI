from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import urlparse

EDITION = Path(__file__).resolve().parents[1]
REPO = EDITION.parents[1]

@lru_cache(maxsize=1)
def dataset():
    return json.loads((EDITION / 'data' / 'pilot_evidence.json').read_text(encoding='utf-8'))

def sources():
    return {s['id']: s for s in dataset()['sources']}

AUTHORITATIVE_HOSTS = {'pubmed.ncbi.nlm.nih.gov', 'pmc.ncbi.nlm.nih.gov', 'www.ncbi.nlm.nih.gov',
    'medlineplus.gov', 'dailymed.nlm.nih.gov', 'clinicaltrials.gov', 'reporter.nih.gov',
    'www.ebi.ac.uk', 'omim.org', 'www.orpha.net', 'rarediseases.org', 'globalgenes.org',
    'www.eurordis.org', 'angelman.org', 'cdkl5.com', 'www.cacna1a.org',
    'www.stxbp1disorders.org', 'www.pwsausa.org', 'buffaloinitiative.org'}

def valid_source(s):
    """Check the reviewed registry contract, not scientific truth by URL alone."""
    if not all(s.get(k) for k in ('source', 'source_url', 'evidence_type', 'evidence_level',
                                 'retrieved_at', 'source_family', 'verification_status', 'extracted_claim', 'uncertainty')):
        return False
    address = urlparse(s['source_url'])
    if address.scheme != 'https' or address.hostname not in AUTHORITATIVE_HOSTS or address.username or address.password:
        return False
    if s.get('claim_kind') not in {'direct_source_report', 'inferred_relationship', 'proposed_hypothesis'}:
        return False
    if (s.get('identifier') or '').startswith('PMID:'):
        pmid = s.get('pmid', '')
        if not isinstance(pmid, str) or not pmid.isdigit() or s['identifier'] != 'PMID:' + pmid:
            return False
        if address.hostname != 'pubmed.ncbi.nlm.nih.gov' or address.path != '/' + pmid + '/':
            return False
        if not all(s.get(k) for k in ('title', 'journal', 'authors', 'publication_year',
                                     'publication_types', 'study_design', 'sample_size', 'metadata_source_url')):
            return False
    return True

def valid_refs(refs):
    known = sources()
    return bool(refs) and all(r in known and valid_source(known[r]) for r in refs)

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

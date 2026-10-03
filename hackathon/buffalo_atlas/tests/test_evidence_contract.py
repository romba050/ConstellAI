import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

EDITION = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EDITION))
from atlas.data import dataset, sources, valid_source, disease_by_id
from atlas.api import disease_bundle
from atlas.graph import build_graph
from atlas.core import score_candidate

class EvidenceContractTests(unittest.TestCase):
    def test_all_papers_have_indexed_metadata_and_explicit_sample_context(self):
        papers=[s for s in sources().values() if s.get('pmid')]
        self.assertEqual(len(papers),11)
        for s in papers:
            self.assertTrue(valid_source(s),s['id'])
            self.assertTrue(s['doi']);self.assertTrue(s['journal']);self.assertTrue(s['authors'])
            self.assertIn('availability',s['sample_size'])
            self.assertTrue(s['study_design']);self.assertTrue(s['uncertainty'])

    def test_fabricated_origin_or_mismatched_pmid_fails_closed(self):
        s=copy.deepcopy(sources()['fink2017'])
        s['source_url']='https://invented-database.invalid/paper'
        self.assertFalse(valid_source(s))
        s=copy.deepcopy(sources()['fink2017']);s['pmid']='123'
        self.assertFalse(valid_source(s))

    def test_clinvar_condition_and_variant_aggregate_are_distinct(self):
        s=sources()['clinvar-155984']
        self.assertEqual(s['condition_classification'],'Pathogenic')
        self.assertEqual(s['variant_aggregate_classification'],'Pathogenic/Likely pathogenic')
        self.assertIn('no conflicts',s['review_status'])
        b=disease_bundle('angelman')
        edges=[e for e in b['graph']['edges'] if e['source']=='clinvar-155984']
        self.assertTrue(edges)
        self.assertFalse(any(e.get('mechanistic_effect') for e in edges))

    def test_funding_aims_and_ontology_terms_never_create_drug_effects(self):
        b=disease_bundle('angelman')
        self.assertTrue(b['research_programmes'])
        grant=next(n for n in b['graph']['nodes'] if n['id']=='nih:11353907')
        self.assertEqual(grant['study_subtype'],'funded_research_programme')
        for e in b['graph']['edges']:
            if 'nih:11353907' in e['source_ids'] or any(r.startswith(('MONDO:','HP:','OMIM:')) for r in e['source_ids']):
                self.assertNotIn('mechanistic_effect',e)
        self.assertEqual(b['ranking']['ranked'][0]['priority_score'],.63)

    def test_journal_prestige_and_authors_do_not_change_priority(self):
        disease=disease_by_id('angelman');candidate=dataset()['interventions'][0]
        before=score_candidate(disease,candidate)['priority_score']
        changed=copy.deepcopy(sources())
        for s in changed.values():
            if s.get('pmid'):
                s['journal']='Synthetic journal label for invariance test';s['authors']=['Synthetic test author']
        with patch('atlas.data.sources',return_value=changed),patch('atlas.core.sources',return_value=changed):
            after=score_candidate(disease,candidate)['priority_score']
        self.assertEqual(before,after)

    def test_offline_reproduction_is_deterministic_and_refuses_overwrite(self):
        spec=importlib.util.spec_from_file_location('reproduce_dataset',EDITION/'tools/reproduce_dataset.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            first=module.reproduce(Path(tmp)/'first');second=module.reproduce(Path(tmp)/'second')
            self.assertEqual(first['output_sha256'],second['output_sha256'])
            self.assertEqual(first['source_count'],39)
            for name,digest in first['output_sha256'].items():
                self.assertEqual(hashlib.sha256((Path(tmp)/'first'/name).read_bytes()).hexdigest(),digest)
            with self.assertRaises(ValueError):module.reproduce(Path(tmp)/'first')

if __name__=='__main__':unittest.main()

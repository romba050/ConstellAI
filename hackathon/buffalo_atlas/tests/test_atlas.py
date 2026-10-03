import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen, Request
from urllib.error import HTTPError

EDITION=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EDITION))
from atlas import core
from atlas.data import dataset, disease_by_id, sources, search, discovery, REPO
from atlas.graph import build_graph,validate_graph
from atlas.api import disease_bundle
from atlas.ai import extract,validate_drafts
from atlas.priors import repurposing_prior,frequent_flyer
from atlas.benchmark import report
from atlas.graph_reasoning import score_from_graph,rank_from_graph
from run import make_server

class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.d=copy.deepcopy(disease_by_id('angelman'))
        self.c=copy.deepcopy(dataset()['interventions'][0])

    def test_gain_inhibitor_favourable(self):
        self.assertEqual(core.score_direction_alignment('up','inhibit',['huang2012']),1)
    def test_gain_activator_penalised(self):
        self.assertEqual(core.score_direction_alignment('up','activate',['huang2012']),-.85)
    def test_loss_activator_favourable(self):
        self.assertEqual(core.score_direction_alignment('down','activate',['huang2012']),1)
    def test_loss_inhibitor_penalised(self):
        self.assertEqual(core.score_direction_alignment('down','inhibit',['huang2012']),-.85)
    def test_unknown_direction_never_gets_legacy_partial_credit(self):
        self.assertIsNone(core.score_direction_alignment('unknown','activate',['huang2012']))
    def test_unknown_effect_withholds(self):
        self.c['effects'][0]['effect']='modulate'
        self.assertFalse(core.score_candidate(self.d,self.c)['eligible'])
    def test_missing_evidence_withholds(self):
        self.c['effects'][0]['source_ids']=[]
        r=core.score_candidate(self.d,self.c)
        self.assertFalse(r['eligible']);self.assertIsNone(r['priority_score'])
    def test_fabricated_citation_withholds(self):
        self.c['effects'][0]['source_ids']=['invented-pmid']
        self.assertFalse(core.score_candidate(self.d,self.c)['eligible'])
    def test_partly_unsourced_claims_do_not_silently_pass(self):
        self.c['effects'].append(dict(target='UNRELATED',effect='inhibit',source_ids=[]))
        self.assertFalse(core.score_candidate(self.d,self.c)['eligible'])
    def test_wrong_direction_rejected(self):
        self.c['effects'][0]['effect']='inhibit'
        r=core.score_candidate(self.d,self.c)
        self.assertFalse(r['eligible']);self.assertLess(r['priority_score'],0);self.assertEqual(r['opposed_targets'],['UBE3A'])
    def test_spillover_penalty_lowers_rank(self):
        baseline=core.score_candidate(self.d,self.c)['priority_score']
        self.c['spillover'].append(dict(target='Other mechanism',effect='inhibit',source_ids=['king2013']))
        self.assertAlmostEqual(core.score_candidate(self.d,self.c)['priority_score'],baseline-.22)
    def test_irrelevant_target_never_adds_coverage(self):
        baseline=core.score_candidate(self.d,self.c)
        self.c['effects'].append(dict(target='IRRELEVANT',effect='restore',source_ids=['huang2012']))
        result=core.score_candidate(self.d,self.c)
        self.assertEqual(result['coverage'],baseline['coverage']);self.assertLess(result['priority_score'],baseline['priority_score'])
    def test_evidence_uncertainty_is_penalised(self):
        human=core.score_candidate(self.d,self.c)
        self.c['effects'][0]['source_ids']=['huang2012']
        animal=core.score_candidate(self.d,self.c)
        self.assertLess(animal['priority_score'],human['priority_score'])
    def test_coverage_normalized_not_a_gene_count_contest(self):
        self.d['signature'].append(dict(target='SECOND',direction='loss_of_function',weight=1,source_ids=['angelman-nlm']))
        r=core.score_candidate(self.d,self.c)
        self.assertEqual(r['coverage'],.5);self.assertLess(r['priority_score'],.63)
    def test_unresolved_gene_direction_blocks(self):
        self.assertEqual(core.rank_repurposing_candidates(disease_by_id('cacna1a'))['ranked'],[])
    def test_nonsourced_signature_not_trusted(self):
        self.d['signature'][0]['source_ids']=[]
        self.assertEqual(core.build_disease_signature(self.d),[])
    def test_invalid_numeric_weight_not_trusted(self):
        self.d['signature'][0]['weight']=float('nan')
        self.assertEqual(core.build_disease_signature(self.d),[])
    def test_unknown_spillover_blocks_rank_not_safety_zero(self):
        self.c['spillover_unknown']=True
        r=core.score_candidate(self.d,self.c)
        self.assertFalse(r['eligible']);self.assertTrue(r['spillover']['unknown'])
    def test_safety_kept_separate_no_fake_score(self):
        r=core.score_risk_burden(self.c)
        self.assertIsNone(r['score']);self.assertEqual(len(r['warnings']),2)
    def test_unsourced_safety_becomes_unknown(self):
        self.c['risk']=[dict(domain='Cardiac',label='Invented risk',source_ids=[])]
        self.assertEqual(core.score_risk_burden(self.c)['status'],'Unknown / insufficient evidence')
    def test_remaining_unmodelled_biology_not_erased(self):
        r=core.score_candidate(self.d,self.c)
        self.assertEqual(r['remaining']['uncovered_targets'],[]);self.assertGreater(len(r['remaining']['unresolved']),2)
    def test_redundant_bundle_rejected(self):
        primary=core.score_candidate(self.d,self.c)
        self.assertEqual(core.rank_complementary_candidates(self.d,primary)['candidates'],[])
    def test_opposite_direction_addon_cannot_close_deviation(self):
        primary=core.score_candidate(self.d,self.c)
        self.d['signature'].append(dict(target='SECOND',direction='loss_of_function',weight=1,source_ids=['angelman-nlm']))
        addon=copy.deepcopy(self.c);addon['id']='test-addon';addon['effects']=[dict(target='SECOND',effect='inhibit',source_ids=['huang2012'])]
        self.assertEqual(core.rank_complementary_candidates(self.d,primary,[addon])['candidates'],[])
    def test_repurposing_not_conflated_with_research_compound(self):
        ranking=core.rank_repurposing_candidates(self.d)
        self.assertEqual([r['id'] for r in ranking['ranked']],['topotecan'])
    def test_source_registry_contains_no_patient_records(self):
        self.assertNotIn('patients',dataset());self.assertNotIn('patient_records',dataset())

    def test_strong_irrelevant_evidence_cannot_dilute_uncertainty(self):
        self.c['effects'][0]['source_ids']=['huang2012']
        before=core.score_candidate(self.d,self.c)
        self.c['effects'].append(dict(target='IRRELEVANT',effect='activate',source_ids=['ganaxolone-rct']))
        # Use the actual trial source registry entry.
        self.c['effects'][-1]['source_ids']=[next(k for k,v in sources().items() if v['evidence_type']=='human_randomized_trial')]
        after=core.score_candidate(self.d,self.c)
        self.assertEqual(before['evidence']['uncertainty_penalty'],after['evidence']['uncertainty_penalty'])
        self.assertAlmostEqual(after['priority_score'],before['priority_score']-.22)
    def test_partial_invalid_signature_cannot_inflate_coverage(self):
        self.d['signature'].append(dict(target='SECOND',weight=1,direction='down',source_ids=[]))
        row=core.score_candidate(self.d,self.c)
        self.assertFalse(row['eligible']);self.assertIsNone(row['priority_score']);self.assertIsNone(row['coverage'])
    def test_duplicate_off_signature_targets_not_double_counted(self):
        self.c['effects'] += [dict(target='CDK2',effect='inhibit',source_ids=['huang2012'])]*2
        self.assertEqual(core.score_spillover(self.d['signature'],self.c)['known_count'],2)
    def test_unknown_spillover_addon_cannot_pass(self):
        self.d['signature'].append(dict(target='SECOND',weight=1,direction='down',source_ids=['angelman-nlm']))
        primary=core.score_candidate(self.d,self.c)
        addon=copy.deepcopy(self.c);addon['id']='addon';addon['effects']=[dict(target='SECOND',effect='activate',source_ids=['fink2017'])];addon['spillover']=[];addon['spillover_unknown']=True
        self.assertEqual(core.rank_complementary_candidates(self.d,primary,[addon])['candidates'],[])

class GraphProductTests(unittest.TestCase):
    def test_all_four_pilots_integrity(self):
        for disease in dataset()['diseases']:
            self.assertTrue(validate_graph(build_graph(disease)))
    def test_required_node_types(self):
        types={n['type'] for n in build_graph(disease_by_id('angelman'))['nodes']}
        self.assertTrue({'Disease','Gene','Phenotype','Study','Patient Group','Drug','Trial'}.issubset(types))
    def test_every_edge_has_verified_source_metadata(self):
        graph=build_graph(disease_by_id('angelman'))
        for item in graph['nodes']+graph['edges']:
            for s in item['provenance']:
                for key in ('source','source_url','retrieved_at','evidence_type','evidence_level'):
                    self.assertTrue(s[key])
    def test_unsourced_edge_rejected(self):
        graph=build_graph(disease_by_id('angelman'));graph['edges'][0]['source_ids']=[]
        with self.assertRaises(ValueError):validate_graph(graph)
    def test_dangling_edge_rejected(self):
        graph=build_graph(disease_by_id('angelman'));graph['edges'][0]['target']='missing'
        with self.assertRaises(ValueError):validate_graph(graph)
    def test_duplicate_node_rejected(self):
        graph=build_graph(disease_by_id('angelman'));graph['nodes'].append(graph['nodes'][0])
        with self.assertRaises(ValueError):validate_graph(graph)
    def test_substituted_provenance_rejected(self):
        graph=build_graph(disease_by_id('angelman'));graph['edges'][0]['provenance']=[]
        with self.assertRaises(ValueError):validate_graph(graph)
    def test_patient_group_and_cited_studies_all_diseases(self):
        for d in dataset()['diseases']:
            b=disease_bundle(d['id'])
            self.assertTrue(b['next_steps']['patient'][0]['url']);self.assertTrue(b['studies'])
    def test_trial_status_honest(self):
        trials={t['id']:t for t in dataset()['trials']}
        self.assertEqual(trials['NCT05127226']['status'],'ACTIVE_NOT_RECRUITING')
        self.assertEqual(trials['NCT03572933']['status'],'COMPLETED')
    def test_mimicry_and_falsification_exist(self):
        b=disease_bundle('angelman')
        self.assertEqual(len(b['surrogates']),2);self.assertTrue(b['experiment']['falsifier']);self.assertTrue(b['experiment']['sources'])
    def test_unvalidated_physio_hidden(self):
        self.assertEqual(disease_bundle('angelman')['physiology']['candidates'],[])
    def test_causal_gene_search(self):
        self.assertEqual(search('UBE3A')['results'][0]['id'],'angelman')
    def test_arbitrary_discovery_does_not_rank(self):
        rows=search('cystic')['results'];self.assertTrue(rows)
        d=discovery(next(r['id'] for r in rows if not r['curated']))
        self.assertFalse(d['ranking_allowed']);self.assertEqual(d['rankings'],[]);self.assertEqual(d['graph']['edges'],[])
    def test_search_result_cap(self):
        self.assertLessEqual(len(search('syndrome')['results']),20)
    def test_negative_catalog_id_rejected(self):
        with self.assertRaises(ValueError):discovery('catalog:-1')
    def test_hero_path_has_reusable_asset_and_community(self):
        b=disease_bundle('angelman');h=b['hero_journey']
        self.assertTrue(h['asset']['source_ids']);self.assertIn('availability',h['asset'])
        self.assertTrue(h['neighbor']['organization']);self.assertTrue(h['collaboration']['limitation'])
    def test_neighbor_not_given_ube3a_treatment(self):
        graph=build_graph(disease_by_id('angelman'))
        self.assertFalse(any(e['source']=='topotecan' and e['target']=='prader-willi' for e in graph['edges']))
        self.assertIn('not',dataset()['hero_journey']['neighbor']['caveat'])
    def test_counterexample_explicitly_inference(self):
        edge=next(e for e in build_graph(disease_by_id('angelman'))['edges'] if e['type']=='NOT_IN_SAME_RESTORATION_CLUSTER')
        self.assertEqual(edge['classification'],'INFERENCE');self.assertEqual(edge['observed_or_inferred'],'inferred')
    def test_all_graph_items_expose_evidence_context(self):
        for d in dataset()['diseases']:
            g=build_graph(d)
            for item in g['nodes']+g['edges']:
                self.assertIn(item['classification'],{'FACT','INFERENCE','HYPOTHESIS','CLINICAL EVIDENCE'})
                self.assertTrue(item['contradictory_evidence']);self.assertTrue(item['observed_or_inferred'])
    def test_comparison_has_three_distinct_interventions(self):
        b=disease_bundle('angelman')
        self.assertEqual(len({r['id'] for r in b['comparison']}),3)
        self.assertTrue(all(r['risk_burden']['score'] is None for r in b['comparison']))
    def test_hypothesis_and_clinical_evidence_separate(self):
        edges=build_graph(disease_by_id('cdkl5'))['edges']
        self.assertTrue(any(e['classification']=='CLINICAL EVIDENCE' for e in edges))
        self.assertEqual(disease_bundle('cdkl5')['ranking']['ranked'],[])

class AITests(unittest.TestCase):
    def setUp(self):
        self.nodes={n['id'] for n in build_graph(disease_by_id('angelman'))['nodes']}
        self.draft=copy.deepcopy(dataset()['ai_drafts'][0])
    def test_offline_ai_replay_traceable(self):
        r=extract('huang2012',self.nodes)
        self.assertEqual(r['status'],'proposal_only');self.assertEqual(len(r['relationships']),1)
    def test_fabricated_citation_rejected(self):
        self.draft['source_id']='fake'
        with self.assertRaises(ValueError):validate_drafts([self.draft],'huang2012',self.nodes)
    def test_unsupported_span_rejected(self):
        self.draft['source_span']='This medicine is safe and effective in patients'
        with self.assertRaises(ValueError):validate_drafts([self.draft],'huang2012',self.nodes)
    def test_unknown_node_rejected(self):
        self.draft['object']='gene:INVENTED'
        with self.assertRaises(ValueError):validate_drafts([self.draft],'huang2012',self.nodes)
    def test_ai_cannot_supply_scores(self):
        self.draft['priority_score']=999
        r=validate_drafts([self.draft],'huang2012',self.nodes)
        self.assertNotIn('priority_score',r[0])
    def test_extraction_does_not_mutate_graph(self):
        before=build_graph(disease_by_id('angelman'));extract('huang2012',self.nodes)
        self.assertEqual(before,build_graph(disease_by_id('angelman')))
    def test_live_unavailable_fails_closed(self):
        with patch('atlas.ai.urllib.request.urlopen',side_effect=OSError('Offline')):
            self.assertEqual(extract('huang2012',self.nodes,live=True)['status'],'unavailable')
    def test_live_model_valid_draft_through_adapter(self):
        response=io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps({'relationships':[self.draft]})}}]}).encode())
        with patch('atlas.ai.urllib.request.urlopen',return_value=response):
            self.assertEqual(extract('huang2012',self.nodes,live=True)['status'],'proposal_only')
    def test_openai_missing_key_honest_no_network(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':''}),patch('atlas.ai.urllib.request.urlopen') as call:
            r=extract('huang2012',self.nodes,live=True,provider='openai')
        self.assertEqual(r['status'],'needs_configuration');call.assert_not_called()
    def test_openai_structured_adapter_success_and_no_storage(self):
        output={'id':'test-response','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'relationships':[self.draft]})}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-placeholder'}),patch('atlas.ai.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(output).encode())) as call:
            r=extract('huang2012',self.nodes,live=True,provider='openai')
        self.assertEqual(r['status'],'proposal_only')
        request=call.call_args.args[0];body=json.loads(request.data)
        self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        self.assertFalse(body['store']);self.assertTrue(body['text']['format']['strict'])
        self.assertEqual(body['text']['format']['schema']['properties']['relationships']['items']['properties']['source_id']['enum'],['huang2012'])
    def test_openai_fabricated_span_fails_closed(self):
        self.draft['source_span']='Fabricated clinical safety claim'
        output={'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'relationships':[self.draft]})}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-placeholder'}),patch('atlas.ai.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(output).encode())):
            self.assertEqual(extract('huang2012',self.nodes,live=True,provider='openai')['status'],'unavailable')
    def test_openai_failure_does_not_change_ranking(self):
        before=disease_bundle('angelman')['ranking']
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-placeholder'}),patch('atlas.ai.urllib.request.urlopen',side_effect=OSError('No access')):
            self.assertEqual(extract('huang2012',self.nodes,live=True,provider='openai')['status'],'unavailable')
        self.assertEqual(before,disease_bundle('angelman')['ranking'])

class PriorGraphBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.d=disease_by_id('angelman');self.c=copy.deepcopy(dataset()['interventions'][0])
    def test_disease_specific_prior_not_global_popularity(self):
        self.assertEqual(repurposing_prior('angelman','topotecan')['score'],.30)
        self.assertIsNone(repurposing_prior('cdkl5','topotecan')['score'])
    def test_clinical_prior_does_not_unblock_causal_restoration(self):
        b=disease_bundle('cdkl5');c=b['comparison'][0]
        self.assertEqual(c['repurposing_prior']['score'],.80)
        self.assertFalse(c['eligible']);self.assertIsNone(c['priority_score']);self.assertEqual(b['ranking']['ranked'],[])
    def test_prior_does_not_change_mechanistic_dimensions(self):
        a=core.score_candidate(self.d,self.c,[]);b=core.score_candidate(self.d,self.c)
        for key in ('priority_score','coverage','direction_alignment','risk_burden','remaining','eligible'):
            self.assertEqual(a[key],b[key])
    def test_frequent_flyer_four_links_halves_positive_priority(self):
        records=[dict(candidate_id='topotecan',disease_id='synthetic-test-'+str(i),source_ids=['huang2012'],kind='preclinical_mechanism') for i in range(4)]
        r=frequent_flyer(self.c,.63,records)
        self.assertEqual(r['factor'],.5);self.assertEqual(r['adjusted_priority'],.315)
    def test_duplicate_pair_cannot_increase_degree(self):
        r=copy.deepcopy(dataset()['known_relationships'][0])
        self.assertEqual(frequent_flyer(self.c,.63,[r,r])['local_disease_degree'],1)
    def test_unverified_pair_not_counted_as_prior_or_degree(self):
        r=dict(candidate_id='topotecan',disease_id='angelman',source_ids=['fake'],kind='clinical_symptom_evidence')
        self.assertIsNone(repurposing_prior('angelman','topotecan',[r])['score'])
        self.assertEqual(frequent_flyer(self.c,.63,[r])['local_disease_degree'],0)
    def test_normalisation_cannot_improve_negative_score(self):
        self.assertEqual(frequent_flyer(self.c,-1.22)['adjusted_priority'],-1.22)
        self.assertIsNone(frequent_flyer(self.c,None)['adjusted_priority'])
    def test_graph_projection_matches_adapter_and_lists_edges(self):
        r=score_from_graph(self.d,self.c)
        self.assertEqual(r['priority_score'],core.score_candidate(self.d,self.c)['priority_score'])
        self.assertGreaterEqual(len(r['graph_edge_ids']),3)
    def test_removing_intervention_graph_edge_withholds_score(self):
        g=build_graph(self.d)
        g['edges']=[e for e in g['edges'] if not(e['source']=='topotecan' and e['target']=='gene:UBE3A')]
        r=score_from_graph(self.d,self.c,g)
        self.assertFalse(r['eligible']);self.assertIsNone(r['priority_score'])
        self.assertEqual(rank_from_graph(self.d,g,[self.c])['ranked'],[])
    def test_wrong_direction_in_graph_blocks_ranking(self):
        g=build_graph(self.d)
        next(e for e in g['edges'] if e['source']=='topotecan' and e['target']=='gene:UBE3A')['mechanistic_effect']='inhibit'
        r=score_from_graph(self.d,self.c,g)
        self.assertFalse(r['eligible']);self.assertLess(r['priority_score'],0)
    def test_missing_spillover_graph_edge_is_unknown_not_zero(self):
        g=build_graph(self.d)
        g['edges']=[e for e in g['edges'] if not(e['source']=='topotecan' and e['type']=='INTERVENTION_AFFECTS_OFF_SIGNATURE_BIOLOGY')]
        self.assertFalse(score_from_graph(self.d,self.c,g)['eligible'])
    def test_benchmark_positive_prior_actually_withheld(self):
        for mode in report().values():
            self.assertEqual(mode['n'],4)
            self.assertTrue(all(f['prior_after_withholding'] is None for f in mode['folds']))
            self.assertTrue(all(f['candidate_pool_size']==4 for f in mode['folds']))
    def test_benchmark_source_disjoint_abstentions_count_as_misses(self):
        r=report()['source_disjoint'];self.assertEqual(r['abstentions'],4);self.assertEqual(r['hit_at_1'],0);self.assertEqual(r['mrr'],0)
    def test_benchmark_clinical_and_preclinical_strata_separate(self):
        r=report()['relation_only']
        self.assertEqual(r['strata']['clinical_symptom_evidence']['n'],1)
        self.assertEqual(r['strata']['preclinical_mechanism']['n'],3)
        self.assertEqual(r['strata']['clinical_symptom_evidence']['abstentions'],1)
        self.assertEqual(r['wrong_disease_eligible'],0)

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server(0);cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def get_json(self,path):
        with urlopen(self.base+path,timeout=5) as r:return json.load(r)
    def test_health_clean_start(self):
        self.assertEqual(self.get_json('/api/health')['status'],'ok')
    def test_all_diseases_load_over_http(self):
        for d in dataset()['diseases']:
            self.assertEqual(self.get_json('/api/diseases/'+d['id'])['disease']['id'],d['id'])
    def test_root_serves_ui(self):
        with urlopen(self.base,timeout=5) as r:
            self.assertIn(b'MEDR5 Atlas',r.read());self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])
    def test_demo_route_cached_and_offline(self):
        with patch('atlas.ai.urllib.request.urlopen',side_effect=OSError('Offline')):
            with urlopen(self.base+'/demo',timeout=5) as r:
                self.assertIn(b'MEDR5 Atlas',r.read())
            self.assertTrue(disease_bundle('angelman')['ranking']['ranked'])
    def test_collaboration_brief_cited_reviewable(self):
        doc=self.get_json('/api/brief?id=angelman&type=collaboration')
        self.assertIn('https://www.pnas.org/',doc['text']);self.assertIn('does not imply shared treatment',doc['text'])
        self.assertIn('Falsifier:',doc['text'])
    def test_download_evidence_brief_real_attachment(self):
        with urlopen(self.base+'/api/brief?id=angelman&download=1',timeout=5) as r:
            self.assertIn('attachment;',r.headers['Content-Disposition'])
            text=r.read().decode('utf-8')
            self.assertIn('Clinical safety / quantitative organ burden unknown',text)
            self.assertIn('https://clinicaltrials.gov/study/NCT05127226',text)
    def test_unsupported_collaboration_brief_withheld(self):
        with self.assertRaises(HTTPError) as caught:urlopen(self.base+'/api/brief?id=cdkl5&type=collaboration',timeout=5)
        self.assertEqual(caught.exception.code,400)
    def test_network_unavailable_demo_still_works(self):
        with patch('atlas.ai.urllib.request.urlopen',side_effect=OSError('No external API')):
            b=disease_bundle('angelman')
            self.assertTrue(b['ranking']['ranked']);self.assertTrue(b['graph']['edges']);self.assertTrue(b['experiment']['sources'])
    def test_offline_extraction_api(self):
        request=Request(self.base+'/api/ai/extract',data=json.dumps({'source_id':'huang2012'}).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=5) as r:self.assertEqual(json.load(r)['status'],'proposal_only')
    def test_invalid_post_body(self):
        request=Request(self.base+'/api/ai/extract',data=b'[]',headers={'Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as caught:urlopen(request,timeout=5)
        self.assertEqual(caught.exception.code,400)
    def test_other_origin_rejected(self):
        request=Request(self.base+'/api/ai/extract',data=b'{}',headers={'Origin':'https://other-site.example','Content-Type':'application/json'})
        with self.assertRaises(HTTPError) as caught:urlopen(request,timeout=5)
        self.assertEqual(caught.exception.code,403)
    def test_path_traversal_denied(self):
        with self.assertRaises(HTTPError) as caught:urlopen(self.base+'/%2e%2e/run.py',timeout=5)
        self.assertEqual(caught.exception.code,404)

if __name__=='__main__':unittest.main(verbosity=2)

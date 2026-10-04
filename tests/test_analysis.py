"""Research-priority arithmetic, abstention and source-bound model verification."""
import copy
import itertools
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from atlas import llm
from atlas.analysis.models import AnalyzeResponse, Candidate
from atlas.analysis.graph import GraphIntegrityError, build_graph, disease_node_id, validate_graph
from atlas.analysis.ranking import load_weights, rank_candidates, score_candidate
from atlas.analysis.service import AnalysisService, EvidenceIntegrityError, NO_CANDIDATE, source_references


def assessment(value, evidence_type="preclinical", source_ids=None):
    return {"value": value, "summary": "Test-curated model evidence.", "evidence_type": evidence_type,
            "source_ids": ["test-source"] if source_ids is None else source_ids}


def candidate(cid="test-candidate", status="research_hypothesis"):
    raw = {
        "id": cid, "compound_name": f"Synthetic {cid}", "therapeutic_role": "mechanism_targeting",
        "mechanism_of_action": {"summary": "Test-curated model evidence.", "evidence_type": "preclinical", "source_ids": ["test-source"]},
        "mechanism_alignment": assessment(.8), "variant_effect_compatibility": assessment(.6),
        "human_evidence": assessment(.2, "human_observational"), "preclinical_evidence": assessment(.8),
        "phenotype_relevance": assessment(.9), "evidence_quality": assessment(.7),
        "toxicity": assessment(.2), "organ_burden": assessment(.4), "drug_interactions": assessment(.1),
        "off_target_spillover": assessment(.3), "uncertainty": assessment(.5),
        "status": status, "rationale": "Synthetic fixture; no medical recommendation.",
        "next_validation_step": "Review test-curated model evidence.",
    }
    return raw


def evidence(candidates=None):
    claim = {"summary": "Test-curated model evidence.", "evidence_type": "preclinical", "source_ids": ["test-source"]}
    return {
        "reviewed_on": "2026-10-04",
        "sources": [{"id": "test-source", "title": "Synthetic test record", "url": "https://example.com/test-record",
                     "evidence_type": "preclinical", "reviewed_on": "2026-10-04", "scope": "Synthetic fixture only",
                     "excerpt": "Test-curated model evidence."}],
        "profiles": [{
            "aliases": ["STXBP1-related disorder", "DEE4", "STXBP1"],
            "disease": {"id": "MONDO:0012812", "name": "Developmental and epileptic encephalopathy, 4", "source_ids": ["test-source"]},
            "gene": "STXBP1", "variant_effect": {**claim, "effect": "variant_dependent", "scope": "disease_context"},
            "functional_mechanism": copy.deepcopy(claim), "pathway": copy.deepcopy(claim),
            "candidate_treatments": candidates if candidates is not None else [candidate()],
            "related_disease_evidence": [],
            "recommended_next_experiment": {"title": "Synthetic verification", "question": "Does the model replicate?",
                "design": "Compare controlled test fixtures.", "readouts": ["Fixture validation"],
                "falsification": "Reject an invalid fixture.", "prerequisites": ["Test record"],
                "source_ids": ["test-source"], "status": "proposed_research"},
            "collaborators_or_assets": [], "limitations": ["Synthetic data is only for unit tests."],
        }],
    }


def fake_atlas():
    return SimpleNamespace(
        diseases={
            "MONDO:0012812": {"id": "MONDO:0012812", "name": "Developmental and epileptic encephalopathy, 4",
                "genes": ["STXBP1"], "synonyms": ["DEE4", "ambiguous disease"], "xrefs": ["OMIM:612164"],
                "phenotypes": [{"hp": "HP:0001250", "refs": ["PMID:18469812"]},
                               {"hp": "HP:0001263", "refs": ["PMID:999999999"]}]},
            "MONDO:0033372": {"id": "MONDO:0033372", "name": "Developmental and epileptic encephalopathy, 63",
                "genes": ["CPLX1"], "synonyms": ["DEE63", "ambiguous disease"], "xrefs": []},
        },
        genes={"STXBP1": {"diseases": ["MONDO:0012812"]}, "CPLX1": {"diseases": ["MONDO:0033372"]},
               "MULTI": {"diseases": ["MONDO:0012812", "MONDO:0033372"]}},
        hpo={"HP:0001250": {"name": "Seizure"}, "HP:0001263": {"name": "Global developmental delay"}},
    )


def service(raw=None):
    return AnalysisService(atlas=fake_atlas(), evidence=evidence() if raw is None else raw)


def typed_candidate(raw):
    breakdown = score_candidate(raw)
    return Candidate.model_validate({**raw, "sources": evidence()["sources"], "final_score": breakdown.final_score,
                                    "score_breakdown": breakdown.model_dump(), "rank": None})


class RankingTests(unittest.TestCase):
    def test_known_score_math_and_shared_organ_penalty(self):
        result = score_candidate(candidate())
        self.assertEqual(result.positive_total, 64.5)
        self.assertEqual(result.penalty_total, 17.5)
        self.assertEqual(result.final_score, 47)
        self.assertEqual([t.component for t in result.positive_components], list(load_weights()["positive"]))
        organ = result.risk_penalties[0]
        self.assertEqual((organ.input_value, organ.used_value, organ.contribution), (.4, .4, 6))
        self.assertEqual(sum(t.contribution for t in result.risk_penalties), result.penalty_total)

    def test_unknowns_grant_no_credit_and_full_risks(self):
        raw = candidate()
        for field in load_weights()["positive"]:
            raw[field]["value"] = None
        for field in ("toxicity", "organ_burden", "drug_interactions", "off_target_spillover", "uncertainty"):
            raw[field]["value"] = None
        result = score_candidate(raw)
        self.assertEqual(result.positive_total, 0)
        self.assertEqual(result.penalty_total, 50)
        self.assertEqual(result.unclamped_score, -50)
        self.assertEqual(result.final_score, 0)
        self.assertTrue(all(t.used_value == 1 for t in result.risk_penalties))

    def test_one_unknown_organ_input_uses_full_shared_penalty(self):
        raw = candidate()
        raw["toxicity"]["value"] = None
        organ = score_candidate(raw).risk_penalties[0]
        self.assertIsNone(organ.input_value)
        self.assertEqual((organ.used_value, organ.contribution), (1, 15))

    def test_upper_bound_clamped_and_bad_missing_policy_rejected(self):
        raw = candidate()
        for field in load_weights()["positive"]:
            raw[field]["value"] = 1
        for field in ("toxicity", "organ_burden", "drug_interactions", "off_target_spillover", "uncertainty"):
            raw[field]["value"] = 0
        self.assertEqual(score_candidate(raw).final_score, 100)
        weights = load_weights()
        weights["positive"]["mechanism_alignment"] = 40
        result = score_candidate(raw, weights)
        self.assertEqual((result.unclamped_score, result.final_score), (110, 100))
        weights["unknown_risk_value"] = 0
        with self.assertRaises(ValueError):
            score_candidate(raw, weights)

    def test_permutations_have_same_stable_order_and_ineligible_unranked(self):
        a, b = typed_candidate(candidate("a")), typed_candidate(candidate("b"))
        rejected = typed_candidate(candidate("rejected", "rejected"))
        rejected.final_score = 99
        insufficient = typed_candidate(candidate("insufficient", "insufficient_evidence"))
        insufficient.final_score = 100
        for permutation in itertools.permutations([a, b, rejected, insufficient]):
            rows = rank_candidates(list(permutation))
            self.assertEqual([(r.id, r.rank) for r in rows], [("a", 1), ("b", 2), ("insufficient", None), ("rejected", None)])

    def test_score_never_promotes_curator_status_and_evidence_gates_downgrade(self):
        supported = typed_candidate(candidate("supported", "supported_candidate"))
        result = rank_candidates([supported])[0]
        self.assertEqual(result.status, "research_hypothesis")  # score 47 < supported threshold
        raw = candidate("unresolved")
        raw["variant_effect_compatibility"]["value"] = None
        result = rank_candidates([typed_candidate(raw)])[0]
        self.assertEqual((result.status, result.rank), ("insufficient_evidence", None))
        raw = candidate("weak")
        for field in load_weights()["positive"]:
            raw[field]["value"] = 0.1
        result = rank_candidates([typed_candidate(raw)])[0]
        self.assertEqual((result.status, result.rank), ("insufficient_evidence", None))


class AnalysisTests(unittest.TestCase):
    def test_exact_alias_id_and_gene_have_same_identity(self):
        for query in ("STXBP1-related disorder", "stxbp1", "DEE4", "MONDO:0012812", "OMIM:612164"):
            result = service().analyze({"disease": query})
            AnalyzeResponse.model_validate(result.model_dump())
            self.assertEqual(result.disease.id, "MONDO:0012812")
            self.assertEqual(result.gene, "STXBP1")
            self.assertEqual(result.best_hypothesis_id, "test-candidate")

    def test_unknown_disease_and_cplx1_have_schema_shaped_abstention(self):
        for query in ("unknown rare condition", "CPLX1", "MONDO:0033372"):
            result = service().analyze({"disease": query, "use_openai": True})
            AnalyzeResponse.model_validate(result.model_dump())
            self.assertEqual(result.conclusion, NO_CANDIDATE)
            self.assertEqual(result.candidate_treatments, [])
            self.assertIsNone(result.best_hypothesis_id)
            self.assertEqual(result.analysis_status, "insufficient_evidence")

    def test_unknown_disease_is_not_substituted_with_given_gene(self):
        result = service().analyze({"disease": "unknown rare condition", "gene": "STXBP1"})
        self.assertIsNone(result.disease.id)
        self.assertEqual(result.candidate_treatments, [])
        self.assertEqual(result.gene, "STXBP1")

    def test_conflicting_gene_and_ambiguous_names_refuse_safely(self):
        result = service().analyze({"disease": "DEE4", "gene": "CPLX1"})
        self.assertEqual(result.disease.id, "MONDO:0012812")
        self.assertEqual(result.conclusion, NO_CANDIDATE)
        self.assertTrue(any("conflicts" in text for text in result.limitations))
        for query in ("MULTI", "ambiguous disease"):
            result = service().analyze({"disease": query})
            self.assertIsNone(result.disease.id)
            self.assertEqual(result.candidate_treatments, [])
            self.assertTrue(any("multiple" in text or "ambiguous" in text for text in result.limitations))

    def test_every_nonempty_variant_withholds_all_ranks(self):
        for variant in ("c.123A>T", "p.Arg190Trp", "truncating loss of function", "ClinVar pathogenic", "<script>test</script>"):
            result = service().analyze({"disease": "DEE4", "variant": variant})
            self.assertEqual((result.variant_effect.effect, result.variant_effect.scope), ("unknown", "unresolved"))
            self.assertEqual(result.analysis_status, "insufficient_evidence")
            self.assertEqual(result.conclusion, NO_CANDIDATE)
            self.assertIsNone(result.best_hypothesis_id)
            self.assertTrue(result.candidate_treatments)
            for c in result.candidate_treatments:
                self.assertIsNone(c.rank)
                self.assertEqual(c.status, "insufficient_evidence")
                self.assertIsNone(c.variant_effect_compatibility.value)
                self.assertEqual(c.uncertainty.value, 1)
                self.assertTrue(source_references(c) <= {s.id for s in c.sources})

    def test_source_ledger_closure_and_no_stale_candidate_source_copies(self):
        result = service().analyze({"disease": "DEE4"})
        self.assertEqual(source_references(result), {s.id for s in result.sources})
        for mutate in ("missing", "duplicate", "altered", "prefilled-score"):
            raw = evidence()
            if mutate == "missing":
                raw["profiles"][0]["pathway"]["source_ids"] = ["does-not-exist"]
            elif mutate == "duplicate":
                raw["sources"].append(copy.deepcopy(raw["sources"][0]))
            elif mutate == "altered":
                source = copy.deepcopy(raw["sources"][0])
                source["scope"] = "Invented scope"
                raw["profiles"][0]["candidate_treatments"][0]["sources"] = [source]
            else:
                raw["profiles"][0]["candidate_treatments"][0]["final_score"] = 100
            with self.assertRaises(EvidenceIntegrityError):
                service(raw).analyze({"disease": "DEE4"})

    def test_blank_input_rejected_and_blank_variant_means_no_variant(self):
        with self.assertRaises(ValueError):
            service().analyze({"disease": "   "})
        result = service().analyze({"disease": " DEE4 ", "gene": " stxbp1 ", "variant": "  "})
        self.assertIsNone(result.variant)
        self.assertEqual(result.candidate_treatments[0].rank, 1)


class KnowledgeGraphTests(unittest.TestCase):
    def test_graph_claims_and_endpoints_are_closed_and_scoring_is_unchanged(self):
        result = service().analyze({"disease": "DEE4"})
        graph = result.knowledge_graph
        ids = {n.id for n in graph.nodes}
        source_ids = {s.id for s in result.sources}
        self.assertEqual(result.schema_version, "constellai-analysis-v2")
        self.assertTrue(graph.nodes)
        self.assertTrue(graph.edges)
        self.assertTrue(source_references(graph) <= source_ids)
        self.assertEqual(validate_graph(graph, result.sources), graph)
        for edge in graph.edges:
            self.assertIn(edge.source, ids)
            self.assertIn(edge.target, ids)
            self.assertTrue(edge.scope)
            self.assertTrue(edge.confidence_basis)
            if edge.assertion != "unknown":
                self.assertTrue(edge.claim.source_ids)
        for c in result.candidate_treatments:
            self.assertEqual(c.score_breakdown, score_candidate(candidate(c.id)))
        projected = build_graph(result, fake_atlas())
        self.assertEqual(projected, graph)

    def test_graph_order_stable_across_candidate_and_source_permutations(self):
        rows = [candidate("b"), candidate("a"), candidate("tool", "insufficient_evidence")]
        baseline = service(evidence(rows)).analyze({"disease": "DEE4"}).knowledge_graph
        for permutation in itertools.permutations(rows):
            raw = evidence(list(permutation))
            raw["sources"].reverse()
            result = service(raw).analyze({"disease": "DEE4"})
            self.assertEqual(result.knowledge_graph, baseline)

    def test_hpo_annotation_requires_exact_reviewed_reference(self):
        raw = evidence()
        raw["sources"].append({"id": "test-hpo-paper", "title": "Synthetic HPO reference", "url": "https://example.com/hpo-record",
            "evidence_type": "human_observational", "reviewed_on": "2026-10-04", "scope": "Synthetic test; PMID:18469812.",
            "excerpt": "Synthetic test reference, not clinical evidence."})
        result = service(raw).analyze({"disease": "DEE4"})
        phenotypes = [n for n in result.knowledge_graph.nodes if n.kind == "phenotype"]
        self.assertEqual([n.id for n in phenotypes], ["phenotype:HP:0001250"])
        self.assertEqual(phenotypes[0].source_ids, ["test-hpo-paper"])
        self.assertIn("test-hpo-paper", {s.id for s in result.sources})
        edge = next(e for e in result.knowledge_graph.edges if e.relationship_type == "annotated_phenotype")
        self.assertIn("No new phenotype validation", edge.scope)
        self.assertNotIn("phenotype:HP:0001263", {n.id for n in result.knowledge_graph.nodes})

    def test_entered_variant_is_separate_from_reported_example_and_unresolved(self):
        raw = evidence()
        raw["sources"][0]["excerpt"] = "Synthetic L446F model observation."
        raw["profiles"][0]["variant_effect"]["summary"] = "Synthetic L446F model evidence only."
        result = service(raw).analyze({"disease": "DEE4", "variant": "L446F"})
        variants = [n for n in result.knowledge_graph.nodes if n.kind == "variant"]
        self.assertEqual(len(variants), 2)
        entered = next(n for n in variants if ":entered:" in n.id)
        reported = next(n for n in variants if ":reported:" in n.id)
        self.assertNotEqual(entered.id, reported.id)
        self.assertEqual(entered.source_ids, [])
        self.assertEqual(reported.source_ids, ["test-source"])
        edge = next(e for e in result.knowledge_graph.edges if e.target == entered.id)
        self.assertEqual((edge.assertion, edge.confidence, edge.claim.evidence_type), ("unknown", "unresolved", "unknown"))
        self.assertEqual(edge.claim.source_ids, [])
        self.assertTrue(all(c.rank is None and c.status == "insufficient_evidence" for c in result.candidate_treatments))
        self.assertEqual(result.variant_effect.effect, "unknown")

    def test_unknown_and_known_without_profile_keep_honest_identity_graph(self):
        for query in ({"disease": "CPLX1"}, {"disease": "unknown rare condition", "gene": "STXBP1"}):
            result = service().analyze(query)
            self.assertTrue(any(n.kind == "disease" for n in result.knowledge_graph.nodes))
            self.assertFalse(any(n.kind in {"candidate", "mechanism", "pathway", "phenotype"} for n in result.knowledge_graph.nodes))
            self.assertFalse(any(e.assertion != "unknown" for e in result.knowledge_graph.edges))
            self.assertEqual(result.conclusion, NO_CANDIDATE)

    def test_conflicting_gene_is_explicit_unresolved_input(self):
        result = service().analyze({"disease": "DEE4", "gene": "CPLX1"})
        edge = next(e for e in result.knowledge_graph.edges if e.relationship_type == "unresolved_input_gene")
        self.assertEqual((edge.assertion, edge.confidence), ("unknown", "unresolved"))
        self.assertEqual(edge.claim.source_ids, [])
        node = next(n for n in result.knowledge_graph.nodes if n.id == edge.target)
        self.assertEqual(node.label, "CPLX1")
        self.assertIn("conflicts", node.description)
        self.assertEqual(result.candidate_treatments, [])

    def test_dangling_duplicate_and_unsourced_biology_fail_closed(self):
        result = service().analyze({"disease": "DEE4"})
        for mutation in ("endpoint", "source", "duplicate-node", "duplicate-edge", "uncited", "therapy-claim"):
            graph = result.knowledge_graph.model_copy(deep=True)
            if mutation == "endpoint":
                graph.edges[0].target = "does-not-exist"
            elif mutation == "source":
                graph.edges[0].claim.source_ids = ["does-not-exist"]
            elif mutation == "duplicate-node":
                graph.nodes.append(graph.nodes[0].model_copy(deep=True))
            elif mutation == "duplicate-edge":
                graph.edges.append(graph.edges[0].model_copy(deep=True))
            elif mutation == "uncited":
                graph.edges[0].claim.source_ids = []
            else:
                graph.edges[0].relationship_type = "treats"
            with self.assertRaises(GraphIntegrityError):
                validate_graph(graph, result.sources)

    def test_investigator_requires_explicit_asset_and_grounded_identity(self):
        raw = evidence()
        raw["sources"][0]["title"] = "Synthetic author Test Investigator"
        result = service(raw).analyze({"disease": "DEE4"})
        self.assertFalse(any(n.kind == "investigator" for n in result.knowledge_graph.nodes))
        asset = {"name": "Test Investigator", "kind": "investigator", "description": "Synthetic identity only.",
            "url": "https://example.com/test-investigator", "source_ids": ["test-source"],
            "access_status": "No contact or availability established."}
        raw["profiles"][0]["collaborators_or_assets"] = [asset]
        result = service(raw).analyze({"disease": "DEE4"})
        investigator = next(n for n in result.knowledge_graph.nodes if n.kind == "investigator")
        self.assertEqual(investigator.label, "Test Investigator")
        asset["name"] = "Invented unrelated person"
        with self.assertRaises(EvidenceIntegrityError):
            service(raw).analyze({"disease": "DEE4"})

    def test_cited_unsafe_url_is_rejected(self):
        result = service().analyze({"disease": "DEE4"})
        graph = result.knowledge_graph.model_copy(deep=True)
        graph.nodes[0].url = "javascript:alert(1)"
        with self.assertRaises(GraphIntegrityError):
            validate_graph(graph, result.sources)


class ProductionGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from atlas.store import Atlas
        cls.service = AnalysisService(atlas=Atlas())

    def test_source_reviewed_stxbp1_graph_covers_typed_evidence_and_model_limits(self):
        result = self.service.analyze({"disease": "STXBP1-related disorder"})
        kinds = {n.kind for n in result.knowledge_graph.nodes}
        self.assertTrue({"disease", "gene", "mechanism", "pathway", "phenotype", "variant", "candidate", "paper",
                         "clinical_study", "patient_organisation", "investigator", "research_asset"} <= kinds)
        functional = next(e for e in result.knowledge_graph.edges if e.relationship_type == "reviewed_functional_mechanism")
        self.assertTrue(functional.contradictions)
        self.assertTrue({"guiberson2018", "kovacevic2018", "lammertse2020"} <= source_references(functional.contradictions))
        human = next(e for e in result.knowledge_graph.edges if e.relationship_type == "reported_human_evidence"
                     and e.source == "candidate:stxbp1-levetiracetam")
        self.assertTrue({"wang2022", "xian2023"} <= source_references(human.contradictions))
        self.assertIn("cohorts and endpoints", human.contradictions[0].summary)
        self.assertEqual(result.best_hypothesis_id, "stxbp1-levetiracetam")
        self.assertEqual(result.candidate_treatments[0].final_score, 28.25)
        self.assertEqual(validate_graph(result.knowledge_graph, result.sources, disease_node_id(result.disease)), result.knowledge_graph)

    def test_cplx1_has_known_biology_and_no_therapeutic_transfer(self):
        result = self.service.analyze({"disease": "CPLX1"})
        self.assertEqual(result.conclusion, NO_CANDIDATE)
        self.assertEqual(result.candidate_treatments, [])
        self.assertIsNone(result.best_hypothesis_id)
        self.assertTrue(result.functional_mechanism.source_ids)
        self.assertTrue(result.pathway.source_ids)
        self.assertEqual(result.variant_effect.effect, "unknown")
        self.assertTrue(any(n.kind == "mechanism" for n in result.knowledge_graph.nodes))
        self.assertFalse(any(n.kind == "candidate" for n in result.knowledge_graph.nodes))
        self.assertTrue(any(e.relationship_type == "shared_research_mechanism" for e in result.knowledge_graph.edges))
        self.assertTrue(source_references(result.knowledge_graph) <= {s.id for s in result.sources})

    def test_related_disease_cannot_acquire_primary_candidate_evidence(self):
        result = self.service.analyze({"disease": "STXBP1-related disorder"})
        graph = result.knowledge_graph.model_copy(deep=True)
        edge = next(e for e in graph.edges if e.relationship_type == "candidate_under_research")
        edge.source = "disease:MONDO:0033372"
        with self.assertRaises(GraphIntegrityError):
            validate_graph(graph, result.sources, disease_node_id(result.disease))


class ResponsesTests(unittest.TestCase):
    def response(self, payload, **fields):
        return SimpleNamespace(status="completed", error=None, incomplete_details=None, output=[],
                               output_text=__import__("json").dumps(payload), **fields)

    def test_current_responses_request_shape(self):
        create = Mock(return_value=self.response({"candidates": ["STXBP1"]}))
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.object(llm, "available", return_value=True), patch.object(llm, "_client", client):
            self.assertEqual(llm.resolve_query("test query"), ["STXBP1"])
        args = create.call_args.kwargs
        self.assertEqual(args["text"]["format"]["type"], "json_schema")
        self.assertEqual(args["text"]["format"]["name"], "resolve")
        self.assertIs(args["text"]["format"]["strict"], True)
        self.assertIs(args["store"], False)
        self.assertLessEqual(args["timeout"], 25)
        self.assertNotIn("messages", args)
        self.assertNotIn("response_format", args)

    def test_initial_client_has_bounded_timeout_without_retries(self):
        client = SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=self.response({"candidates": []}))))
        with patch.object(llm, "available", return_value=True), patch.object(llm, "_client", None), patch("openai.OpenAI", return_value=client) as constructor:
            self.assertEqual(llm.resolve_query("test"), [])
        self.assertLessEqual(constructor.call_args.kwargs["timeout"], 25)
        self.assertEqual(constructor.call_args.kwargs["max_retries"], 0)

    def test_incomplete_refusal_malformed_and_extra_fields_fall_back(self):
        base = self.response({"candidates": ["STXBP1"]})
        incomplete = copy.deepcopy(base)
        incomplete.status = "incomplete"
        refusal = copy.deepcopy(base)
        refusal.output = [{"content": [{"type": "refusal", "refusal": "Cannot verify."}]}]
        malformed = copy.deepcopy(base)
        malformed.output_text = "not json"
        extra = self.response({"candidates": [], "therapy": "invented"})
        wrong_type = self.response({"candidates": [5]})
        for response in (incomplete, refusal, malformed, extra, wrong_type):
            with patch.object(llm, "available", return_value=True), patch.object(llm, "_client", SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=response)))):
                self.assertIsNone(llm.resolve_query("test"))

    def test_network_errors_do_not_log_secrets_or_request_contents(self):
        create = Mock(side_effect=RuntimeError("sk-secret patient-text example"))
        with patch.object(llm, "available", return_value=True), patch.object(llm, "_client", SimpleNamespace(responses=SimpleNamespace(create=create))), self.assertLogs("atlas.llm", level="WARNING") as logs:
            self.assertIsNone(llm.resolve_query("private request"))
        combined = " ".join(logs.output)
        self.assertIn("RuntimeError", combined)
        self.assertNotIn("sk-secret", combined)
        self.assertNotIn("patient-text", combined)
        self.assertNotIn("private request", combined)

    def test_original_atlas_claim_extraction_requires_exact_quote(self):
        claim = {"pmid": "1", "kind": "variant_effect", "effect": "loss_of_function", "asset_type": "none",
                 "statement": "A test claim", "quote": "Exact Source Sentence"}
        with patch.object(llm, "_json", return_value={"claims": [claim]}):
            self.assertEqual(llm.extract_claims("TEST", [{"pmid": "1", "text": "Exact Source Sentence"}]), [claim])
            self.assertEqual(llm.extract_claims("TEST", [{"pmid": "1", "text": "exact source sentence"}]), [])

    def test_verified_openai_claims_cannot_change_scores_or_medical_text(self):
        cached = service().analyze({"disease": "DEE4"})
        check = {"claim_id": "functional_mechanism", "source_id": "test-source", "quote": "Test-curated model evidence.",
                 "evidence_type": "preclinical", "classification": "entailed"}
        with patch.object(llm, "available", return_value=True), patch.object(llm, "_json", return_value={"checks": [check]}):
            result = service().analyze({"disease": "DEE4", "use_openai": True})
        self.assertEqual(result.llm.mode, "openai_verified")
        self.assertEqual(result.model_dump(exclude={"llm"}), cached.model_dump(exclude={"llm"}))
        self.assertEqual(result.llm.verified_claims[0], cached.functional_mechanism)

    def test_quote_citation_or_evidence_type_fabrication_is_discarded(self):
        valid = {"claim_id": "functional_mechanism", "source_id": "test-source", "quote": "Test-curated model evidence.",
                 "evidence_type": "preclinical", "classification": "entailed"}
        for field, changed in (("claim_id", "invented"), ("source_id", "invented"), ("quote", "Invented quote"),
                               ("quote", "test-curated model evidence."), ("evidence_type", "human_clinical")):
            check = {**valid, field: changed}
            with patch.object(llm, "available", return_value=True), patch.object(llm, "_json", return_value={"checks": [check]}):
                result = service().analyze({"disease": "DEE4", "use_openai": True})
            self.assertEqual(result.llm.mode, "fallback")
            self.assertEqual(result.llm.verified_claims, [])

    def test_no_key_and_uncertainty_are_explicit_fallbacks(self):
        with patch.object(llm, "available", return_value=False), patch.object(llm, "_json") as request:
            result = service().analyze({"disease": "DEE4", "use_openai": True})
        request.assert_not_called()
        self.assertEqual(result.llm.mode, "fallback")
        self.assertIn("no server-side API key", result.llm.detail)
        check = {"claim_id": "functional_mechanism", "source_id": "test-source", "quote": "Test-curated model evidence.",
                 "evidence_type": "preclinical", "classification": "contradicted"}
        with patch.object(llm, "available", return_value=True), patch.object(llm, "_json", return_value={"checks": [check]}):
            result = service().analyze({"disease": "DEE4", "use_openai": True})
        self.assertEqual(result.llm.mode, "fallback")
        self.assertIn("1 uncertainty or contradiction", result.llm.detail)


if __name__ == "__main__":
    unittest.main()

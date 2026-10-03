"""Synthetic vector fixtures test math only; application evidence stays biomedical."""
from dataclasses import replace
from copy import deepcopy
import math
import unittest

from atlas.therapeutics.adapter import adapt_disease
from atlas.therapeutics.evidence import catalog, interventions, registry, valid_source
from atlas.therapeutics.models import Intervention, InterventionEffect, TherapeuticTarget, signed_direction
from atlas.therapeutics.scoring import complementary_candidates, score_candidate


class VectorFixtureEvidence:
    """A test double, never a registry of fabricated biomedical relationships."""
    def resolve(self, refs, *, mechanistic=False):
        return [{"id": "vector-fixture", "evidence_type": "synthetic_unit_test"}] if refs == ("vector-fixture",) else None

    def effect_direction(self, effect):
        return effect.direction if self.resolve(effect.source_ids) and effect.claim_kind == "direct_source_report" else None


def target(symbol, deviation=-1, weight=1):
    return TherapeuticTarget(symbol, symbol, deviation, weight, ("vector-fixture",), "Synthetic signed-vector fixture")


def effect(symbol, sign=1, refs=("vector-fixture",)):
    return InterventionEffect("test:" + symbol, symbol, symbol, sign, refs,
                              "TEST_ONLY_DIRECTION", "Synthetic signed-vector fixture; not biomedical evidence")


def intervention(id="test-primary", effects=(), spillover=(), kind="existing_drug"):
    return Intervention(id, id, kind, "Synthetic vector fixture", tuple(effects), tuple(spillover))


class SignedScoringTests(unittest.TestCase):
    def setUp(self):
        self.ev = VectorFixtureEvidence()

    def score(self, targets, candidate):
        return score_candidate(targets, candidate, self.ev, ("Unmodeled fixture biology",))

    def test_four_direction_quadrants(self):
        for deviation in (-1, 1):
            for action in (-1, 1):
                with self.subTest(deviation=deviation, action=action):
                    row = self.score([target("A", deviation)], intervention(effects=[effect("A", action)]))
                    matches = action == -deviation
                    self.assertEqual(row["direction_match"]["value"], 1 if matches else -1)
                    self.assertEqual(row["mechanistic_coverage"]["value"], 1 if matches else 0)
                    self.assertEqual(row["mechanistic_fit"]["score"], 1 if matches else -.85)
                    self.assertEqual(row["ranking_status"], "provisional" if matches else "withheld")

    def test_unknown_never_gets_partial_credit(self):
        for deviation, action in ((None, 1), (-1, None), (None, None)):
            with self.subTest(deviation=deviation, action=action):
                row = self.score([target("A", deviation)], intervention(effects=[effect("A", action)]))
                self.assertIsNone(row["mechanistic_fit"]["score"])
                self.assertIsNone(row["direction_match"]["value"])
                self.assertIsNone(row["mechanistic_coverage"]["value"])
                self.assertIsNone(row["wrong_direction_effects"]["penalty"])
                self.assertEqual(row["ranking_status"], "withheld")

    def test_weighted_desired_coverage_and_remaining_deviation(self):
        row = self.score([target("A", weight=3), target("B", weight=1)], intervention(effects=[effect("A")]))
        self.assertEqual(row["mechanistic_coverage"]["value"], .75)
        self.assertEqual(row["remaining_deviation"]["targets"][0]["target"], "B")
        self.assertEqual(row["remaining_deviation"]["modeled_uncovered_fraction"], .25)
        self.assertIn("Unmodeled fixture biology", row["remaining_deviation"]["unresolved_biology"])

    def test_wrong_direction_withholds_even_when_net_positive(self):
        row = self.score([target("A", weight=3), target("B")], intervention(effects=[effect("A"), effect("B", -1)]))
        self.assertEqual(row["wrong_direction_effects"]["penalty"], .212)
        self.assertEqual(row["mechanistic_fit"]["score"], .537)
        self.assertEqual(row["ranking_status"], "withheld")

    def test_unrelated_targets_lower_fit_without_improving_coverage(self):
        specific = self.score([target("A")], intervention(effects=[effect("A")]))
        broad = self.score([target("A")], intervention(effects=[effect("A"), effect("X"), effect("Y")]))
        self.assertEqual(broad["mechanistic_coverage"], specific["mechanistic_coverage"])
        self.assertLess(broad["mechanistic_fit"]["score"], specific["mechanistic_fit"]["score"])
        self.assertEqual(broad["spillover"]["listed_penalty"], .44)

    def test_duplicate_edges_do_not_inflate_coverage_or_spillover(self):
        row = self.score([target("A")], intervention(effects=[effect("A"), effect("A"), effect("X")], spillover=[effect("X")]))
        self.assertEqual(row["mechanistic_coverage"]["value"], 1)
        self.assertEqual(row["spillover"]["known_count"], 1)
        self.assertEqual(row["mechanistic_fit"]["score"], .78)

    def test_conflicting_effect_directions_withhold_ranking(self):
        row = self.score([target("A")], intervention(effects=[effect("A"), effect("A", -1)]))
        self.assertIsNone(row["mechanistic_fit"]["score"])
        self.assertEqual(row["ranking_status"], "withheld")

    def test_missing_provenance_on_causal_or_spillover_edge_is_unknown(self):
        for candidate in (intervention(effects=[effect("A", refs=())]),
                          intervention(effects=[effect("A")], spillover=[effect("X", refs=())])):
            with self.subTest(candidate=candidate):
                row = self.score([target("A")], candidate)
                self.assertIsNone(row["mechanistic_fit"]["score"])

    def test_unsigned_spillover_is_unknown(self):
        row = self.score([target("A")], intervention(effects=[effect("A")], spillover=[effect("X", None)]))
        self.assertIsNone(row["mechanistic_fit"]["score"])
        self.assertTrue(row["spillover"]["unresolved"])
        self.assertEqual(row["direction_match"]["value"], 1)
        self.assertEqual(row["mechanistic_coverage"]["value"], 1)

    def test_no_overlap_or_no_effect_does_not_create_rank(self):
        for candidate in (intervention(effects=[effect("X")]), intervention()):
            row = self.score([target("A")], candidate)
            self.assertIsNone(row["mechanistic_fit"]["score"])
            self.assertEqual(row["evidence_strength"]["status"], "unknown")

    def test_empty_spillover_inventory_never_proves_selectivity(self):
        row = self.score([target("A")], intervention(effects=[effect("A")]))
        self.assertEqual(row["spillover"]["inventory_status"], "incomplete")
        self.assertEqual(row["clinical_safety_evidence"]["status"], "not_established_for_this_disease")
        self.assertIsNone(row["clinical_safety_evidence"]["assessment_score"])

    def test_add_on_closes_remaining_axis(self):
        targets = [target("A"), target("B")]
        primary = self.score(targets, intervention(effects=[effect("A")]))
        addon = self.score(targets, intervention("test-addon", [effect("B")]))
        result = complementary_candidates(targets, primary, [primary, addon])
        self.assertEqual(result["proposed"][0]["deviation_closed"], ["B"])
        self.assertEqual(result["proposed"][0]["net_gain"], .44)
        self.assertIn("unknown", result["proposed"][0]["clinical_safety_evidence"])

    def test_redundancy_is_not_complementarity(self):
        targets = [target("A"), target("B")]
        primary = self.score(targets, intervention(effects=[effect("A")]))
        duplicate = self.score(targets, intervention("test-duplicate", [effect("A")]))
        result = complementary_candidates(targets, primary, [primary, duplicate])
        self.assertFalse(result["proposed"])
        self.assertGreater(result["evaluated"][0]["redundancy_penalty"], 0)
        self.assertLess(result["evaluated"][0]["net_gain"], 0)

    def test_redundancy_and_new_spillover_can_erase_add_on_gain(self):
        targets = [target("A"), target("B")]
        primary = self.score(targets, intervention(effects=[effect("A")]))
        broad = self.score(targets, intervention("test-broad", [effect("A"), effect("B"), effect("X"), effect("Y")]))
        result = complementary_candidates(targets, primary, [primary, broad])
        self.assertFalse(result["proposed"])
        self.assertEqual(result["evaluated"][0]["net_gain"], -.05)

    def test_unknown_or_opposed_add_on_withholds_bundle(self):
        targets = [target("A"), target("B")]
        primary = self.score(targets, intervention(effects=[effect("A")]))
        for candidate in (intervention("test-unknown", [effect("B", None)]),
                          intervention("test-opposed", [effect("B"), effect("A", -1)])):
            addon = self.score(targets, candidate)
            result = complementary_candidates(targets, primary, [primary, addon])
            self.assertFalse(result["proposed"])
            self.assertIsNone(result["evaluated"][0]["net_gain"])

    def test_invalid_weights_and_duplicate_targets_rejected(self):
        for weight in (0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError):
                target("A", weight=weight)
        with self.assertRaises(ValueError):
            self.score([target("A"), target("A")], intervention(effects=[effect("A")]))

    def test_direction_tokens_are_strict(self):
        self.assertEqual(signed_direction("loss-of-function"), -1)
        self.assertEqual(signed_direction("gain of function"), 1)
        for token in ("restore", "boost", "agonize", "high", "elevated"):
            self.assertEqual(signed_direction(token), 1)
        for token in ("block", "antagonize", "suppress", "reduced", "low"):
            self.assertEqual(signed_direction(token), -1)
        for token in ("mixed", "dominant_negative", "modulate", "pathogenic", "unknown", None):
            self.assertIsNone(signed_direction(token))


class ReviewedCatalogTests(unittest.TestCase):
    def setUp(self):
        self.disease = {"id": "MONDO:0007113", "name": "Angelman syndrome", "genes": ["UBE3A"]}

    def test_all_catalog_sources_meet_reviewed_contract(self):
        self.assertEqual(len(catalog()["profiles"]), 1)
        for source in catalog()["sources"]:
            with self.subTest(source=source["id"]):
                self.assertTrue(valid_source(source))

    def test_all_released_intervention_edges_have_explicit_provenance(self):
        evidence = registry()
        edge_ids = []
        for candidate in interventions("ube3a-deficiency"):
            for e in candidate.effects + candidate.spillover:
                self.assertIsNotNone(evidence.effect_direction(e))
                self.assertTrue(e.context)
                edge_ids.append(e.id)
        self.assertEqual(len(set(edge_ids)), len(edge_ids))

    def test_label_or_pathogenicity_is_not_mechanistic_provenance(self):
        evidence = registry()
        for ref in ("topotecan-label", "clinvar-155984", "MONDO:0007113"):
            self.assertIsNotNone(evidence.resolve((ref,)))
            self.assertIsNone(evidence.resolve((ref,), mechanistic=True))
        self.assertIsNone(evidence.resolve(("not-a-reviewed-source",)))

    def test_exact_disease_and_gene_adapter(self):
        result = adapt_disease(self.disease)
        self.assertEqual(result["targets"][0].disease_direction, -1)
        self.assertEqual(result["targets"][0].desired_direction, 1)
        self.assertEqual(result["status"], "disease_level_research_context")

    def test_same_gene_does_not_transfer_disease_direction(self):
        result = adapt_disease({**self.disease, "id": "different-disease"})
        self.assertIsNone(result["targets"][0].disease_direction)
        self.assertEqual(result["status"], "unknown")

    def test_gene_mismatch_blocks_profile(self):
        result = adapt_disease({**self.disease, "genes": ["STXBP1"]})
        self.assertIsNone(result["profile_id"])
        self.assertIsNone(result["targets"][0].disease_direction)

    def test_unknown_mechanism_returns_unknown(self):
        result = adapt_disease(self.disease, mechanism="gain-of-function")
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["targets"][0].disease_direction)

    def test_public_clinvar_example_is_not_a_functional_direction(self):
        result = adapt_disease(self.disease, variant="VCV000155984.20")
        self.assertTrue(result["context"]["variant_sources"])
        self.assertIsNone(result["targets"][0].disease_direction)

    def test_unreviewed_variant_cannot_override_known_mechanism(self):
        result = adapt_disease(self.disease, variant="unreviewed-variant", mechanism="ube3a-deficiency")
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["targets"][0].disease_direction)

    def test_real_pilot_separates_fit_evidence_and_clinical_risk(self):
        adapted = adapt_disease(self.disease)
        candidate = interventions("ube3a-deficiency")[0]
        row = score_candidate(adapted["targets"], candidate, registry(), adapted["unresolved"])
        self.assertEqual(row["mechanistic_fit"]["score"], .78)
        self.assertEqual(row["mechanistic_coverage"]["value"], 1)
        self.assertEqual(row["spillover"]["known_count"], 1)
        self.assertEqual(row["clinical_safety_evidence"]["status"], "not_established_for_this_disease")
        self.assertNotIn("regulatory_label", row["evidence_strength"]["types"])
        self.assertEqual(len(row["clinical_safety_evidence"]["warnings"]), 2)

    def test_missing_candidate_provenance_withholds_real_pilot(self):
        adapted = adapt_disease(self.disease)
        candidate = interventions("ube3a-deficiency")[0]
        candidate = replace(candidate, effects=(replace(candidate.effects[0], source_ids=()),))
        row = score_candidate(adapted["targets"], candidate, registry())
        self.assertIsNone(row["mechanistic_fit"]["score"])

    def test_invalid_source_url_or_mismatched_pmid_rejected(self):
        original = registry().sources["huang2012"]
        for fields in ({"source_url": "https://example.org/unsupported"},
                       {"pmid": "123"}, {"pmid": None}, {"authors": []}, {"study_design": ""}):
            with self.subTest(fields=fields):
                source = deepcopy(original)
                source.update(fields)
                self.assertFalse(valid_source(source))

    def test_unknown_variant_keeps_published_effect_evidence_separate(self):
        from atlas.therapeutics import opportunities
        result = opportunities(self.disease, variant="unreviewed-variant")
        row = result["candidates"][0]
        self.assertIsNone(row["mechanistic_fit"]["score"])
        self.assertEqual(row["evidence_strength"]["status"], "sourced")
        self.assertIn("human_cellular", row["evidence_strength"]["types"])

    def test_inferred_edge_cannot_become_an_observed_direction(self):
        candidate = interventions("ube3a-deficiency")[0]
        inferred = replace(candidate.effects[0], claim_kind="inferred_relationship")
        self.assertIsNone(registry().effect_direction(inferred))

    def test_disease_overview_cannot_be_used_as_drug_effect_evidence(self):
        candidate = interventions("ube3a-deficiency")[0]
        unsupported = replace(candidate.effects[0], source_ids=("angelman-nlm",))
        self.assertIsNone(registry().effect_direction(unsupported))


if __name__ == "__main__":
    unittest.main()

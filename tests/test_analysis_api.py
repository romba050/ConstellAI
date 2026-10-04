"""Public contract, cached fixture parity and original atlas route checks."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch

from fastapi.testclient import TestClient

from atlas import server
from atlas.analysis import graph as evidence_graph
from atlas.analysis.models import AnalyzeResponse
from atlas.analysis.service import AnalysisService, NO_CANDIDATE
from test_analysis import evidence, fake_atlas, service

ROOT = Path(__file__).resolve().parent.parent


class AnalysisAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(server.app)

    def test_health_exposes_only_key_capability_flag(self):
        with patch.object(server.llm, "available", return_value=False):
            payload = self.client.get("/api/v1/health").json()
        self.assertEqual(set(payload), {"status", "schema_version", "scoring_version", "openai_enabled"})
        self.assertIs(payload["openai_enabled"], False)
        self.assertEqual(payload["scoring_version"], "therapeutic-priority-1")
        self.assertEqual(payload["schema_version"], "constellai-analysis-v2")
        self.assertNotIn("key", json.dumps(payload).lower())

    def test_schema_matches_frozen_contract_file(self):
        payload = self.client.get("/api/v1/schema").json()
        self.assertEqual(payload, json.loads((ROOT / "docs/analyze-disease.schema.json").read_text(encoding="utf-8")))

    def test_api_matches_service_and_returns_a_valid_model(self):
        with patch.object(server, "analysis_service", service()):
            response = self.client.post("/api/v1/analyze_disease", json={"disease": "DEE4"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        AnalyzeResponse.model_validate(payload)
        self.assertEqual(payload, service().analyze({"disease": "DEE4"}).model_dump())

    def test_variant_and_no_candidate_api_paths(self):
        with patch.object(server, "analysis_service", service()):
            for query in ({"disease": "DEE4", "variant": "c.123A>T"}, {"disease": "CPLX1"},
                          {"disease": "unknown", "gene": "STXBP1"}, {"disease": "DEE4", "gene": "CPLX1"}):
                response = self.client.post("/api/v1/analyze_disease", json=query)
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                AnalyzeResponse.model_validate(payload)
                self.assertEqual(payload["conclusion"], NO_CANDIDATE)
                self.assertIsNone(payload["best_hypothesis_id"])
                self.assertTrue(all(c["rank"] is None for c in payload["candidate_treatments"]))

    def test_mock_responses_transport_through_public_api_preserves_ranking(self):
        check = {"claim_id": "functional_mechanism", "source_id": "test-source",
                 "quote": "Test-curated model evidence.", "evidence_type": "preclinical", "classification": "entailed"}
        response = SimpleNamespace(status="completed", error=None, incomplete_details=None, output=[],
                                   output_text=json.dumps({"checks": [check]}))
        create = Mock(return_value=response)
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        with patch.object(server, "analysis_service", service()), patch.object(server.llm, "available", return_value=True), patch.object(server.llm, "_client", client):
            cached = self.client.post("/api/v1/analyze_disease", json={"disease": "DEE4"}).json()
            result = self.client.post("/api/v1/analyze_disease", json={"disease": "DEE4", "use_openai": True})
        self.assertEqual(result.status_code, 200)
        payload = result.json()
        AnalyzeResponse.model_validate(payload)
        self.assertEqual(payload["llm"]["mode"], "openai_verified")
        self.assertEqual({k: v for k, v in payload.items() if k != "llm"}, {k: v for k, v in cached.items() if k != "llm"})
        self.assertIs(create.call_args.kwargs["store"], False)
        self.assertEqual(create.call_args.kwargs["text"]["format"]["name"], "therapeutic_evidence_checks")

    def test_bad_requests_are_rejected(self):
        with patch.object(server, "analysis_service", service()):
            for query in ({"disease": ""}, {"disease": "   "}, {"disease": "DEE4", "rank": 1},
                          {"disease": "DEE4", "variant": "x" * 201}):
                self.assertEqual(self.client.post("/api/v1/analyze_disease", json=query).status_code, 422)

    def test_corrupt_source_ledger_returns_sanitized_unavailable(self):
        raw = evidence()
        raw["profiles"][0]["pathway"]["source_ids"] = ["private-invalid-source"]
        with patch.object(server, "analysis_service", AnalysisService(atlas=fake_atlas(), evidence=raw)):
            response = self.client.post("/api/v1/analyze_disease", json={"disease": "DEE4"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-invalid-source", response.text)
        self.assertIn("withheld", response.json()["detail"])

    def test_invalid_graph_is_withheld_before_api_return(self):
        result = service().analyze({"disease": "DEE4"})
        graph = result.knowledge_graph.model_copy(deep=True)
        graph.edges[0].target = "private-invalid-endpoint"
        with patch.object(server, "analysis_service", service()), patch.object(evidence_graph, "build_graph", return_value=graph):
            response = self.client.post("/api/v1/analyze_disease", json={"disease": "DEE4"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-invalid-endpoint", response.text)
        self.assertIn("withheld", response.json()["detail"])

    def test_original_graph_entities_and_routes_are_preserved(self):
        response = self.client.get("/api/atlas")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["points"])
        self.assertTrue(payload["edges"])
        response = self.client.get("/api/disease/MONDO:0012812")
        self.assertEqual(response.status_code, 200)
        self.assertIn("phenotypes", response.json())
        self.assertIn("neighbors", response.json())
        self.assertEqual(self.client.get("/api/entity/gene/CPLX1").status_code, 200)
        self.assertEqual(self.client.get("/api/disease/MONDO:does-not-exist").status_code, 404)
        self.assertEqual(self.client.get("/atlas").status_code, 200)
        self.assertIn("<html", self.client.get("/atlas").text.lower())

    def test_original_search_can_disable_ai_reconciliation(self):
        with patch.object(server.llm, "available", return_value=True), patch.object(server.llm, "resolve_query") as resolve:
            response = self.client.get("/api/search", params={"q": "totally unknown source check", "use_openai": "false"})
        self.assertEqual(response.status_code, 200)
        resolve.assert_not_called()

    def test_production_evidence_and_demo_fixture_match_api(self):
        expected = json.loads((ROOT / "web/demo-analysis.json").read_text(encoding="utf-8"))
        AnalyzeResponse.model_validate(expected)
        response = self.client.post("/api/v1/analyze_disease", json={"disease": "STXBP1-related disorder"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        self.assertEqual(expected["disease"]["id"], "MONDO:0012812")
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertIn("research.js", self.client.get("/").text)


if __name__ == "__main__":
    unittest.main()

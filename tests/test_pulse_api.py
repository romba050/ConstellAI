"""Public Pulse reads and scheduler lifecycle preserve the reviewed analysis boundary."""
import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from atlas import server
from atlas.pulse.models import PulseResponse


ROOT = Path(__file__).resolve().parents[1]


def pending_snapshot():
    return PulseResponse(
        state="pending", scheduler_enabled=True, scheduler_running=False,
        watchlist=["STXBP1", "CPLX1"], providers=[], unreviewed_count=0,
        total_records=0, items=[], limitations=["Discoveries require expert review."],
    )


class PulseApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(server.app)

    def test_read_uses_saved_snapshot_without_starting_source_or_ai_calls(self):
        fake = Mock()
        fake.snapshot.return_value = pending_snapshot()
        with patch.object(server, "pulse_service", fake):
            response = self.client.get("/api/v1/pulse", params={"gene": "STXBP1", "limit": 100})
        self.assertEqual(response.status_code, 200)
        PulseResponse.model_validate(response.json())
        fake.snapshot.assert_called_once_with(gene="STXBP1", limit=100)
        fake.tick.assert_not_called()
        fake.refresh.assert_not_called()

    def test_invalid_filter_or_limit_is_rejected_before_storage(self):
        fake = Mock()
        with patch.object(server, "pulse_service", fake):
            for query in ({"limit": 0}, {"limit": 201}, {"gene": ""},
                          {"gene": "x" * 41}, {"gene": "STXBP1<script>"}):
                self.assertEqual(self.client.get("/api/v1/pulse", params=query).status_code, 422)
        fake.snapshot.assert_not_called()

    def test_unavailable_feed_is_sanitized_and_does_not_interrupt_research(self):
        with patch.object(server.pulse_service, "snapshot", side_effect=ValueError("private-db-path-or-token")):
            response = self.client.get("/api/v1/pulse")
            hero = self.client.post("/api/v1/analyze_disease", json={"disease": "STXBP1"})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private-db-path-or-token", response.text)
        self.assertEqual(hero.status_code, 200)
        self.assertEqual(hero.json(), json.loads((ROOT / "web/demo-analysis.json").read_text(encoding="utf-8")))

    def test_background_discovery_contract_is_separate_from_scoring_contract(self):
        self.assertNotIn("Pulse", json.dumps(self.client.get("/api/v1/schema").json()))
        expected = json.loads((ROOT / "web/demo-analysis.json").read_text(encoding="utf-8"))
        fake = Mock()
        fake.snapshot.return_value = pending_snapshot()
        with patch.object(server, "pulse_service", fake):
            self.client.get("/api/v1/pulse")
            response = self.client.post("/api/v1/analyze_disease", json={"disease": "STXBP1"})
        self.assertEqual(response.json(), expected)


class PulseLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_enabled_scheduler_ticks_in_a_background_worker(self):
        fake = Mock(enabled=True)
        fake.tick.return_value = False
        with patch.object(server, "pulse_service", fake), patch.object(server.asyncio, "sleep", side_effect=asyncio.CancelledError):
            with self.assertRaises(asyncio.CancelledError):
                await server._pulse_loop()
        fake.tick.assert_called_once_with()

    async def test_disabled_lifespan_never_starts_fetches(self):
        fake = Mock(enabled=False)
        fake.scheduler_running = False
        with patch.object(server, "pulse_service", fake):
            async with server.lifespan(server.app):
                self.assertFalse(fake.scheduler_running)
        fake.tick.assert_not_called()

    async def test_lifespan_marks_active_then_stops_scheduler(self):
        fake = Mock(enabled=True)
        fake.tick.return_value = False
        tick_started = asyncio.Event()

        async def worker():
            tick_started.set()
            await asyncio.Event().wait()

        with patch.object(server, "pulse_service", fake), patch.object(server, "_pulse_loop", worker):
            async with server.lifespan(server.app):
                await asyncio.wait_for(tick_started.wait(), timeout=1)
                self.assertTrue(fake.scheduler_running)
            self.assertFalse(fake.scheduler_running)


if __name__ == "__main__":
    unittest.main()

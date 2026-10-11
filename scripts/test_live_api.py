"""Automated smoke tests for the live JalSaathi deployment on AWS CloudFront.

Usage: python scripts/test_live_api.py
"""

import json
import time
import unittest
import urllib.request

BASE = "https://d2735023v3xj6.cloudfront.net/api/v1"


def get_json(path: str) -> tuple[int, dict, float]:
    url = f"{BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "JalSaathi-Test/1.0"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=10) as resp:
        elapsed = time.perf_counter() - t0
        data = json.loads(resp.read().decode("utf-8"))
        return resp.status, data, elapsed


class TestLiveApi(unittest.TestCase):
    def test_health(self):
        status, data, elapsed = get_json("/health")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("bot"), "Srott_bot")
        self.assertLess(elapsed, 2.0, "Health check should respond within 2 seconds")

    def test_stats(self):
        status, data, elapsed = get_json("/stats")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("villages"), 496)
        self.assertEqual(data.get("cases"), 573)
        self.assertIn("scale_run", data)
        self.assertEqual(data["scale_run"].get("status"), "SUCCEEDED")
        self.assertEqual(data["scale_run"]["items"].get("succeeded"), 560)
        self.assertEqual(data["scale_run"]["items"].get("failed"), 0)
        self.assertIn("repeat_failures", data)
        self.assertEqual(data["repeat_failures"]["totals"]["both"], 149)

    def test_config(self):
        status, data, elapsed = get_json("/config")
        self.assertEqual(status, 200)
        self.assertIn("map", data)
        self.assertEqual(data["map"].get("provider"), "Amazon Location Service")
        self.assertIn("push", data)
        self.assertTrue(data["push"].get("vapid_public_key"))

    def test_villages_list(self):
        status, data, elapsed = get_json("/villages")
        self.assertEqual(status, 200)
        villages = data.get("villages", [])
        self.assertGreaterEqual(len(villages), 496)
        sample = villages[0]
        self.assertIn("key", sample)
        self.assertIn("name", sample)
        self.assertIn("district", sample)
        self.assertIn("status", sample)

    def test_village_bundle_behta_lakhi(self):
        status, data, elapsed = get_json("/villages/412558")
        self.assertEqual(status, 200)
        v = data.get("village", {})
        self.assertEqual(v.get("name"), "BEHTA LAKHI")
        self.assertEqual(v.get("block"), "Harpalpur")
        self.assertEqual(v.get("district"), "Hardoi")
        cases = data.get("cases", [])
        self.assertGreaterEqual(len(cases), 1)
        ecoli = next((c for c in cases if c.get("code") in ("ecoli", "coliform")), None)
        self.assertIsNotNone(ecoli, "Behta Lakhi should have bacteriological case")
        self.assertIn("links", data)
        self.assertIn("telegram_join", data["links"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

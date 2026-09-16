"""
Automated Verification Suite for API TEST CLI
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ConfigManager
from client import APIDiagnosticsClient
from ui import (
    get_rgb_banner,
    render_model_discovery_page,
    render_benchmark_report,
    render_slash_commands,
)


class TestConfigManager(unittest.TestCase):
    def test_config_operations(self):
        cfg = ConfigManager()
        cfg.save_profile("TempUnitTest", "https://api.openai.com/v1", "sk-test123456", "gpt-4o-mini")
        active = cfg.get_active_profile()
        self.assertEqual(active["name"], "TempUnitTest")
        self.assertEqual(active["base_url"], "https://api.openai.com/v1")
        self.assertEqual(active["api_key"], "sk-test123456")

        # Cleanup temp unit test profile
        cfg.delete_profile("TempUnitTest")


class TestClientDiagnostics(unittest.TestCase):
    def test_error_formatting_offline(self):
        client = APIDiagnosticsClient("http://127.0.0.1:59999/v1", api_key="", timeout=1.0)
        res = client.fetch_models()
        self.assertFalse(res["success"])
        self.assertTrue("Connection Refused" in res["error"] or "Connect Timeout" in res["error"])

    def test_single_model_health_offline(self):
        client = APIDiagnosticsClient("http://127.0.0.1:59999/v1", api_key="", timeout=1.0)
        health = client.test_single_model_health("gpt-4o")
        self.assertEqual(health["status"], "FAILED")
        self.assertTrue("Connection Refused" in health["error_reason"] or "Connect Timeout" in health["error_reason"])


class TestUIRendering(unittest.TestCase):
    def test_rgb_banner(self):
        banner = get_rgb_banner()
        self.assertIsNotNone(banner)
        self.assertTrue(len(banner.plain) > 0)

    def test_model_discovery_page_render(self):
        mock_results = [
            {"model": "gpt-4o", "status": "OK", "latency_ms": 120.5, "error_reason": None},
            {"model": "llama-3-70b", "status": "FAILED", "latency_ms": None, "error_reason": "HTTP 401: Unauthorized (Invalid Key)"},
        ]
        render_model_discovery_page("https://api.openai.com/v1", mock_results, 85.0)

    def test_benchmark_report_render(self):
        mock_benchmark = {
            "success": True,
            "error": None,
            "status_code": 200,
            "model": "gpt-4o-mini",
            "ttft_ms": 185.4,
            "total_latency_ms": 780.2,
            "generation_latency_ms": 594.8,
            "tps": 75.6,
            "tokens": 45,
            "response_text": "Quantum computing harnesses superposition and entanglement to perform complex computations exponentially faster than classical bits.",
            "headers": {},
        }
        render_benchmark_report(mock_benchmark)


if __name__ == "__main__":
    unittest.main()

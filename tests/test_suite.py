"""
Automated Verification Suite for API TEST CLI
Comprehensive offline unit and integration tests.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from apitestllm._compat import ensure_utf8_stdio
from apitestllm.cli import execute_noninteractive, parse_arguments
from apitestllm.client import APIDiagnosticsClient, calculate_statistics
from apitestllm.config import DEFAULT_PRESETS, ConfigManager, detect_provider
from apitestllm.exporter import (
    auto_export,
    export_to_csv,
    export_to_html,
    export_to_json,
    export_to_markdown,
)
from apitestllm.ui import (
    get_rgb_banner,
    render_benchmark_report,
    render_history_table,
    render_model_comparison_matrix,
    render_model_discovery_page,
    render_multi_run_benchmark_report,
    render_presets_table,
    render_slash_commands,
    render_stress_test_report,
)

ensure_utf8_stdio()


class TestConfigManager(unittest.TestCase):
    def test_config_operations(self):
        cfg = ConfigManager()
        cfg.save_profile(
            "TempUnitTest", "https://api.openai.com/v1", "sk-test123456", "gpt-4o-mini"
        )
        active = cfg.get_active_profile()
        assert active is not None
        self.assertEqual(active["name"], "TempUnitTest")
        self.assertEqual(active["base_url"], "https://api.openai.com/v1")
        self.assertEqual(active["api_key"], "sk-test123456")

        # Cleanup temp unit test profile
        cfg.delete_profile("TempUnitTest")

    def test_detect_provider(self):
        self.assertEqual(detect_provider("https://api.openai.com/v1"), "OpenAI")
        self.assertEqual(
            detect_provider("https://api.groq.com/openai/v1"), "Groq Cloud"
        )
        self.assertEqual(detect_provider("https://openrouter.ai/api/v1"), "OpenRouter")
        self.assertEqual(detect_provider("https://api.cerebras.ai/v1"), "Cerebras")
        self.assertEqual(detect_provider("https://api.deepseek.com/v1"), "DeepSeek")
        self.assertEqual(detect_provider("http://localhost:11434/v1"), "Ollama (Local)")
        self.assertEqual(detect_provider("http://localhost:8000/v1"), "vLLM (Local)")
        self.assertEqual(
            detect_provider("https://my-custom-endpoint.org/v1"),
            "Custom / OpenAI-Compatible",
        )

    def test_history_operations(self):
        cfg = ConfigManager()
        cfg.clear_history()
        self.assertEqual(len(cfg.get_history()), 0)

        record = {
            "model": "gpt-4o-mini",
            "ttft_ms": 150.0,
            "tps": 80.0,
            "success": True,
        }
        cfg.add_history(record)
        hist = cfg.get_history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["model"], "gpt-4o-mini")

        cfg.clear_history()
        self.assertEqual(len(cfg.get_history()), 0)


class TestClientDiagnostics(unittest.TestCase):
    def test_error_formatting_offline(self):
        client = APIDiagnosticsClient(
            "http://127.0.0.1:59999/v1", api_key="", timeout=1.0
        )
        res = client.fetch_models()
        self.assertFalse(res["success"])
        self.assertTrue(
            "Connection Refused" in res["error"] or "Connect Timeout" in res["error"]
        )

    def test_single_model_health_offline(self):
        client = APIDiagnosticsClient(
            "http://127.0.0.1:59999/v1", api_key="", timeout=1.0
        )
        health = client.test_single_model_health("gpt-4o")
        self.assertEqual(health["status"], "FAILED")
        self.assertTrue(
            "Connection Refused" in health["error_reason"]
            or "Connect Timeout" in health["error_reason"]
        )

    def test_calculate_statistics(self):
        # Empty array
        st_empty = calculate_statistics([])
        self.assertEqual(st_empty["mean"], 0.0)

        # Normal array: [100.0, 200.0, 300.0]
        data = [100.0, 200.0, 300.0]
        stats = calculate_statistics(data)
        self.assertEqual(stats["min"], 100.0)
        self.assertEqual(stats["max"], 300.0)
        self.assertEqual(stats["mean"], 200.0)
        self.assertEqual(stats["median"], 200.0)
        self.assertEqual(stats["stdev"], 100.0)

    @patch.object(APIDiagnosticsClient, "run_stream_benchmark")
    def test_multi_run_benchmark(self, mock_stream):
        mock_stream.side_effect = [
            {
                "success": True,
                "model": "test-model",
                "ttft_ms": 200.0,
                "tps": 80.0,
                "total_latency_ms": 500.0,
                "generation_latency_ms": 300.0,
                "tokens": 40,
                "response_text": "Ans 1",
            },
            {
                "success": True,
                "model": "test-model",
                "ttft_ms": 150.0,
                "tps": 85.0,
                "total_latency_ms": 450.0,
                "generation_latency_ms": 300.0,
                "tokens": 40,
                "response_text": "Ans 2",
            },
            {
                "success": True,
                "model": "test-model",
                "ttft_ms": 160.0,
                "tps": 82.0,
                "total_latency_ms": 460.0,
                "generation_latency_ms": 300.0,
                "tokens": 40,
                "response_text": "Ans 3",
            },
        ]
        client = APIDiagnosticsClient("https://api.openai.com/v1")
        multi_res = client.run_multi_run_benchmark("test-model", runs=3)
        self.assertTrue(multi_res["success"])
        self.assertEqual(multi_res["successful_runs"], 3)
        self.assertEqual(multi_res["stats"]["cold_start_ttft_ms"], 200.0)
        self.assertAlmostEqual(multi_res["stats"]["warm_ttft_ms"], 155.0, places=1)
        self.assertTrue(multi_res["stats"]["stability_score"] > 90.0)

    @patch.object(APIDiagnosticsClient, "run_stream_benchmark")
    def test_model_comparison(self, mock_stream):
        mock_stream.side_effect = [
            {
                "success": True,
                "model": "model-fast-ttft",
                "ttft_ms": 90.0,
                "tps": 50.0,
                "total_latency_ms": 400.0,
                "tokens": 30,
            },
            {
                "success": True,
                "model": "model-high-tps",
                "ttft_ms": 250.0,
                "tps": 120.0,
                "total_latency_ms": 350.0,
                "tokens": 30,
            },
        ]
        client = APIDiagnosticsClient("https://api.openai.com/v1")
        cmp_res = client.run_model_comparison(["model-fast-ttft", "model-high-tps"])
        self.assertEqual(cmp_res["successful_models"], 2)
        winners = cmp_res["winners"]
        self.assertEqual(winners["fastest_ttft"]["model"], "model-fast-ttft")
        self.assertEqual(winners["highest_tps"]["model"], "model-high-tps")
        self.assertEqual(winners["lowest_latency"]["model"], "model-high-tps")

    @patch.object(APIDiagnosticsClient, "test_single_chat_request")
    def test_stress_test(self, mock_request):
        mock_request.side_effect = [
            {
                "success": True,
                "latency_ms": 100.0,
                "tokens": 10,
                "status_code": 200,
                "error": None,
            },
            {
                "success": True,
                "latency_ms": 120.0,
                "tokens": 10,
                "status_code": 200,
                "error": None,
            },
            {
                "success": False,
                "latency_ms": 50.0,
                "tokens": 0,
                "status_code": 429,
                "error": "HTTP 429: Rate limit",
            },
        ]
        client = APIDiagnosticsClient("https://api.openai.com/v1")
        stress_res = client.run_stress_test(
            "model-test", concurrency=2, total_requests=3
        )
        self.assertEqual(stress_res["total_requests"], 3)
        self.assertEqual(stress_res["successful_requests"], 2)
        self.assertEqual(stress_res["failed_requests"], 1)
        self.assertAlmostEqual(stress_res["success_rate_pct"], 66.7, places=1)
        self.assertIn("HTTP 429: Rate limit", stress_res["error_breakdown"])


class TestExporters(unittest.TestCase):
    def setUp(self):
        self.sample_benchmark = {
            "success": True,
            "model": "gpt-4o",
            "ttft_ms": 180.5,
            "total_latency_ms": 650.0,
            "generation_latency_ms": 469.5,
            "tps": 85.2,
            "tokens": 40,
            "response_text": "Superposition and entanglement power quantum speedup.",
        }

    def test_export_json(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            out = export_to_json(self.sample_benchmark, temp_path)
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["generator"], "API TEST CLI")
            self.assertEqual(data["report"]["model"], "gpt-4o")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_export_csv(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            temp_path = tf.name

        try:
            out = export_to_csv(self.sample_benchmark, temp_path)
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("gpt-4o", content)
            self.assertIn("TTFT", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_export_markdown(self):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tf:
            temp_path = tf.name

        try:
            out = export_to_markdown(self.sample_benchmark, temp_path)
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("# ⚡ API TEST CLI", content)
            self.assertIn("`gpt-4o`", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_export_html(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tf:
            temp_path = tf.name

        try:
            out = export_to_html(self.sample_benchmark, temp_path)
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("API TEST CLI Telemetry Report", content)
            self.assertIn("gpt-4o", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_auto_export(self):
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tf:
            temp_path = tf.name

        try:
            out = auto_export(self.sample_benchmark, temp_path)
            self.assertTrue(out.endswith(".html"))
            self.assertTrue(os.path.exists(out))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestUIRendering(unittest.TestCase):
    def test_rgb_banner(self):
        banner = get_rgb_banner()
        self.assertIsNotNone(banner)
        self.assertTrue(len(banner.plain) > 0)

    def test_model_discovery_page_render(self):
        mock_results = [
            {
                "model": "gpt-4o",
                "status": "OK",
                "latency_ms": 120.5,
                "error_reason": None,
            },
            {
                "model": "llama-3-70b",
                "status": "FAILED",
                "latency_ms": None,
                "error_reason": "HTTP 401: Unauthorized (Invalid Key)",
            },
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
            "reasoning_text": "Analyzing the physical principles of qubit superpositions...",
            "reasoning_tokens": 12,
            "headers": {},
        }
        render_benchmark_report(mock_benchmark)

    def test_multi_run_benchmark_render(self):
        mock_multi = {
            "success": True,
            "model": "gpt-4o-mini",
            "total_runs": 3,
            "successful_runs": 3,
            "ttft_ms": 180.0,
            "tps": 80.0,
            "total_latency_ms": 600.0,
            "generation_latency_ms": 420.0,
            "tokens": 40,
            "stats": {
                "ttft": {
                    "min": 170.0,
                    "max": 190.0,
                    "mean": 180.0,
                    "median": 180.0,
                    "p95": 189.0,
                    "stdev": 10.0,
                },
                "tps": {
                    "min": 75.0,
                    "max": 85.0,
                    "mean": 80.0,
                    "median": 80.0,
                    "p95": 84.5,
                    "stdev": 5.0,
                },
                "total_latency": {
                    "min": 580.0,
                    "max": 620.0,
                    "mean": 600.0,
                    "median": 600.0,
                    "p95": 618.0,
                    "stdev": 20.0,
                },
                "stability_score": 93.8,
                "cold_start_ttft_ms": 190.0,
                "warm_ttft_ms": 175.0,
            },
            "runs": [
                {
                    "run_number": 1,
                    "success": True,
                    "ttft_ms": 190.0,
                    "tps": 75.0,
                    "total_latency_ms": 620.0,
                    "tokens": 40,
                },
                {
                    "run_number": 2,
                    "success": True,
                    "ttft_ms": 170.0,
                    "tps": 85.0,
                    "total_latency_ms": 580.0,
                    "tokens": 40,
                },
                {
                    "run_number": 3,
                    "success": True,
                    "ttft_ms": 180.0,
                    "tps": 80.0,
                    "total_latency_ms": 600.0,
                    "tokens": 40,
                },
            ],
        }
        render_multi_run_benchmark_report(mock_multi)

    def test_comparison_matrix_render(self):
        mock_cmp = {
            "prompt": "Test comparison",
            "models": [
                {
                    "model": "gpt-4o",
                    "success": True,
                    "ttft_ms": 150.0,
                    "tps": 60.0,
                    "total_latency_ms": 500.0,
                    "tokens": 30,
                },
                {
                    "model": "llama-3.3-70b",
                    "success": True,
                    "ttft_ms": 90.0,
                    "tps": 130.0,
                    "total_latency_ms": 320.0,
                    "tokens": 30,
                },
            ],
            "winners": {
                "fastest_ttft": {"model": "llama-3.3-70b", "value": 90.0},
                "highest_tps": {"model": "llama-3.3-70b", "value": 130.0},
                "lowest_latency": {"model": "llama-3.3-70b", "value": 320.0},
            },
        }
        render_model_comparison_matrix(mock_cmp)

    def test_stress_test_render(self):
        mock_stress = {
            "model": "gpt-4o-mini",
            "concurrency": 5,
            "total_requests": 10,
            "successful_requests": 9,
            "failed_requests": 1,
            "success_rate_pct": 90.0,
            "duration_sec": 2.5,
            "aggregate_tps": 150.0,
            "total_tokens": 375,
            "latency_stats": {
                "min": 150.0,
                "max": 450.0,
                "mean": 220.0,
                "median": 200.0,
                "p95": 410.0,
            },
            "error_breakdown": {"HTTP 429: Rate Limit": 1},
        }
        render_stress_test_report(mock_stress)

    def test_history_and_presets_render(self):
        history = [
            {
                "timestamp": "2026-09-17 12:00:00",
                "model": "gpt-4o",
                "ttft_ms": 150.0,
                "tps": 80.0,
                "total_latency_ms": 500.0,
                "success": True,
            }
        ]
        render_history_table(history)
        render_presets_table(DEFAULT_PRESETS)
        render_slash_commands()


class TestCLIArgs(unittest.TestCase):
    def test_parse_arguments(self):
        args = parse_arguments(
            ["--scan", "--base-url", "https://api.openai.com/v1", "--json"]
        )
        self.assertTrue(args.scan)
        self.assertEqual(args.base_url, "https://api.openai.com/v1")
        self.assertTrue(args.json)

        args2 = parse_arguments(
            [
                "--benchmark",
                "--model",
                "gpt-4o-mini",
                "--runs",
                "3",
                "--max-ttft",
                "300.0",
            ]
        )
        self.assertTrue(args2.benchmark)
        self.assertEqual(args2.model, "gpt-4o-mini")
        self.assertEqual(args2.runs, 3)
        self.assertEqual(args2.max_ttft, 300.0)

        args3 = parse_arguments(
            ["--compare", "--models", "gpt-4o,llama-3.3-70b", "--output", "report.html"]
        )
        self.assertTrue(args3.compare)
        self.assertEqual(args3.models, "gpt-4o,llama-3.3-70b")
        self.assertEqual(args3.output, "report.html")

        args4 = parse_arguments(
            ["--stress", "--model", "gpt-4o", "--concurrency", "10", "--requests", "50"]
        )
        self.assertTrue(args4.stress)
        self.assertEqual(args4.concurrency, 10)
        self.assertEqual(args4.requests, 50)

    @patch.object(APIDiagnosticsClient, "run_stream_benchmark")
    def test_execute_noninteractive_benchmark_success(self, mock_stream):
        mock_stream.return_value = {
            "success": True,
            "model": "gpt-4o",
            "ttft_ms": 150.0,
            "tps": 90.0,
            "total_latency_ms": 500.0,
            "generation_latency_ms": 350.0,
            "tokens": 45,
            "response_text": "Success",
        }
        args = parse_arguments(
            [
                "--benchmark",
                "--base-url",
                "https://api.openai.com/v1",
                "--model",
                "gpt-4o",
                "--json",
                "--max-ttft",
                "200.0",
            ]
        )
        exit_code = execute_noninteractive(args)
        self.assertEqual(exit_code, 0)

    @patch.object(APIDiagnosticsClient, "run_stream_benchmark")
    def test_execute_noninteractive_assertion_failure(self, mock_stream):
        mock_stream.return_value = {
            "success": True,
            "model": "gpt-4o",
            "ttft_ms": 350.0,
            "tps": 30.0,
            "total_latency_ms": 1500.0,
            "generation_latency_ms": 1150.0,
            "tokens": 45,
            "response_text": "Slow response",
        }
        args = parse_arguments(
            [
                "--benchmark",
                "--base-url",
                "https://api.openai.com/v1",
                "--model",
                "gpt-4o",
                "--max-ttft",
                "200.0",
                "--json",
            ]
        )
        exit_code = execute_noninteractive(args)
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()

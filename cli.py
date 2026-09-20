"""
API TEST CLI - Main Interactive Navigation Loop, REPL & Non-Interactive CLI Engine
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Ensure UTF-8 on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.box import ROUNDED, DOUBLE
from rich.status import Status
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from config import ConfigManager, DEFAULT_PRESETS, sanitize_base_url, detect_provider
from client import APIDiagnosticsClient
from picker import interactive_model_picker, read_key
from palette import prompt_live_input
from exporter import auto_export, export_to_json, export_to_csv, export_to_markdown, export_to_html
from ui import (
    clear_screen,
    print_banner,
    render_home_screen,
    render_slash_commands,
    render_model_discovery_page,
    render_benchmark_report,
    render_multi_run_benchmark_report,
    render_model_comparison_matrix,
    render_stress_test_report,
    render_history_table,
    render_presets_table,
)

console = Console()


class APITestApp:
    def __init__(self):
        self.config_mgr = ConfigManager()
        self.cached_models_raw: List[Dict[str, Any]] = []
        self.last_result: Optional[Dict[str, Any]] = None

    def get_client(self, base_url: str = "", api_key: str = "", timeout: float = 30.0) -> APIDiagnosticsClient:
        if base_url:
            return APIDiagnosticsClient(base_url=base_url, api_key=api_key, timeout=timeout)
        profile = self.config_mgr.get_active_profile() or {}
        return APIDiagnosticsClient(
            base_url=profile.get("base_url", ""),
            api_key=profile.get("api_key", ""),
            timeout=float(profile.get("timeout", 30.0)),
        )

    def prompt_input(self, prompt_text: str = "Command / Choice", default: str = "") -> str:
        """Standard input helper."""
        try:
            val = Prompt.ask(f"[bold grey85]❯ {prompt_text}[/bold grey85]", default=default).strip()
            return val
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Operation canceled by user.[/yellow]")
            return "/back"

    def handle_slash_command(self, cmd: str) -> Optional[str]:
        """
        Interprets global slash commands.
        Returns an action string if handled, or None if regular input.
        """
        cmd_clean = cmd.strip().lower()

        if cmd_clean in ["/quick", "/scan", "/fetch"]:
            self.run_quick_scan()
            return "handled"

        if cmd_clean in ["/test", "/eval", "/qbench", "/quicktest"]:
            self.run_quick_benchmark()
            return "handled"

        if cmd_clean in ["/compare", "/cmp", "/arena"]:
            self.run_model_comparison_interactive()
            return "handled"

        if cmd_clean in ["/stress", "/load", "/concurrency"]:
            self.run_stress_test_interactive()
            return "handled"

        if cmd_clean in ["/export", "/exp"]:
            self.export_results_interactive()
            return "handled"

        if cmd_clean in ["/history", "/h"]:
            self.view_history_interactive()
            return "handled"

        if cmd_clean in ["/presets", "/pre"]:
            self.browse_presets_interactive()
            return "handled"

        if cmd_clean in ["/exit", "/quit", "/q"]:
            self.exit_app()

        if cmd_clean in ["/clear", "/cls"]:
            clear_screen()
            return "handled"

        if cmd_clean in ["/back"]:
            return "back"

        if cmd_clean in ["/config", "/c"]:
            self.run_configuration_wizard()
            return "handled"

        if cmd_clean in ["/profiles", "/p"]:
            self.manage_profiles()
            return "handled"

        if cmd_clean in ["/models", "/m"]:
            self.run_model_discovery()
            return "handled"

        if cmd_clean in ["/bench", "/b"]:
            self.run_speed_benchmark()
            return "handled"

        if cmd_clean in ["/stream", "/s"]:
            self.run_interactive_stream()
            return "handled"

        if cmd_clean in ["/start"]:
            self.run_suite_menu()
            return "handled"

        if cmd_clean in ["/", "/help", "/?"]:
            from palette import print_inline_slash_preview
            print_inline_slash_preview()
            return "handled"

        return None

    def exit_app(self):
        console.print()
        console.print("[bold cyan]Thank you for using API TEST CLI. Goodbye![/bold cyan]")
        sys.exit(0)

    def select_profile_interactive(self, profiles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Displays table of all saved profiles and lets user select one."""
        clear_screen()
        print_banner(show_subtitle=False)

        active_prof = self.config_mgr.get_active_profile() or {}
        active_name = active_prof.get("name")

        table = Table(title="Saved Profiles & API Providers", title_style="bold cyan", box=ROUNDED, border_style="grey50", expand=True)
        table.add_column("#", width=4, justify="right", style="dim grey70")
        table.add_column("Profile Name", width=22, style="bold bright_white")
        table.add_column("Endpoint Base URL", min_width=35, style="bright_white")
        table.add_column("API Key", width=14, justify="center")
        table.add_column("Default Model", width=20, style="magenta")
        table.add_column("Status", width=12, justify="center")

        for idx, prof in enumerate(profiles, 1):
            is_active = prof["name"] == active_name
            status_str = "[bold green]● Active[/bold green]" if is_active else "[dim]—[/dim]"
            key_str = "[green]Configured[/green]" if prof.get("api_key") else "[yellow]None[/yellow]"
            model_str = prof.get("default_model") or "Auto"

            table.add_row(
                str(idx),
                prof["name"],
                prof["base_url"],
                key_str,
                model_str,
                status_str
            )

        console.print(table)
        console.print()

        console.print("[bold grey85]Select a profile number to use, or [0] to cancel.[/bold grey85]")
        choice = self.prompt_input("Profile Number", default="1")

        if choice.lower() in ["0", "b", "back", "cancel"]:
            return None

        if choice.isdigit():
            t_i = int(choice) - 1
            if 0 <= t_i < len(profiles):
                return profiles[t_i]

        return active_prof

    def _resolve_target_endpoint_for_quick(self, command_title: str) -> Optional[Tuple[APIDiagnosticsClient, str]]:
        """
        Helper for /quick, /test, /compare, and /stress:
        - If configured profiles exist: asks if user wants to use an existing profile or enter a new endpoint.
        """
        profiles = self.config_mgr.list_profiles()
        has_profiles = bool(profiles and any(p.get("base_url") for p in profiles))

        if has_profiles:
            clear_screen()
            print_banner(show_subtitle=False)

            active_prof = self.config_mgr.get_active_profile() or {}
            active_name = active_prof.get("name", "Custom")
            active_url = active_prof.get("base_url", "")

            ask_text = Text()
            ask_text.append(f"{command_title}\n\n", style="bold cyan")
            ask_text.append("Saved Profile Detected:\n", style="grey78")
            ask_text.append(f"• Active Profile: {active_name}\n", style="bold bright_cyan")
            ask_text.append(f"• Endpoint: {active_url}\n", style="bright_white")
            ask_text.append(f"• Total Saved Profiles: {len(profiles)}\n\n", style="dim grey70")
            ask_text.append("Do you want to use an existing configured profile?", style="bold yellow")

            console.print(Panel(ask_text, title="[bold grey78]Profile Check[/bold grey78]", border_style="grey50", box=ROUNDED, padding=(1, 2)))
            console.print()
            console.print("  [bold cyan][1][/bold cyan] [bold white]Yes[/bold white] — Select from saved profiles / Use current")
            console.print("  [bold cyan][2][/bold cyan] [bold white]No[/bold white]  — Enter a new API endpoint & test directly")
            console.print("  [bold cyan][0][/bold cyan] Cancel & Return")
            console.print()

            choice = self.prompt_input("Select Option [1: Yes | 2: No | 0: Back]", default="1")
            c_low = choice.lower().strip()

            if c_low in ["0", "b", "back"]:
                return None

            if c_low in ["1", "y", "yes"]:
                selected_prof = self.select_profile_interactive(profiles)
                if not selected_prof:
                    return None
                b_url = selected_prof.get("base_url", "")
                a_key = selected_prof.get("api_key", "")
                client = self.get_client(base_url=b_url, api_key=a_key)
                return client, b_url

        # Prompt for endpoint & API key
        clear_screen()
        print_banner(show_subtitle=False)

        info_panel = Panel(
            f"[bold bright_white]{command_title}[/bold bright_white]\n"
            "[dim grey70]Enter API Endpoint URL and optional API key to fetch and test models.[/dim grey70]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2)
        )
        console.print(info_panel)
        console.print()

        raw_url = self.prompt_input("Target Endpoint URL (e.g. https://api.openai.com/v1)")
        if not raw_url or raw_url.startswith("/"):
            res = self.handle_slash_command(raw_url)
            if res in ["back", "handled"]:
                return None
            if not raw_url:
                return None

        base_url = sanitize_base_url(raw_url)
        api_key = self.prompt_input("API Key (Optional, press Enter for empty/local)", default="")
        if api_key.startswith("/"):
            if self.handle_slash_command(api_key) == "back":
                return None

        client = self.get_client(base_url=base_url, api_key=api_key)
        return client, base_url

    def run_quick_scan(self):
        """
        Quick Command (/quick or /scan):
        Fetches all models and probes health status in parallel.
        """
        resolved = self._resolve_target_endpoint_for_quick("⚡ Quick Scan: Model Discovery & Health Check ⚡")
        if not resolved:
            return
        client, base_url = resolved

        with Status("[bold cyan]Connecting to endpoint & fetching model catalog...[/bold cyan]", spinner="dots"):
            fetch_res = client.fetch_models()

        if not fetch_res["success"]:
            render_model_discovery_page(
                base_url=base_url,
                results=[],
                discovery_latency_ms=fetch_res["latency_ms"],
                global_error=fetch_res["error"],
            )
            self.prompt_input("Press Enter to return to menu", default="")
            return

        raw_models = fetch_res["models"]
        self.cached_models_raw = raw_models
        self._execute_health_scan_flow(client, raw_models, fetch_res.get("endpoint_used", base_url), fetch_res["latency_ms"])

    def run_quick_benchmark(self):
        """
        Quick Command (/test or /eval):
        Fetches models, lets user pick one with arrow keys, and runs live speed & TTFT benchmark.
        """
        resolved = self._resolve_target_endpoint_for_quick("⚡ Quick Benchmark: Speed & TTFT Performance Test ⚡")
        if not resolved:
            return
        client, base_url = resolved

        with Status("[bold cyan]Connecting to endpoint & discovering models...[/bold cyan]", spinner="dots"):
            fetch_res = client.fetch_models()

        models_list = fetch_res.get("models", []) if fetch_res.get("success") else []
        self.cached_models_raw = models_list
        self._execute_benchmark_flow(client, models_list, base_url)

    def _execute_health_scan_flow(self, client: APIDiagnosticsClient, raw_models: List[Dict[str, Any]], base_url: str, discovery_latency_ms: float):
        """Helper to run parallel health probes across all models and show status board."""
        model_ids = [m["id"] for m in raw_models if isinstance(m, dict) and "id" in m]
        total_models = len(model_ids)

        probed_results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[cyan]Probing {total_models} models...", total=total_models)

            def on_step(completed_cnt: int, total_cnt: int, item_res: Dict[str, Any]):
                m_label = item_res.get('model', '')[:22]
                progress.update(task, advance=1, description=f"[cyan]Probing {m_label}... ({completed_cnt}/{total_cnt})")

            probed_results = client.probe_all_models_parallel(
                model_ids=model_ids,
                max_workers=8,
                timeout=15.0,
                progress_callback=on_step
            )

        render_model_discovery_page(
            base_url=base_url,
            results=probed_results,
            discovery_latency_ms=discovery_latency_ms,
            global_error=None,
        )

        scan_data = {
            "base_url": base_url,
            "models": probed_results,
            "discovery_latency_ms": discovery_latency_ms,
        }
        self.last_result = scan_data

        console.print("[bold grey85]Options:[/bold grey85] Enter [b] to benchmark a model, [e] to export scan, or [Enter] to return.")
        action = self.prompt_input("Action", default="")
        if action.lower() in ["b", "bench", "benchmark"]:
            self._execute_benchmark_flow(client, raw_models, base_url)
        elif action.lower() in ["e", "exp", "export"]:
            filename = self.prompt_input("Export file (e.g. scan.html, scan.json, scan.md)", default="models_scan.html")
            if filename:
                auto_export(scan_data, filename)
                console.print(f"[bold green]✓ Scan report exported to {filename}[/bold green]")
                time.sleep(1)

    def _execute_benchmark_flow(self, client: APIDiagnosticsClient, models_list: List[Dict[str, Any]], base_url: str):
        """Helper to run model picker and live stream benchmark with telemetry."""
        selected_model, _ = interactive_model_picker(
            client=client,
            cached_models_raw=models_list,
            title="Select Model to Benchmark",
            endpoint_name=base_url
        )

        if not selected_model:
            return

        clear_screen()
        print_banner(show_subtitle=False)

        info_box = Text()
        info_box.append("⚡ Speed & TTFT Benchmark Mode ⚡\n\n", style="bold green")
        info_box.append("Selected Model: ", style="bold grey70")
        info_box.append(f"{selected_model}\n", style="bold bright_cyan")
        info_box.append("Endpoint: ", style="bold grey70")
        info_box.append(f"{base_url}", style="bright_white")

        console.print(Panel(info_box, border_style="green", box=ROUNDED, padding=(1, 2)))
        console.print()

        prompt_text = self.prompt_input("Test Prompt", default="Explain quantum computing in 2 concise sentences.")
        if prompt_text.startswith("/"):
            res = self.handle_slash_command(prompt_text)
            if res in ["back", "handled"]:
                return

        runs_str = self.prompt_input("Benchmark Iterations [1: Quick Single Run | 3+: Statistical Percentiles]", default="1")
        runs = max(1, min(20, int(runs_str) if runs_str.isdigit() else 1))

        console.print()
        console.print(f"[bold grey85]Initiating benchmark for [cyan]{selected_model}[/cyan] ({runs} {'run' if runs == 1 else 'runs'})...[/bold grey85]")
        console.print()

        if runs > 1:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"[cyan]Running {runs} benchmark iterations...", total=runs)

                def on_run_step(curr, total, r):
                    progress.update(task, advance=1, description=f"[cyan]Completed run #{curr}/{total} (TTFT: {r.get('ttft_ms', 0):.1f}ms)")

                result = client.run_multi_run_benchmark(
                    model_id=selected_model,
                    prompt=prompt_text,
                    runs=runs,
                    max_tokens=350,
                    progress_callback=on_run_step,
                )
            render_multi_run_benchmark_report(result)
        else:
            first_token_marked = [False]

            def on_status_update(status_msg: str):
                console.print(f"[dim grey70]● {status_msg}[/dim grey70]")

            def on_chunk(chunk_str: str, metrics: Dict[str, Any]):
                if not first_token_marked[0]:
                    first_token_marked[0] = True
                    console.print(f"[bold green]✓ First token arrived! TTFT: {metrics.get('ttft_ms', 0):.1f} ms | Speed: {metrics.get('tps', 0):.1f} T/s[/bold green]\n")
                sys.stdout.write(chunk_str)
                sys.stdout.flush()

            console.print("[bold cyan]─── Live Streaming Response & Telemetry ───[/bold cyan]")
            result = client.run_stream_benchmark(
                model_id=selected_model,
                prompt=prompt_text,
                max_tokens=350,
                chunk_callback=on_chunk,
                status_callback=on_status_update,
            )
            console.print("\n")
            time.sleep(0.5)
            render_benchmark_report(result)

        self.last_result = result

        # Save to persistent history
        self.config_mgr.add_history({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": selected_model,
            "base_url": base_url,
            "ttft_ms": result.get("ttft_ms", 0.0),
            "tps": result.get("tps", 0.0),
            "total_latency_ms": result.get("total_latency_ms", 0.0),
            "success": result.get("success", False),
            "runs": runs,
        })

        console.print("[bold grey85]Options:[/bold grey85] Enter [e] to Export report, or [Enter] to return.")
        act = self.prompt_input("Action", default="")
        if act.lower() in ["e", "exp", "export"]:
            default_fn = f"benchmark_{selected_model.replace('/', '_')}.html"
            filename = self.prompt_input("Export file (e.g. report.html, report.json, report.md, report.csv)", default=default_fn)
            if filename:
                path = auto_export(result, filename)
                console.print(f"[bold green]✓ Benchmark report exported to: {path}[/bold green]")
                time.sleep(1.2)

    def run_model_comparison_interactive(self):
        """Interactive multi-model comparison arena."""
        resolved = self._resolve_target_endpoint_for_quick("🥊 Model Arena: Head-to-Head Comparison 🥊")
        if not resolved:
            return
        client, base_url = resolved

        if not self.cached_models_raw:
            with Status("[bold cyan]Fetching candidate models from endpoint...[/bold cyan]", spinner="dots"):
                fetch_res = client.fetch_models()
                if fetch_res.get("success"):
                    self.cached_models_raw = fetch_res.get("models", [])

        available_ids = [m["id"] for m in self.cached_models_raw if isinstance(m, dict) and "id" in m]

        clear_screen()
        print_banner(show_subtitle=False)
        console.print(Panel(
            "[bold bright_white]Model Arena: Select Models to Compare[/bold bright_white]\n"
            "[dim grey70]Enter 2 or more model IDs separated by commas (e.g. 'gpt-4o, gpt-4o-mini').[/dim grey70]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2)
        ))
        console.print()

        if available_ids:
            console.print("[bold grey85]Sample Discovered Models:[/bold grey85] " + ", ".join(f"[cyan]{m}[/cyan]" for m in available_ids[:8]))
            console.print()

        default_input = f"{available_ids[0]}, {available_ids[1]}" if len(available_ids) >= 2 else (available_ids[0] if available_ids else "gpt-4o, gpt-4o-mini")
        models_input = self.prompt_input("Enter comma-separated Model IDs to compare", default=default_input)
        if models_input.startswith("/"):
            if self.handle_slash_command(models_input) == "back":
                return
            return

        selected_models = [m.strip() for m in models_input.split(",") if m.strip()]
        if len(selected_models) < 2:
            console.print("[yellow]Please provide at least 2 models for head-to-head comparison.[/yellow]")
            time.sleep(1.5)
            return

        prompt = self.prompt_input("Comparison Benchmark Prompt", default="Explain quantum computing in 2 concise sentences.")
        if prompt.startswith("/"):
            return

        runs_str = self.prompt_input("Runs per model [1-5]", default="1")
        runs = max(1, min(5, int(runs_str) if runs_str.isdigit() else 1))

        console.print()
        comparison_result = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[cyan]Benchmarking {len(selected_models)} models...", total=len(selected_models))

            def on_progress(curr, total, model_name, res):
                progress.update(task, advance=1, description=f"[cyan]Completed {model_name} ({curr}/{total})")

            comparison_result = client.run_model_comparison(
                model_ids=selected_models,
                prompt=prompt,
                runs_per_model=runs,
                max_tokens=300,
                progress_callback=on_progress,
            )

        render_model_comparison_matrix(comparison_result)
        self.last_result = comparison_result

        # Save to history
        self.config_mgr.add_history({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": f"Arena ({len(selected_models)} models)",
            "base_url": base_url,
            "ttft_ms": comparison_result.get("winners", {}).get("fastest_ttft", {}).get("value", 0.0),
            "tps": comparison_result.get("winners", {}).get("highest_tps", {}).get("value", 0.0),
            "total_latency_ms": comparison_result.get("winners", {}).get("lowest_latency", {}).get("value", 0.0),
            "success": bool(comparison_result.get("successful_models", 0) > 0),
            "runs": runs,
        })

        exp = self.prompt_input("Export arena report? (e.g. arena.html, arena.md, arena.json) or Enter to skip", default="")
        if exp and not exp.startswith("/"):
            path = auto_export(comparison_result, exp)
            console.print(f"[bold green]✓ Successfully exported arena report to: {path}[/bold green]")
            time.sleep(1.2)

        self.prompt_input("Press Enter to return to menu", default="")

    def run_stress_test_interactive(self):
        """Interactive concurrency and rate-limit stress test."""
        resolved = self._resolve_target_endpoint_for_quick("🌪 Concurrency & Load Stress Test 🌪")
        if not resolved:
            return
        client, base_url = resolved

        target_model, _ = interactive_model_picker(
            client=client,
            cached_models_raw=self.cached_models_raw,
            title="Select Target Model for Stress Test",
            endpoint_name=base_url
        )
        if not target_model:
            return

        clear_screen()
        print_banner(show_subtitle=False)
        console.print(Panel(
            f"[bold bright_white]Concurrency Stress Testing for: [cyan]{target_model}[/cyan][/bold bright_white]\n"
            "[dim grey70]Simulates multiple concurrent client threads firing requests simultaneously.[/dim grey70]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2)
        ))
        console.print()

        concurrency_str = self.prompt_input("Concurrency level (parallel client workers)", default="5")
        concurrency = max(1, min(50, int(concurrency_str) if concurrency_str.isdigit() else 5))

        requests_str = self.prompt_input("Total requests to fire", default="15")
        total_requests = max(concurrency, min(200, int(requests_str) if requests_str.isdigit() else 15))

        test_prompt = self.prompt_input("Stress prompt", default="Say hello in one word.")

        console.print()
        stress_result = {}
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"[cyan]Firing {total_requests} requests across {concurrency} workers...", total=total_requests)

            def on_progress(completed, total, r):
                progress.update(task, advance=1, description=f"[cyan]Progress: {completed}/{total} requests")

            stress_result = client.run_stress_test(
                model_id=target_model,
                prompt=test_prompt,
                concurrency=concurrency,
                total_requests=total_requests,
                max_tokens=25,
                progress_callback=on_progress,
            )

        render_stress_test_report(stress_result)
        self.last_result = stress_result

        # Save to history
        self.config_mgr.add_history({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": f"{target_model} [Stress {concurrency}x]",
            "base_url": base_url,
            "ttft_ms": stress_result.get("latency_stats", {}).get("median", 0.0),
            "tps": stress_result.get("aggregate_tps", 0.0),
            "total_latency_ms": stress_result.get("latency_stats", {}).get("mean", 0.0),
            "success": stress_result.get("success_rate_pct", 0.0) >= 80.0,
            "runs": total_requests,
        })

        exp = self.prompt_input("Export stress report? (e.g. stress.html, stress.json) or Enter to skip", default="")
        if exp and not exp.startswith("/"):
            path = auto_export(stress_result, exp)
            console.print(f"[bold green]✓ Successfully exported stress test report to: {path}[/bold green]")
            time.sleep(1.2)

        self.prompt_input("Press Enter to return to menu", default="")

    def export_results_interactive(self):
        """Export recent results or history to disk."""
        if not self.last_result:
            console.print("[yellow]No recent benchmark or scan result in memory to export.[/yellow]")
            console.print("[dim grey70]Run /bench, /test, /compare, or /stress first.[/dim grey70]")
            hist = self.config_mgr.get_history()
            if hist:
                console.print()
                if Confirm.ask("[bold cyan]Would you like to export your historical telemetry runs to JSON?[/bold cyan]", default=True):
                    path = export_to_json({"history": hist}, "api_test_history.json")
                    console.print(f"[bold green]✓ Exported history to: {path}[/bold green]")
            time.sleep(1.5)
            return

        clear_screen()
        print_banner(show_subtitle=False)
        console.print(Panel(
            "[bold bright_white]Export Telemetry & Benchmark Report[/bold bright_white]\n"
            "[dim grey70]Supports: .json (Full data), .csv (Spreadsheet), .md (GitHub Markdown), .html (Interactive Dashboard)[/dim grey70]",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2)
        ))
        console.print()

        default_name = f"benchmark_report_{int(time.time())}.html"
        filename = self.prompt_input("Destination filename", default=default_name)
        if filename.startswith("/") or not filename:
            return

        try:
            path = auto_export(self.last_result, filename)
            console.print(f"\n[bold green]✓ Report successfully exported to: {path}[/bold green]")
        except Exception as exc:
            console.print(f"\n[bold red]Export failed: {exc}[/bold red]")
        time.sleep(1.5)

    def view_history_interactive(self):
        """Displays historical runs table with option to clear or export."""
        hist = self.config_mgr.get_history(limit=30)
        render_history_table(hist)

        if hist:
            console.print("[bold grey85]Options:[/bold grey85] Enter [c] to Clear history, [e] to Export JSON, or [Enter] to return.")
            act = self.prompt_input("Action", default="").lower().strip()
            if act in ["c", "clear"]:
                self.config_mgr.clear_history()
                console.print("[bold green]History cleared successfully.[/bold green]")
                time.sleep(1)
            elif act in ["e", "export"]:
                path = export_to_json({"history": hist}, "api_test_history.json")
                console.print(f"[bold green]✓ Exported history to: {path}[/bold green]")
                time.sleep(1.5)

    def browse_presets_interactive(self):
        """Displays provider presets and allows 1-click profile creation."""
        clear_screen()
        print_banner(show_subtitle=False)
        render_presets_table(DEFAULT_PRESETS)
        console.print(f"[bold grey85]Select a preset number [1-{len(DEFAULT_PRESETS)}] to apply, or [0] to return.[/bold grey85]")
        choice = self.prompt_input("Preset Number", default="1")
        if choice in ["0", "back", "b"] or choice.startswith("/"):
            return

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(DEFAULT_PRESETS):
                preset = DEFAULT_PRESETS[idx]
                p_name = preset["name"].split()[0]
                api_key = self.prompt_input(f"Enter API Key for {preset['name']} (optional/leave blank)", default=preset.get("api_key", ""))
                self.config_mgr.save_profile(
                    name=p_name,
                    base_url=preset["base_url"],
                    api_key=api_key,
                    default_model=preset["default_model"],
                )
                self.cached_models_raw = []
                console.print(f"[bold green]✓ Preset '{preset['name']}' configured and activated![/bold green]")
                time.sleep(1.5)

    def run_configuration_wizard(self):
        """Interactive setup for endpoint and API key with preset recommendations."""
        clear_screen()
        print_banner(show_subtitle=False)
        console.print(Panel("[bold bright_white]Configure API Endpoint Profile[/bold bright_white]\n[dim grey70]Select a popular provider preset or enter a custom endpoint URL.[/dim grey70]", border_style="grey50", box=ROUNDED))
        console.print()

        console.print("[bold grey85]Available Provider Presets:[/bold grey85]")
        for i, preset in enumerate(DEFAULT_PRESETS, 1):
            console.print(f"  [bold cyan][{i}][/bold cyan] {preset['name']} [dim]({preset['base_url']})[/dim]")
        console.print(f"  [bold cyan][{len(DEFAULT_PRESETS) + 1}][/bold cyan] Custom Endpoint URL")
        console.print()

        choice = self.prompt_input(f"Choose preset [1-{len(DEFAULT_PRESETS) + 1}]", default="1")
        slash_res = self.handle_slash_command(choice)
        if slash_res in ["back", "handled"]:
            return

        selected_url = ""
        selected_model = ""
        profile_name = "Custom"

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(DEFAULT_PRESETS):
                preset = DEFAULT_PRESETS[idx]
                selected_url = preset["base_url"]
                selected_model = preset["default_model"]
                profile_name = preset["name"].split()[0]

        url_input = self.prompt_input("API Base URL (e.g. https://api.openai.com/v1)", default=selected_url or "https://api.openai.com/v1")
        if url_input.startswith("/"):
            if self.handle_slash_command(url_input) == "back":
                return
        selected_url = sanitize_base_url(url_input)

        if not selected_url:
            console.print("[yellow]Base URL cannot be empty.[/yellow]")
            time.sleep(1)
            return

        key_input = self.prompt_input("API Key (Press Enter if not required / local)", default="")
        if key_input.startswith("/"):
            if self.handle_slash_command(key_input) == "back":
                return

        def_model = self.prompt_input("Default Model Identifier (Optional, e.g. gpt-4o-mini)", default=selected_model)
        if def_model.startswith("/"):
            if self.handle_slash_command(def_model) == "back":
                return

        p_name = self.prompt_input("Profile Name", default=profile_name)
        if p_name.startswith("/"):
            if self.handle_slash_command(p_name) == "back":
                return

        self.config_mgr.save_profile(
            name=p_name or "Custom",
            base_url=selected_url,
            api_key=key_input,
            default_model=def_model,
        )
        self.cached_models_raw = []

        console.print(f"[bold green]✓ Profile '{p_name or 'Custom'}' successfully saved and set as active![/bold green]")
        time.sleep(1.2)

    def manage_profiles(self):
        """Displays profile management menu to view, switch, or delete profiles."""
        while True:
            profiles = self.config_mgr.list_profiles()
            if not profiles:
                console.print("[yellow]No profiles configured yet.[/yellow]")
                time.sleep(1)
                self.run_configuration_wizard()
                return

            clear_screen()
            print_banner(show_subtitle=False)

            active_prof = self.config_mgr.get_active_profile() or {}
            active_name = active_prof.get("name")

            table = Table(title="Saved Profiles & Configurations", title_style="bold cyan", box=ROUNDED, border_style="grey50", expand=True)
            table.add_column("#", width=4, justify="right", style="dim grey70")
            table.add_column("Profile Name", width=20, style="bold bright_white")
            table.add_column("Endpoint URL", min_width=35, style="bright_white")
            table.add_column("Key", width=12, justify="center")
            table.add_column("Default Model", width=22, style="magenta")
            table.add_column("Status", width=12, justify="center")

            for idx, prof in enumerate(profiles, 1):
                is_active = prof["name"] == active_name
                status_str = "[bold green]● Active[/bold green]" if is_active else "[dim]—[/dim]"
                key_str = "[green]Set[/green]" if prof.get("api_key") else "[yellow]None[/yellow]"
                model_str = prof.get("default_model") or "Auto"

                table.add_row(
                    str(idx),
                    prof["name"],
                    prof["base_url"],
                    key_str,
                    model_str,
                    status_str
                )

            console.print(table)
            console.print()
            console.print("  [bold cyan][s][/bold cyan] Switch active profile")
            console.print("  [bold cyan][a][/bold cyan] Add new profile")
            console.print("  [bold cyan][d][/bold cyan] Delete a profile")
            console.print("  [bold cyan][0][/bold cyan] Return to previous menu")
            console.print()

            act = self.prompt_input("Select Action [s/a/d/0]", default="s").lower().strip()
            if act in ["0", "back", "b", "/back"]:
                break
            elif act in ["a", "add"]:
                self.run_configuration_wizard()
            elif act in ["d", "del", "delete"]:
                del_idx = self.prompt_input("Enter Profile # to delete")
                if del_idx.isdigit():
                    t_i = int(del_idx) - 1
                    if 0 <= t_i < len(profiles):
                        del_name = profiles[t_i]["name"]
                        if Confirm.ask(f"[bold red]Delete profile '{del_name}'?[/bold red]"):
                            self.config_mgr.delete_profile(del_name)
                            console.print(f"[green]Profile '{del_name}' deleted.[/green]")
                            time.sleep(1)
            elif act in ["s", "switch"]:
                sw_idx = self.prompt_input("Enter Profile # to activate")
                if sw_idx.isdigit():
                    t_i = int(sw_idx) - 1
                    if 0 <= t_i < len(profiles):
                        sel_name = profiles[t_i]["name"]
                        self.config_mgr.set_active_profile(sel_name)
                        self.cached_models_raw = []
                        console.print(f"[bold green]Switched active profile to '{sel_name}'.[/bold green]")
                        time.sleep(1)

    def run_model_discovery(self):
        """Fetches all models and runs parallel health probes on every single model."""
        client = self.get_client()
        profile = self.config_mgr.get_active_profile() or {}

        with Status("[bold cyan]Connecting to endpoint & discovering model catalog...[/bold cyan]", spinner="dots"):
            fetch_res = client.fetch_models()

        if not fetch_res["success"]:
            render_model_discovery_page(
                base_url=profile.get("base_url", ""),
                results=[],
                discovery_latency_ms=fetch_res["latency_ms"],
                global_error=fetch_res["error"],
            )
            self.prompt_input("Press Enter to return to menu", default="")
            return

        raw_models = fetch_res["models"]
        self.cached_models_raw = raw_models
        self._execute_health_scan_flow(client, raw_models, fetch_res.get("endpoint_used", profile.get("base_url", "")), fetch_res["latency_ms"])

    def run_speed_benchmark(self):
        """Selects a model with arrow-key picker and runs live latency & TTFT benchmark."""
        profile = self.config_mgr.get_active_profile() or {}
        client = self.get_client()
        self._execute_benchmark_flow(client, self.cached_models_raw, profile.get("base_url", ""))

    def run_interactive_stream(self):
        """Selects a model with arrow-key picker and enters interactive prompt REPL."""
        profile = self.config_mgr.get_active_profile() or {}
        client = self.get_client()

        selected_model, updated_cache = interactive_model_picker(
            client=client,
            cached_models_raw=self.cached_models_raw,
            title="Interactive Live Stream — Select Target Model",
            endpoint_name=profile.get("base_url", "")
        )
        self.cached_models_raw = updated_cache

        if not selected_model:
            return

        clear_screen()
        print_banner(show_subtitle=False)

        info_box = Text()
        info_box.append("⚡ Interactive Live Streaming REPL ⚡\n\n", style="bold cyan")
        info_box.append("Selected Model: ", style="bold grey70")
        info_box.append(f"{selected_model}\n", style="bold bright_cyan")
        info_box.append("Type your prompt and press Enter. Enter ", style="dim grey78")
        info_box.append("'/back'", style="bold white")
        info_box.append(" or ", style="dim grey78")
        info_box.append("'exit'", style="bold white")
        info_box.append(" to return.", style="dim grey78")

        console.print(Panel(info_box, border_style="cyan", box=ROUNDED, padding=(1, 2)))
        console.print()

        while True:
            prompt = self.prompt_input("Prompt")
            if not prompt or prompt.lower() in ["exit", "quit", "q", "/back", "back", "0"]:
                break
            if prompt.startswith("/"):
                res = self.handle_slash_command(prompt)
                if res in ["back", "handled"]:
                    break
                continue

            console.print()
            console.print(f"[dim]Sending request to {selected_model}...[/dim]\n")

            def on_chunk(chunk_str: str, metrics: Dict[str, Any]):
                sys.stdout.write(chunk_str)
                sys.stdout.flush()

            res = client.run_stream_benchmark(
                model_id=selected_model,
                prompt=prompt,
                max_tokens=600,
                chunk_callback=on_chunk,
            )

            console.print("\n")
            if res["success"]:
                console.print(f"[dim grey70]⚡ TTFT: {res['ttft_ms']:.1f}ms | Latency: {res['total_latency_ms']:.1f}ms | Speed: {res['tps']:.1f} T/s | Tokens: {res['tokens']}[/dim grey70]")
            else:
                console.print(f"[bold red]Error: {res['error']}[/bold red]")
            console.print()

    def run_suite_menu(self):
        """Inner workspace menu with all testing features."""
        while True:
            profile = self.config_mgr.get_active_profile() or {}
            clear_screen()
            print_banner(show_subtitle=False)

            header_text = Text()
            header_text.append(f"Active Profile: ", style="bold grey70")
            header_text.append(f"{profile.get('name', 'Custom')}  ", style="bold cyan")
            header_text.append(f"|  Endpoint: ", style="bold grey70")
            header_text.append(f"{profile.get('base_url', 'None')}", style="bright_white")

            console.print(Panel(header_text, border_style="grey50", box=ROUNDED, padding=(0, 2)))
            console.print()

            opt1 = Panel("[bold white][1] Model Discovery & Health Status Board[/bold white]\n[dim grey70]Discover models, run full parallel health probes ([OK]/[FAILED])[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt2 = Panel("[bold white][2] Speed & TTFT Benchmark (Single or Multi-Run)[/bold white]\n[dim grey70]Measure TTFT latency, P95, throughput & stability score[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt3 = Panel("[bold white][3] Model Arena (Head-to-Head 2+ Models Comparison)[/bold white]\n[dim grey70]Compare multiple models side-by-side with winner badges[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt4 = Panel("[bold white][4] Concurrency & Load Stress Test[/bold white]\n[dim grey70]Test rate limits, concurrent streams & aggregate throughput[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt5 = Panel("[bold white][5] Interactive Live Stream REPL[/bold white]\n[dim grey70]Interactive prompt testing with real-time token stream[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt6 = Panel("[bold white][6] Export Telemetry & Historical Runs[/bold white]\n[dim grey70]Save HTML/JSON/CSV reports or view telemetry history[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt7 = Panel("[bold white][7] Reconfigure Endpoint / Presets[/bold white]\n[dim grey70]Switch profile, add new endpoint, or load provider presets[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt0 = Panel("[bold white][0] Back to Home Screen[/bold white]\n[dim grey70]Return to main landing screen[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")

            console.print(opt1)
            console.print(opt2)
            console.print(opt3)
            console.print(opt4)
            console.print(opt5)
            console.print(opt6)
            console.print(opt7)
            console.print(opt0)
            console.print()

            choice = prompt_live_input("Select Option [0-7] or type '/' for commands")

            slash_res = self.handle_slash_command(choice)
            if slash_res == "back":
                break
            if slash_res == "handled":
                continue

            if choice in ["1", "m", "models", "/models"]:
                self.run_model_discovery()
            elif choice in ["2", "b", "bench", "/bench"]:
                self.run_speed_benchmark()
            elif choice in ["3", "compare", "arena", "/compare"]:
                self.run_model_comparison_interactive()
            elif choice in ["4", "stress", "load", "/stress"]:
                self.run_stress_test_interactive()
            elif choice in ["5", "s", "stream", "/stream"]:
                self.run_interactive_stream()
            elif choice in ["6", "export", "history", "/export", "/history"]:
                self.export_results_interactive()
            elif choice in ["7", "c", "config", "presets", "/config", "/presets"]:
                self.run_configuration_wizard()
            elif choice in ["0", "back", "b", "home", "/back"]:
                break
            else:
                console.print("[yellow]Invalid selection. Enter 0-7 or '/' for help.[/yellow]")
                time.sleep(1)

    def main_loop(self):
        """Top-level main loop."""
        while True:
            profile = self.config_mgr.get_active_profile()
            render_home_screen(profile)

            choice = prompt_live_input("Select Option [1: Start | 2: Exit] or type '/'")

            slash_res = self.handle_slash_command(choice)

            if slash_res == "handled":
                continue

            if choice in ["1", "start", "s", "/start"]:
                if not self.config_mgr.has_configured_profile():
                    console.print("[yellow]No API endpoint configured yet. Let's set up your profile first.[/yellow]")
                    time.sleep(1)
                    self.run_configuration_wizard()
                    if not self.config_mgr.has_configured_profile():
                        continue

                self.run_suite_menu()

            elif choice in ["2", "exit", "quit", "q", "/exit"]:
                self.exit_app()
            else:
                console.print("[yellow]Please enter 1 (Start), 2 (Exit), or type '/' for slash commands.[/yellow]")
                time.sleep(1.2)


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments for non-interactive CI/CD and script automation."""
    parser = argparse.ArgumentParser(
        description="API TEST CLI - High-Performance AI Endpoint Benchmark, TTFT Telemetry & Diagnostics",
        prog="api_test.py",
    )
    parser.add_argument("--scan", action="store_true", help="Run non-interactive model discovery and health probe scan")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark against a model")
    parser.add_argument("--compare", action="store_true", help="Run multi-model comparison arena")
    parser.add_argument("--stress", action="store_true", help="Run concurrency & rate-limit stress test")

    parser.add_argument("--model", type=str, default="", help="Target model ID for benchmark or stress test")
    parser.add_argument("--models", type=str, default="", help="Comma-separated model IDs for comparison (e.g. gpt-4o,gpt-4o-mini)")
    parser.add_argument("--prompt", type=str, default="", help="Custom benchmark or test prompt")
    parser.add_argument("--runs", type=int, default=1, help="Number of benchmark iterations (default: 1)")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrency workers for stress test (default: 5)")
    parser.add_argument("--requests", type=int, default=15, help="Total requests for stress test (default: 15)")

    parser.add_argument("--base-url", type=str, default="", help="Override API endpoint base URL")
    parser.add_argument("--api-key", type=str, default="", help="Override API key")
    parser.add_argument("--profile", type=str, default="", help="Use specific saved profile name")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds")

    parser.add_argument("--output", type=str, default="", help="Export results to file (.json, .csv, .md, .html)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON to stdout (headless / CI mode)")

    # CI/CD Threshold Assertions
    parser.add_argument("--max-ttft", type=float, default=0.0, help="Fail with exit code 1 if TTFT exceeds this threshold in ms")
    parser.add_argument("--min-tps", type=float, default=0.0, help="Fail with exit code 1 if throughput is below this threshold in tokens/sec")
    parser.add_argument("--min-success-rate", type=float, default=0.0, help="Fail with exit code 1 if success rate drops below this percentage")

    return parser.parse_args(argv)


def execute_noninteractive(args: argparse.Namespace) -> int:
    """Executes non-interactive command line workflows and CI assertions."""
    config_mgr = ConfigManager()

    # Resolve active profile or override
    base_url = args.base_url
    api_key = args.api_key
    timeout = args.timeout

    if args.profile:
        config_mgr.set_active_profile(args.profile)

    if not base_url:
        prof = config_mgr.get_active_profile() or {}
        base_url = prof.get("base_url", "")
        if not api_key:
            api_key = prof.get("api_key", "")

    base_url = sanitize_base_url(base_url)
    if not base_url:
        if args.json:
            print(json.dumps({"error": "No endpoint base URL specified or configured."}, indent=2))
        else:
            console.print("[bold red]Error: No API endpoint specified. Provide --base-url or configure a profile.[/bold red]")
        return 1

    client = APIDiagnosticsClient(base_url=base_url, api_key=api_key, timeout=timeout)

    # Mode 1: Scan
    if args.scan:
        fetch_res = client.fetch_models()
        if not fetch_res.get("success"):
            if args.json:
                print(json.dumps(fetch_res, indent=2))
            else:
                render_model_discovery_page(base_url, [], fetch_res.get("latency_ms", 0.0), fetch_res.get("error"))
            return 1

        raw_models = fetch_res.get("models", [])
        model_ids = [m["id"] for m in raw_models if isinstance(m, dict) and "id" in m]
        results = client.probe_all_models_parallel(model_ids=model_ids)

        scan_data = {"base_url": base_url, "models": results, "discovery_latency_ms": fetch_res["latency_ms"]}
        if args.json:
            print(json.dumps(scan_data, indent=2))
        else:
            render_model_discovery_page(base_url, results, fetch_res["latency_ms"])

        if args.output:
            auto_export(scan_data, args.output)

        failed_count = sum(1 for r in results if r.get("status") != "OK")
        return 1 if (results and failed_count == len(results)) else 0

    # Mode 2: Benchmark
    elif args.benchmark:
        target_model = args.model
        if not target_model:
            prof = config_mgr.get_active_profile() or {}
            target_model = prof.get("default_model", "")

        if not target_model:
            fetch_res = client.fetch_models()
            if fetch_res.get("success") and fetch_res.get("models"):
                target_model = fetch_res["models"][0]["id"]
            else:
                if args.json:
                    print(json.dumps({"error": "No target model specified. Use --model <id>"}, indent=2))
                else:
                    console.print("[bold red]Error: Target model not specified. Use --model <id>[/bold red]")
                return 1

        prompt = args.prompt or "Explain quantum computing in 2 concise sentences."

        if args.runs > 1:
            res = client.run_multi_run_benchmark(model_id=target_model, prompt=prompt, runs=args.runs)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                render_multi_run_benchmark_report(res)
        else:
            res = client.run_stream_benchmark(model_id=target_model, prompt=prompt)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                render_benchmark_report(res)

        if args.output:
            auto_export(res, args.output)

        if not res.get("success"):
            return 1

        # CI Assertions
        if args.max_ttft > 0.0 and res.get("ttft_ms", 0.0) > args.max_ttft:
            if not args.json:
                console.print(f"[bold red]CI Failure: TTFT ({res.get('ttft_ms')} ms) exceeded threshold ({args.max_ttft} ms)[/bold red]")
            return 1

        if args.min_tps > 0.0 and res.get("tps", 0.0) < args.min_tps:
            if not args.json:
                console.print(f"[bold red]CI Failure: Throughput ({res.get('tps')} T/s) below threshold ({args.min_tps} T/s)[/bold red]")
            return 1

        return 0

    # Mode 3: Compare
    elif args.compare:
        models_raw = args.models
        if not models_raw:
            if args.json:
                print(json.dumps({"error": "Comparison requires --models <model1,model2,...>"}, indent=2))
            else:
                console.print("[bold red]Error: Comparison requires --models <model1,model2,...>[/bold red]")
            return 1

        selected_models = [m.strip() for m in models_raw.split(",") if m.strip()]
        if len(selected_models) < 2:
            if args.json:
                print(json.dumps({"error": "At least 2 models required for comparison."}, indent=2))
            else:
                console.print("[bold red]Error: At least 2 models required for comparison.[/bold red]")
            return 1

        prompt = args.prompt or "Explain quantum computing in 2 concise sentences."
        res = client.run_model_comparison(model_ids=selected_models, prompt=prompt, runs_per_model=args.runs)

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_model_comparison_matrix(res)

        if args.output:
            auto_export(res, args.output)

        return 0 if res.get("successful_models", 0) > 0 else 1

    # Mode 4: Stress
    elif args.stress:
        target_model = args.model
        if not target_model:
            prof = config_mgr.get_active_profile() or {}
            target_model = prof.get("default_model", "")

        if not target_model:
            if args.json:
                print(json.dumps({"error": "Target model required for stress test. Use --model <id>"}, indent=2))
            else:
                console.print("[bold red]Error: Target model required for stress test. Use --model <id>[/bold red]")
            return 1

        prompt = args.prompt or "Say hello in one word."
        res = client.run_stress_test(
            model_id=target_model,
            prompt=prompt,
            concurrency=args.concurrency,
            total_requests=args.requests,
        )

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            render_stress_test_report(res)

        if args.output:
            auto_export(res, args.output)

        if args.min_success_rate > 0.0 and res.get("success_rate_pct", 0.0) < args.min_success_rate:
            if not args.json:
                console.print(f"[bold red]CI Failure: Success rate ({res.get('success_rate_pct')}%) below threshold ({args.min_success_rate}%)[/bold red]")
            return 1

        return 0

    return 0


def main():
    args = parse_arguments()

    # Check if any non-interactive flags were requested
    if args.scan or args.benchmark or args.compare or args.stress:
        code = execute_noninteractive(args)
        sys.exit(code)

    # Otherwise enter interactive REPL
    app = APITestApp()
    try:
        app.main_loop()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[bold cyan]API TEST CLI exited cleanly.[/bold cyan]")


if __name__ == "__main__":
    main()

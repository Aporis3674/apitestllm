"""
API TEST CLI - Main Interactive Navigation Loop & REPL
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.box import ROUNDED
from rich.status import Status
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from config import ConfigManager, DEFAULT_PRESETS, sanitize_base_url
from client import APIDiagnosticsClient
from picker import interactive_model_picker, read_key
from palette import prompt_live_input
from ui import (
    clear_screen,
    print_banner,
    render_home_screen,
    render_slash_commands,
    render_model_discovery_page,
    render_benchmark_report,
)

console = Console()


class APITestApp:
    def __init__(self):
        self.config_mgr = ConfigManager()
        self.cached_models_raw: List[Dict[str, Any]] = []

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
        Helper for /quick and /test:
        - If configured profiles exist: asks if user wants to use an existing profile or input a new endpoint.
          - If Yes: lets user pick from saved profiles.
          - If No: prompts for endpoint URL & optional key.
        - If no saved profiles: prompts directly for endpoint URL & optional key.
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

        # No profiles OR user selected NO: prompt for endpoint & API key
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
        - Asks if user wants to use existing profile or enter a new endpoint.
        - Fetches all models and probes health status in parallel.
        - Displays Model Discovery & Health Status Board.
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
        self._execute_health_scan_flow(client, raw_models, fetch_res.get("endpoint_used", base_url), fetch_res["latency_ms"])

    def run_quick_benchmark(self):
        """
        Quick Command (/test or /eval):
        - Asks if user wants to use existing profile or enter a new endpoint.
        - Fetches models, lets user pick one with arrow keys, and runs live speed & TTFT benchmark.
        """
        resolved = self._resolve_target_endpoint_for_quick("⚡ Quick Benchmark: Speed & TTFT Performance Test ⚡")
        if not resolved:
            return
        client, base_url = resolved

        with Status("[bold cyan]Connecting to endpoint & discovering models...[/bold cyan]", spinner="dots"):
            fetch_res = client.fetch_models()

        models_list = fetch_res.get("models", []) if fetch_res.get("success") else []
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

        console.print("[bold grey85]Options:[/bold grey85] Enter [b] to benchmark a model, or [Enter] to return.")
        action = self.prompt_input("Action", default="")
        if action.lower() in ["b", "bench", "benchmark"]:
            self._execute_benchmark_flow(client, raw_models, base_url)

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

        console.print()
        console.print(f"[bold grey85]Initiating benchmark for [cyan]{selected_model}[/cyan]...[/bold grey85]")
        console.print()

        def on_status_update(status_msg: str):
            console.print(f"[dim grey70]● {status_msg}[/dim grey70]")

        console.print("[bold cyan]─── Live Streaming Response & Telemetry ───[/bold cyan]")

        first_token_marked = [False]

        def on_chunk(chunk_str: str, metrics: Dict[str, Any]):
            if not first_token_marked[0]:
                first_token_marked[0] = True
                console.print(f"[bold green]✓ First token arrived! TTFT: {metrics['ttft_ms']:.1f} ms | Speed: {metrics['tps']:.1f} T/s[/bold green]")
                console.print()
            sys.stdout.write(chunk_str)
            sys.stdout.flush()

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
        self.prompt_input("Press Enter to continue", default="")

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

        key_input = self.prompt_input("API Key (Optional, press Enter for empty/local)", default="")
        if key_input.startswith("/"):
            if self.handle_slash_command(key_input) == "back":
                return

        model_input = self.prompt_input("Default Model ID (Optional)", default=selected_model)
        if model_input.startswith("/"):
            if self.handle_slash_command(model_input) == "back":
                return

        name_input = self.prompt_input("Profile Name", default=profile_name)

        self.config_mgr.save_profile(
            name=name_input,
            base_url=selected_url,
            api_key=key_input,
            default_model=model_input,
        )

        self.cached_models_raw = []

        console.print()
        console.print(f"[bold green]✓ Profile '{name_input}' successfully saved and set as active![/bold green]")
        time.sleep(1.0)

    def manage_profiles(self):
        """Lists, switches, or deletes saved profiles."""
        clear_screen()
        print_banner(show_subtitle=False)
        profiles = self.config_mgr.list_profiles()
        active_prof = self.config_mgr.get_active_profile()
        active = active_prof.get("name") if active_prof else None

        console.print(Panel("[bold bright_white]Saved API Profiles[/bold bright_white]", border_style="grey50", box=ROUNDED))
        console.print()

        if not profiles:
            console.print("[yellow]No profiles saved yet.[/yellow]")
        else:
            for idx, prof in enumerate(profiles, 1):
                is_active = prof["name"] == active
                active_marker = "[bold green]● (ACTIVE)[/bold green]" if is_active else ""
                key_tag = "[green]Key: Set[/green]" if prof.get("api_key") else "[yellow]Key: None[/yellow]"
                console.print(f"  [bold cyan][{idx}][/bold cyan] [bold white]{prof['name']}[/bold white] {active_marker}")
                console.print(f"      Endpoint: [bright_white]{prof['base_url']}[/bright_white] | {key_tag} | Model: [magenta]{prof.get('default_model') or 'Auto'}[/magenta]")
                console.print()

        console.print("[dim]Options: Enter [Number] to switch active profile, [a] to Add New, [d Number] to delete, or [b] to go Back.[/dim]")
        choice = self.prompt_input("Profile Action", default="b")

        if choice.lower() in ["b", "back", "0", ".."]:
            return
        if choice.lower() in ["a", "add", "new"]:
            self.run_configuration_wizard()
            return
        if choice.lower().startswith("d "):
            target_idx = choice[2:].strip()
            if target_idx.isdigit():
                t_i = int(target_idx) - 1
                if 0 <= t_i < len(profiles):
                    deleted_name = profiles[t_i]["name"]
                    self.config_mgr.delete_profile(deleted_name)
                    self.cached_models_raw = []
                    console.print(f"[yellow]Deleted profile '{deleted_name}'.[/yellow]")
                    time.sleep(1)
            return

        if choice.isdigit():
            t_i = int(choice) - 1
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
            console.print(f"[dim]Sending request to {selected_model}...[/dim]")

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
        """Inner workspace menu after pressing Start."""
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
            opt2 = Panel("[bold white][2] Speed & TTFT Benchmark (Select Model with Arrows)[/bold white]\n[dim grey70]Pick model from discovered list, measure TTFT latency & tokens/sec[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt3 = Panel("[bold white][3] Interactive Live Stream (Select Model with Arrows)[/bold white]\n[dim grey70]Pick model from discovered list, chat with real-time token stream[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt4 = Panel("[bold white][4] Reconfigure Endpoint / Switch Profile[/bold white]\n[dim grey70]Update Base URL, API Key, or switch saved profiles[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")
            opt0 = Panel("[bold white][0] Back to Home Screen[/bold white]\n[dim grey70]Return to main landing screen[/dim grey70]", border_style="grey50", box=ROUNDED, style="on #1e1e1e")

            console.print(opt1)
            console.print(opt2)
            console.print(opt3)
            console.print(opt4)
            console.print(opt0)
            console.print()

            choice = prompt_live_input("Select Option [0-4] or type '/' for commands")

            slash_res = self.handle_slash_command(choice)
            if slash_res == "back":
                break
            if slash_res == "handled":
                continue

            if choice in ["1", "m", "models", "/models"]:
                self.run_model_discovery()
            elif choice in ["2", "b", "bench", "/bench"]:
                self.run_speed_benchmark()
            elif choice in ["3", "s", "stream", "/stream"]:
                self.run_interactive_stream()
            elif choice in ["4", "c", "config", "/config"]:
                self.run_configuration_wizard()
            elif choice in ["0", "back", "b", "home", "/back"]:
                break
            else:
                console.print("[yellow]Invalid selection. Enter 1-4, 0, or '/' for help.[/yellow]")
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


def main():
    app = APITestApp()
    try:
        app.main_loop()
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[bold cyan]API TEST CLI exited cleanly.[/bold cyan]")


if __name__ == "__main__":
    main()

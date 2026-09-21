"""
API TEST CLI - Rich TUI Components, RGB ASCII Banner & Visual Engine
"""

import colorsys
import os
from typing import Any

from rich.align import Align
from rich.box import DOUBLE, ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ._compat import ensure_utf8_stdio

ensure_utf8_stdio()

console = Console()

ASCII_BANNER_BLOCK = [
    r" █████╗ ██████╗ ██╗    ████████╗███████╗███████╗████████╗",
    r"██╔══██╗██╔══██╗██║    ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝",
    r"███████║██████╔╝██║       ██║   █████╗  ███████╗   ██║   ",
    r"██╔══██║██╔═══╝ ██║       ██║   ██╔══╝  ╚════██║   ██║   ",
    r"██║  ██║██║     ██║       ██║   ███████╗███████║   ██║   ",
    r"╚═╝  ╚═╝╚═╝     ╚═╝       ╚═╝   ╚══════╝╚══════╝   ╚═╝   ",
]


def clear_screen():
    """Clears the console buffer cleanly across Windows and POSIX."""
    os.system("cls" if os.name == "nt" else "clear")


def get_rgb_banner() -> Text:
    """Generates an eye-catching RGB rainbow/gradient ASCII art banner for API TEST."""
    text = Text()
    total_lines = len(ASCII_BANNER_BLOCK)
    for i, line in enumerate(ASCII_BANNER_BLOCK):
        line_len = len(line)
        for j, char in enumerate(line):
            # Dynamic Hue calculation across X and Y axes for smooth rainbow gradient
            hue = ((j / max(line_len, 1)) * 0.75 + (i / total_lines) * 0.25) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
            text.append(
                char, style=f"rgb({int(r * 255)},{int(g * 255)},{int(b * 255)})"
            )
        text.append("\n")
    return text


def print_banner(show_subtitle: bool = True):
    """Renders the RGB banner and project subtitle."""
    banner_text = get_rgb_banner()
    console.print(Align.center(banner_text))
    if show_subtitle:
        subtitle = Text(
            "⚡ High-Performance AI Endpoint & Latency Benchmark Suite ⚡",
            style="bold cyan",
        )
        console.print(Align.center(subtitle))
        console.print()


def render_home_screen(profile: dict[str, Any] | None):
    """
    Renders the main home screen.
    If no profile is configured yet, explicitly shows 'Not Configured' status.
    If configured, displays active profile details with grey buttons.
    """
    clear_screen()
    print_banner(show_subtitle=True)

    profile_data: dict[str, Any] = profile or {}
    is_configured = bool(profile_data.get("base_url"))

    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Field", style="bold grey70")
    info_table.add_column("Value", style="bold white")

    if is_configured:
        base_url = profile_data.get("base_url", "Not configured")
        api_key = profile_data.get("api_key", "")
        key_display = (
            f"[green]Configured ({api_key[:4]}...{api_key[-3:]})[/green]"
            if api_key
            else "[yellow]None (Optional/Local)[/yellow]"
        )
        default_model = profile_data.get("default_model") or "[dim]Auto-detect[/dim]"
        profile_name = profile_data.get("name", "Custom")

        info_table.add_row(
            "Active Profile",
            f"[bold cyan]{profile_name}[/bold cyan] [green](Saved)[/green]",
        )
        info_table.add_row("Base URL", f"[bright_white]{base_url}[/bright_white]")
        info_table.add_row("API Key", key_display)
        info_table.add_row("Default Model", f"[magenta]{default_model}[/magenta]")

        panel_title = "[bold grey78]Active Configuration[/bold grey78]"
        btn1_sub = (
            f"[dim grey70]Continue with profile '{profile_name}' "
            "or reconfigure[/dim grey70]"
        )
    else:
        info_table.add_row("Active Profile", "[dim grey50]None[/dim grey50]")
        info_table.add_row(
            "Base URL", "[bold yellow]⚠ Not Configured Yet[/bold yellow]"
        )
        info_table.add_row("API Key", "[dim grey50]Not Set[/dim grey50]")
        info_table.add_row(
            "Status", "[bold yellow]Click [1. START] to set up endpoint[/bold yellow]"
        )

        panel_title = "[bold grey78]Configuration Status[/bold grey78]"
        btn1_sub = "[dim grey70]Add API Endpoint & start testing[/dim grey70]"

    profile_panel = Panel(
        info_table,
        title=panel_title,
        title_align="left",
        border_style="grey50",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(profile_panel)
    console.print()

    # Sleek Grey Buttons
    button_1 = Panel(
        f"[bold grey93]1. START[/bold grey93]\n{btn1_sub}",
        border_style="grey62",
        box=ROUNDED,
        style="on #222222",
        padding=(0, 2),
    )

    button_2 = Panel(
        (
            "[bold grey93]2. EXIT[/bold grey93]\n"
            "[dim grey70]Terminate application & return to terminal[/dim grey70]"
        ),
        border_style="grey62",
        box=ROUNDED,
        style="on #222222",
        padding=(0, 2),
    )

    console.print(Columns([button_1, button_2], expand=True, equal=True))
    console.print()

    # Instructions & Slash Command Notice in Quick Tips
    hint_text = Text()
    hint_text.append("💡 Quick Tips: ", style="bold yellow")
    hint_text.append("Select ", style="grey78")
    hint_text.append("[1]", style="bold bright_white")
    if is_configured:
        hint_text.append(" to launch tests or reconfigure. Enter ", style="grey78")
    else:
        hint_text.append(" to configure your API endpoint. Enter ", style="grey78")
    hint_text.append("[2]", style="bold bright_white")
    hint_text.append(" or ", style="grey78")
    hint_text.append("[q]", style="bold bright_white")
    hint_text.append(" to exit.\n", style="grey78")
    hint_text.append("Press ", style="grey78")
    hint_text.append("[/]", style="bold cyan")
    hint_text.append(
        " at any moment to open the instant live Slash Command palette & preview.",
        style="bold #cccccc",
    )

    console.print(Panel(hint_text, border_style="grey37", box=ROUNDED, padding=(0, 2)))
    console.print()


def render_slash_commands():
    """Displays full list of available slash commands in a clean table modal."""
    table = Table(
        title="Global Slash Commands",
        title_style="bold cyan",
        box=ROUNDED,
        border_style="cyan",
    )
    table.add_column("Command", style="bold green", no_wrap=True)
    table.add_column("Alias", style="bold yellow", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("/start", "1", "Start testing suite with current or new profile")
    table.add_row(
        "/quick",
        "scan",
        "Instantly fetch and inspect model health with quick endpoint entry",
    )
    table.add_row(
        "/test", "eval", "Quick benchmark: pick a model and run speed telemetry"
    )
    table.add_row(
        "/compare", "cmp", "Head-to-head multi-model performance arena & leaderboard"
    )
    table.add_row(
        "/stress",
        "load",
        "Concurrency & rate-limit load test with aggregate throughput",
    )
    table.add_row(
        "/export", "exp", "Export benchmark results to JSON, CSV, Markdown, or HTML"
    )
    table.add_row(
        "/history", "h", "Browse and inspect past benchmark telemetry history"
    )
    table.add_row(
        "/presets",
        "pre",
        "Apply popular cloud (Groq, Cerebras, OpenRouter) or local presets",
    )
    table.add_row(
        "/models", "m", "Fetch all models and check real-time status (OK / Failed)"
    )
    table.add_row("/bench", "b", "Run multi-run statistical benchmark (TTFT, TPS, P95)")
    table.add_row(
        "/stream", "s", "Interactive live streaming test with real-time token metrics"
    )
    table.add_row("/config", "c", "Reconfigure Base URL, API Key, and profile settings")
    table.add_row("/profiles", "p", "Switch, view, or manage saved API profiles")
    table.add_row("/clear", "cls", "Clear terminal screen buffer")
    table.add_row("/back", "0, ..", "Navigate back to previous menu or home screen")
    table.add_row("/help", "?, /", "Display this slash commands reference list")
    table.add_row("/exit", "2, q", "Quit the API Test CLI application")

    console.print(Panel(table, border_style="cyan", box=DOUBLE, padding=(1, 2)))


def render_model_discovery_page(
    base_url: str,
    results: list[dict[str, Any]],
    discovery_latency_ms: float,
    global_error: str | None = None,
):
    """
    Renders the dedicated Model Discovery & Health Status Page.
    Displays every model with green [OK] or red [FAILED] status badge,
    along with exact HTTP and fallback failure diagnostic reasons.
    """
    clear_screen()
    print_banner(show_subtitle=False)

    title_text = Text(
        "⚡ Model Discovery & Health Status Board ⚡", style="bold white on grey23"
    )
    console.print(Align.center(title_text))
    console.print()

    endpoint_info = Text()
    endpoint_info.append("Target Endpoint: ", style="bold grey70")
    endpoint_info.append(f"{base_url}\n", style="bold bright_cyan")
    endpoint_info.append("Discovery Ping Latency: ", style="bold grey70")
    endpoint_info.append(
        f"{discovery_latency_ms:.1f} ms",
        style="bold green" if discovery_latency_ms < 500 else "bold yellow",
    )
    console.print(
        Panel(endpoint_info, border_style="grey50", box=ROUNDED, padding=(0, 2))
    )
    console.print()

    if global_error:
        err_panel = Panel(
            f"[bold red]❌ Failed to Fetch Models from Endpoint[/bold red]\n\n"
            f"[bold white]Diagnostic Reason:[/bold white]\n"
            f"[bright_red]{global_error}[/bright_red]\n\n"
            f"[dim grey70]Possible Solutions:[/dim grey70]\n"
            f" • Check if your Base URL requires '/v1' suffix (e.g. https://api.openai.com/v1)\n"
            f" • Verify that your API Key is valid and has sufficient quota\n"
            " • Ensure your local model runner "
            "(Ollama, vLLM, LMStudio) is actively running",
            title="[bold red]Endpoint Diagnostics Error[/bold red]",
            border_style="red",
            box=ROUNDED,
            padding=(1, 2),
        )
        console.print(err_panel)
        console.print()
        return

    table = Table(
        title="Discovered AI Models & Health Inspection",
        title_style="bold cyan",
        box=ROUNDED,
        border_style="grey50",
        expand=True,
    )
    table.add_column("#", style="dim grey70", width=4, justify="right")
    table.add_column("Model ID", style="bold bright_white", min_width=25)
    table.add_column("Status", justify="center", width=12)
    table.add_column("Latency", justify="right", width=12)
    table.add_column("Diagnostic / Health Reason", style="white", min_width=35)

    ok_count = 0
    failed_count = 0

    for idx, item in enumerate(results, 1):
        model_id = item.get("model") or item.get("id") or "unknown"
        status = item.get("status", "OK")
        latency = item.get("latency_ms")
        latency_str = f"{latency:.1f} ms" if latency is not None else "—"
        error_reason = item.get("error_reason")

        if status == "OK":
            ok_count += 1
            status_badge = "[bold green]● OK[/bold green]"
            reason_str = "[green]Ready & Operational[/green]"
            lat_style = "green" if (latency and latency < 500) else "yellow"
        else:
            failed_count += 1
            status_badge = "[bold red]✖ FAILED[/bold red]"
            reason_str = (
                "[bold red]"
                f"{error_reason or 'Model unreachable or rejected request'}"
                "[/bold red]"
            )
            lat_style = "dim red"

        table.add_row(
            str(idx),
            model_id,
            status_badge,
            f"[{lat_style}]{latency_str}[/{lat_style}]",
            reason_str,
        )

    console.print(table)
    console.print()

    # Summary Statistics Bar
    summary_text = Text()
    summary_text.append("📊 Summary: ", style="bold white")
    summary_text.append(f"Total Discovered: {len(results)}  |  ", style="bold grey78")
    summary_text.append(f"Healthy (OK): {ok_count}  ", style="bold green")
    summary_text.append(
        f"|  Failed: {failed_count}  ",
        style="bold red" if failed_count > 0 else "dim grey70",
    )
    summary_text.append(
        f"|  Fetch Latency: {discovery_latency_ms:.1f} ms", style="bold cyan"
    )

    console.print(
        Panel(summary_text, border_style="grey42", box=ROUNDED, padding=(0, 2))
    )
    console.print()


def render_benchmark_report(result: dict[str, Any]):
    """Renders detailed performance metrics for TTFT, tokens/sec, and
    response health."""
    clear_screen()
    print_banner(show_subtitle=False)

    success = result.get("success", False)
    model = result.get("model", "unknown")
    status_code = result.get("status_code", 0)

    if not success:
        err_msg = result.get("error", "Unknown execution failure")
        err_panel = Panel(
            f"[bold red]❌ Model Benchmark Execution Failed[/bold red]\n\n"
            f"[bold white]Target Model:[/bold white] [cyan]{model}[/cyan]\n"
            f"[bold white]HTTP Status:[/bold white] [red]{status_code}[/red]\n"
            f"[bold white]Failure Cause:[/bold white] "
            f"[bright_red]{err_msg}[/bright_red]\n\n"
            "[dim]The model could not answer the test prompt. "
            "Check token limits or model name validity.[/dim]",
            title="[bold red]Benchmark Failed[/bold red]",
            border_style="red",
            box=ROUNDED,
            padding=(1, 2),
        )
        console.print(err_panel)
        console.print()
        return

    ttft = result.get("ttft_ms", 0.0)
    total_lat = result.get("total_latency_ms", 0.0)
    gen_lat = result.get("generation_latency_ms", 0.0)
    tps = result.get("tps", 0.0)
    tokens = result.get("tokens", 0)
    text_content = result.get("response_text", "").strip()

    metrics_table = Table(box=ROUNDED, border_style="grey50", expand=True)
    metrics_table.add_column("Metric", style="bold grey70")
    metrics_table.add_column("Measurement", style="bold white")
    metrics_table.add_column("Evaluation / Rating", style="bold cyan")

    if ttft < 250:
        ttft_rating = "[bold green]⚡ Ultra-Fast (<250ms)[/bold green]"
    elif ttft < 700:
        ttft_rating = "[green]✓ Good (<700ms)[/green]"
    elif ttft < 1500:
        ttft_rating = "[yellow]▲ Moderate (<1.5s)[/yellow]"
    else:
        ttft_rating = "[red]▼ Slow (>1.5s)[/red]"

    if tps > 80:
        tps_rating = "[bold green]⚡ High Throughput (>80 T/s)[/bold green]"
    elif tps > 40:
        tps_rating = "[green]✓ Solid Speed (>40 T/s)[/green]"
    elif tps > 15:
        tps_rating = "[yellow]▲ Normal (>15 T/s)[/yellow]"
    else:
        tps_rating = "[red]▼ Low Throughput (<15 T/s)[/red]"

    metrics_table.add_row(
        "Target Model",
        f"[bold cyan]{model}[/bold cyan]",
        "[green]● Operational (HTTP 200)[/green]",
    )
    metrics_table.add_row(
        "TTFT (Time to First Token)",
        f"[bold bright_white]{ttft:.1f} ms[/bold bright_white]",
        ttft_rating,
    )
    metrics_table.add_row(
        "Total Response Latency",
        f"[bold bright_white]{total_lat:.1f} ms[/bold bright_white]",
        f"Streamed in {gen_lat:.1f} ms",
    )
    metrics_table.add_row(
        "Token Generation Speed",
        f"[bold bright_white]{tps:.1f} tokens/sec[/bold bright_white]",
        tps_rating,
    )
    metrics_table.add_row(
        "Generated Tokens Count",
        f"[bold bright_white]{tokens} tokens[/bold bright_white]",
        f"~{len(text_content)} characters",
    )

    # If statistical multi-run data is available
    if "stats" in result and isinstance(result["stats"], dict):
        st = result["stats"]
        stability = st.get("stability_score", 100.0)
        stab_style = (
            "bold green" if stability >= 90 else "yellow" if stability >= 70 else "red"
        )
        metrics_table.add_row(
            "Stability Score",
            f"[{stab_style}]{stability:.1f}%[/{stab_style}]",
            "Based on throughput variance",
        )
        metrics_table.add_row(
            "Cold Start TTFT",
            (
                f"[bold bright_white]{st.get('cold_start_ttft_ms', 0):.1f} "
                "ms[/bold bright_white]"
            ),
            "Initial request latency",
        )
        metrics_table.add_row(
            "Warm Avg TTFT",
            (
                f"[bold bright_white]{st.get('warm_ttft_ms', 0):.1f} "
                "ms[/bold bright_white]"
            ),
            "Warmed connection latency",
        )

    perf_panel = Panel(
        metrics_table,
        title=f"[bold green]⚡ Benchmark Telemetry: {model} ⚡[/bold green]",
        border_style="green",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(perf_panel)
    console.print()

    # Reasoning / Thinking Tokens Panel (DeepSeek R1 / OpenAI o1 / etc.)
    reasoning_text = result.get("reasoning_text", "").strip()
    if reasoning_text:
        reasoning_panel = Panel(
            reasoning_text,
            title=(
                "[bold cyan]🧠 Model Thought / Reasoning Process "
                f"({result.get('reasoning_tokens', 0)} tokens)[/bold cyan]"
            ),
            title_align="left",
            border_style="cyan",
            box=ROUNDED,
            padding=(1, 2),
        )
        console.print(reasoning_panel)
        console.print()

    response_panel = Panel(
        text_content if text_content else "[dim]No text content returned.[/dim]",
        title="[bold grey78]Generated Response Output[/bold grey78]",
        title_align="left",
        border_style="grey42",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(response_panel)
    console.print()


def render_multi_run_benchmark_report(result: dict[str, Any]):
    """Renders comprehensive multi-run statistics with percentiles and
    individual run breakdown."""
    render_benchmark_report(result)

    runs = result.get("runs", [])
    if len(runs) > 1:
        table = Table(
            title="Iteration Breakdown & Consistency",
            title_style="bold grey85",
            box=ROUNDED,
            border_style="grey50",
            expand=True,
        )
        table.add_column("Run #", justify="center", width=8, style="dim grey70")
        table.add_column("Status", justify="center", width=12)
        table.add_column("TTFT (ms)", justify="right", style="bold bright_white")
        table.add_column("Total Latency (ms)", justify="right")
        table.add_column("Throughput", justify="right", style="bold cyan")
        table.add_column("Tokens", justify="right")

        for r in runs:
            st_badge = (
                "[bold green]● OK[/bold green]"
                if r.get("success")
                else "[bold red]✖ FAIL[/bold red]"
            )
            table.add_row(
                f"#{r.get('run_number', 1)}",
                st_badge,
                f"{r.get('ttft_ms', 0.0):.1f} ms",
                f"{r.get('total_latency_ms', 0.0):.1f} ms",
                f"{r.get('tps', 0.0):.1f} T/s",
                str(r.get("tokens", 0)),
            )

        console.print(table)
        console.print()


def render_model_comparison_matrix(data: dict[str, Any]):
    """Renders head-to-head multi-model comparison matrix with winner badges."""
    clear_screen()
    print_banner(show_subtitle=False)

    models_data = data.get("models", [])
    prompt = data.get("prompt", "")
    winners = data.get("winners", {})

    console.print(
        Panel(
            "[bold bright_white]🥊 Model Arena Performance Matrix[/bold bright_white]\n"
            f"[dim grey70]Prompt: '{prompt}'[/dim grey70]",
            border_style="cyan",
            box=ROUNDED,
            padding=(0, 2),
        )
    )
    console.print()

    # Winners Leaderboard
    if winners:
        w_table = Table(
            show_header=False, box=ROUNDED, border_style="gold1", expand=True
        )
        w_table.add_column("Category", style="bold yellow", width=24)
        w_table.add_column("Winner Model", style="bold bright_white")
        w_table.add_column("Score / Metric", style="bold green", justify="right")

        if "fastest_ttft" in winners:
            w = winners["fastest_ttft"]
            w_table.add_row(
                "🏆 Fastest TTFT (First Token)",
                f"[bold cyan]{w['model']}[/bold cyan]",
                f"{w['value']:.1f} ms",
            )

        if "highest_tps" in winners:
            w = winners["highest_tps"]
            w_table.add_row(
                "🚀 Highest Throughput (Speed)",
                f"[bold cyan]{w['model']}[/bold cyan]",
                f"{w['value']:.1f} tokens/sec",
            )

        if "lowest_latency" in winners:
            w = winners["lowest_latency"]
            w_table.add_row(
                "⏱ Fastest Overall Response",
                f"[bold cyan]{w['model']}[/bold cyan]",
                f"{w['value']:.1f} ms",
            )

        console.print(
            Panel(
                w_table,
                title="[bold gold1]★ Leaderboard Winners ★[/bold gold1]",
                border_style="gold1",
                box=ROUNDED,
                padding=(0, 1),
            )
        )
        console.print()

    # Full Comparison Table
    table = Table(
        title="All Models Comparison",
        title_style="bold grey85",
        box=ROUNDED,
        border_style="grey50",
        expand=True,
    )
    table.add_column("#", width=4, justify="right", style="dim grey70")
    table.add_column("Model ID", style="bold bright_white", min_width=24)
    table.add_column("Status", justify="center", width=10)
    table.add_column("TTFT (ms)", justify="right", width=14)
    table.add_column("Throughput", justify="right", width=18)
    table.add_column("Total Latency", justify="right", width=16)
    table.add_column("Tokens", justify="right", width=10)

    for idx, m in enumerate(models_data, 1):
        is_ok = m.get("success", False)
        status_str = (
            "[bold green]● OK[/bold green]"
            if is_ok
            else "[bold red]✖ FAILED[/bold red]"
        )

        ttft_str = f"{m.get('ttft_ms', 0):.1f} ms" if is_ok else "—"
        tps_str = f"{m.get('tps', 0):.1f} T/s" if is_ok else "—"
        tot_str = f"{m.get('total_latency_ms', 0):.1f} ms" if is_ok else "—"
        tok_str = str(m.get("tokens", 0)) if is_ok else "—"

        # Highlight winners
        is_fastest_ttft = winners.get("fastest_ttft", {}).get("model") == m.get("model")
        is_highest_tps = winners.get("highest_tps", {}).get("model") == m.get("model")

        m_display = m.get("model", "unknown")
        if is_fastest_ttft:
            ttft_str = f"[bold green]⚡ {ttft_str}[/bold green]"
        if is_highest_tps:
            tps_str = f"[bold green]🚀 {tps_str}[/bold green]"

        table.add_row(
            str(idx), m_display, status_str, ttft_str, tps_str, tot_str, tok_str
        )

    console.print(table)
    console.print()


def render_stress_test_report(data: dict[str, Any]):
    """Renders concurrent load and rate-limit stress test report."""
    clear_screen()
    print_banner(show_subtitle=False)

    model = data.get("model", "unknown")
    concurrency = data.get("concurrency", 0)
    data.get("total_requests", 0)
    success_req = data.get("successful_requests", 0)
    failed_req = data.get("failed_requests", 0)
    success_rate = data.get("success_rate_pct", 0.0)
    duration_s = data.get("duration_sec", 0.0)
    agg_tps = data.get("aggregate_tps", 0.0)
    total_tok = data.get("total_tokens", 0)
    stats_lat = data.get("latency_stats", {})

    rate_color = (
        "bold green"
        if success_rate >= 99
        else "bold yellow"
        if success_rate >= 80
        else "bold red"
    )

    table = Table(box=ROUNDED, border_style="grey50", expand=True)
    table.add_column("Load Test Parameter / Metric", style="bold grey70")
    table.add_column("Measurement", style="bold white")
    table.add_column("Evaluation", style="bold cyan")

    table.add_row(
        "Target Model",
        f"[bold cyan]{model}[/bold cyan]",
        f"Tested across {concurrency} parallel streams",
    )
    table.add_row(
        "Success Rate",
        f"[{rate_color}]{success_rate:.1f}%[/{rate_color}]",
        f"{success_req} succeeded / {failed_req} failed",
    )
    table.add_row(
        "Aggregate Throughput",
        f"[bold green]{agg_tps:.1f} tokens/sec[/bold green]",
        f"{total_tok} total tokens in {duration_s:.2f}s",
    )
    table.add_row(
        "P95 Latency",
        f"[bold bright_white]{stats_lat.get('p95', 0):.1f} ms[/bold bright_white]",
        "95% of requests completed under this",
    )
    table.add_row(
        "Mean Latency",
        f"[bold bright_white]{stats_lat.get('mean', 0):.1f} ms[/bold bright_white]",
        (
            f"Min: {stats_lat.get('min', 0):.1f} ms | "
            f"Max: {stats_lat.get('max', 0):.1f} ms"
        ),
    )

    panel = Panel(
        table,
        title=f"[bold cyan]🌪 Concurrency & Load Stress Test: {model} 🌪[/bold cyan]",
        border_style="cyan",
        box=ROUNDED,
        padding=(1, 2),
    )
    console.print(panel)
    console.print()

    err_breakdown = data.get("error_breakdown", {})
    if err_breakdown:
        err_table = Table(
            title="Observed Errors & Throttling",
            title_style="bold red",
            box=ROUNDED,
            border_style="red",
            expand=True,
        )
        err_table.add_column("Failure Cause / HTTP Code", style="bold bright_red")
        err_table.add_column("Count", justify="right", style="bold white", width=10)
        for err, count in err_breakdown.items():
            err_table.add_row(err, str(count))
        console.print(err_table)
        console.print()


def render_history_table(history: list[dict[str, Any]]):
    """Renders recent benchmark history table."""
    clear_screen()
    print_banner(show_subtitle=False)

    if not history:
        console.print(
            Panel(
                "[dim]No benchmark history recorded yet. "
                "Run /bench or /test to save telemetry.[/dim]",
                title="History",
                border_style="grey50",
            )
        )
        console.print()
        return

    table = Table(
        title="Recent Benchmark History",
        title_style="bold cyan",
        box=ROUNDED,
        border_style="grey50",
        expand=True,
    )
    table.add_column("#", width=4, justify="right", style="dim grey70")
    table.add_column("Timestamp", width=18, style="dim grey70")
    table.add_column("Model", style="bold bright_white", min_width=20)
    table.add_column("TTFT", justify="right", width=12)
    table.add_column("Throughput", justify="right", width=14, style="bold cyan")
    table.add_column("Latency", justify="right", width=12)
    table.add_column("Status", justify="center", width=10)

    for idx, item in enumerate(history, 1):
        ts = item.get("timestamp", "—")
        m = item.get("model", "unknown")
        ttft = f"{item.get('ttft_ms', 0):.1f} ms"
        tps = f"{item.get('tps', 0):.1f} T/s"
        lat = f"{item.get('total_latency_ms', 0):.1f} ms"
        ok = item.get("success", False)
        st = "[green]● OK[/green]" if ok else "[red]✖ FAIL[/red]"
        table.add_row(str(idx), ts, m, ttft, tps, lat, st)

    console.print(table)
    console.print()


def render_presets_table(presets: list[dict[str, Any]]):
    """Renders table of popular cloud and local presets."""
    table = Table(
        title="Available Provider Presets",
        title_style="bold cyan",
        box=ROUNDED,
        border_style="grey50",
        expand=True,
    )
    table.add_column("#", width=4, justify="right", style="dim grey70")
    table.add_column("Provider Name", style="bold bright_white", width=25)
    table.add_column("Endpoint URL", style="bright_white")
    table.add_column("Default Model", style="magenta", width=28)

    for idx, p in enumerate(presets, 1):
        table.add_row(
            str(idx),
            p.get("name", ""),
            p.get("base_url", ""),
            p.get("default_model", ""),
        )

    console.print(table)
    console.print()

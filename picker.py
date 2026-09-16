"""
API TEST CLI - Interactive Arrow-Key Model Picker & Discovery Selector
"""

import os
import sys
import time
from typing import List, Dict, Any, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED, DOUBLE
from rich.prompt import Prompt
from rich.status import Status

console = Console()


def read_key() -> str:
    """Reads a single keypress cross-platform (Windows msvcrt + POSIX termios)."""
    if not sys.stdin.isatty():
        line = sys.stdin.readline()
        if not line:
            return 'enter'
        return line.strip()

    if os.name == 'nt':
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b'\x00', b'\xe0'):
            ch2 = msvcrt.getch()
            if ch2 == b'H':
                return 'up'
            elif ch2 == b'P':
                return 'down'
            elif ch2 == b'K':
                return 'left'
            elif ch2 == b'M':
                return 'right'
            elif ch2 == b'G':
                return 'home'
            elif ch2 == b'O':
                return 'end'
            elif ch2 == b'I':
                return 'page_up'
            elif ch2 == b'Q':
                return 'page_down'
            return ''
        elif ch in (b'\r', b'\n'):
            return 'enter'
        elif ch == b'\x1b':
            return 'escape'
        elif ch in (b'\x08', b'\x7f'):
            return 'backspace'
        else:
            try:
                return ch.decode('utf-8', errors='ignore')
            except Exception:
                return ''
    else:
        import tty
        import termios
        if not sys.stdin.isatty():
            return 'enter'
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1) if select_stdin() else ''
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'up'
                    elif ch3 == 'B':
                        return 'down'
                    elif ch3 == 'C':
                        return 'right'
                    elif ch3 == 'D':
                        return 'left'
                return 'escape'
            elif ch in ('\r', '\n'):
                return 'enter'
            elif ch in ('\x08', '\x7f'):
                return 'backspace'
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def select_stdin() -> bool:
    import select
    dr, _, _ = select.select([sys.stdin], [], [], 0.05)
    return bool(dr)


def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


def render_picker_view(
    title: str,
    items: List[Dict[str, Any]],
    selected_idx: int,
    filter_query: str = "",
    page_size: int = 10,
    endpoint_name: str = ""
):
    """Renders the interactive arrow-key model selection screen."""
    clear_terminal()

    # Header Card
    header_text = Text()
    header_text.append("⚡ Select AI Model from Endpoint Catalog ⚡\n", style="bold cyan")
    if endpoint_name:
        header_text.append("Target Endpoint: ", style="bold grey70")
        header_text.append(f"{endpoint_name}\n", style="bright_white")
    header_text.append("Use ", style="grey78")
    header_text.append("[↑ / ↓]", style="bold bright_white")
    header_text.append(" Arrow Keys to move, ", style="grey78")
    header_text.append("[Enter]", style="bold bright_white")
    header_text.append(" to select, ", style="grey78")
    header_text.append("[/]", style="bold cyan")
    header_text.append(" to filter, ", style="grey78")
    header_text.append("[Esc / q]", style="bold bright_white")
    header_text.append(" to go back.", style="grey78")

    console.print(Panel(header_text, title=f"[bold grey78]{title}[/bold grey78]", border_style="grey50", box=ROUNDED, padding=(0, 2)))
    console.print()

    if filter_query:
        console.print(f"[bold cyan]🔍 Filter Query:[/bold cyan] [bold white]{filter_query}[/bold white] [dim](Press Esc to clear filter)[/dim]\n")

    if not items:
        console.print(Panel("[yellow]No models matched your filter query.[/yellow]\n[dim]Press [Backspace] to modify filter or [Esc] to reset.[/dim]", border_style="yellow", box=ROUNDED))
        console.print()
        return

    # Pagination calculations
    total_items = len(items)
    selected_idx = max(0, min(selected_idx, total_items - 1))
    start_idx = max(0, min(selected_idx - (page_size // 2), total_items - page_size))
    end_idx = min(start_idx + page_size, total_items)

    table = Table(box=ROUNDED, border_style="grey50", expand=True, show_header=True)
    table.add_column("", width=3, justify="center")
    table.add_column("#", width=4, justify="right", style="dim grey70")
    table.add_column("Model Identifier", min_width=30, style="bold")
    table.add_column("Owner / Provider", width=18, style="cyan")
    table.add_column("Context / Spec", width=20, style="dim grey78")

    if start_idx > 0:
        table.add_row("", "", f"[dim grey50]▲ ({start_idx} more models above - scroll up)...[/dim grey50]", "", "")

    for idx in range(start_idx, end_idx):
        item = items[idx]
        is_selected = idx == selected_idx

        m_id = item.get("id", "Unknown")
        owner = item.get("owned_by") or "ai"
        ctx = item.get("context_window") or item.get("context_length")
        ctx_str = f"{ctx:,} tokens" if isinstance(ctx, int) else (str(ctx) if ctx else "Standard")

        if item.get("is_custom_action"):
            if is_selected:
                cursor = "[bold bright_cyan]❯[/bold bright_cyan]"
                num_str = "[bold bright_cyan]★[/bold bright_cyan]"
                m_str = f"[bold bright_yellow on #2e2815] {m_id} [/bold bright_yellow on #2e2815]"
                o_str = "[yellow]Custom[/yellow]"
                c_str = "[dim yellow]Manual Entry[/dim yellow]"
            else:
                cursor = " "
                num_str = "★"
                m_str = f"[yellow]{m_id}[/yellow]"
                o_str = "[dim yellow]Custom[/dim yellow]"
                c_str = "[dim]Manual Entry[/dim]"
        elif item.get("is_refresh_action"):
            if is_selected:
                cursor = "[bold bright_cyan]❯[/bold bright_cyan]"
                num_str = "[bold bright_cyan]↺[/bold bright_cyan]"
                m_str = f"[bold bright_cyan on #1b2838] {m_id} [/bold bright_cyan on #1b2838]"
                o_str = "[cyan]Endpoint[/cyan]"
                c_str = "[dim cyan]Re-scan API[/dim cyan]"
            else:
                cursor = " "
                num_str = "↺"
                m_str = f"[dim cyan]{m_id}[/dim cyan]"
                o_str = "[dim cyan]Endpoint[/dim cyan]"
                c_str = "[dim]Re-scan API[/dim]"
        else:
            if is_selected:
                cursor = "[bold bright_cyan]❯[/bold bright_cyan]"
                num_str = f"[bold bright_cyan]{idx + 1}[/bold bright_cyan]"
                m_str = f"[bold bright_white on #232d3f] {m_id} [/bold bright_white on #232d3f]"
                o_str = f"[bold cyan]{owner}[/bold cyan]"
                c_str = f"[bright_white]{ctx_str}[/bright_white]"
            else:
                cursor = " "
                num_str = str(idx + 1)
                m_str = f"[white]{m_id}[/white]"
                o_str = f"[dim cyan]{owner}[/dim cyan]"
                c_str = f"[dim grey70]{ctx_str}[/dim grey70]"

        table.add_row(cursor, num_str, m_str, o_str, c_str)

    if end_idx < total_items:
        table.add_row("", "", f"[dim grey50]▼ ({total_items - end_idx} more models below - scroll down)...[/dim grey50]", "", "")

    console.print(table)
    console.print()

    # Footer status
    footer = Text()
    footer.append(f"Showing {selected_idx + 1} of {total_items} options  |  ", style="bold grey70")
    footer.append("Press [Enter] to Confirm Selection", style="bold green")
    console.print(Align.center(footer))
    console.print()


def interactive_model_picker(
    client,
    cached_models_raw: List[Dict[str, Any]],
    title: str = "Select AI Model",
    endpoint_name: str = ""
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Main interactive entry point for selecting a model.
    1. Fetches models if cached list is empty.
    2. Renders arrow-key interactive navigator.
    3. Returns selected model ID (or custom model entered by user), and updated models cache.
    """
    models = list(cached_models_raw)

    # 1. Fetch if empty
    if not models:
        with Status("[bold cyan]Fetching available AI models from endpoint catalog...[/bold cyan]", spinner="dots"):
            fetch_res = client.fetch_models()

        if fetch_res["success"] and fetch_res["models"]:
            models = fetch_res["models"]
        else:
            clear_terminal()
            err_msg = fetch_res.get("error", "Could not retrieve models list.")
            console.print(Panel(
                f"[bold red]❌ Failed to Fetch Models from Endpoint[/bold red]\n\n"
                f"[bold white]Diagnostic Reason:[/bold white] [bright_red]{err_msg}[/bright_red]\n\n"
                f"Would you like to enter a model name manually or retry?",
                title="[bold red]Model Discovery Error[/bold red]",
                border_style="red",
                box=ROUNDED,
                padding=(1, 2)
            ))
            console.print()
            console.print("  [bold cyan][1][/bold cyan] Enter Model ID Manually")
            console.print("  [bold cyan][2][/bold cyan] Retry Discovery")
            console.print("  [bold cyan][0][/bold cyan] Cancel & Return to Menu")
            console.print()

            sub_choice = Prompt.ask("[bold grey85]❯ Choice[/bold grey85]", default="1")
            if sub_choice == "1":
                custom_id = Prompt.ask("[bold grey85]❯ Enter Model ID (e.g. gpt-4o, claude-opus-5)[/bold grey85]").strip()
                return (custom_id if custom_id else None), models
            elif sub_choice == "2":
                return interactive_model_picker(client, [], title, endpoint_name)
            else:
                return None, models

    # Check if stdin is interactive
    is_interactive = True
    if os.name != 'nt' and not sys.stdin.isatty():
        is_interactive = False

    # 2. Interactive Selection Loop
    filter_query = ""
    selected_idx = 0

    while True:
        filtered_items: List[Dict[str, Any]] = []
        q = filter_query.lower().strip()

        for m in models:
            m_id = m.get("id", "")
            if not q or q in m_id.lower() or q in str(m.get("owned_by", "")).lower():
                filtered_items.append(m)

        filtered_items.append({
            "id": "✏ [Enter Custom Model ID Manually]",
            "owned_by": "custom",
            "is_custom_action": True,
        })
        filtered_items.append({
            "id": "↺ [Refresh Models List from API]",
            "owned_by": "api",
            "is_refresh_action": True,
        })

        if not is_interactive:
            clear_terminal()
            console.print(Panel("[bold bright_white]Discovered AI Models List[/bold bright_white]", border_style="grey50", box=ROUNDED))
            for i, itm in enumerate(filtered_items, 1):
                console.print(f"  [{i}] {itm.get('id')} ({itm.get('owned_by', '')})")
            console.print()
            raw_choice = Prompt.ask("Select Model Number or enter custom name", default="1")
            if raw_choice.isdigit():
                c_i = int(raw_choice) - 1
                if 0 <= c_i < len(filtered_items):
                    sel = filtered_items[c_i]
                    if sel.get("is_custom_action"):
                        custom_val = Prompt.ask("Enter custom model ID").strip()
                        return (custom_val if custom_val else None), models
                    elif sel.get("is_refresh_action"):
                        return interactive_model_picker(client, [], title, endpoint_name)
                    return sel.get("id"), models
            return (raw_choice if raw_choice else None), models

        render_picker_view(
            title=title,
            items=filtered_items,
            selected_idx=selected_idx,
            filter_query=filter_query,
            page_size=10,
            endpoint_name=endpoint_name
        )

        key = read_key()

        if key == 'up':
            selected_idx = max(0, selected_idx - 1)
        elif key == 'down':
            selected_idx = min(len(filtered_items) - 1, selected_idx + 1)
        elif key == 'page_up':
            selected_idx = max(0, selected_idx - 8)
        elif key == 'page_down':
            selected_idx = min(len(filtered_items) - 1, selected_idx + 8)
        elif key == 'home':
            selected_idx = 0
        elif key == 'end':
            selected_idx = len(filtered_items) - 1
        elif key == 'escape' or (key == 'q' and not filter_query) or (key == 'b' and not filter_query):
            if filter_query:
                filter_query = ""
                selected_idx = 0
            else:
                return None, models
        elif key == 'backspace':
            if filter_query:
                filter_query = filter_query[:-1]
                selected_idx = 0
        elif key == 'enter':
            if 0 <= selected_idx < len(filtered_items):
                chosen = filtered_items[selected_idx]
                if chosen.get("is_custom_action"):
                    clear_terminal()
                    console.print(Panel("[bold bright_white]Enter Custom Model Identifier[/bold bright_white]", border_style="yellow", box=ROUNDED))
                    custom_id = Prompt.ask("[bold grey85]❯ Target Model ID[/bold grey85]").strip()
                    return (custom_id if custom_id else None), models
                elif chosen.get("is_refresh_action"):
                    return interactive_model_picker(client, [], title, endpoint_name)
                else:
                    return chosen.get("id"), models
        elif key == '/':
            clear_terminal()
            console.print(Panel("[bold cyan]🔍 Filter AI Models[/bold cyan]\n[dim]Enter search keyword to filter models list.[/dim]", border_style="cyan", box=ROUNDED))
            filter_query = Prompt.ask("[bold grey85]❯ Search Keyword[/bold grey85]", default=filter_query).strip()
            selected_idx = 0
        elif len(key) == 1 and key.isprintable():
            filter_query += key
            selected_idx = 0

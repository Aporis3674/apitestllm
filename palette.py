"""
API TEST CLI - Dynamic Live Slash Command Preview & Animated Prompt Engine
"""

import os
import sys
from typing import Optional, List, Tuple
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

from picker import read_key

console = Console()

SLASH_COMMANDS = [
    ("/start", "Launch testing suite with active profile"),
    ("/quick", "Quick Scan: Input URL & key, instantly fetch & inspect models"),
    ("/test", "Quick Benchmark: Input URL & key, fetch models & run speed test"),
    ("/models", "Fetch model catalog & inspect health status (Active profile)"),
    ("/bench", "Run speed & TTFT latency benchmark (Active profile)"),
    ("/stream", "Interactive prompt live streaming test (Active profile)"),
    ("/config", "Reconfigure API endpoint URL & key"),
    ("/profiles", "Switch or manage saved profiles"),
    ("/clear", "Clear terminal screen"),
    ("/exit", "Quit application"),
]


def make_prompt_renderable(prompt_label: str, buffer: str, highlight_idx: int = 0) -> Group | Text:
    """
    Constructs the dynamic UI element:
    1. Prompt line with active typing text and cursor.
    2. If buffer starts with '/', dynamically displays the grey preview box
       filtered to matching commands in real time.
    3. If buffer does not start with '/', the preview box is completely hidden.
    """
    prompt_text = Text()
    prompt_text.append(f"❯ {prompt_label}: ", style="bold grey85")
    prompt_text.append(buffer, style="bold white")
    prompt_text.append("█", style="bold cyan")

    if buffer.startswith("/"):
        q = buffer.lower().strip()
        matched = [
            (cmd, desc) for cmd, desc in SLASH_COMMANDS
            if (q == "/" or cmd.startswith(q) or (len(q) > 1 and q[1:] in cmd[1:]))
        ]
        if not matched:
            matched = SLASH_COMMANDS

        table = Table(box=None, show_header=False, padding=(0, 1))
        table.add_column("Command", style="bold grey93", width=14)
        table.add_column("Desc", style="grey70")

        total_m = len(matched)
        h_idx = highlight_idx % max(1, total_m)

        for idx, (cmd, desc) in enumerate(matched):
            if idx == h_idx:
                table.add_row(f"[bold bright_cyan on #222222]❯ {cmd}[/bold bright_cyan on #222222]", f"[bright_white on #222222]{desc}[/bright_white on #222222]")
            else:
                table.add_row(f"[bold grey93]  {cmd}[/bold grey93]", f"[grey70]{desc}[/grey70]")

        panel = Panel(
            table,
            title="[grey78]Slash Commands Preview[/grey78]",
            title_align="left",
            border_style="grey50",
            box=ROUNDED,
            padding=(0, 1),
        )
        return Group(prompt_text, Text(""), panel)

    return prompt_text


def prompt_live_input(prompt_label: str = "Select Option [1: Start | 2: Exit] or type '/'") -> str:
    """
    Live-animated interactive prompt:
    - Automatically displays the sleek grey preview box the moment '/' is typed.
    - Instantly hides the preview box when '/' is deleted with Backspace.
    - Dynamically filters commands in real time as more characters are typed.
    - Supports Up/Down arrow keys and Tab to cycle commands.
    """
    if not sys.stdin.isatty():
        from rich.prompt import Prompt
        return Prompt.ask(f"[bold grey85]❯ {prompt_label}[/bold grey85]", default="1").strip()

    buffer = ""
    highlight_idx = 0

    with Live(make_prompt_renderable(prompt_label, buffer, highlight_idx), console=console, refresh_per_second=30, transient=True) as live:
        while True:
            k = read_key()
            if not k:
                continue

            if k == 'enter':
                if buffer.startswith("/"):
                    q = buffer.lower().strip()
                    matched = [
                        cmd for cmd, _ in SLASH_COMMANDS
                        if (q == "/" or cmd.startswith(q) or (len(q) > 1 and q[1:] in cmd[1:]))
                    ]
                    if matched and (buffer == "/" or buffer == q):
                        buffer = matched[highlight_idx % len(matched)]
                break

            elif k == 'up':
                if buffer.startswith("/"):
                    highlight_idx = max(0, highlight_idx - 1)
                    live.update(make_prompt_renderable(prompt_label, buffer, highlight_idx))

            elif k == 'down':
                if buffer.startswith("/"):
                    highlight_idx += 1
                    live.update(make_prompt_renderable(prompt_label, buffer, highlight_idx))

            elif k == 'tab':
                if buffer.startswith("/"):
                    q = buffer.lower().strip()
                    matched = [
                        cmd for cmd, _ in SLASH_COMMANDS
                        if (q == "/" or cmd.startswith(q) or (len(q) > 1 and q[1:] in cmd[1:]))
                    ]
                    if matched:
                        buffer = matched[highlight_idx % len(matched)]
                        live.update(make_prompt_renderable(prompt_label, buffer, highlight_idx))

            elif k == 'backspace':
                if buffer:
                    buffer = buffer[:-1]
                    highlight_idx = 0
                    live.update(make_prompt_renderable(prompt_label, buffer, highlight_idx))

            elif k == 'escape':
                buffer = "/back"
                break

            elif len(k) == 1 and k.isprintable():
                buffer += k
                highlight_idx = 0
                live.update(make_prompt_renderable(prompt_label, buffer, highlight_idx))

    console.print(f"[bold grey85]❯ {prompt_label}: [/bold grey85][bold white]{buffer}[/bold white]")
    return buffer.strip() if buffer.strip() else "1"

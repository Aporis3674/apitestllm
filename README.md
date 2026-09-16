# ⚡ API TEST CLI

> **High-Performance AI Endpoint Benchmark, TTFT Telemetry & Health Diagnostic TUI**

```
 █████╗ ██████╗ ██╗    ████████╗███████╗███████╗████████╗
██╔══██╗██╔══██╗██║    ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝
███████║██████╔╝██║       ██║   █████╗  ███████╗   ██║   
██╔══██║██╔═══╝ ██║       ██║   ██╔══╝  ╚════██║   ██║   
██║  ██║██║     ██║       ██║   ███████╗███████║   ██║   
╚═╝  ╚═╝╚═╝     ╚═╝       ╚═╝   ╚══════╝╚══════╝   ╚═╝   
```

<p align="center">
  <a href="#-key-features">Features</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-slash-commands">Slash Commands</a> •
  <a href="#-telemetry-metrics">Metrics</a> •
  <a href="README_FA.md">راهنمای فارسی 🇮🇷</a>
</p>

---

## 🌟 Key Features

- 🌈 **Vibrant RGB ASCII Typography**: Dynamic gradient rainbow ASCII art banner on startup.
- 🎛 **Sleek Grey Buttons & Modern Menu**: Minimalist visual buttons (`[1] START`, `[2] EXIT`) with intuitive keyboard navigation.
- ⚡ **Dynamic Animated Slash Command Palette**:
  - Typing `/` instantly renders a sleek grey preview box below the prompt.
  - Deleting `/` with Backspace automatically vanishes the preview box.
  - Real-time command filtering and interactive selection.
- 🚀 **One-Shot Direct Commands (`/quick` & `/test`)**:
  - `/quick` (or `/scan`): Instantly checks for saved profiles or accepts a new endpoint, fetches all models, and displays parallel health probes.
  - `/test` (or `/eval`): Checks for saved profiles or accepts a new endpoint, lists models, lets you pick one with arrow keys, and runs a real-time TTFT & tokens/sec speed benchmark.
- 🎯 **Interactive Arrow-Key Model Picker**:
  - Automatically fetches all available AI models from the endpoint.
  - Navigate models with **[↑ / ↓] Keyboard Arrow Keys** or PageUp/PageDown.
  - Real-time search filter: type any keyword to filter models instantly.
- 🔎 **Model Discovery & Health Status Board**:
  - Discovers all models and executes concurrent health probes with a live progress bar.
  - Clear status indicators: `[● OK]` (Green) or `[✖ FAILED]` (Red).
  - Explicit diagnostic failure causes (HTTP 401 Unauthorized, 404 Not Found, 429 Quota Exceeded, 502 Bad Gateway, Connection Refused, Connect Timeout, or Fallback errors).
- 📊 **Real-Time Speed & Latency Telemetry**:
  - **TTFT (Time To First Token)** in milliseconds (`ms`).
  - **Total Latency** in milliseconds (`ms`).
  - **Token Throughput Speed** in tokens per second (`tokens/sec`).
  - **Live Streaming Telemetry**: Real-time status updates (`Connecting...`, `Waiting for TTFT...`, `Streaming response...`) with reasoning token support.
- 💾 **Persistent Profile Management**: Stores your endpoints, keys, and model preferences securely in `~/.api_test_cli/config.json`.

---

## 🚀 Quickstart

### 1. Requirements
- Python 3.9 or higher
- `rich` and `httpx`

```bash
pip install rich httpx
```

### 2. Run
```bash
python api_test.py
```
*On Windows, you can also double-click `run.bat`.*

---

## 🧭 Slash Commands Reference

| Command | Alias | Description |
|---|---|---|
| `/quick` | `/scan`, `/fetch` | **Quick Scan**: Choose saved profile or enter new URL/key, instantly fetch & inspect models |
| `/test` | `/eval`, `/qbench` | **Quick Benchmark**: Choose saved profile or new URL/key, pick model & run speed test |
| `/start` | `1` | Start testing suite with active profile |
| `/models` | `m` | Fetch model list & health status board for active profile |
| `/bench` | `b` | Benchmark TTFT latency & tokens/sec for active profile |
| `/stream` | `s` | Interactive live streaming prompt testing |
| `/config` | `c` | Setup or reconfigure endpoint & API key |
| `/profiles` | `p` | Switch, view, or manage multiple saved profiles |
| `/clear` | `cls` | Clear terminal screen |
| `/back` | `0, ..` | Return to previous screen |
| `/exit` | `2, q` | Quit the CLI application |

---

## 📊 Telemetry Metrics

```
┌────────────────────────────────── ⚡ Benchmark Telemetry: gpt-4o ⚡ ──────────────────────────────────┐
│                                                                                                       │
│  ┌───────────────────────────────────┬───────────────────────┬─────────────────────────────────────┐  │
│  │ Metric                            │ Measurement           │ Evaluation / Rating                 │  │
│  ├───────────────────────────────────┼───────────────────────┼─────────────────────────────────────┤  │
│  │ Target Model                      │ gpt-4o                │ ● Operational (HTTP 200)            │  │
│  │ TTFT (Time to First Token)        │ 210.4 ms              │ ⚡ Ultra-Fast (<250ms)              │  │
│  │ Total Response Latency            │ 580.2 ms              │ Streamed in 369.8 ms                │  │
│  │ Token Generation Speed            │ 128.5 tokens/sec      │ ⚡ High Throughput (>80 T/s)        │  │
│  │ Generated Tokens Count            │ 48 tokens             │ ~210 characters                     │  │
│  └───────────────────────────────────┴───────────────────────┴─────────────────────────────────────┘  │
│                                                                                                       │
└───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
api-test-cli/
├── api_test.py       # Main CLI entrypoint
├── cli.py            # REPL loop, navigation & interactive command dispatcher
├── palette.py        # Animated live slash command preview engine
├── picker.py         # Arrow-key interactive model selector with search filter
├── client.py         # HTTP engine, SSE streaming, TTFT/TPS metrics & error parser
├── ui.py             # Rich RGB ASCII banner, tables, buttons & telemetry cards
├── config.py         # Persistent profile & config manager (~/.api_test_cli/config.json)
├── run.bat           # Windows 1-click launcher
├── requirements.txt  # Project dependencies
└── test_suite.py     # Automated unit & integration tests
```

---

## 📄 License

Distributed under the GNU General Public License v3.0.

"""
API TEST CLI - Telemetry & Benchmark Exporter (JSON, CSV, Markdown, HTML)
"""

import os
import json
import csv
import time
from datetime import datetime
from typing import Dict, Any, List, Optional


def export_to_json(data: Dict[str, Any], filepath: str) -> str:
    """Exports benchmark or test results to formatted JSON."""
    out_dir = os.path.dirname(os.path.abspath(filepath))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    payload = {
        "generator": "API TEST CLI",
        "exported_at": datetime.now().isoformat(),
        "report": data,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return os.path.abspath(filepath)


def export_to_csv(data: Dict[str, Any], filepath: str) -> str:
    """Exports benchmark, comparison, or stress test results to CSV format."""
    out_dir = os.path.dirname(os.path.abspath(filepath))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Case 1: Model Comparison
        if "models" in data and isinstance(data["models"], list):
            writer.writerow(["Model", "Status", "TTFT (ms)", "Total Latency (ms)", "TPS (tokens/s)", "Tokens", "HTTP Code", "Error"])
            for m in data["models"]:
                writer.writerow([
                    m.get("model", "unknown"),
                    "OK" if m.get("success") else "FAILED",
                    m.get("ttft_ms", 0.0),
                    m.get("total_latency_ms", 0.0),
                    m.get("tps", 0.0),
                    m.get("tokens", 0),
                    m.get("status_code", 0),
                    m.get("error") or "",
                ])

        # Case 2: Stress Test
        elif "concurrency" in data and "results" in data:
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Model", data.get("model", "")])
            writer.writerow(["Concurrency", data.get("concurrency", 0)])
            writer.writerow(["Total Requests", data.get("total_requests", 0)])
            writer.writerow(["Successful Requests", data.get("successful_requests", 0)])
            writer.writerow(["Failed Requests", data.get("failed_requests", 0)])
            writer.writerow(["Success Rate (%)", data.get("success_rate_pct", 0.0)])
            writer.writerow(["Aggregate TPS", data.get("aggregate_tps", 0.0)])
            writer.writerow(["Duration (sec)", data.get("duration_sec", 0.0)])
            writer.writerow([])
            writer.writerow(["Request #", "Status", "Latency (ms)", "Tokens", "HTTP Status", "Error"])
            for idx, r in enumerate(data.get("results", []), 1):
                writer.writerow([
                    idx,
                    "SUCCESS" if r.get("success") else "FAILED",
                    r.get("latency_ms", 0.0),
                    r.get("tokens", 0),
                    r.get("status_code", 0),
                    r.get("error") or "",
                ])

        # Case 3: Single or Multi-run Benchmark
        else:
            writer.writerow(["Metric", "Value", "Unit / Notes"])
            writer.writerow(["Model", data.get("model", "unknown"), ""])
            writer.writerow(["Success", data.get("success", False), ""])
            writer.writerow(["TTFT", data.get("ttft_ms", 0.0), "ms"])
            writer.writerow(["Total Latency", data.get("total_latency_ms", 0.0), "ms"])
            writer.writerow(["Generation Latency", data.get("generation_latency_ms", 0.0), "ms"])
            writer.writerow(["Throughput", data.get("tps", 0.0), "tokens/sec"])
            writer.writerow(["Tokens", data.get("tokens", 0), "tokens"])

            if "stats" in data and isinstance(data["stats"], dict):
                st = data["stats"]
                writer.writerow(["Stability Score", st.get("stability_score", 100.0), "%"])
                writer.writerow(["Cold Start TTFT", st.get("cold_start_ttft_ms", 0.0), "ms"])
                writer.writerow(["Warm TTFT", st.get("warm_ttft_ms", 0.0), "ms"])

            # Individual runs breakdown
            if "runs" in data and len(data["runs"]) > 1:
                writer.writerow([])
                writer.writerow(["Run #", "TTFT (ms)", "Total Latency (ms)", "TPS", "Tokens", "Status"])
                for r in data["runs"]:
                    writer.writerow([
                        r.get("run_number", 1),
                        r.get("ttft_ms", 0.0),
                        r.get("total_latency_ms", 0.0),
                        r.get("tps", 0.0),
                        r.get("tokens", 0),
                        "OK" if r.get("success") else "FAILED",
                    ])

    return os.path.abspath(filepath)


def export_to_markdown(data: Dict[str, Any], filepath: str) -> str:
    """Exports telemetry to a clean GitHub-flavored Markdown report."""
    out_dir = os.path.dirname(os.path.abspath(filepath))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# ⚡ API TEST CLI - Performance & Telemetry Report",
        f"*Generated on {timestamp}*",
        "",
    ]

    # Case 1: Model Comparison Matrix
    if "models" in data and isinstance(data["models"], list):
        prompt = data.get("prompt", "")
        lines.append(f"### 🥊 Model Arena Comparison")
        if prompt:
            lines.append(f"**Prompt:** `{prompt}`\n")

        # Winners
        winners = data.get("winners", {})
        if winners:
            lines.append("#### 🏆 Leaderboard Badges")
            if "fastest_ttft" in winners:
                w = winners["fastest_ttft"]
                lines.append(f"- ⚡ **Fastest TTFT:** `{w['model']}` ({w['value']} ms)")
            if "highest_tps" in winners:
                w = winners["highest_tps"]
                lines.append(f"- 🚀 **Highest Throughput:** `{w['model']}` ({w['value']} tokens/sec)")
            if "lowest_latency" in winners:
                w = winners["lowest_latency"]
                lines.append(f"- ⏱ **Fastest Overall:** `{w['model']}` ({w['value']} ms)")
            lines.append("")

        lines.append("| Model | Status | TTFT (ms) | Total Latency | Throughput | Tokens |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for m in data["models"]:
            status = "🟢 OK" if m.get("success") else "🔴 FAILED"
            lines.append(
                f"| `{m.get('model')}` | {status} | {m.get('ttft_ms', 0):.1f} ms | "
                f"{m.get('total_latency_ms', 0):.1f} ms | {m.get('tps', 0):.1f} T/s | {m.get('tokens', 0)} |"
            )

    # Case 2: Stress Test
    elif "concurrency" in data and "results" in data:
        lines.append(f"### 🌪 Concurrency & Load Stress Test")
        lines.append(f"- **Target Model:** `{data.get('model')}`")
        lines.append(f"- **Concurrency Level:** `{data.get('concurrency')} parallel workers`")
        lines.append(f"- **Total Requests:** `{data.get('total_requests')}`")
        lines.append(f"- **Success Rate:** `{data.get('success_rate_pct')}%` ({data.get('successful_requests')}/{data.get('total_requests')})")
        lines.append(f"- **Aggregate Throughput:** `{data.get('aggregate_tps')} tokens/sec`")
        lines.append(f"- **Test Duration:** `{data.get('duration_sec')} s`\n")

        stats = data.get("latency_stats", {})
        lines.append("| Latency Metric | Measurement |")
        lines.append("| :--- | :---: |")
        lines.append(f"| P95 Latency | `{stats.get('p95', 0)} ms` |")
        lines.append(f"| Mean Latency | `{stats.get('mean', 0)} ms` |")
        lines.append(f"| Median Latency | `{stats.get('median', 0)} ms` |")
        lines.append(f"| Min Latency | `{stats.get('min', 0)} ms` |")
        lines.append(f"| Max Latency | `{stats.get('max', 0)} ms` |")

        if data.get("error_breakdown"):
            lines.append("\n#### ❌ Error Breakdown")
            for err, count in data["error_breakdown"].items():
                lines.append(f"- `{err}`: {count} occurrences")

    # Case 3: Benchmark Report
    else:
        model = data.get("model", "unknown")
        lines.append(f"### 🎯 Benchmark Telemetry: `{model}`")
        lines.append("")
        lines.append("| Metric | Measurement | Notes |")
        lines.append("| :--- | :---: | :--- |")
        lines.append(f"| Target Model | `{model}` | HTTP {data.get('status_code', 200)} |")
        lines.append(f"| TTFT (Time To First Token) | `{data.get('ttft_ms', 0):.1f} ms` | Time to start output |")
        lines.append(f"| Total Response Latency | `{data.get('total_latency_ms', 0):.1f} ms` | Stream duration |")
        lines.append(f"| Token Generation Speed | `{data.get('tps', 0):.1f} tokens/sec` | Throughput |")
        lines.append(f"| Tokens Generated | `{data.get('tokens', 0)} tokens` | ~{len(data.get('response_text', ''))} chars |")

        if "stats" in data:
            st = data["stats"]
            lines.append(f"| Stability Score | `{st.get('stability_score', 100)}%` | Based on throughput variance |")
            lines.append(f"| Cold Start TTFT | `{st.get('cold_start_ttft_ms', 0):.1f} ms` | Run #1 |")
            lines.append(f"| Warm Average TTFT | `{st.get('warm_ttft_ms', 0):.1f} ms` | Runs #2+ |")

        if data.get("response_text"):
            lines.append("\n#### 💬 Model Response Output")
            lines.append(f"> {data.get('response_text')}\n")

    content = "\n".join(lines) + "\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return os.path.abspath(filepath)


def export_to_html(data: Dict[str, Any], filepath: str) -> str:
    """
    Exports telemetry to a standalone, modern, dark-mode HTML dashboard.
    Completely offline: zero external fonts or CDN scripts.
    """
    out_dir = os.path.dirname(os.path.abspath(filepath))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Determine report type
    is_comparison = "models" in data and isinstance(data["models"], list)
    is_stress = "concurrency" in data and "results" in data

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>API TEST Telemetry Report</title>
<style>
  :root {{
    --bg: #0d1117;
    --card-bg: #161b22;
    --border: #30363d;
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --yellow: #d29922;
    --red: #f85149;
    --purple: #bc8cff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background-color: var(--bg);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    padding: 2rem 1rem;
  }}
  .container {{
    max-width: 1000px;
    margin: 0 auto;
  }}
  header {{
    text-align: center;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
  }}
  .title {{
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #58a6ff, #bc8cff, #3fb950);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
  }}
  .subtitle {{
    color: var(--text-secondary);
    font-size: 0.95rem;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
  }}
  .card-label {{
    color: var(--text-secondary);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
  }}
  .card-value {{
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text-primary);
  }}
  .card-unit {{
    font-size: 0.9rem;
    font-weight: normal;
    color: var(--text-secondary);
  }}
  .badge {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
  }}
  .badge-green {{ background: rgba(63, 185, 80, 0.15); color: var(--green); }}
  .badge-blue {{ background: rgba(88, 166, 255, 0.15); color: var(--accent); }}
  .badge-yellow {{ background: rgba(210, 153, 34, 0.15); color: var(--yellow); }}
  .badge-red {{ background: rgba(248, 81, 73, 0.15); color: var(--red); }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    background: var(--card-bg);
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--border);
  }}
  th, td {{
    padding: 0.85rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  th {{
    background: #21262d;
    color: var(--text-secondary);
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
  }}
  tr:last-child td {{
    border-bottom: none;
  }}
  tr:hover td {{
    background: rgba(88, 166, 255, 0.05);
  }}
  .response-box {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-top: 1.5rem;
  }}
  .response-title {{
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 0.75rem;
  }}
  .response-content {{
    white-space: pre-wrap;
    font-family: monospace;
    font-size: 0.9rem;
    background: #0d1117;
    padding: 1rem;
    border-radius: 6px;
    border: 1px solid var(--border);
    color: #e6edf3;
  }}
  footer {{
    text-align: center;
    margin-top: 3rem;
    color: var(--text-secondary);
    font-size: 0.85rem;
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="title">⚡ API TEST CLI Telemetry Report</div>
    <div class="subtitle">Generated at {timestamp}</div>
  </header>
"""

    if is_comparison:
        winners = data.get("winners", {})
        w_ttft = winners.get("fastest_ttft", {}).get("model", "—")
        w_tps = winners.get("highest_tps", {}).get("model", "—")
        w_lat = winners.get("lowest_latency", {}).get("model", "—")

        html_content += f"""
  <div class="grid">
    <div class="card">
      <div class="card-label">⚡ Fastest TTFT</div>
      <div class="card-value" style="color: var(--green); font-size: 1.3rem;">{w_ttft}</div>
    </div>
    <div class="card">
      <div class="card-label">🚀 Highest Throughput</div>
      <div class="card-value" style="color: var(--accent); font-size: 1.3rem;">{w_tps}</div>
    </div>
    <div class="card">
      <div class="card-label">⏱ Fastest Latency</div>
      <div class="card-value" style="color: var(--purple); font-size: 1.3rem;">{w_lat}</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Model</th>
        <th>Status</th>
        <th>TTFT</th>
        <th>Total Latency</th>
        <th>Throughput</th>
        <th>Tokens</th>
      </tr>
    </thead>
    <tbody>
"""
        for m in data.get("models", []):
            st_badge = '<span class="badge badge-green">OK</span>' if m.get("success") else '<span class="badge badge-red">FAILED</span>'
            html_content += f"""
      <tr>
        <td><strong>{m.get('model')}</strong></td>
        <td>{st_badge}</td>
        <td>{m.get('ttft_ms', 0):.1f} ms</td>
        <td>{m.get('total_latency_ms', 0):.1f} ms</td>
        <td><strong>{m.get('tps', 0):.1f}</strong> <span class="card-unit">T/s</span></td>
        <td>{m.get('tokens', 0)}</td>
      </tr>
"""
        html_content += """
    </tbody>
  </table>
"""

    elif is_stress:
        html_content += f"""
  <div class="grid">
    <div class="card">
      <div class="card-label">Success Rate</div>
      <div class="card-value" style="color: var(--green);">{data.get('success_rate_pct')}<span class="card-unit">%</span></div>
    </div>
    <div class="card">
      <div class="card-label">Aggregate Throughput</div>
      <div class="card-value" style="color: var(--accent);">{data.get('aggregate_tps')}<span class="card-unit"> T/s</span></div>
    </div>
    <div class="card">
      <div class="card-label">Concurrency Level</div>
      <div class="card-value">{data.get('concurrency')} <span class="card-unit">workers</span></div>
    </div>
    <div class="card">
      <div class="card-label">P95 Latency</div>
      <div class="card-value" style="color: var(--yellow);">{data.get('latency_stats', {}).get('p95', 0)}<span class="card-unit"> ms</span></div>
    </div>
  </div>
"""

    else:
        model = data.get("model", "unknown")
        ttft = data.get("ttft_ms", 0.0)
        tps = data.get("tps", 0.0)
        tot_lat = data.get("total_latency_ms", 0.0)
        tokens = data.get("tokens", 0)

        html_content += f"""
  <div class="grid">
    <div class="card">
      <div class="card-label">Target Model</div>
      <div class="card-value" style="font-size: 1.3rem; color: var(--accent);">{model}</div>
      <div class="card-unit">HTTP {data.get('status_code', 200)}</div>
    </div>
    <div class="card">
      <div class="card-label">TTFT Latency</div>
      <div class="card-value" style="color: var(--green);">{ttft:.1f}<span class="card-unit"> ms</span></div>
    </div>
    <div class="card">
      <div class="card-label">Throughput Speed</div>
      <div class="card-value" style="color: var(--accent);">{tps:.1f}<span class="card-unit"> T/s</span></div>
    </div>
    <div class="card">
      <div class="card-label">Total Latency</div>
      <div class="card-value">{tot_lat:.1f}<span class="card-unit"> ms</span></div>
    </div>
  </div>
"""
        if data.get("response_text"):
            html_content += f"""
  <div class="response-box">
    <div class="response-title">Model Output Content</div>
    <div class="response-content">{data.get('response_text')}</div>
  </div>
"""

    html_content += """
  <footer>
    Benchmarked with <strong>API TEST CLI</strong> &bull; Open-Source AI Endpoint Telemetry
  </footer>
</div>
</body>
</html>
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(filepath)


def auto_export(data: Dict[str, Any], filepath: str) -> str:
    """
    Automatically routes export to JSON, CSV, Markdown, or HTML based on the file extension.
    """
    lower = filepath.lower()
    if lower.endswith(".json"):
        return export_to_json(data, filepath)
    elif lower.endswith(".csv"):
        return export_to_csv(data, filepath)
    elif lower.endswith(".md") or lower.endswith(".markdown"):
        return export_to_markdown(data, filepath)
    elif lower.endswith(".html") or lower.endswith(".htm"):
        return export_to_html(data, filepath)
    else:
        # Default to JSON
        return export_to_json(data, filepath + ".json")

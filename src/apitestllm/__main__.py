"""API TEST CLI entry point - High-Performance AI Endpoint Benchmark Suite."""

from apitestllm._compat import ensure_utf8_stdio
from apitestllm.cli import main

ensure_utf8_stdio()

if __name__ == "__main__":
    main()

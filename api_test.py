#!/usr/bin/env python3
"""Direct launcher for environments without uv. Use `uv run apitestllm` when uv is available."""

from apitestllm.cli import main

if __name__ == "__main__":
    main()

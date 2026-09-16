#!/usr/bin/env python3
"""
API TEST CLI - High-Performance AI Endpoint & Latency Benchmark Suite
"""

import os
import sys

# Ensure local module directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main

if __name__ == "__main__":
    main()

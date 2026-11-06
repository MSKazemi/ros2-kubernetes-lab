#!/usr/bin/env python3
"""Run the harness without installing it: python3 experiments/e02-dds-resilience/run.py --help"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ddsres.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

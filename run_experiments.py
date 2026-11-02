#!/usr/bin/env python3
"""
run_experiments.py
==================
Direct launcher for experimental data collection (MT2013 - CC09).
Compatible with the project proposal design document.
"""

from subprocess import run
import sys
import os

if __name__ == "__main__":
    script = os.path.join(os.path.dirname(__file__), "01_collect_data.py")
    sys.exit(run([sys.executable, script] + sys.argv[1:]).returncode)

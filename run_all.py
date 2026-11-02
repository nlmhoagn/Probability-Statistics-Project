#!/usr/bin/env python3
"""
run_all.py
==========
Master Reproducibility Pipeline for MT2013 Course Project (Class CC09)
Two-Factor Experimental Design (Length L and Complexity K)

Executes the entire experimental workflow in order:
  Step 1: 01_collect_data.py         -> Collect 2-axis brute-force timing dataset
  Step 2: 02_clean_and_preprocess.py -> Validate, clean, tag axes, compute log features
  Step 3: 03_statistical_analysis.py -> Descriptive stats, CIs, t-tests, ANOVA, OLS regression
  Step 4: 04_visualize.py            -> Generate LaTeX/TikZ vector figures
  Step 5: 05_export_excel.py         -> Export MT2013_CC09_Data.xlsx workbook
"""

import os
import subprocess
import sys


def run_step(script_name: str, base_dir: str, extra_args: list[str] = None) -> None:
    script_path = os.path.join(base_dir, script_name)
    cmd = [sys.executable, script_path] + (extra_args or [])
    print(f"\n>>> Running {script_name} ...")
    result = subprocess.run(cmd, cwd=base_dir)
    if result.returncode != 0:
        sys.exit(f"Error: {script_name} exited with code {result.returncode}")


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pass_args = sys.argv[1:]

    # Step 1: Collect data (passes any CLI arguments like --samples-fast, etc.)
    run_step("01_collect_data.py", base_dir, pass_args)

    # Step 2: Clean and preprocess
    run_step("02_clean_and_preprocess.py", base_dir)

    # Step 3: Statistical analysis & LaTeX table generation
    run_step("03_statistical_analysis.py", base_dir)

    # Step 4: Visualize & TikZ figures
    run_step("04_visualize.py", base_dir)

    # Step 5: Export multi-sheet Excel file
    run_step("05_export_excel.py", base_dir)

    print("\n" + "=" * 75)
    print("All 2-Factor pipeline steps completed successfully!")
    print("=" * 75)


if __name__ == "__main__":
    main()

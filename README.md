# 2-Factor Experimental Reproducibility Package (MT2013 - CC09)

**Project Title:** Analysis of the Relationship between Password Length, Character Set Complexity, and Brute-force Cracking Time and Number of Attempts  
**Course:** Probability and Statistics (MT2013)  
**Instructor:** Le Xuan Dai  
**Technical Implementation:** Two-Factor Controlled Experiment ($L$ and $K$)

---

## 1. Experimental Methodology Overview

To answer the core cybersecurity question:
> *"Does extending password length ($L$) or expanding character set complexity ($K$) provide more effective protection against exhaustive brute-force attacks?"*

The experiment is rigorously structured across two orthogonal axes:
1. **Axis 1 (Length Effect on Full Complexity):** Fixed $K = 70$ (digits, lowercase, uppercase, symbols `!@#$%^&*`), evaluating $L \in \{1, 2, 3, 4\}$.
2. **Axis 2 (Complexity Effect at Fixed Length):** Fixed length $L = 4$, evaluating four standard security complexity tiers:
   - Digits (`0-9`, $K = 10, N = 10^4 = 10,000$)
   - Lowercase (`a-z`, $K = 26, N = 26^4 = 456,976$)
   - Alphanumeric (`0-9, a-z, A-Z`, $K = 62, N = 62^4 = 14,776,336$)
   - Full Symbols (`0-9, a-z, A-Z, !@#$%^&*`, $K = 70, N = 70^4 = 24,010,000$)

*(The group $L=4, K=70$ is shared across both axes to eliminate redundant computation).*

---

## 2. Directory Structure

```text
Probability-Statistics-Project/
├── config.py                 # Central definitions of CHARSETS, AXIS_1, AXIS_2 & hardware
├── 01_collect_data.py        # Section 2.7 & Appendix B.1: Deterministic SHA-256 data collection
├── run_experiments.py        # Alias launcher matching proposal specification
├── 02_clean_and_preprocess.py# Section 2.8: Data validation, multi-factor tagging & log transforms
├── 03_statistical_analysis.py# Sections 3 & 4: Descriptive stats, CIs, t-tests, ANOVA & OLS
├── 04_visualize.py           # Section 4: Generates standalone LaTeX/TikZ figures
├── 05_export_excel.py        # Guideline Section 10: Multi-sheet MT2013_CC09_Data.xlsx exporter
├── analysis.R                # Equivalent R script with ANOVA, Tukey HSD, and diagnostics
├── run_all.py                # Master automation pipeline (runs steps 01 through 05)
├── data/
│   ├── raw_experiment_data.csv             # Raw collected observations
│   ├── extended_multicharset_results.csv   # Identical raw file matching proposal name
│   ├── processed_experiment_data.csv       # Clean dataset with engineered features
│   ├── summary_extended_multicharset.csv   # Summary table for all surveyed groups
│   └── MT2013_CC09_Data.xlsx               # Multi-sheet Excel workbook for submission
├── results/
│   ├── summary_all_groups.csv              # Summary stats across all 7 groups
│   ├── table_axis1_length_stats.csv        # Axis 1: Descriptive stats, 95% CIs, and t-tests
│   ├── table_axis1_growth_factors.csv      # Axis 1: Growth ratios between L and L+1
│   ├── table_axis2_charset_stats.csv       # Axis 2: Complexity stats and empirical gain
│   ├── table_tradeoff_length_vs_complexity.csv # Practical security trade-off matrix
│   ├── statistical_summary.json            # Regression models and ANOVA results
│   └── latex_tables.tex                    # Ready-to-use LaTeX booktabs tables
├── figures/
│   ├── fig1_norm_attempts_hist.tex         # Histogram: Normalized attempts vs U(0,1)
│   ├── fig2_axis1_regression.tex           # Plot: log10(T) vs Length L (K=70)
│   ├── fig3_axis2_boxplot.tex              # Boxplot: log10(T) across 4 complexity levels
│   └── fig4_time_vs_attempts.tex           # Scatter: Time T vs Attempts A (Global OLS)
└── logs/
    ├── experiment_config.json              # CPU, OS specs and execution parameters
    └── preprocessing_report.json           # Validation and IQR fence details
```

---

## 3. How to Execute the Pipeline

Use Python 3.10 or newer (the included experiment was run with Python 3.14.5).
The Python pipeline uses only the standard library; no pip dependencies are required.
The optional `analysis.R` script uses base R's `stats` package.

Clone the repository and enter its root directory:

```powershell
git clone https://github.com/nlmhoagn/Probability-Statistics-Project.git
cd Probability-Statistics-Project
```

Run the entire pipeline in sequence with a single command:

```powershell
python run_all.py
```

This collects new timing measurements and overwrites the generated files in
`data/`, `results/`, `figures/`, and `logs/`. To analyze the included measurements
without collecting them again, run steps 02 through 05 below.

Or execute custom runs (e.g. customized sample sizes):

```powershell
# Custom run: 60 samples for fast groups, 30 for heavy groups (default: 20 heavy)
python 01_collect_data.py --samples-fast 60 --samples-heavy 30 --seed 202610

# Preprocess & feature engineering
python 02_clean_and_preprocess.py

# Statistical analysis, ANOVA, and regression
python 03_statistical_analysis.py

# Generate LaTeX figures
python 04_visualize.py

# Export multi-sheet Excel file
python 05_export_excel.py
```

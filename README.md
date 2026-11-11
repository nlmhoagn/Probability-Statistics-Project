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
│   ├── table_axis2_anova.csv              # ANOVA for log10 time
│   ├── table_axis2_pairwise.csv           # Welch comparisons with Holm-adjusted p-values
│   ├── table_tradeoff_length_vs_complexity.csv # Keyspace ratios, measurements and projections
│   ├── residuals_data.csv                 # Row-level fitted values and residuals
│   ├── table_sensitivity.csv              # Fits with and without high-latency flags
│   ├── statistical_summary.json           # OLS, ANOVA and median-centered Levene check
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

Use Python 3.10 or newer for the main pipeline (the included experiment was
collected with Python 3.14.5). It uses the standard library; no pip install is
required. For the optional report figures below use Python 3.11 or newer.
The optional `analysis.R` script uses base R's `stats` package.

Clone the repository and enter its root directory:

```powershell
git clone https://github.com/nlmhoagn/Probability-Statistics-Project.git
cd Probability-Statistics-Project
```

### Reproduce the saved analysis

The saved raw data contains 340 measured trials. The group still needs to
decide whether this dataset is the final submission dataset. To reproduce the
tables, TikZ figures and Excel workbook from these measurements, run:

```powershell
# Preprocess & feature engineering
python 02_clean_and_preprocess.py

# Statistical analysis, ANOVA, and regression
python 03_statistical_analysis.py

# Generate LaTeX figures
python 04_visualize.py

# Export multi-sheet Excel file
python 05_export_excel.py
```

Preprocessing checks the exact target rank and the group counts against the
experiment log. The main analyses retain all valid rows. The sensitivity table
shows how the two regressions change when high-latency rows are excluded.
Pairwise tests compare mean log times, and the exponentiated differences compare
geometric mean times. The trade-off table lists the assumed throughput alongside
each projection. A regression p-value stored as zero reflects floating-point underflow.

Run the regression tests with `python -m unittest -v`. They build outputs in
temporary directories from the included CSV and experiment log.

Scripts 02--05 overwrite derived files in `data/`, `results/`, `figures/` and
`logs/preprocessing_report.json`, but do not recollect the raw measurements.
The workbook's ZIP metadata can vary between runs. Check the numerical tables
and the output of the tests rather than comparing Excel files byte-for-byte.

### Regenerate the report figures

The report uses the PDF figures created by Nguyen Nhat Huy's
`report_figures/make_figures.py`. Their plotting dependencies are optional and
were verified on Python 3.11.16 with the pinned versions below:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-figures.txt
.\.venv\Scripts\python.exe report_figures/make_figures.py
```

On macOS or Linux, use `.venv/bin/python` instead. Figures are written to
`report_figures/output/` as PDF and PNG files. The mean-attempt confidence
intervals use the same Student-t critical values as `03_statistical_analysis.py`.
The script prints cross-checks against `results/table_axis1_length_stats.csv`.
Rerun steps 02--03 first if the raw data changes, and upload updated PDFs to
Overleaf when the results change. Rendering can vary with fonts and platform.

### Collect a new dataset

Only after preserving the existing data and experiment log, run:

```powershell
python run_all.py
```

This runs the experiment again and **overwrites the raw dataset and experiment
log**, as well as downstream outputs. Measurements depend on the machine and
system load; a fixed seed reproduces sampled targets, not measured times. The
default collection uses 60 samples per small group, 20 per large group and
seed `202610`; inspect options with `python 01_collect_data.py --help`.

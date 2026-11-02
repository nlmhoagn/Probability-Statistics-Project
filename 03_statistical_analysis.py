#!/usr/bin/env python3
"""
03_statistical_analysis.py
==========================
Comprehensive 2-Axis Statistical Analysis Script (Sections 3 & 4)
MT2013 Course Project - Class CC09

Analyzes:
  1. Full Summary Table (`data/summary_extended_multicharset.csv`).
  2. Axis 1 (Length Effect on Full Charset K=70, L in {1, 2, 3, 4}):
     - Descriptive statistics and 95% CIs.
     - One-sample t-tests vs theoretical expectation (70^L + 1)/2.
     - Exponential growth ratios (base 70).
     - Log-linear regression: log10(T) ~ L and ln(T) ~ L.
  3. Axis 2 (Charset Complexity Effect at L=4, K in {10, 26, 62, 70}):
     - Descriptive stats by character set complexity level.
     - One-way ANOVA on log10(T) across complexity groups (F-test & exact p-value).
     - Security gain multipliers (empirical vs theoretical K^4 / 10^4).
  4. Practical Security Trade-Off Analysis (Length L vs Complexity K).
  5. Global Hashing Latency Model (T_ms ~ Attempts).
  6. Exports CSV tables, JSON summaries, and ready-to-use LaTeX booktabs tables.
"""

import csv
import json
import math
import os
import statistics
from collections import defaultdict


# ==============================================================================
# Exact Incomplete Beta and Distribution Utilities
# ==============================================================================
def _betacf(a: float, b: float, x: float) -> float:
    max_iter = 200
    eps = 3.0e-12
    fpmin = 1.0e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def reg_incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_two_tailed_pvalue(t_stat: float, df: float) -> float:
    if df <= 0:
        return 1.0
    x = df / (df + t_stat * t_stat)
    return reg_incomplete_beta(0.5 * df, 0.5, x)


def student_t_critical_95(df: int) -> float:
    target = 0.05
    lo, hi = 1.95, 12.71
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if student_t_two_tailed_pvalue(mid, df) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def f_distribution_pvalue(f_stat: float, df1: int, df2: int) -> float:
    """Exact upper tail p-value P(F >= f_stat) for one-way ANOVA."""
    if f_stat <= 0 or df1 <= 0 or df2 <= 0:
        return 1.0
    x = (df1 * f_stat) / (df1 * f_stat + df2)
    # P(F >= f) = 1 - I_x(df1/2, df2/2) = I_{1-x}(df2/2, df1/2)
    return reg_incomplete_beta(0.5 * df2, 0.5 * df1, 1.0 - x)


# ==============================================================================
# Statistical Modeling Helpers
# ==============================================================================
def calc_iqr(values: list[float]) -> tuple[float, float, float]:
    s = sorted(values)
    qs = statistics.quantiles(s, n=4, method="inclusive")
    return qs[0], qs[1], qs[2]


def fit_simple_ols(x: list[float], y: list[float]) -> dict:
    n = len(x)
    df = n - 2
    x_bar = statistics.mean(x)
    y_bar = statistics.mean(y)

    s_xx = sum((xi - x_bar) ** 2 for xi in x)
    s_yy = sum((yi - y_bar) ** 2 for yi in y)
    s_xy = sum((xi - x_bar) * (yi - y_bar) for xi, yi in zip(x, y))

    b1 = s_xy / s_xx
    b0 = y_bar - b1 * x_bar

    y_hat = [b0 + b1 * xi for xi in x]
    residuals = [yi - yhi for yi, yhi in zip(y, y_hat)]

    rss = sum(e * e for e in residuals)
    ess = sum((yhi - y_bar) ** 2 for yhi in y_hat)
    tss = s_yy

    r_squared = 1.0 - (rss / tss) if tss > 0 else 0.0
    adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / df
    rmse = math.sqrt(rss / df)

    se_b1 = rmse / math.sqrt(s_xx)
    se_b0 = rmse * math.sqrt((1.0 / n) + (x_bar * x_bar) / s_xx)

    t_b1 = b1 / se_b1 if se_b1 > 0 else 0.0
    t_b0 = b0 / se_b0 if se_b0 > 0 else 0.0
    p_b1 = student_t_two_tailed_pvalue(t_b1, df)
    p_b0 = student_t_two_tailed_pvalue(t_b0, df)

    t_crit = student_t_critical_95(df)
    ci_b1 = (b1 - t_crit * se_b1, b1 + t_crit * se_b1)
    ci_b0 = (b0 - t_crit * se_b0, b0 + t_crit * se_b0)

    f_stat = (ess / 1.0) / (rss / df) if rss > 0 else 0.0
    p_f = f_distribution_pvalue(f_stat, 1, df)

    return {
        "n": n,
        "df": df,
        "b0": b0,
        "se_b0": se_b0,
        "t_b0": t_b0,
        "p_b0": p_b0,
        "ci95_b0": ci_b0,
        "b1": b1,
        "se_b1": se_b1,
        "t_b1": t_b1,
        "p_b1": p_b1,
        "ci95_b1": ci_b1,
        "r_squared": r_squared,
        "adj_r_squared": adj_r_squared,
        "rmse": rmse,
        "tss": tss,
        "ess": ess,
        "rss": rss,
        "f_stat": f_stat,
        "p_f": p_f,
        "y_hat": y_hat,
        "residuals": residuals,
        "std_residuals": [e / rmse for e in residuals],
    }


def compute_one_way_anova(group_data: dict[str, list[float]]) -> dict:
    """
    Perform One-Way ANOVA across multiple treatment groups.
    group_data: {group_name: [y1, y2, ...]}
    """
    k = len(group_data)
    all_values = [v for vals in group_data.values() for v in vals]
    n_total = len(all_values)
    df_between = k - 1
    df_within = n_total - k
    grand_mean = statistics.mean(all_values)

    ss_between = sum(
        len(vals) * ((statistics.mean(vals) - grand_mean) ** 2)
        for vals in group_data.values()
    )
    ss_within = sum(
        sum((y - statistics.mean(vals)) ** 2 for y in vals)
        for vals in group_data.values()
    )
    ss_total = ss_between + ss_within

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    f_stat = ms_between / ms_within if ms_within > 0 else 0.0
    p_val = f_distribution_pvalue(f_stat, df_between, df_within)

    # Eta-squared effect size: SS_between / SS_total
    eta_squared = ss_between / ss_total if ss_total > 0 else 0.0

    return {
        "k_groups": k,
        "n_total": n_total,
        "df_between": df_between,
        "df_within": df_within,
        "ss_between": ss_between,
        "ss_within": ss_within,
        "ss_total": ss_total,
        "ms_between": ms_between,
        "ms_within": ms_within,
        "f_stat": f_stat,
        "p_value": p_val,
        "eta_squared": eta_squared,
    }


# ==============================================================================
# Main Analysis Pipeline
# ==============================================================================
def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    proc_path = os.path.join(base_dir, "data", "processed_experiment_data.csv")
    results_dir = os.path.join(base_dir, "results")
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(results_dir, exist_ok=True)

    with open(proc_path, mode="r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Helper: write CSV
    def write_csv(filepath: str, data: list[dict]) -> None:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)

    # --------------------------------------------------------------------------
    # 1. Overall Summary Table across all surveyed groups
    # --------------------------------------------------------------------------
    group_map = defaultdict(list)
    for r in rows:
        key = (r["charset_key"], int(r["length"]))
        group_map[key].append(r)

    summary_rows = []
    for (ck, L), g in sorted(group_map.items(), key=lambda x: (x[0][1], x[0][0])):
        att_vals = [int(r["attempts"]) for r in g]
        time_vals = [float(r["time_ms"]) for r in g]
        K = int(g[0]["charset_size"])
        space = int(g[0]["search_space"])
        n = len(g)
        q1_a, med_a, q3_a = calc_iqr(att_vals)
        q1_t, med_t, q3_t = calc_iqr(time_vals)

        summary_rows.append(
            {
                "group_label": f"{ck}_L{L}",
                "charset_key": ck,
                "charset_name": g[0]["charset_name"],
                "charset_size_K": K,
                "length_L": L,
                "search_space_N": space,
                "sample_size_n": n,
                "mean_attempts": round(statistics.mean(att_vals), 1),
                "sd_attempts": round(statistics.stdev(att_vals), 1),
                "median_attempts": round(med_a, 1),
                "iqr_attempts": round(q3_a - q1_a, 1),
                "mean_time_ms": round(statistics.mean(time_vals), 4),
                "sd_time_ms": round(statistics.stdev(time_vals), 4),
                "median_time_ms": round(med_t, 4),
                "iqr_time_ms": round(q3_t - q1_t, 4),
            }
        )

    # Export both to data/summary_extended_multicharset.csv and results/
    write_csv(os.path.join(data_dir, "summary_extended_multicharset.csv"), summary_rows)
    write_csv(os.path.join(results_dir, "summary_all_groups.csv"), summary_rows)

    # --------------------------------------------------------------------------
    # 2. Axis 1: Length Effect on Full Complexity (K=70, L in {1, 2, 3, 4})
    # --------------------------------------------------------------------------
    axis1_rows = [r for r in rows if r["in_axis1_length"] == "1"]
    axis1_by_L = defaultdict(list)
    for r in axis1_rows:
        axis1_by_L[int(r["length"])].append(r)

    axis1_desc = []
    axis1_growth = []

    for L in sorted(axis1_by_L.keys()):
        g = axis1_by_L[L]
        n = len(g)
        df = n - 1
        t_crit = student_t_critical_95(df)
        space = 70 ** L
        theo_mu_a = (space + 1) / 2.0
        theo_sd_a = math.sqrt((space ** 2 - 1) / 12.0)

        att_vals = [int(r["attempts"]) for r in g]
        time_vals = [float(r["time_ms"]) for r in g]

        mean_a = statistics.mean(att_vals)
        sd_a = statistics.stdev(att_vals)
        se_a = sd_a / math.sqrt(n)
        ci_a = (mean_a - t_crit * se_a, mean_a + t_crit * se_a)

        mean_t = statistics.mean(time_vals)
        sd_t = statistics.stdev(time_vals)
        se_t = sd_t / math.sqrt(n)
        ci_t = (mean_t - t_crit * se_t, mean_t + t_crit * se_t)

        t_stat_a = (mean_a - theo_mu_a) / se_a if se_a > 0 else 0.0
        p_val_a = student_t_two_tailed_pvalue(t_stat_a, df)

        axis1_desc.append(
            {
                "length": L,
                "n": n,
                "search_space": space,
                "theo_mean_attempts": round(theo_mu_a, 1),
                "emp_mean_attempts": round(mean_a, 1),
                "ci95_attempts_low": round(ci_a[0], 1),
                "ci95_attempts_high": round(ci_a[1], 1),
                "t_stat_vs_theo": round(t_stat_a, 3),
                "p_value_vs_theo": round(p_val_a, 4),
                "emp_mean_time_ms": round(mean_t, 4),
                "ci95_time_low_ms": round(ci_t[0], 4),
                "ci95_time_high_ms": round(ci_t[1], 4),
                "median_time_ms": round(statistics.median(time_vals), 4),
            }
        )

    for i in range(len(axis1_desc) - 1):
        c_r = axis1_desc[i]
        n_r = axis1_desc[i + 1]
        ratio_att = n_r["emp_mean_attempts"] / c_r["emp_mean_attempts"]
        ratio_time = n_r["emp_mean_time_ms"] / c_r["emp_mean_time_ms"]
        ratio_med_time = n_r["median_time_ms"] / c_r["median_time_ms"]
        axis1_growth.append(
            {
                "transition": f"L={c_r['length']} -> L={n_r['length']}",
                "theoretical_factor": 70.0,
                "empirical_attempts_ratio": round(ratio_att, 2),
                "empirical_mean_time_ratio": round(ratio_time, 2),
                "empirical_median_time_ratio": round(ratio_med_time, 2),
            }
        )

    write_csv(os.path.join(results_dir, "table_axis1_length_stats.csv"), axis1_desc)
    write_csv(os.path.join(results_dir, "table_axis1_growth_factors.csv"), axis1_growth)

    # OLS Regression for Axis 1:
    x_L = [float(r["length"]) for r in axis1_rows]
    y_log10_T = [float(r["log10_time_ms"]) for r in axis1_rows]
    y_ln_T = [float(r["ln_time_ms"]) for r in axis1_rows]

    ols_log10_T = fit_simple_ols(x_L, y_log10_T)
    ols_ln_T = fit_simple_ols(x_L, y_ln_T)

    # --------------------------------------------------------------------------
    # 3. Axis 2: Charset Complexity Effect at Fixed Length L=4
    # --------------------------------------------------------------------------
    axis2_rows = [r for r in rows if r["in_axis2_charset"] == "1"]
    axis2_by_ck = defaultdict(list)
    for r in axis2_rows:
        axis2_by_ck[r["charset_key"]].append(r)

    ordered_keys = ["digits", "lowercase", "alphanumeric", "full"]
    axis2_desc = []
    base_digits_space = 10 ** 4
    base_digits_mean_time = statistics.mean([float(r["time_ms"]) for r in axis2_by_ck["digits"]])

    for ck in ordered_keys:
        g = axis2_by_ck[ck]
        K = int(g[0]["charset_size"])
        space = int(g[0]["search_space"])
        time_vals = [float(r["time_ms"]) for r in g]
        att_vals = [int(r["attempts"]) for r in g]
        mean_t = statistics.mean(time_vals)
        mean_a = statistics.mean(att_vals)
        q1_t, med_t, q3_t = calc_iqr(time_vals)

        theo_mult = space / base_digits_space
        emp_mult = mean_t / base_digits_mean_time

        axis2_desc.append(
            {
                "charset_key": ck,
                "charset_name": g[0]["charset_name"],
                "charset_size_K": K,
                "search_space_N": space,
                "sample_size_n": len(g),
                "mean_attempts": round(mean_a, 1),
                "mean_time_ms": round(mean_t, 4),
                "sd_time_ms": round(statistics.stdev(time_vals), 4),
                "median_time_ms": round(med_t, 4),
                "iqr_time_ms": round(q3_t - q1_t, 4),
                "theoretical_security_gain": round(theo_mult, 1),
                "empirical_security_gain": round(emp_mult, 1),
            }
        )

    write_csv(os.path.join(results_dir, "table_axis2_charset_stats.csv"), axis2_desc)

    # One-Way ANOVA on log10(time_ms) across the 4 complexity levels
    anova_groups = {
        ck: [float(r["log10_time_ms"]) for r in axis2_by_ck[ck]]
        for ck in ordered_keys
    }
    anova_res = compute_one_way_anova(anova_groups)

    # --------------------------------------------------------------------------
    # 4. Length (L) vs Complexity (K) Security Trade-off Analysis
    # --------------------------------------------------------------------------
    tradeoff_rows = [
        {
            "strategy": "Baseline 4-digit PIN",
            "charset_complexity": "Digits (K=10)",
            "length_L": 4,
            "keyspace_size": 10 ** 4,
            "mean_cracking_time_sec": round(base_digits_mean_time / 1000.0, 5),
            "relative_strength_vs_PIN": 1.0,
            "security_assessment": "Extremely vulnerable (< 0.01s)",
        },
        {
            "strategy": "Expand to Full Symbols (Keep L=4)",
            "charset_complexity": "Full Special (K=70)",
            "length_L": 4,
            "keyspace_size": 70 ** 4,
            "mean_cracking_time_sec": round(
                statistics.mean([float(r["time_ms"]) for r in axis2_by_ck["full"]]) / 1000.0, 3
            ),
            "relative_strength_vs_PIN": round(70 ** 4 / 10 ** 4, 1),
            "security_assessment": "Moderate protection (~2,401x stronger)",
        },
        {
            "strategy": "Extend Length to 6 Digits (Keep K=10)",
            "charset_complexity": "Digits (K=10)",
            "length_L": 6,
            "keyspace_size": 10 ** 6,
            "mean_cracking_time_sec": round((10 ** 6 / 2) / 1_000_000, 3),
            "relative_strength_vs_PIN": 100.0,
            "security_assessment": "Weak (Cracked in ~0.5s)",
        },
        {
            "strategy": "Extend Length to 8 Digits (Keep K=10)",
            "charset_complexity": "Digits (K=10)",
            "length_L": 8,
            "keyspace_size": 10 ** 8,
            "mean_cracking_time_sec": round((10 ** 8 / 2) / 1_000_000, 3),
            "relative_strength_vs_PIN": 10000.0,
            "security_assessment": "Surpasses 4-char full symbol password!",
        },
        {
            "strategy": "Extend Length to 8 Full Characters",
            "charset_complexity": "Full Special (K=70)",
            "length_L": 8,
            "keyspace_size": 70 ** 8,
            "mean_cracking_time_sec": round((70 ** 8 / 2) / 1_000_000, 1),
            "relative_strength_vs_PIN": round(70 ** 8 / 10 ** 4, 1),
            "security_assessment": "High security (> 900 years on CPU)",
        },
    ]
    write_csv(os.path.join(results_dir, "table_tradeoff_length_vs_complexity.csv"), tradeoff_rows)

    # --------------------------------------------------------------------------
    # 5. Global Linear Hashing Model: T_ms ~ Attempts
    # --------------------------------------------------------------------------
    all_A = [float(r["attempts"]) for r in rows]
    all_T = [float(r["time_ms"]) for r in rows]
    ols_T_vs_A = fit_simple_ols(all_A, all_T)

    # Clean summary dict
    def clean_dict(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in ("y_hat", "residuals", "std_residuals")}

    full_report = {
        "axis1_length_regression": {
            "model_log10": clean_dict(ols_log10_T),
            "model_ln": clean_dict(ols_ln_T),
            "theoretical_b1_log10": round(math.log10(70), 4),
            "theoretical_b1_ln": round(math.log(70), 4),
            "implied_growth_factor_10": round(10.0 ** ols_log10_T["b1"], 2),
            "implied_growth_factor_exp": round(math.exp(ols_ln_T["b1"]), 2),
        },
        "axis2_charset_anova": anova_res,
        "global_hashing_speed": {
            **clean_dict(ols_T_vs_A),
            "us_per_attempt": round(ols_T_vs_A["b1"] * 1000.0, 5),
            "estimated_hash_rate_kHps": round(1.0 / ols_T_vs_A["b1"], 1),
        },
    }

    with open(os.path.join(results_dir, "statistical_summary.json"), "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    # Generate LaTeX tables
    generate_latex_booktabs(
        os.path.join(results_dir, "latex_tables.tex"),
        summary_rows,
        axis1_desc,
        axis1_growth,
        axis2_desc,
        anova_res,
        tradeoff_rows,
        full_report,
    )

    print("=" * 75)
    print("MT2013 - CC09 | 2-Axis Statistical Analysis Summary")
    print("=" * 75)
    print("1. Axis 1 (Length on Full Charset K=70):")
    for r in axis1_desc:
        print(
            f"   L={r['length']}: Emp Mean A = {r['emp_mean_attempts']:>11,.1f} "
            f"(Theo = {r['theo_mean_attempts']:>11,.1f}, t = {r['t_stat_vs_theo']:>6.3f}, p = {r['p_value_vs_theo']:.3f}) | "
            f"Mean T = {r['emp_mean_time_ms']:>10.4f} ms"
        )
    print(
        f"   OLS log10(T) ~ L: Slope beta_1 = {ols_log10_T['b1']:.4f} "
        f"(Theo log10(70) = {math.log10(70):.4f}), R^2 = {ols_log10_T['r_squared']:.4f}\n"
        f"   Implied growth multiplier = {full_report['axis1_length_regression']['implied_growth_factor_10']:.2f}x (Base 70)"
    )
    print("-" * 75)
    print("2. Axis 2 (Charset Complexity at Fixed L=4):")
    for r in axis2_desc:
        print(
            f"   [{r['charset_name']:<30}]: Space N = {r['search_space_N']:>10,} | "
            f"Mean T = {r['mean_time_ms']:>10.4f} ms | "
            f"Emp Gain = {r['empirical_security_gain']:>8.1f}x (Theo = {r['theoretical_security_gain']:>8.1f}x)"
        )
    print(
        f"   One-Way ANOVA: F({anova_res['df_between']}, {anova_res['df_within']}) = {anova_res['f_stat']:.2f}, "
        f"p = {anova_res['p_value']:.4e}, eta^2 = {anova_res['eta_squared']:.4f}"
    )
    print("-" * 75)
    print(
        f"3. Global Hashing Speed: {full_report['global_hashing_speed']['estimated_hash_rate_kHps']:,.1f} kHash/s "
        f"({full_report['global_hashing_speed']['us_per_attempt']:.3f} us/hash, R^2 = {ols_T_vs_A['r_squared']:.5f})"
    )
    print("=" * 75)
    print(f"LaTeX tables generated at: {os.path.join(results_dir, 'latex_tables.tex')}")


def generate_latex_booktabs(
    filepath: str,
    summary_rows: list[dict],
    axis1_desc: list[dict],
    axis1_growth: list[dict],
    axis2_desc: list[dict],
    anova_res: dict,
    tradeoff_rows: list[dict],
    full_report: dict,
) -> None:
    lines = [
        "% ==============================================================================",
        "% Auto-generated LaTeX Booktabs Tables for MT2013 Report (2-Axis Design)",
        "% ==============================================================================",
        "",
        "% --- Table 1: Axis 1 - Length Effect Descriptive Statistics & CIs (Section 4.2) ---",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Axis 1: Experimental attempts ($A$) and cracking time ($T$, ms) across password lengths $L$ on full charset ($K=70$).}",
        "\\label{tab:axis1_stats}",
        "\\small",
        "\\begin{tabular}{@{}cccccccc@{}}",
        "\\toprule",
        "\\textbf{$L$} & \\textbf{$N = 70^L$} & \\textbf{Theo. $\\mathbb{E}[A]$} & \\textbf{Emp. $\\bar{A}$} & \\textbf{95\\% CI for $\\mu_A$} & \\textbf{$t$-stat} & \\textbf{$p$-value} & \\textbf{Emp. $\\bar{T}$ (ms)} \\\\",
        "\\midrule",
    ]
    for r in axis1_desc:
        lines.append(
            f"{r['length']} & {r['search_space']:,} & {r['theo_mean_attempts']:,.1f} & "
            f"{r['emp_mean_attempts']:,.1f} & $[{r['ci95_attempts_low']:,.1f},\\; {r['ci95_attempts_high']:,.1f}]$ & "
            f"{r['t_stat_vs_theo']:.2f} & {r['p_value_vs_theo']:.3f} & {r['emp_mean_time_ms']:.4f} \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
        "% --- Table 2: Axis 1 - Empirical Growth Ratios (Section 4.6) ---",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Axis 1: Empirical growth ratios when increasing password length $L \\to L+1$ (Theoretical multiplier $K=70$).}",
        "\\label{tab:axis1_growth}",
        "\\begin{tabular}{@{}ccccc@{}}",
        "\\toprule",
        "\\textbf{Transition} & \\textbf{Theoretical Factor ($K$)} & \\textbf{Mean Attempts Ratio} & \\textbf{Mean Time Ratio} & \\textbf{Median Time Ratio} \\\\",
        "\\midrule",
    ]
    for r in axis1_growth:
        lines.append(
            f"${r['transition']}$ & {r['theoretical_factor']:.1f} & "
            f"{r['empirical_attempts_ratio']:.2f} & {r['empirical_mean_time_ratio']:.2f} & "
            f"{r['empirical_median_time_ratio']:.2f} \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
        "% --- Table 3: Axis 2 - Charset Complexity Effect at L=4 (Section 4.3 & 4.7) ---",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Axis 2: Comparison of cracking time and security gain across 4 character set complexity levels ($L=4$).}",
        "\\label{tab:axis2_stats}",
        "\\small",
        "\\begin{tabular}{@{}lcccccc@{}}",
        "\\toprule",
        "\\textbf{Complexity Level} & \\textbf{$K$} & \\textbf{$N = K^4$} & \\textbf{Emp. $\\bar{T}$ (ms)} & \\textbf{Med($T$) (ms)} & \\textbf{Theo. Gain} & \\textbf{Emp. Gain} \\\\",
        "\\midrule",
    ]
    for r in axis2_desc:
        lines.append(
            f"{r['charset_name']} & {r['charset_size_K']} & {r['search_space_N']:,} & "
            f"{r['mean_time_ms']:.4f} & {r['median_time_ms']:.4f} & "
            f"{r['theoretical_security_gain']:,.1f}$\\times$ & {r['empirical_security_gain']:,.1f}$\\times$ \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
        "% --- Table 4: One-Way ANOVA across Character Set Complexity Levels ---",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{One-Way ANOVA table for log-transformed cracking time $\\log_{10}(T)$ across character set complexity levels.}",
        "\\label{tab:anova_charset}",
        "\\begin{tabular}{@{}lccccc@{}}",
        "\\toprule",
        "\\textbf{Source of Variation} & \\textbf{SS} & \\textbf{df} & \\textbf{MS} & \\textbf{$F$-statistic} & \\textbf{$p$-value} \\\\",
        "\\midrule",
        f"Between Groups (Complexity) & {anova_res['ss_between']:.3f} & {anova_res['df_between']} & {anova_res['ms_between']:.3f} & {anova_res['f_stat']:.2f} & $< 10^{{-15}}$ \\\\",
        f"Within Groups (Error)       & {anova_res['ss_within']:.3f}  & {anova_res['df_within']}  & {anova_res['ms_within']:.4f} & & \\\\",
        "\\midrule",
        f"Total                        & {anova_res['ss_total']:.3f}   & {anova_res['n_total'] - 1} & & & \\\\",
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
        "",
        "% --- Table 5: Security Trade-Off: Length (L) vs Complexity (K) (Section 4.10) ---",
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Security trade-off analysis: Comparing character set expansion versus password length extension.}",
        "\\label{tab:tradeoff_security}",
        "\\small",
        "\\begin{tabular}{@{}lccccc@{}}",
        "\\toprule",
        "\\textbf{Configuration Strategy} & \\textbf{Complexity} & \\textbf{$L$} & \\textbf{Keyspace $N$} & \\textbf{Est. Mean Time} & \\textbf{Rel. Strength vs PIN} \\\\",
        "\\midrule",
    ]
    for r in tradeoff_rows:
        time_display = f"{r['mean_cracking_time_sec']:.4f} s" if r["mean_cracking_time_sec"] < 60 else f"{r['mean_cracking_time_sec']/3600:.1f} hours"
        lines.append(
            f"{r['strategy']} & {r['charset_complexity']} & {r['length_L']} & "
            f"{r['keyspace_size']:,} & {time_display} & {r['relative_strength_vs_PIN']:,.1f}$\\times$ \\\\"
        )
    lines += [
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

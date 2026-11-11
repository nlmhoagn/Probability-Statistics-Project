#!/usr/bin/env python3
"""
make_figures.py  --  T15: report figures (MT2013 password brute-force project)

Reads data/processed_experiment_data.csv and writes vector PDF + 300-dpi PNG
figures to report_figures/output/. Nothing in the existing pipeline is touched.

Everything is derived from the CSV (group sizes, K, L, theory), so the script
keeps working when the team re-collects data or changes the design.
Only numpy + matplotlib are needed (no scipy, no pandas).

Usage (from the repo root):
    python report_figures/make_figures.py
    python report_figures/make_figures.py --data data/processed_experiment_data.csv --out report_figures/output
"""

import argparse
import csv
import math
import os
import runpy
from collections import defaultdict
from statistics import NormalDist

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------------------------------- style
plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 10,
        "axes.titlesize": 10,
        "axes.labelsize": 10,
        "legend.fontsize": 8.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.6,
        "pdf.fonttype": 42,  # embed TrueType so Overleaf/pdfLaTeX keeps the text selectable
        "savefig.bbox": "tight",
    }
)
C_DATA = "#2F5D8C"    # observations / boxes
C_THEORY = "#C0392B"  # theory / reference lines
C_FIT = "#E08A1E"     # fitted lines
C_MEAN = "#1B1B1B"


# --------------------------------------------------------------------------- helpers
def read_rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def t_crit_975(df):
    """Use the same Student-t critical value as the analysis tables."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    analysis = runpy.run_path(os.path.join(root, "03_statistical_analysis.py"))
    return analysis["student_t_critical_95"](df)


def ols(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    xm, ym = x.mean(), y.mean()
    sxx = ((x - xm) ** 2).sum()
    b1 = ((x - xm) * (y - ym)).sum() / sxx
    b0 = ym - b1 * xm
    fitted = b0 + b1 * x
    resid = y - fitted
    rss = (resid**2).sum()
    tss = ((y - ym) ** 2).sum()
    se_b1 = math.sqrt(rss / (n - 2) / sxx)
    return {"b0": b0, "b1": b1, "r2": 1 - rss / tss, "se_b1": se_b1, "n": n, "fitted": fitted, "resid": resid}


def save(fig, out_dir, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out_dir, f"{name}.{ext}"), dpi=300)
    plt.close(fig)
    print(f"  wrote {name}.pdf / .png")


def fmt_int(v, _pos=None):
    return f"{int(v):,}" if v >= 1 else f"{v:g}"


# --------------------------------------------------------------------------- data
def load(path):
    rows = read_rows(path)
    recs = []
    for r in rows:
        recs.append(
            {
                "axis1": r["in_axis1_length"] == "1",
                "axis2": r["in_axis2_charset"] == "1",
                "charset": r["charset_key"],
                "K": int(r["charset_size"]),
                "L": int(r["length"]),
                "N": int(r["search_space"]),
                "A": float(r["attempts"]),
                "T": float(r["time_sec"]),  # seconds (as in the team plan)
                "U": float(r["norm_attempts"]),
                "jitter": r.get("os_jitter_flag", "0") == "1",
            }
        )
    return recs


# --------------------------------------------------------------------------- figures
def fig_box_by_L(ax1, key, ylabel, title, out_dir, name, theory=False):
    Ls = sorted({r["L"] for r in ax1})
    data = [[r[key] for r in ax1 if r["L"] == L] for L in Ls]
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    ax.boxplot(
        data,
        positions=range(len(Ls)),
        widths=0.55,
        patch_artist=True,
        showmeans=True,
        boxprops=dict(facecolor="#CFDDEC", edgecolor=C_DATA),
        medianprops=dict(color=C_DATA, linewidth=1.6),
        whiskerprops=dict(color=C_DATA),
        capprops=dict(color=C_DATA),
        flierprops=dict(marker="o", markersize=3, markerfacecolor="none", markeredgecolor=C_DATA),
        meanprops=dict(marker="D", markerfacecolor=C_MEAN, markeredgecolor=C_MEAN, markersize=4),
    )
    if theory:
        K = ax1[0]["K"]
        ax.plot(range(len(Ls)), [(K**L + 1) / 2 for L in Ls], "v", color=C_THEORY, markersize=6, label=r"Theoretical mean $(K^L+1)/2$")
    ax.set_yscale("log")
    ax.set_xticks(range(len(Ls)))
    ax.set_xticklabels([f"{L}\n(n={len(d)})" for L, d in zip(Ls, data)])
    ax.set_xlabel("Password length $L$ (characters)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(plt.Line2D([], [], marker="D", color="none", markerfacecolor=C_MEAN, markeredgecolor=C_MEAN, markersize=4))
    labels.append("Sample mean")
    ax.legend(handles, labels, loc="upper left", frameon=False)
    save(fig, out_dir, name)


def fig_mean_ci(ax1, out_dir):
    K = ax1[0]["K"]
    Ls = sorted({r["L"] for r in ax1})
    means, lows, highs, ns = [], [], [], []
    for L in Ls:
        a = np.array([r["A"] for r in ax1 if r["L"] == L])
        n = len(a)
        m, s = a.mean(), a.std(ddof=1)
        h = t_crit_975(n - 1) * s / math.sqrt(n)
        means.append(m), lows.append(m - h), highs.append(m + h), ns.append(n)
    means, lows, highs = map(np.array, (means, lows, highs))
    theo = np.array([(K**L + 1) / 2 for L in Ls])
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    Lgrid = np.linspace(min(Ls) - 0.15, max(Ls) + 0.15, 100)
    ax.plot(Lgrid, (K**Lgrid + 1) / 2, "-", color=C_THEORY, linewidth=1.4, label=r"Theory $E[A\mid L]=(K^L+1)/2$")
    ax.errorbar(Ls, means, yerr=[means - lows, highs - means], fmt="o", color=C_DATA, capsize=4, markersize=5, label="Sample mean, 95% CI")
    for L, m, n in zip(Ls, means, ns):
        ax.annotate(f"n={n}", (L, m), textcoords="offset points", xytext=(7, -12), fontsize=8, color=C_DATA)
    ax.set_yscale("log")
    ax.set_xticks(Ls)
    ax.set_xlabel("Password length $L$ (characters)")
    ax.set_ylabel("Number of attempts $A$")
    ax.set_title(f"Mean attempts vs. theory (K = {K})")
    ax.legend(loc="upper left", frameon=False)
    save(fig, out_dir, "fig3_mean_attempts_ci_vs_theory")
    return dict(zip(Ls, zip(means, lows, highs, theo)))


def fig_L_vs_logT(ax1, out_dir):
    K = ax1[0]["K"]
    Ls = np.array([r["L"] for r in ax1], float)
    logT = np.log10([r["T"] for r in ax1])
    fit = ols(Ls, logT)
    rng = np.random.default_rng(0)  # jitter only; fixed seed so the figure is reproducible
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    ax.scatter(Ls + rng.uniform(-0.12, 0.12, len(Ls)), logT, s=9, alpha=0.45, color=C_DATA, edgecolor="none", label="Observations")
    for L in sorted(set(Ls)):
        ax.plot(L, logT[Ls == L].mean(), "D", color=C_MEAN, markersize=5, label="Group mean of $\\log_{10}T$" if L == min(Ls) else None)
    xg = np.array([Ls.min() - 0.2, Ls.max() + 0.2])
    ax.plot(xg, fit["b0"] + fit["b1"] * xg, "-", color=C_FIT, linewidth=1.8,
            label=rf"OLS fit: slope $={fit['b1']:.3f}$, $R^2={fit['r2']:.3f}$")
    ax.plot(xg, fit["b0"] + math.log10(K) * (xg - xg[0]) + fit["b1"] * xg[0], "--", color=C_THEORY, linewidth=1.2,
            label=rf"Reference slope $\log_{{10}}K={math.log10(K):.3f}$")
    ax.set_xticks(sorted(set(Ls)))
    ax.set_xlabel("Password length $L$ (characters)")
    ax.set_ylabel(r"$\log_{10}$ of cracking time $T$ (s)")
    ax.set_title("Cracking time vs. password length")
    ax.legend(loc="upper left", frameon=False)
    save(fig, out_dir, "fig4_scatter_L_logT")
    return fit


def fig_A_vs_T(rows, out_dir):
    A = np.array([r["A"] for r in rows])
    T = np.array([r["T"] for r in rows])
    fit = ols(A, T)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.8))
    groups = sorted({(r["charset"], r["L"]) for r in rows}, key=lambda g: min(r["N"] for r in rows if (r["charset"], r["L"]) == g))
    cmap = plt.get_cmap("viridis")
    for i, g in enumerate(groups):
        sel = [(r["A"], r["T"]) for r in rows if (r["charset"], r["L"]) == g]
        col = cmap(i / max(1, len(groups) - 1) * 0.9)
        a1.scatter(*zip(*sel), s=8, alpha=0.6, color=col, edgecolor="none", label=f"{g[0]}, L={g[1]}")
        a2.scatter(*zip(*sel), s=8, alpha=0.6, color=col, edgecolor="none")
    xg = np.linspace(0, A.max() * 1.03, 100)
    a1.plot(xg, fit["b0"] + fit["b1"] * xg, color=C_FIT, linewidth=1.6,
            label=f"OLS: slope = {fit['b1']*1e6:.3f} µs/attempt, $R^2$ = {fit['r2']:.3f}")
    a1.set_xlabel("Number of attempts $A$ ($\\times10^{6}$)")
    a1.xaxis.set_major_formatter(lambda v, _p: f"{v/1e6:g}")
    a1.set_ylabel("Cracking time $T$ (s)")
    a1.set_title("(a) Linear scale")
    h, lab = a1.get_legend_handles_labels()
    fig.legend(h, lab, frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.30, 0.02), ncol=4)
    xl =np.logspace(0, math.log10(A.max() * 1.2), 50)
    a2.plot(xl, fit["b1"] * xl, color=C_FIT, linewidth=1.6, label="Proportional line through origin (same slope)")
    a2.set_xscale("log"), a2.set_yscale("log")
    a2.set_xlabel("Number of attempts $A$")
    a2.set_ylabel("Cracking time $T$ (s)")
    a2.set_title("(b) Log–log scale")
    a2.legend(frameon=False, fontsize=7, loc="lower right")
    save(fig, out_dir, "fig5_scatter_A_T")
    return fit


def fig_hist_U(rows, out_dir, bins=5):
    groups = sorted({(r["charset"], r["L"]) for r in rows}, key=lambda g: (min(r["N"] for r in rows if (r["charset"], r["L"]) == g), g))
    ncol = 4
    nrow = math.ceil(len(groups) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(9.2, 2.3 * nrow), sharex=True, sharey=True)
    axes = np.atleast_1d(axes).ravel()
    edges = np.linspace(0, 1, bins + 1)
    for ax, g in zip(axes, groups):
        u = [r["U"] for r in rows if (r["charset"], r["L"]) == g]
        ax.hist(u, bins=edges, density=True, color="#CFDDEC", edgecolor=C_DATA)
        ax.axhline(1, color=C_THEORY, linestyle="--", linewidth=1.2)
        ax.set_title(f"{g[0]}, L={g[1]} (n={len(u)})", fontsize=9)
        ax.set_ylim(0, 2.0)
    for ax in axes[len(groups):]:
        ax.axis("off")
    for ax in axes[: len(groups)]:
        ax.set_xlabel("$U=A/K^L$")
    for i in range(0, len(axes), ncol):
        axes[i].set_ylabel("Density")
    fig.suptitle(f"Normalised attempts $U$ per group vs. Uniform(0,1) (dashed); {bins} equal bins", fontsize=10)
    fig.tight_layout()
    save(fig, out_dir, "fig6_hist_U_by_group")


def fig_residuals(ax1, out_dir):
    L = np.array([r["L"] for r in ax1], float)
    y = np.log10([r["T"] for r in ax1])
    fit = ols(L, y)
    res, fitted = fit["resid"], fit["fitted"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.2, 3.6))
    a1.scatter(fitted, res, s=9, alpha=0.5, color=C_DATA, edgecolor="none")
    a1.axhline(0, color=C_THEORY, linestyle="--", linewidth=1.2)
    a1.set_xlabel(r"Fitted $\widehat{\log_{10}T}$")
    a1.set_ylabel("Residual")
    a1.set_title("(a) Residuals vs. fitted values")
    srt = np.sort(res)
    n = len(srt)
    q = np.array([NormalDist().inv_cdf((i - 0.5) / n) for i in range(1, n + 1)])
    a2.scatter(q, srt, s=9, alpha=0.6, color=C_DATA, edgecolor="none")
    sd = res.std(ddof=2)
    a2.plot(q, q * sd, color=C_THEORY, linestyle="--", linewidth=1.2, label="Normal reference line")
    a2.set_xlabel("Theoretical normal quantiles")
    a2.set_ylabel("Ordered residuals")
    a2.set_title("(b) Normal Q–Q plot")
    a2.legend(frameon=False)
    save(fig, out_dir, "fig7_residuals_logT_on_L")


def fig_axis2_box(ax2, out_dir):
    order = sorted({(r["K"], r["charset"]) for r in ax2})
    data = [[math.log10(r["T"]) for r in ax2 if r["charset"] == c] for _k, c in order]
    L = ax2[0]["L"]
    fig, ax = plt.subplots(figsize=(5.4, 3.8))
    ax.boxplot(
        data, positions=range(len(order)), widths=0.55, patch_artist=True, showmeans=True,
        boxprops=dict(facecolor="#CFDDEC", edgecolor=C_DATA), medianprops=dict(color=C_DATA, linewidth=1.6),
        whiskerprops=dict(color=C_DATA), capprops=dict(color=C_DATA),
        flierprops=dict(marker="o", markersize=3, markerfacecolor="none", markeredgecolor=C_DATA),
        meanprops=dict(marker="D", markerfacecolor=C_MEAN, markeredgecolor=C_MEAN, markersize=4),
    )
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([f"K={k}\n{c}\n(n={len(d)})" for (k, c), d in zip(order, data)], fontsize=8)
    ax.set_xlabel(f"Character-set size $K$ (fixed length $L={L}$)")
    ax.set_ylabel(r"$\log_{10}$ of cracking time $T$ (s)")
    ax.set_title("Cracking time by character-set size")
    save(fig, out_dir, "fig8_axis2_boxplot_logT_by_K")


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--data", default=os.path.join(root, "data", "processed_experiment_data.csv"))
    ap.add_argument("--out", default=os.path.join(root, "report_figures", "output"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    rows = load(args.data)
    ax1 = [r for r in rows if r["axis1"]]
    ax2 = [r for r in rows if r["axis2"]]
    print(f"Read {len(rows)} rows from {args.data}")
    print(f"  axis-1 rows: {len(ax1)} (K={ax1[0]['K']}, L={sorted({r['L'] for r in ax1})}); axis-2 rows: {len(ax2)}")
    print(f"  OS-jitter flagged rows (kept in all figures): {sum(r['jitter'] for r in rows)}")
    print("Writing figures:")

    fig_box_by_L(ax1, "A", "Number of attempts $A$", "Attempts by password length", args.out, "fig1_box_attempts_by_L", theory=True)
    fig_box_by_L(ax1, "T", "Cracking time $T$ (s)", "Cracking time by password length", args.out, "fig2_box_time_by_L")
    ci = fig_mean_ci(ax1, args.out)
    fit_L = fig_L_vs_logT(ax1, args.out)
    fit_AT = fig_A_vs_T(rows, args.out)
    fig_hist_U(rows, args.out)
    fig_residuals(ax1, args.out)
    fig_axis2_box(ax2, args.out)

    # numbers behind the figures, for cross-checking against the team's tables (T16)
    print("\nCross-check numbers (compare with results/table_axis1_length_stats.csv):")
    for L, (m, lo, hi, th) in ci.items():
        print(f"  L={L}: mean A = {m:,.1f}  95% CI [{lo:,.1f}, {hi:,.1f}]  theory = {th:,.1f}")
    print(f"  log10(T) ~ L : slope = {fit_L['b1']:.4f} (SE {fit_L['se_b1']:.4f}), R^2 = {fit_L['r2']:.4f}, n = {fit_L['n']}")
    print(f"  T ~ A (all rows): slope = {fit_AT['b1']*1e6:.4f} us/attempt, intercept = {fit_AT['b0']:.3f} s, R^2 = {fit_AT['r2']:.4f}, n = {fit_AT['n']}")


if __name__ == "__main__":
    main()

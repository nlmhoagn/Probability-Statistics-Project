#!/usr/bin/env python3
"""
02_clean_and_preprocess.py
==========================
Data Validation, Preprocessing, and Feature Engineering Script (Section 2.8)
MT2013 Course Project - Class CC09

Performs:
  1. Validate observation IDs, target ranks, measured times, and sample counts.
  2. Multi-factor tagging:
     - in_axis1_length (boolean: K=70, L in {1, 2, 3, 4})
     - in_axis2_charset (boolean: L=4, K in {10, 26, 62, 70})
  3. Feature engineering:
     - Normalized rank: u = A / K^L
     - Theoretical mean & SD: (K^L + 1)/2 and sqrt((K^(2L) - 1)/12)
     - Log-transformations: ln(T_ms), log10(T_ms), ln(A), log10(A)
     - Latency per hash: us_per_attempt = (T_ms * 1000) / A
  4. Flag high per-attempt latency using an upper IQR fence within each group.
  5. Exports cleaned dataset to `data/processed_experiment_data.csv`.
"""

import csv
import json
import math
import os
import statistics
from collections import Counter, defaultdict

from config import CHARSETS, HEAVY_SEARCH_SPACE_THRESHOLD


def compute_quartiles(values: list[float]) -> tuple[float, float, float]:
    """Return (Q1, Median, Q3) for a numeric list."""
    s = sorted(values)
    n = len(s)
    if n < 4:
        return s[0], statistics.median(s), s[-1]
    qs = statistics.quantiles(s, n=4, method="inclusive")
    return qs[0], qs[1], qs[2]


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(base_dir, "data", "raw_experiment_data.csv")
    proc_path = os.path.join(base_dir, "data", "processed_experiment_data.csv")
    report_path = os.path.join(base_dir, "logs", "preprocessing_report.json")
    config_path = os.path.join(base_dir, "logs", "experiment_config.json")

    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw data not found at {raw_path}. Run 01_collect_data.py first.")

    with open(raw_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    total_raw = len(raw_rows)
    missing_count = 0
    invalid_domain_count = 0
    valid_rows = []
    seen_ids = set()

    for r in raw_rows:
        if any(v is None or str(v).strip() == "" for v in r.values()):
            missing_count += 1
            continue

        obs_id = int(r["obs_id"])
        if obs_id in seen_ids:
            raise ValueError(f"Duplicate observation ID: {obs_id}")
        seen_ids.add(obs_id)

        K = int(r["charset_size"])
        L = int(r["length"])
        space = int(r["search_space"])
        attempts = int(r["attempts"])
        time_ms = float(r["time_ms"])
        time_sec = float(r["time_sec"])
        throughput = float(r["throughput_hash_s"])

        # Domain validity: 1 <= A <= K^L, T > 0, K^L consistent
        if not (
            L > 0 and 1 <= attempts <= space and space == K ** L
            and math.isfinite(time_ms) and time_ms > 0
            and math.isfinite(time_sec) and time_sec > 0
            and math.isclose(time_ms, time_sec * 1000.0)
            and math.isfinite(throughput) and throughput > 0
        ):
            invalid_domain_count += 1
            continue

        alphabet = CHARSETS[r["charset_key"]]["chars"]
        target = r["target_sample"].removeprefix("'")
        if K != len(alphabet) or len(target) != L or any(char not in alphabet for char in target):
            raise ValueError(f"Invalid target or character set at observation {obs_id}")
        rank = 0
        for char in target:
            rank = rank * K + alphabet.index(char)
        if attempts != rank + 1:
            raise ValueError(f"Attempt count does not match target rank at observation {obs_id}")

        us_per_attempt = (time_ms * 1000.0) / attempts
        in_axis1 = 1 if (r["charset_key"] == "full" and L in (1, 2, 3, 4)) else 0
        in_axis2 = 1 if (L == 4 and r["charset_key"] in ("digits", "lowercase", "alphanumeric", "full")) else 0

        valid_rows.append(
            {
                "obs_id": obs_id,
                "axis_tag": r["axis"],
                "in_axis1_length": in_axis1,
                "in_axis2_charset": in_axis2,
                "charset_key": r["charset_key"],
                "charset_name": r["charset_name"],
                "charset_size": K,
                "length": L,
                "search_space": space,
                "trial_in_group": int(r["trial_in_group"]),
                "target_sample": r["target_sample"],
                "attempts": attempts,
                "norm_attempts": round(attempts / space, 6),
                "theo_mean_attempts": round((space + 1) / 2.0, 2),
                "theo_sd_attempts": round(math.sqrt((space ** 2 - 1) / 12.0), 2),
                "time_ms": time_ms,
                "time_sec": time_sec,
                "ln_time_ms": round(math.log(time_ms), 6),
                "log10_time_ms": round(math.log10(time_ms), 6),
                "ln_attempts": round(math.log(attempts), 6),
                "log10_attempts": round(math.log10(attempts), 6),
                "us_per_attempt": round(us_per_attempt, 6),
                "throughput_khash_s": round(throughput / 1000.0, 2),
            }
        )

    group_counts = Counter((r["charset_key"], r["length"]) for r in valid_rows)
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        parameters = config["parameters"]
        expected_counts = {
            (group["charset"], group["L"]): parameters[
                "samples_heavy" if group["search_space"] > HEAVY_SEARCH_SPACE_THRESHOLD else "samples_fast"
            ]
            for group in config["groups_surveyed"]
        }
        if group_counts != expected_counts or len(valid_rows) != parameters["total_observations"]:
            raise ValueError(f"Valid sample counts {dict(group_counts)} differ from the experiment log {expected_counts}")
    if not valid_rows:
        raise ValueError("No valid observations in the input data")

    # Flag unusually high per-attempt latency within each group.
    by_group = defaultdict(list)
    for r in valid_rows:
        key = (r["charset_key"], r["length"])
        by_group[key].append(r["us_per_attempt"])

    bounds_by_group = {}
    for key, latencies in sorted(by_group.items()):
        q1, med, q3 = compute_quartiles(latencies)
        iqr = q3 - q1
        upper_fence = q3 + 3.0 * iqr
        bounds_by_group[f"{key[0]}_L{key[1]}"] = {
            "q1_us": round(q1, 4),
            "median_us": round(med, 4),
            "q3_us": round(q3, 4),
            "upper_fence_us": round(upper_fence, 4),
            "sample_size": len(latencies),
            "flagged_count": 0,
        }

    jitter_count = 0
    for r in valid_rows:
        key_str = f"{r['charset_key']}_L{r['length']}"
        fence = bounds_by_group[key_str]["upper_fence_us"]
        is_jitter = 1 if r["us_per_attempt"] > fence else 0
        r["os_jitter_flag"] = is_jitter
        jitter_count += is_jitter
        bounds_by_group[key_str]["flagged_count"] += is_jitter

    fieldnames = list(valid_rows[0].keys())
    with open(proc_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_rows)

    report = {
        "total_raw": total_raw,
        "missing_removed": missing_count,
        "invalid_removed": invalid_domain_count,
        "total_clean": len(valid_rows),
        "os_jitter_flagged": jitter_count,
        "bounds_by_group": bounds_by_group,
        "output_file": "data/processed_experiment_data.csv",
    }

    with open(report_path, mode="w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 75)
    print("MT2013 - CC09 | Preprocessing & 2-Axis Feature Engineering Complete")
    print(f"Total raw observations:  {total_raw}")
    print(f"Clean valid records:    {len(valid_rows)}")
    print(f"OS jitter flags:        {jitter_count}")
    print(f"Saved processed dataset: {proc_path}")
    print("=" * 75)


if __name__ == "__main__":
    main()

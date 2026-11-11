#!/usr/bin/env python3
"""
01_collect_data.py (also accessible as run_experiments.py)
==========================================================
Experimental Data Collection Script for MT2013 Course Project (Class CC09)
Topic: Analysis of the Relationship between Password Length, Character Set Complexity,
       and Brute-force Cracking Time and Number of Attempts.

Implements the 2-Factor Controlled Experimental Design:
  - Axis 1: Length Effect on Full Complexity (K = 70 fixed, L in {1, 2, 3, 4})
  - Axis 2: Complexity Effect at Fixed Length (L = 4 fixed, K in {10, 26, 62, 70})
  - Shared Group: (full, L=4) is utilized by both axes to eliminate redundant runtime.

Outputs:
  - data/raw_experiment_data.csv
  - data/extended_multicharset_results.csv (identical copy for compatibility)
  - logs/experiment_config.json
"""

import argparse
import csv
import hashlib
import itertools
import json
import os
import random
import shutil
import time
from config import CHARSETS, HEAVY_SEARCH_SPACE_THRESHOLD, get_hardware_environment


def run_single_trial(target: str, alphabet: str) -> tuple[int, float]:
    """
    Execute exhaustive deterministic brute-force matching against SHA-256 target digest.

    Returns:
        attempts (int): 1-based candidate comparisons performed.
        elapsed_ms (float): Wall-clock CPU time in milliseconds.
    """
    length = len(target)
    target_digest = hashlib.sha256(target.encode("ascii")).digest()
    attempts = 0

    t_start = time.perf_counter_ns()
    for candidate_tuple in itertools.product(alphabet, repeat=length):
        attempts += 1
        candidate_bytes = "".join(candidate_tuple).encode("ascii")
        if hashlib.sha256(candidate_bytes).digest() == target_digest:
            break
    t_end = time.perf_counter_ns()

    elapsed_ms = (t_end - t_start) / 1_000_000.0
    return attempts, elapsed_ms


def run_calibrated_benchmark(alphabet: str) -> float:
    """Benchmark raw single-core hashing throughput to measure baseline speed."""
    target = alphabet[len(alphabet) // 2] * 3
    target_digest = hashlib.sha256(target.encode("ascii")).digest()
    attempts = 0
    t0 = time.perf_counter()
    for c in itertools.product(alphabet, repeat=3):
        attempts += 1
        if hashlib.sha256("".join(c).encode("ascii")).digest() == target_digest:
            break
        if attempts >= 100_000:
            break
    t1 = time.perf_counter()
    duration = max(t1 - t0, 1e-6)
    return attempts / duration


def main() -> None:
    parser = argparse.ArgumentParser(
        description="2-Axis Experimental Data Collection for MT2013 (Length L and Complexity K)."
    )
    parser.add_argument(
        "--samples-fast",
        type=int,
        default=60,
        help="Number of trials per group for fast search spaces (N <= 500,000; default: 60).",
    )
    parser.add_argument(
        "--samples-heavy",
        type=int,
        default=20,
        help="Number of trials for large search spaces (K=62, K=70 at L=4; default: 20).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=202610,
        help="Master random seed for full experiment reproducibility (default: 202610).",
    )
    args = parser.parse_args()
    if min(args.samples_fast, args.samples_heavy) < 2:
        parser.error("--samples-fast and --samples-heavy must each be at least 2")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    rng = random.Random(args.seed)

    print("=" * 75)
    print("MT2013 - CC09 | 2-Factor Experimental Data Collection (L and K)")
    print("=" * 75)
    print(f"Random seed:          {args.seed}")
    print(f"Fast groups samples:  {args.samples_fast} per group")
    print(f"Heavy groups samples: {args.samples_heavy} per group")
    print("-" * 75)

    # 1. Warm-up and baseline throughput
    full_chars = CHARSETS["full"]["chars"]
    baseline_hps = run_calibrated_benchmark(full_chars)
    print(f"System Baseline Hash Rate: {baseline_hps:,.0f} SHA-256 hashes/sec")
    print("-" * 75)

    # Define unique experimental groups across both axes
    groups = [
        # Axis 1: Length Effect on Full Charset (K = 70)
        ("full", 1, "axis1_length"),
        ("full", 2, "axis1_length"),
        ("full", 3, "axis1_length"),
        # Axis 2: Charset Complexity Effect at Fixed Length (L = 4)
        ("digits", 4, "axis2_charset"),
        ("lowercase", 4, "axis2_charset"),
        ("alphanumeric", 4, "axis2_charset"),
        # Shared between Axis 1 (L=4) and Axis 2 (Full complexity K=70)
        ("full", 4, "both"),
    ]

    fieldnames = [
        "obs_id",
        "axis",
        "charset_key",
        "charset_name",
        "charset_size",
        "length",
        "search_space",
        "trial_in_group",
        "target_sample",
        "attempts",
        "time_ms",
        "time_sec",
        "throughput_hash_s",
    ]

    all_rows = []
    obs_id = 0
    total_start = time.perf_counter()

    for charset_key, length, axis_tag in groups:
        c_info = CHARSETS[charset_key]
        alphabet = c_info["chars"]
        K = c_info["K"]
        search_space = K ** length
        n_samples = (
            args.samples_heavy if search_space > HEAVY_SEARCH_SPACE_THRESHOLD else args.samples_fast
        )

        print(
            f"Collecting: [{c_info['name']:<35}] L={length} | "
            f"Space N = {search_space:>10,} | n = {n_samples:>2} ...",
            end="",
            flush=True,
        )

        g_start = time.perf_counter()
        for trial in range(1, n_samples + 1):
            obs_id += 1
            # Sample target uniformly at random from keyspace K^L
            target = "".join(rng.choices(alphabet, k=length))
            attempts, elapsed_ms = run_single_trial(target, alphabet)
            elapsed_sec = elapsed_ms / 1000.0
            throughput = (attempts / elapsed_sec) if elapsed_sec > 0 else 0.0

            all_rows.append(
                {
                    "obs_id": obs_id,
                    "axis": axis_tag,
                    "charset_key": charset_key,
                    "charset_name": c_info["name"],
                    "charset_size": K,
                    "length": length,
                    "search_space": search_space,
                    "trial_in_group": trial,
                    "target_sample": f"'{target}",
                    "attempts": attempts,
                    "time_ms": round(elapsed_ms, 6),
                    "time_sec": round(elapsed_sec, 9),
                    "throughput_hash_s": round(throughput, 1),
                }
            )

        g_elapsed = time.perf_counter() - g_start
        print(f" Done ({g_elapsed:.2f}s)")

    total_duration = time.perf_counter() - total_start
    print("-" * 75)
    print(f"Data collection completed in {total_duration:.2f}s | Total observations: {len(all_rows)}")

    # Write output CSVs
    raw_path = os.path.join(data_dir, "raw_experiment_data.csv")
    ext_path = os.path.join(data_dir, "extended_multicharset_results.csv")

    for path in (raw_path, ext_path):
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

    # Save log and config
    config_log = {
        "hardware_environment": get_hardware_environment(),
        "baseline_hash_rate_hps": round(baseline_hps, 1),
        "parameters": {
            "samples_fast": args.samples_fast,
            "samples_heavy": args.samples_heavy,
            "random_seed": args.seed,
            "total_observations": len(all_rows),
        },
        "groups_surveyed": [
            {
                "charset": g[0],
                "K": CHARSETS[g[0]]["K"],
                "L": g[1],
                "axis": g[2],
                "search_space": CHARSETS[g[0]]["K"] ** g[1],
            }
            for g in groups
        ],
        "total_runtime_seconds": round(total_duration, 2),
    }

    log_path = os.path.join(logs_dir, "experiment_config.json")
    with open(log_path, mode="w", encoding="utf-8") as f:
        json.dump(config_log, f, indent=2)

    print(f"Saved: {raw_path}")
    print(f"Saved: {ext_path}")
    print(f"Saved: {log_path}")
    print("=" * 75)


if __name__ == "__main__":
    main()

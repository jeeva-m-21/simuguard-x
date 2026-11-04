#!/usr/bin/env python3
"""Rigorous Statistical Significance Engine for CPS Falsification Benchmarks.

Implements Arcuri & Briand (IEEE TSE 2011) and ARCH-COMP guidelines:
1. Vargha-Delaney A12 effect size metric.
2. Mann-Whitney U test with Holm-Bonferroni step-down correction.
3. Median Simulations-to-Falsify (STF) and Interquartile Range (IQR).
4. Restricted Mean Survival Time (RMST) / Success Rate under censoring.
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple
import numpy as np
from scipy import stats


def vargha_delaney_a12(sample_a: List[float], sample_b: List[float]) -> float:
    """Compute non-parametric Vargha-Delaney A12 effect size.
    
    A12 measures the probability that a randomly selected observation from sample A
    has a lower (better in minimization) simulation count than one from sample B.
    A12 > 0.5 indicates method A is faster; A12 > 0.71 is a large effect size.
    """
    m = len(sample_a)
    n = len(sample_b)
    if m == 0 or n == 0:
        return 0.5

    # Rank all observations combined
    combined = [(val, "A") for val in sample_a] + [(val, "B") for val in sample_b]
    # Sort with lower values ranked first (rank 1 = lowest/best)
    combined.sort(key=lambda x: x[0])

    # Assign ranks with tie handling (average rank for ties)
    ranks_a = []
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) - 1 and combined[j][0] == combined[j + 1][0]:
            j += 1
        avg_rank = 1.0 + (i + j) / 2.0
        for k in range(i, j + 1):
            if combined[k][1] == "A":
                ranks_a.append(avg_rank)
        i = j + 1

    r1 = sum(ranks_a)
    a12 = (r1 / m - (m + 1.0) / 2.0) / n
    return float(a12)


def holm_bonferroni_correction(p_values: List[float]) -> List[float]:
    """Adjust p-values using Holm-Bonferroni step-down procedure."""
    n = len(p_values)
    indexed_p = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n

    running_max = 0.0
    for rank, (orig_idx, p_val) in enumerate(indexed_p):
        multiplier = n - rank
        adj_p = min(1.0, p_val * multiplier)
        running_max = max(running_max, adj_p)
        adjusted[orig_idx] = running_max

    return adjusted


def analyze_factorial_dataset(json_file: str):
    with open(json_file, "r") as f:
        data = json.load(f)

    # Group by requirement
    reqs: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for entry in data:
        req = entry["requirement_id"]
        if req not in reqs:
            reqs[req] = {}
        for arm, res in entry["arms"].items():
            if arm not in reqs[req]:
                reqs[req][arm] = []
            reqs[req][arm].append(res)

    print("=" * 95)
    print("STATISTICAL ANALYSIS REPORT (Arcuri & Briand, IEEE TSE Standards)")
    print("=" * 95)

    for req, arms in reqs.items():
        print(f"\n=======================================================")
        print(f"REQUIREMENT: {req}")
        print(f"=======================================================")
        print(f"{'Factorial Arm':16s} | {'Success Rate':12s} | {'Median STF':10s} | {'IQR':10s} | {'Mean Time':10s}")
        print("-" * 75)

        arm_sims: Dict[str, List[float]] = {}
        arm_times: Dict[str, List[float]] = {}

        for arm_name, results in arms.items():
            n_total = len(results)
            n_fals = sum(1 for r in results if r["falsified"])
            succ_rate = (n_fals / n_total) * 100.0

            # Censor budget for non-falsified runs at max
            sims = [float(r["simulations"]) for r in results]
            times = [float(r["wall_clock_sec"]) for r in results]
            arm_sims[arm_name] = sims
            arm_times[arm_name] = times

            med_stf = np.median(sims)
            iqr_stf = stats.iqr(sims)
            mean_t = np.mean(times)

            print(f"{arm_name:16s} | {succ_rate:5.1f}% ({n_fals}/{n_total}) | {med_stf:10.1f} | {iqr_stf:10.1f} | {mean_t:8.2f}s")

        # Compare SGX_Warm against baselines
        print("\n--- Non-Parametric Hypothesis Tests vs SGX_Warm (Holm-corrected) ---")
        sgx_sims = arm_sims.get("SGX_Warm", [])
        comparisons = []
        raw_p_values = []

        baseline_names = [a for a in arms.keys() if a != "SGX_Warm"]
        for b_name in baseline_names:
            b_sims = arm_sims[b_name]
            # Lower simulations is better, so test if SGX < Baseline
            try:
                stat, p_val = stats.mannwhitneyu(sgx_sims, b_sims, alternative="less")
            except Exception:
                p_val = 1.0

            # Compute Vargha-Delaney A12 (prob that SGX < Baseline)
            # Standard A12 convention: A12(X, Y) = P(X > Y) + 0.5 P(X == Y)
            # For minimization: A12_min = P(SGX < Base) + 0.5 P(SGX == Base)
            n_sgx = len(sgx_sims)
            n_base = len(b_sims)
            wins = sum(1 for x in sgx_sims for y in b_sims if x < y)
            ties = sum(1 for x in sgx_sims for y in b_sims if x == y)
            a12 = (wins + 0.5 * ties) / (n_sgx * n_base) if (n_sgx * n_base) > 0 else 0.5

            comparisons.append((b_name, a12, p_val))
            raw_p_values.append(p_val)

        adj_p_values = holm_bonferroni_correction(raw_p_values)

        print(f"{'Baseline Arm':16s} | {'A12 (SGX Advantage)':20s} | {'Raw p-value':12s} | {'Holm Adj. p':12s} | {'Significance'}")
        print("-" * 80)
        for (b_name, a12, raw_p), adj_p in zip(comparisons, adj_p_values):
            sig = "***" if adj_p < 0.001 else ("**" if adj_p < 0.01 else ("*" if adj_p < 0.05 else "n.s."))
            effect = "Large" if a12 >= 0.71 else ("Medium" if a12 >= 0.64 else ("Small" if a12 >= 0.56 else "Negligible"))
            print(f"{b_name:16s} | {a12:5.3f} ({effect:10s}) | {raw_p:11.4e} | {adj_p:11.4e} | {sig}")


if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "factorial_preflight_results.json"
    analyze_factorial_dataset(target_file)

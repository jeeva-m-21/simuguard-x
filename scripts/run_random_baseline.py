#!/usr/bin/env python3
"""Uniform Random Testing Baseline Runner for ARCH-COMP Benchmarks.

Provides empirical ablation comparison against SimuGuard-X:
Evaluates AT1, AT2, and AT51 using naive uniform random input exploration.
"""

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

# Add src to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simuguard.benchmarks.interfaces import BENCHMARK_INTERFACES
from simuguard.benchmarks.requirements import AT_BENCHMARK_REQUIREMENTS
from simuguard.benchmarks.simulator import SimulinkSimulator
from simuguard.stl.evaluator import evaluate_trajectory_robustness


def run_random_falsifier(
    simulator: SimulinkSimulator,
    scenario_template: Dict[str, Any],
    stl_spec: Dict[str, Any],
    max_simulations: int = 50,
    seed: int = 42,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Execute Uniform Random Search on scenario parameter space."""
    rng = np.random.default_rng(seed)
    t_start = time.time()

    # Extract bounds and dimensions
    signals_bounds = []
    for sig in scenario_template.get("signals", []):
        knots = sig["time_knots"]
        bounds = sig.get("bounds", [[0.0, 100.0]] * len(knots))
        signals_bounds.append((sig["signal_name"], knots, bounds))

    best_rho = float("inf")
    falsified = False
    sims_executed = 0
    violation_time = None

    for sim_idx in range(1, max_simulations + 1):
        # Sample random scenario
        candidate_scenario = copy.deepcopy(scenario_template)
        for sig_idx, (name, knots, bounds) in enumerate(signals_bounds):
            vals = [rng.uniform(b[0], b[1]) for b in bounds]
            candidate_scenario["signals"][sig_idx]["values"] = vals

        trace = simulator.simulate(candidate_scenario)
        sims_executed += 1

        if not trace.is_valid:
            continue

        rob_res = evaluate_trajectory_robustness(trace.time, trace.signals, stl_spec)
        current_rho = rob_res.rho_post_exact

        if current_rho < best_rho:
            best_rho = current_rho

        if rob_res.is_falsified:
            falsified = True
            violation_time = rob_res.violation_time
            wall_clock = time.time() - t_start
            if verbose:
                print(f"  [Random Search] Falsified at simulation {sims_executed}! rho={current_rho:.4f}")
            return {
                "falsified": True,
                "simulations": sims_executed,
                "wall_clock_sec": wall_clock,
                "best_rho": best_rho,
                "violation_time": violation_time,
            }

    wall_clock = time.time() - t_start
    return {
        "falsified": False,
        "simulations": sims_executed,
        "wall_clock_sec": wall_clock,
        "best_rho": best_rho,
        "violation_time": None,
    }


def run_comparative_experiment(
    max_sims: int = 50,
    seed: int = 42,
    output_file: str = "baseline_comparison_results.json",
):
    print("=" * 85)
    print("SIMUGUARD-X vs. UNIFORM RANDOM BASELINE: ABLATION COMPARISON")
    print("=" * 85)
    print(f"Random Search Budget : {max_sims} simulations per requirement")
    print(f"Random Seed          : {seed}")
    print("-" * 85)

    # Load SimuGuard-X pilot suite results
    pilot_suite_file = Path("pilot_suite_results.json")
    if not pilot_suite_file.is_file():
        raise FileNotFoundError("pilot_suite_results.json not found. Run scripts/run_pilot_suite.py first.")

    with open(pilot_suite_file, "r") as f:
        simuguard_results = {r["requirement_id"]: r for r in json.load(f)}

    cache_dir = Path("cache")

    # Initialize headless Simulink engine
    print("\n[Simulink] Booting persistent MATLAB Engine session...")
    simulator = SimulinkSimulator(model_name="Autotrans_shift", use_fast_restart=True)

    comparison_records: List[Dict[str, Any]] = []

    try:
        for req_id, req_meta in AT_BENCHMARK_REQUIREMENTS.items():
            print(f"\n--- Running Random Search on {req_id} ---")
            cache_file = cache_dir / f"{req_id}_synthesis.json"
            if not cache_file.is_file():
                print(f"Missing cached synthesis for {req_id}, skipping...")
                continue

            with open(cache_file, "r") as f:
                synth = json.load(f)

            stl_spec = synth["track_a_stl"]
            scenario_spec = synth["track_b_scenario"]

            rand_res = run_random_falsifier(
                simulator=simulator,
                scenario_template=scenario_spec,
                stl_spec=stl_spec,
                max_simulations=max_sims,
                seed=seed,
                verbose=True,
            )

            sg_res = simuguard_results.get(req_id, {})

            # Compute comparative speedups
            sg_sims = sg_res.get("simulations", max_sims)
            rand_sims = rand_res["simulations"]

            sim_reduction = 0.0
            if rand_res["falsified"] and sg_res.get("falsified", False):
                sim_reduction = max(0.0, (rand_sims - sg_sims) / rand_sims * 100.0)
            elif not rand_res["falsified"] and sg_res.get("falsified", False):
                sim_reduction = 100.0  # Random failed within budget, SimuGuard-X succeeded

            rec = {
                "requirement_id": req_id,
                "category": req_meta["category"],
                "simuguard": {
                    "falsified": sg_res.get("falsified", False),
                    "simulations": sg_sims,
                    "wall_clock_sec": sg_res.get("wall_clock_sec", 0.0),
                    "best_rho": sg_res.get("robustness_rho", 0.0),
                    "gate2_confirmed": sg_res.get("gate2_confirmed", False),
                },
                "random_search": {
                    "falsified": rand_res["falsified"],
                    "simulations": rand_sims,
                    "wall_clock_sec": rand_res["wall_clock_sec"],
                    "best_rho": rand_res["best_rho"],
                },
                "simulation_reduction_pct": sim_reduction,
            }
            comparison_records.append(rec)

    finally:
        print("\n[Simulink] Closing MATLAB Engine session...")
        simulator.close()

    # Save to JSON
    out_path = Path(output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(comparison_records, f, indent=2)

    # Print IEEE TCAD Comparative Summary Table
    print("\n" + "=" * 95)
    print("IEEE TCAD EXPERIMENTAL TABLE: SIMUGUARD-X vs. UNIFORM RANDOM SEARCH")
    print("=" * 95)
    print(f"{'Req ID':<7} | {'SimuGuard-X (STF)':<18} | {'Random (STF)':<15} | {'SimuGuard-X Time':<18} | {'Random Time':<15} | {'Sim Reduction':<14}")
    print("-" * 95)

    for c in comparison_records:
        sg = c["simuguard"]
        rnd = c["random_search"]

        sg_stf_str = f"{sg['simulations']} (FALSIFIED)" if sg["falsified"] else f"{sg['simulations']} (SURVIVED)"
        rnd_stf_str = f"{rnd['simulations']} (FALSIFIED)" if rnd["falsified"] else f">{rnd['simulations']} (SURVIVED)"
        reduc_str = f"{c['simulation_reduction_pct']:.1f}% fewer sims" if sg["falsified"] else "N/A"

        print(
            f"{c['requirement_id']:<7} | "
            f"{sg_stf_str:<18} | "
            f"{rnd_stf_str:<15} | "
            f"{sg['wall_clock_sec']:<18.2f}s | "
            f"{rnd['wall_clock_sec']:<15.2f}s | "
            f"{reduc_str:<14}"
        )
    print("=" * 95)
    print(f"\nSaved comparative ablation results to: {out_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="SimuGuard-X vs Random Search Baseline")
    parser.add_argument("--sims", type=int, default=50, help="Max simulations for random baseline")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="baseline_comparison_results.json", help="Output JSON path")
    args = parser.parse_args()

    run_comparative_experiment(
        max_sims=args.sims,
        seed=args.seed,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run CMA-ES Falsification Search on MATLAB/Simulink Benchmarks."""

import argparse
import json
import os
import sys
from pathlib import Path
import numpy as np

# Add src to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simuguard.benchmarks.simulator import SimulinkSimulator
from simuguard.falsifier.optimizer import CMAESFalsifier


def run_falsification_study(
    req_id: str = "AT51",
    max_generations: int = 25,
    seed: int = 42,
    output_file: str = "falsification_results.json",
):
    print("=" * 70)
    print("SIMUGUARD-X: AUTOMATED NEURO-SYMBOLIC FALSIFICATION EXPERIMENT")
    print("=" * 70)
    print(f"Target Requirement : {req_id}")
    print(f"Algorithm          : CMA-ES with Theorem 3 Three-Regime Curriculum")
    print(f"Max Generations    : {max_generations}")
    print(f"Random Seed        : {seed}")
    print("-" * 70)

    pilot_file = Path("pilot_synthesis_results.json")
    if not pilot_file.is_file():
        raise FileNotFoundError(
            "pilot_synthesis_results.json not found. Run scripts/run_pilot.py first."
        )

    with open(pilot_file, "r") as f:
        pilot_data = json.load(f)

    scenario_template = pilot_data["track_b_scenario"]
    stl_spec = pilot_data["track_a_stl"]

    print(f"Loaded synthesized scenario template: {scenario_template.get('scenario_name')}")
    print(f"Target STL Formula: {stl_spec.get('stl_formula')}")
    print("-" * 70)

    # Initialize headless Simulink engine with FastRestart
    simulator = SimulinkSimulator(model_name="Autotrans_shift", use_fast_restart=True)

    try:
        falsifier = CMAESFalsifier(
            simulator=simulator,
            scenario_template=scenario_template,
            stl_spec=stl_spec,
            max_generations=max_generations,
            seed=seed,
        )

        res = falsifier.run(verbose=True)

        print("\n" + "=" * 70)
        print("EXPERIMENT SUMMARY")
        print("=" * 70)
        print(f"Status                  : {'FALSIFIED (Counterexample Found!)' if res.falsified else 'NOT FALSIFIED'}")
        print(f"Simulations Executed    : {res.simulations_count}")
        print(f"Regime 0 Inadmissible   : {res.regime_0_rejections} (Simulink calls saved)")
        print(f"Total Wall-Clock Time   : {res.wall_clock_time_sec:.2f} seconds")
        print(f"Best Regime Reached     : Regime {res.best_regime}")
        print(f"Best Precondition (rho) : {res.best_rho_pre:.4f}")
        print(f"Best Consequent (rho)   : {res.best_rho_post:.4f}")
        print("=" * 70)

        # Serialize results
        out_data = {
            "requirement_id": req_id,
            "falsified": res.falsified,
            "simulations_count": res.simulations_count,
            "regime_0_skips": res.regime_0_rejections,
            "wall_clock_time_sec": res.wall_clock_time_sec,
            "best_regime": res.best_regime,
            "best_rho_pre": res.best_rho_pre,
            "best_rho_post": res.best_rho_post,
            "best_parameters": res.best_candidate.tolist(),
            "history": res.convergence_history,
        }

        if res.gate2_result is not None:
            g2 = res.gate2_result
            out_data["gate2_verification"] = {
                "is_confirmed": g2.is_confirmed,
                "is_numerical_artifact": g2.is_numerical_artifact,
                "scr_baseline": g2.scr_baseline,
                "scr_tightened": g2.scr_tightened,
                "rho_baseline": g2.rho_baseline,
                "rho_tightened": g2.rho_tightened,
                "robustness_discrepancy": g2.robustness_discrepancy,
                "tightened_solver": g2.tightened_solver,
                "details": g2.details,
            }

        if res.counterexample_trace is not None:
            trace = res.counterexample_trace
            out_data["counterexample_summary"] = {
                "max_speed": float(np.max(trace.signals.get("speed", [0.0]))),
                "max_rpm": float(np.max(trace.signals.get("RPM", [0.0]))),
                "gears_reached": [float(g) for g in sorted(list(set(trace.signals.get("gear", []).tolist())))],
            }

        out_path = Path(output_file)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"\nSaved falsification report to: {out_path}")

    finally:
        simulator.close()


def main():
    parser = argparse.ArgumentParser(description="SimuGuard-X Falsification CLI")
    parser.add_argument("--req", type=str, default="AT51", help="Requirement ID")
    parser.add_argument("--gens", type=int, default=20, help="Max CMA-ES generations")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="falsification_results.json", help="Output path")
    args = parser.parse_args()

    run_falsification_study(
        req_id=args.req,
        max_generations=args.gens,
        seed=args.seed,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verification Script for Pillar 5 / Gate 2: Solver Integrity Verification."""

import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simuguard.benchmarks.simulator import SimulinkSimulator
from simuguard.solvers.integrity import (
    SolverIntegrityGate,
    compute_step_collapse_ratio,
)


def test_unit_scr():
    print("=" * 65)
    print("STEP 1: UNIT TESTING STEP-COLLAPSE RATIO (SCR)")
    print("=" * 65)

    # Test Case 1: Uniform steps (0.05s)
    t_uniform = np.linspace(0.0, 30.0, 601)
    scr_1, med_1, min_1 = compute_step_collapse_ratio(t_uniform)
    print(f"Test 1 (Uniform): Median dt={med_1:.4f}, Min dt={min_1:.4f}, SCR={scr_1:.2f}")
    assert abs(scr_1 - 1.0) < 1e-4, f"Expected SCR=1.0, got {scr_1}"

    # Test Case 2: Simulated solver collapse (chatter down to 1e-6)
    dt_collapsed = np.full(500, 0.05)
    dt_collapsed[250] = 1e-6  # Single localized step collapse
    t_collapsed = np.cumsum(np.insert(dt_collapsed, 0, 0.0))
    scr_2, med_2, min_2 = compute_step_collapse_ratio(t_collapsed)
    print(f"Test 2 (Step Collapse): Median dt={med_2:.4f}, Min dt={min_2:.6f}, SCR={scr_2:.2f}")
    assert scr_2 >= 1000.0, f"Expected SCR >= 1000, got {scr_2}"
    print("  --> SCR Unit tests PASSED successfully!\n")


def test_gate2_on_counterexample():
    print("=" * 65)
    print("STEP 2: INTEGRATION TEST - GATE 2 ON LIVE COUNTEREXAMPLE")
    print("=" * 65)

    fals_file = Path("falsification_results.json")
    pilot_file = Path("pilot_synthesis_results.json")
    if not fals_file.is_file() or not pilot_file.is_file():
        print("Required results files missing. Skipping integration test.")
        return

    with open(fals_file, "r") as f:
        fals_data = json.load(f)

    with open(pilot_file, "r") as f:
        pilot_data = json.load(f)

    stl_spec = pilot_data["track_a_stl"]
    scenario_template = pilot_data["track_b_scenario"]
    best_params = fals_data["best_parameters"]

    print(f"Requirement ID     : {fals_data['requirement_id']}")
    print(f"Target Formula     : {stl_spec['stl_formula']}")
    print(f"Baseline Falsified : {fals_data['falsified']}")
    print(f"Baseline rho_post  : {fals_data['best_rho_post']:.4f}")

    # Reconstruct counterexample scenario
    counterexample_scenario = json.loads(json.dumps(scenario_template))
    idx = 0
    for sig in counterexample_scenario.get("signals", []):
        n = len(sig["time_knots"])
        sig["values"] = best_params[idx : idx + n]
        idx += n

    # Initialize simulator
    simulator = SimulinkSimulator(model_name="Autotrans_shift", use_fast_restart=True)
    try:
        # 1. Simulate baseline
        print("\nSimulating baseline candidate...")
        baseline_trace = simulator.simulate(counterexample_scenario)
        assert baseline_trace.is_valid, "Baseline simulation failed"

        # 2. Run Gate 2 Verification
        gate = SolverIntegrityGate(
            stiff_solver="ode15s",
            tight_reltol="1e-7",
            tight_abstol="1e-9",
            delta_tol=0.05,
        )

        res = gate.verify_counterexample(
            simulator=simulator,
            scenario_spec=counterexample_scenario,
            baseline_trace=baseline_trace,
            stl_spec=stl_spec,
        )

        print("\n" + "=" * 65)
        print("GATE 2 VERIFICATION OUTCOME")
        print("=" * 65)
        print(f"Confirmed Genuine   : {res.is_confirmed}")
        print(f"Numerical Artifact  : {res.is_numerical_artifact}")
        print(f"Baseline Robustness : {res.rho_baseline:.4f}")
        print(f"Tightened Robustness: {res.rho_tightened:.4f}")
        print(f"Discrepancy (Drift) : {res.robustness_discrepancy:.4f}")
        print(f"Baseline SCR        : {res.scr_baseline:.2f}")
        print(f"Tightened SCR       : {res.scr_tightened:.2f}")
        print(f"Certification Note  : {res.details}")
        print("=" * 65)

    finally:
        simulator.close()


if __name__ == "__main__":
    test_unit_scr()
    test_gate2_on_counterexample()

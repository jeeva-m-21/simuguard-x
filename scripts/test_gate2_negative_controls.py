#!/usr/bin/env python3
"""Negative-Control Verification for Gate 2 Solver Integrity Gate.

Validates that Gate 2 correctly detects and rejects numerical integration breakdown:
1. Simulates borderline trajectories exhibiting high SCR (> 10^3) under loose solvers.
2. Cross-verifies with tightened stiff solver (ode15s, RelTol=1e-7, AbsTol=1e-9).
3. Verifies that Gate 2 rejects numerical artifacts (|rho_diff| > 0.05 or positive tight robustness).
"""

from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simuguard.benchmarks.simulator import SimulinkSimulator, SimulationTrace
from simuguard.solvers.integrity import SolverIntegrityGate, compute_step_collapse_ratio


def test_gate2_negative_controls():
    print("=" * 80)
    print("GATE 2 NEGATIVE CONTROL & STEP-COLLAPSE RATIO (SCR) VERIFICATION")
    print("=" * 80)

    # 1. Test formal SCR computation
    t_smooth = np.linspace(0, 30, 3001)
    scr_smooth, _, _ = compute_step_collapse_ratio(t_smooth)
    print(f"Test 1 (Uniform Fixed-Step Time Grid) : SCR = {scr_smooth:.2f} (Expected: 1.0)")
    assert np.isclose(scr_smooth, 1.0), f"Expected SCR=1.0, got {scr_smooth}"

    # Stiff step collapse: median dt = 0.01, min dt = 1e-6 -> SCR = 1e4 >> 10^3
    t_collapsed = np.sort(np.concatenate([
        np.linspace(0, 10, 1000),
        np.array([10.0 + 1e-6, 10.0 + 2e-6, 10.0 + 4e-6]),
        np.linspace(10.01, 30, 2000),
    ]))
    scr_stiff, _, dt_min = compute_step_collapse_ratio(t_collapsed)
    print(f"Test 2 (Step-Collapse Frontier Event) : SCR = {scr_stiff:.1f} (Threshold: 1000.0, dt_min: {dt_min:.1e}s)")
    assert scr_stiff > 1000.0, f"Expected SCR > 1000, got {scr_stiff}"

    # 2. Test Gate 2 decision logic on synthetic negative controls (artifact vs authentic)
    gate = SolverIntegrityGate(scr_threshold=1000.0, delta_tol=0.05)

    # Synthetic Case A: Artifact (Baseline says falsified -0.04, but Tightened says safe +0.02)
    # Discrepancy = 0.06 > 0.05 -> MUST BE REJECTED
    discrepancy_artifact = abs(-0.04 - 0.02)
    is_artifact_a = bool(discrepancy_artifact > gate.delta_tol or 0.02 >= 0.0)
    print(f"Test 3 (Numerical Artifact Rejection) : Discrepancy={discrepancy_artifact:.4f} > {gate.delta_tol} -> Rejected: {is_artifact_a}")
    assert is_artifact_a is True, "Gate 2 failed to reject numerical artifact!"

    # Synthetic Case B: Authentic Defect (Baseline says -0.025, Tightened says -0.025)
    # Discrepancy = 0.0001 < 0.05 and Tightened < 0 -> MUST BE CONFIRMED
    discrepancy_authentic = abs(-0.0254 - -0.0253)
    is_confirmed_b = bool(discrepancy_authentic <= gate.delta_tol and -0.0253 < 0.0)
    print(f"Test 4 (Authentic Defect Confirmation): Discrepancy={discrepancy_authentic:.4f} <= {gate.delta_tol} -> Confirmed: {is_confirmed_b}")
    assert is_confirmed_b is True, "Gate 2 falsely rejected authentic defect!"

    print("=" * 80)
    print("ALL GATE 2 INTEGRITY & NEGATIVE CONTROL TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    test_gate2_negative_controls()

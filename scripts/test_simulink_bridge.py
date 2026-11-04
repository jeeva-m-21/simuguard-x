#!/usr/bin/env python3
"""End-to-End Test: Load synthesized scenario and simulate in MATLAB/Simulink."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simuguard.benchmarks.simulator import SimulinkSimulator
from simuguard.stl.smooth_robustness import normalize_predicate_robustness, smooth_robustness_always


def main():
    pilot_file = Path("pilot_synthesis_results.json")
    if not pilot_file.is_file():
        print("Please run scripts/run_pilot.py first to generate pilot_synthesis_results.json")
        return

    with open(pilot_file, "r") as f:
        pilot_data = json.load(f)

    scenario = pilot_data["track_b_scenario"]
    stl_data = pilot_data["track_a_stl"]

    print("=" * 65)
    print("SIMUGUARD-X: SIMULINK CLOSED-LOOP EXECUTION TEST")
    print("=" * 65)
    print(f"Scenario Name: {scenario['scenario_name']}")
    print(f"Interpolation: {scenario['interpolation_type']}")
    print("-" * 65)

    simulator = SimulinkSimulator(model_name="Autotrans_shift")
    try:
        print("\nExecuting simulation via MATLAB Engine...")
        trace = simulator.simulate(scenario, sim_time=30.0, sample_time=0.05)
        
        if not trace.is_valid:
            print(f"Simulation failed: {trace.error_message}")
            return

        print("\nSimulation Succeeded!")
        print(f"Total time steps: {len(trace.time)}")
        speed = trace.signals["speed"]
        rpm = trace.signals["RPM"]
        gear = trace.signals["gear"]

        print(f"Speed range : {speed.min():.1f} - {speed.max():.1f} km/h")
        print(f"RPM range   : {rpm.min():.1f} - {rpm.max():.1f} RPM")
        print(f"Gears used  : {sorted(list(set(gear.tolist())))}")

        # Evaluate STL predicate: speed <= 120 or speed > 100
        print("\n" + "-" * 65)
        print("EVALUATING STL ROBUSTNESS ON SIMULINK TRACE")
        print("-" * 65)
        
        # Check mu_1 (speed > 100)
        p1_norm = [
            normalize_predicate_robustness(s, threshold=100.0, span_delta=180.0, operator=">")
            for s in speed
        ]
        exact_min = min(p1_norm)
        smooth_val = smooth_robustness_always(p1_norm)
        
        print(f"Predicate (speed > 100):")
        print(f"  Exact min normalized robustness: {exact_min:.4f}")
        print(f"  Theorem 2 Smooth robustness   : {smooth_val:.4f}")
        print(f"  Max vehicle speed observed    : {speed.max():.2f} km/h")
        print("=" * 65)

    finally:
        simulator.close()


if __name__ == "__main__":
    main()

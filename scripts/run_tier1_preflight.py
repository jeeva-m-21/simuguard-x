#!/usr/bin/env python3
"""Tier 1 Pre-Flight Experiment: Fair Same-Search-Space Comparison Across 5 Optimizers.

Evaluates 5 optimizers on the exact same low-rank Scenario DSL across 3 seeds:
1. SimuGuard-X (Theorem 3 Lexicographic Curriculum + LLM Warm Start)
2. Deb-Constrained CMA-ES (Deb's Feasibility Tournament Rules + Uniform Start)
3. Dokhanchi Vacuity-Aware CMA-ES (min(rho_post, rho_pre + C_pre) + Uniform Start)
4. Plain CMA-ES (Classical Max-Min STL Robustness + Uniform Start)
5. Random Search (Uniform Random Exploration on same DSL bounds)
"""

import copy
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict, List
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simuguard.benchmarks.requirements import AT_BENCHMARK_REQUIREMENTS
from simuguard.benchmarks.simulator import SimulinkSimulator
from simuguard.falsifier.optimizer import CMAESFalsifier
from simuguard.falsifier.baselines import (
    DebConstrainedCMAES,
    DokhanchiVacuityCMAES,
    PlainCMAES,
    RandomSearchBaseline,
)


def run_preflight(
    req_ids: List[str] = ["AT1", "AT2", "AT51"],
    seeds: List[int] = [42, 43, 44],
    max_generations: int = 15,
    max_sims_per_run: int = 80,
    output_file: str = "tier1_preflight_results.json",
):
    print("=" * 90)
    print("TIER 1 PRE-FLIGHT: FAIR SAME-SEARCH-SPACE BENCHMARK (5 OPTIMIZERS)")
    print("=" * 90)
    print(f"Target Requirements  : {req_ids}")
    print(f"Evaluation Seeds     : {seeds}")
    print(f"Budget per run       : {max_sims_per_run} simulations (max {max_generations} gens)")
    print("-" * 90)

    cache_dir = Path("cache")
    results = []

    # Boot persistent Simulink Engine with FastRestart
    simulator = SimulinkSimulator(model_name="Autotrans_shift", use_fast_restart=True)

    try:
        for req_id in req_ids:
            synthesis_file = cache_dir / f"{req_id}_synthesis.json"
            if not synthesis_file.is_file():
                print(f"[Error] Synthesis cache not found for {req_id}: {synthesis_file}")
                continue

            with open(synthesis_file, "r") as f:
                synth_data = json.load(f)

            scenario_template = synth_data["track_b_scenario"]
            stl_spec = synth_data["track_a_stl"]

            print(f"\n=======================================================", flush=True)
            print(f"EVALUATING REQUIREMENT: {req_id}", flush=True)
            print(f"Category: {AT_BENCHMARK_REQUIREMENTS[req_id]['category']}", flush=True)
            print(f"Formula : {stl_spec.get('stl_formula')}", flush=True)
            print(f"=======================================================", flush=True)

            for seed in seeds:
                print(f"\n--- Random Seed: {seed} ---", flush=True)

                # Method 1: SimuGuard-X (Lexicographic + Warm Start)
                opt_sg = CMAESFalsifier(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                )
                res_sg = opt_sg.run(verbose=False)
                print(f"  [SimuGuard-X]    Falsified: {str(res_sg.falsified):5s} | Sims: {res_sg.simulations_count:3d} | Best rho: {res_sg.best_rho_post:.4f} | Time: {res_sg.wall_clock_time_sec:.2f}s", flush=True)

                # Method 2: Deb-Constrained CMA-ES (Uniform Start + Deb Feasibility Rules)
                opt_deb = DebConstrainedCMAES(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                )
                res_deb = opt_deb.run(max_sims=max_sims_per_run, verbose=False)
                print(f"  [Deb-CMA-ES]     Falsified: {str(res_deb.falsified):5s} | Sims: {res_deb.simulations_count:3d} | Best rho: {res_deb.best_rho_post:.4f} | Time: {res_deb.wall_clock_time_sec:.2f}s", flush=True)

                # Method 3: Dokhanchi Vacuity-Aware CMA-ES (Uniform Start + C_pre = 0.5)
                opt_dok = DokhanchiVacuityCMAES(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    c_pre=0.5,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                )
                res_dok = opt_dok.run(max_sims=max_sims_per_run, verbose=False)
                print(f"  [Dokhanchi-CMA]  Falsified: {str(res_dok.falsified):5s} | Sims: {res_dok.simulations_count:3d} | Best rho: {res_dok.best_rho_post:.4f} | Time: {res_dok.wall_clock_time_sec:.2f}s", flush=True)

                # Method 4: Plain CMA-ES (Uniform Start + Classical STL Max-Min)
                opt_plain = PlainCMAES(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                )
                res_plain = opt_plain.run(max_sims=max_sims_per_run, verbose=False)
                print(f"  [Plain-CMA-ES]   Falsified: {str(res_plain.falsified):5s} | Sims: {res_plain.simulations_count:3d} | Best rho: {res_plain.best_rho_post:.4f} | Time: {res_plain.wall_clock_time_sec:.2f}s", flush=True)

                # Method 5: Random Search (Uniform Random Exploration on same DSL)
                opt_rnd = RandomSearchBaseline(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    seed=seed,
                    enable_gate2=True,
                )
                res_rnd = opt_rnd.run(max_sims=max_sims_per_run, verbose=False)
                print(f"  [Random Search]  Falsified: {str(res_rnd.falsified):5s} | Sims: {res_rnd.simulations_count:3d} | Best rho: {res_rnd.best_rho_post:.4f} | Time: {res_rnd.wall_clock_time_sec:.2f}s", flush=True)

                results.append({
                    "requirement_id": req_id,
                    "seed": seed,
                    "simuguard": {
                        "falsified": res_sg.falsified,
                        "simulations": res_sg.simulations_count,
                        "best_rho": res_sg.best_rho_post,
                        "wall_clock_sec": res_sg.wall_clock_time_sec,
                    },
                    "deb_cmaes": {
                        "falsified": res_deb.falsified,
                        "simulations": res_deb.simulations_count,
                        "best_rho": res_deb.best_rho_post,
                        "wall_clock_sec": res_deb.wall_clock_time_sec,
                    },
                    "dokhanchi_cmaes": {
                        "falsified": res_dok.falsified,
                        "simulations": res_dok.simulations_count,
                        "best_rho": res_dok.best_rho_post,
                        "wall_clock_sec": res_dok.wall_clock_time_sec,
                    },
                    "plain_cmaes": {
                        "falsified": res_plain.falsified,
                        "simulations": res_plain.simulations_count,
                        "best_rho": res_plain.best_rho_post,
                        "wall_clock_sec": res_plain.wall_clock_time_sec,
                    },
                    "random_search": {
                        "falsified": res_rnd.falsified,
                        "simulations": res_rnd.simulations_count,
                        "best_rho": res_rnd.best_rho_post,
                        "wall_clock_sec": res_rnd.wall_clock_time_sec,
                    },
                })

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print("\n" + "=" * 90)
        print(f"Pre-Flight Evaluation Completed! Results saved to {output_file}")
        print("=" * 90)

    finally:
        simulator.close()


if __name__ == "__main__":
    run_preflight()

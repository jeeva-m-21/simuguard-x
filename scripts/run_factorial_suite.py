#!/usr/bin/env python3
"""Full 2x2 Factorial & Init-Swap Falsification Suite across ARCH-COMP Benchmarks.

Ablation Matrix per Requirement & Seed:
1. SGX_Warm     : SimuGuard-X Lexicographic Curriculum + LLM Warm Start (Full System)
2. SGX_Cold     : SimuGuard-X Lexicographic Curriculum + Uniform Cold Start (Curriculum alone)
3. Deb_Warm     : Deb-Constrained CMA-ES + LLM Warm Start (Deb with Warm Start)
4. Deb_Cold     : Deb-Constrained CMA-ES + Uniform Cold Start (Pure Deb Baseline)
5. Dok_Cold     : Dokhanchi Vacuity-Aware CMA-ES (C_pre = 0.5) + Uniform Cold Start
6. Plain_Cold   : Standard CMA-ES (Classical Max-Min STL) + Uniform Cold Start
7. Random_Search: Uniform Random Sampling on Scenario DSL bounds
"""

import argparse
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


def run_suite(
    req_ids: List[str] = ["AT1", "AT2", "AT51"],
    seeds: List[int] = [42, 43, 44],
    max_generations: int = 15,
    max_sims_per_run: int = 150,
    output_file: str = "factorial_results.json",
):
    print("=" * 100, flush=True)
    print("SIMUGUARD-X: FULL 2x2 FACTORIAL & INIT-SWAP BENCHMARK SUITE", flush=True)
    print("=" * 100, flush=True)
    print(f"Target Requirements  : {req_ids}", flush=True)
    print(f"Evaluation Seeds     : {seeds} (Total seeds: {len(seeds)})", flush=True)
    print(f"Budget per run       : {max_sims_per_run} simulations (max {max_generations} gens)", flush=True)
    print("-" * 100, flush=True)

    cache_dir = Path("cache")
    all_results = []

    simulator = SimulinkSimulator(model_name="Autotrans_shift", use_fast_restart=True)

    try:
        for req_id in req_ids:
            synthesis_file = cache_dir / f"{req_id}_synthesis.json"
            if not synthesis_file.is_file():
                print(f"[Error] Synthesis cache not found for {req_id}: {synthesis_file}", flush=True)
                continue

            with open(synthesis_file, "r") as f:
                synth_data = json.load(f)

            scenario_template = synth_data["track_b_scenario"]
            stl_spec = synth_data["track_a_stl"]

            print(f"\n=================================================================", flush=True)
            print(f"BENCHMARK SPECIFICATION: {req_id}", flush=True)
            print(f"Category: {AT_BENCHMARK_REQUIREMENTS[req_id]['category']}", flush=True)
            print(f"Formula : {stl_spec.get('stl_formula')}", flush=True)
            print(f"=================================================================", flush=True)

            for seed in seeds:
                print(f"\n>>> Running Seed: {seed} on {req_id} <<<", flush=True)
                seed_record = {
                    "requirement_id": req_id,
                    "seed": seed,
                    "arms": {},
                }

                # Arm 1: Full SimuGuard-X (Curriculum + Warm Start)
                opt_sg_warm = CMAESFalsifier(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                    use_uniform_init=False,
                )
                res_sg_warm = opt_sg_warm.run(verbose=False)
                seed_record["arms"]["SGX_Warm"] = {
                    "falsified": res_sg_warm.falsified,
                    "simulations": res_sg_warm.simulations_count,
                    "sims_to_first_trigger": res_sg_warm.sims_to_first_trigger,
                    "sims_post_trigger": res_sg_warm.sims_post_trigger,
                    "best_rho": res_sg_warm.best_rho_post,
                    "wall_clock_sec": res_sg_warm.wall_clock_time_sec,
                }
                print(f"  [1. SGX_Warm]     Falsified: {str(res_sg_warm.falsified):5s} | Sims: {res_sg_warm.simulations_count:3d} (Trig: {res_sg_warm.sims_to_first_trigger:2d}, Post: {res_sg_warm.sims_post_trigger:2d}) | rho: {res_sg_warm.best_rho_post:.4f} | Time: {res_sg_warm.wall_clock_time_sec:.2f}s", flush=True)

                # Arm 2: SimuGuard-X Curriculum Alone (Curriculum + Uniform Cold Start)
                opt_sg_cold = CMAESFalsifier(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                    use_uniform_init=True,
                )
                res_sg_cold = opt_sg_cold.run(verbose=False)
                seed_record["arms"]["SGX_Cold"] = {
                    "falsified": res_sg_cold.falsified,
                    "simulations": res_sg_cold.simulations_count,
                    "sims_to_first_trigger": res_sg_cold.sims_to_first_trigger,
                    "sims_post_trigger": res_sg_cold.sims_post_trigger,
                    "best_rho": res_sg_cold.best_rho_post,
                    "wall_clock_sec": res_sg_cold.wall_clock_time_sec,
                }
                print(f"  [2. SGX_Cold]     Falsified: {str(res_sg_cold.falsified):5s} | Sims: {res_sg_cold.simulations_count:3d} (Trig: {res_sg_cold.sims_to_first_trigger:2d}, Post: {res_sg_cold.sims_post_trigger:2d}) | rho: {res_sg_cold.best_rho_post:.4f} | Time: {res_sg_cold.wall_clock_time_sec:.2f}s", flush=True)

                # Arm 3: Deb-Constrained CMA-ES with LLM Warm Start (Deb + Warm)
                opt_deb_warm = DebConstrainedCMAES(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                    use_warm_start=True,
                )
                res_deb_warm = opt_deb_warm.run(max_sims=max_sims_per_run, verbose=False)
                seed_record["arms"]["Deb_Warm"] = {
                    "falsified": res_deb_warm.falsified,
                    "simulations": res_deb_warm.simulations_count,
                    "sims_to_first_trigger": res_deb_warm.sims_to_first_trigger,
                    "sims_post_trigger": res_deb_warm.sims_post_trigger,
                    "best_rho": res_deb_warm.best_rho_post,
                    "wall_clock_sec": res_deb_warm.wall_clock_time_sec,
                }
                print(f"  [3. Deb_Warm]     Falsified: {str(res_deb_warm.falsified):5s} | Sims: {res_deb_warm.simulations_count:3d} (Trig: {res_deb_warm.sims_to_first_trigger:2d}, Post: {res_deb_warm.sims_post_trigger:2d}) | rho: {res_deb_warm.best_rho_post:.4f} | Time: {res_deb_warm.wall_clock_time_sec:.2f}s", flush=True)

                # Arm 4: Deb-Constrained CMA-ES with Uniform Cold Start (Pure Deb)
                opt_deb_cold = DebConstrainedCMAES(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                    use_warm_start=False,
                )
                res_deb_cold = opt_deb_cold.run(max_sims=max_sims_per_run, verbose=False)
                seed_record["arms"]["Deb_Cold"] = {
                    "falsified": res_deb_cold.falsified,
                    "simulations": res_deb_cold.simulations_count,
                    "sims_to_first_trigger": res_deb_cold.sims_to_first_trigger,
                    "sims_post_trigger": res_deb_cold.sims_post_trigger,
                    "best_rho": res_deb_cold.best_rho_post,
                    "wall_clock_sec": res_deb_cold.wall_clock_time_sec,
                }
                print(f"  [4. Deb_Cold]     Falsified: {str(res_deb_cold.falsified):5s} | Sims: {res_deb_cold.simulations_count:3d} (Trig: {res_deb_cold.sims_to_first_trigger:2d}, Post: {res_deb_cold.sims_post_trigger:2d}) | rho: {res_deb_cold.best_rho_post:.4f} | Time: {res_deb_cold.wall_clock_time_sec:.2f}s", flush=True)

                # Arm 5: Dokhanchi Vacuity-Aware CMA-ES (C_pre = 0.5, Cold Start)
                opt_dok_cold = DokhanchiVacuityCMAES(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    c_pre=0.5,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                    use_warm_start=False,
                )
                res_dok_cold = opt_dok_cold.run(max_sims=max_sims_per_run, verbose=False)
                seed_record["arms"]["Dok_Cold"] = {
                    "falsified": res_dok_cold.falsified,
                    "simulations": res_dok_cold.simulations_count,
                    "sims_to_first_trigger": res_dok_cold.sims_to_first_trigger,
                    "sims_post_trigger": res_dok_cold.sims_post_trigger,
                    "best_rho": res_dok_cold.best_rho_post,
                    "wall_clock_sec": res_dok_cold.wall_clock_time_sec,
                }
                print(f"  [5. Dok_Cold]     Falsified: {str(res_dok_cold.falsified):5s} | Sims: {res_dok_cold.simulations_count:3d} (Trig: {res_dok_cold.sims_to_first_trigger:2d}, Post: {res_dok_cold.sims_post_trigger:2d}) | rho: {res_dok_cold.best_rho_post:.4f} | Time: {res_dok_cold.wall_clock_time_sec:.2f}s", flush=True)

                # Arm 6: Plain CMA-ES (Classical Max-Min STL, Cold Start)
                opt_plain_cold = PlainCMAES(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    max_generations=max_generations,
                    seed=seed,
                    enable_gate2=True,
                    use_warm_start=False,
                )
                res_plain_cold = opt_plain_cold.run(max_sims=max_sims_per_run, verbose=False)
                seed_record["arms"]["Plain_Cold"] = {
                    "falsified": res_plain_cold.falsified,
                    "simulations": res_plain_cold.simulations_count,
                    "sims_to_first_trigger": res_plain_cold.sims_to_first_trigger,
                    "sims_post_trigger": res_plain_cold.sims_post_trigger,
                    "best_rho": res_plain_cold.best_rho_post,
                    "wall_clock_sec": res_plain_cold.wall_clock_time_sec,
                }
                print(f"  [6. Plain_Cold]   Falsified: {str(res_plain_cold.falsified):5s} | Sims: {res_plain_cold.simulations_count:3d} (Trig: {res_plain_cold.sims_to_first_trigger:2d}, Post: {res_plain_cold.sims_post_trigger:2d}) | rho: {res_plain_cold.best_rho_post:.4f} | Time: {res_plain_cold.wall_clock_time_sec:.2f}s", flush=True)

                # Arm 7: Random Search (Uniform Exploration on Scenario DSL)
                opt_rnd = RandomSearchBaseline(
                    simulator=simulator,
                    scenario_template=scenario_template,
                    stl_spec=stl_spec,
                    seed=seed,
                    enable_gate2=True,
                )
                res_rnd = opt_rnd.run(max_sims=max_sims_per_run, verbose=False)
                seed_record["arms"]["Random_Search"] = {
                    "falsified": res_rnd.falsified,
                    "simulations": res_rnd.simulations_count,
                    "sims_to_first_trigger": res_rnd.sims_to_first_trigger,
                    "sims_post_trigger": res_rnd.sims_post_trigger,
                    "best_rho": res_rnd.best_rho_post,
                    "wall_clock_sec": res_rnd.wall_clock_time_sec,
                }
                print(f"  [7. Random_Search]Falsified: {str(res_rnd.falsified):5s} | Sims: {res_rnd.simulations_count:3d} (Trig: {res_rnd.sims_to_first_trigger:2d}, Post: {res_rnd.sims_post_trigger:2d}) | rho: {res_rnd.best_rho_post:.4f} | Time: {res_rnd.wall_clock_time_sec:.2f}s", flush=True)

                all_results.append(seed_record)

                # Persist intermediate results incrementally after every seed
                with open(output_file, "w") as f:
                    json.dump(all_results, f, indent=2)

        print("\n" + "=" * 100, flush=True)
        print(f"Experiment Suite Completed! All results saved to {output_file}", flush=True)
        print("=" * 100, flush=True)

    finally:
        simulator.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 2x2 Factorial Suite")
    parser.add_argument("--reqs", type=str, nargs="+", default=["AT1", "AT2", "AT51"], help="Requirement IDs to evaluate")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44], help="Random seeds to evaluate")
    parser.add_argument("--output", type=str, default="factorial_results.json", help="Output JSON file")
    parser.add_argument("--max-sims", type=int, default=150, help="Simulation budget per run")
    args = parser.parse_args()

    run_suite(req_ids=args.reqs, seeds=args.seeds, output_file=args.output, max_sims_per_run=args.max_sims)

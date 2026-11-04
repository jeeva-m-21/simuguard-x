#!/usr/bin/env python3
"""Run Full Automatic Transmission Benchmark Pilot Suite (AT1, AT2, AT51).

Executes neuro-symbolic specification synthesis, CMA-ES falsification with Theorem 3
three-regime curriculum, and Gate 2 solver integrity verification across all target specs.
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
from simuguard.config import DEFAULT_MODEL
from simuguard.falsifier.optimizer import CMAESFalsifier
from simuguard.llm.client import FireworksClient
from simuguard.llm.parser import extract_json
from simuguard.llm.prompts import build_track_a_stl_prompt, build_track_b_scenario_prompt


def get_or_synthesize_spec(
    client: FireworksClient,
    req_id: str,
    req_meta: Dict[str, Any],
    cache_dir: Path,
) -> Dict[str, Any]:
    """Retrieve cached neuro-symbolic synthesis or query Fireworks AI."""
    cache_file = cache_dir / f"{req_id}_synthesis.json"
    if cache_file.is_file():
        print(f"[{req_id}] Loading cached neuro-symbolic synthesis from {cache_file.name}")
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[{req_id}] Synthesizing STL (Track A) & Scenario DSL (Track B) via Fireworks...")
    model_bench = req_meta["model"]
    interface = BENCHMARK_INTERFACES[model_bench]
    req_text = req_meta["text"]

    # Track A: STL
    msgs_a = build_track_a_stl_prompt(req_text, model_bench, interface)
    res_a = client.chat_completion(msgs_a, json_mode=True, max_tokens=2048)
    stl_json = extract_json(res_a["content"])

    # Track B: Scenario DSL
    msgs_b = build_track_b_scenario_prompt(req_text, stl_json, model_bench, interface)
    res_b = client.chat_completion(msgs_b, json_mode=True, max_tokens=2048)
    scenario_json = extract_json(res_b["content"])

    total_cost = res_a["cost_usd"] + res_b["cost_usd"]
    total_tokens = res_a["total_tokens"] + res_b["total_tokens"]
    total_latency = res_a["latency_sec"] + res_b["latency_sec"]

    out = {
        "requirement_id": req_id,
        "track_a_stl": stl_json,
        "track_b_scenario": scenario_json,
        "llm_stats": {
            "total_tokens": total_tokens,
            "cost_usd": total_cost,
            "latency_sec": total_latency,
        },
    }

    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"[{req_id}] Synthesis complete! Tokens: {total_tokens} | Cost: ${total_cost:.5f} | Latency: {total_latency:.2f}s")
    return out


def run_suite(
    model_name: str = DEFAULT_MODEL,
    max_gens: int = 15,
    seed: int = 42,
    output_file: str = "pilot_suite_results.json",
):
    print("=" * 80)
    print("SIMUGUARD-X: AUTOMATIC TRANSMISSION BENCHMARK PILOT SUITE")
    print("=" * 80)
    print(f"Inference Model      : {model_name}")
    print(f"Target Requirements  : {list(AT_BENCHMARK_REQUIREMENTS.keys())}")
    print(f"Max Generations/Spec : {max_gens}")
    print(f"Random Seed          : {seed}")
    print("-" * 80)

    cache_dir = Path("cache")
    client = FireworksClient(default_model=model_name)

    # 1. Boot persistent Simulink Engine with FastRestart
    print("\n[Simulink] Booting persistent MATLAB Engine session...")
    simulator = SimulinkSimulator(model_name="Autotrans_shift", use_fast_restart=True)

    suite_results: List[Dict[str, Any]] = []

    try:
        for req_id, req_meta in AT_BENCHMARK_REQUIREMENTS.items():
            print("\n" + "=" * 80)
            print(f"EVALUATING REQUIREMENT: {req_id} ({req_meta['category']})")
            print(f"Specification: \"{req_meta['text']}\"")
            print("=" * 80)

            # Step 1: LLM Synthesis
            synth_data = get_or_synthesize_spec(client, req_id, req_meta, cache_dir)
            stl_spec = synth_data["track_a_stl"]
            scenario_spec = synth_data["track_b_scenario"]
            llm_stats = synth_data.get("llm_stats", {"cost_usd": 0.0, "total_tokens": 0})

            print(f"Formal Formula : {stl_spec.get('stl_formula')}")
            print(f"Scenario Name  : {scenario_spec.get('scenario_name')}")

            # Step 2: Falsification with CMA-ES & Theorem 3 Curriculum & Gate 2
            falsifier = CMAESFalsifier(
                simulator=simulator,
                scenario_template=scenario_spec,
                stl_spec=stl_spec,
                max_generations=max_gens,
                seed=seed,
                enable_gate2=True,
            )

            res = falsifier.run(verbose=True)

            # Collect metrics
            crit_signal = "N/A"
            crit_val = None
            if res.counterexample_trace is not None:
                signals = res.counterexample_trace.signals
                if req_id == "AT1":
                    crit_signal = "Max Speed (km/h)"
                    crit_val = float(np.max(signals.get("speed", [0.0])))
                elif req_id == "AT2":
                    crit_signal = "Max RPM"
                    crit_val = float(np.max(signals.get("RPM", [0.0])))
                elif req_id == "AT51":
                    crit_signal = "Gears Reached"
                    crit_val = sorted(list(set(signals.get("gear", []).tolist())))

            g2_confirmed = False
            g2_drift = 0.0
            if res.gate2_result:
                g2_confirmed = res.gate2_result.is_confirmed
                g2_drift = res.gate2_result.robustness_discrepancy

            item_result = {
                "requirement_id": req_id,
                "category": req_meta["category"],
                "formula": stl_spec.get("stl_formula"),
                "falsified": res.falsified,
                "simulations": res.simulations_count,
                "regime_0_skips": res.regime_0_rejections,
                "wall_clock_sec": res.wall_clock_time_sec,
                "robustness_rho": res.best_rho_post,
                "critical_signal": crit_signal,
                "critical_value": crit_val,
                "gate2_confirmed": g2_confirmed,
                "gate2_drift": g2_drift,
                "llm_tokens": llm_stats.get("total_tokens", 0),
                "llm_cost_usd": llm_stats.get("cost_usd", 0.0),
            }
            suite_results.append(item_result)

    finally:
        print("\n[Simulink] Closing MATLAB Engine session...")
        simulator.close()

    # Save consolidated JSON report
    out_path = Path(output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(suite_results, f, indent=2)

    # Output formatted IEEE TCAD Table
    print("\n" + "=" * 90)
    print("IEEE TCAD EXPERIMENTAL RESULTS SUMMARY: AUTOMATIC TRANSMISSION BENCHMARK")
    print("=" * 90)
    header = f"{'Req ID':<7} | {'Category':<22} | {'Status':<12} | {'Sims':<5} | {'WTTF (s)':<9} | {'rho*':<8} | {'Gate 2':<8} | {'Drift':<8}"
    print(header)
    print("-" * 90)
    for r in suite_results:
        status_str = "FALSIFIED" if r["falsified"] else "SURVIVED"
        gate_str = "CONFIRMED" if r["gate2_confirmed"] else "N/A"
        row = (
            f"{r['requirement_id']:<7} | "
            f"{r['category'][:22]:<22} | "
            f"{status_str:<12} | "
            f"{r['simulations']:<5} | "
            f"{r['wall_clock_sec']:<9.2f} | "
            f"{r['robustness_rho']:<8.4f} | "
            f"{gate_str:<8} | "
            f"{r['gate2_drift']:<8.5f}"
        )
        print(row)
    print("=" * 90)
    print(f"\nSaved consolidated pilot suite dataset to: {out_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="SimuGuard-X Pilot Benchmark Suite")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Fireworks model ID")
    parser.add_argument("--gens", type=int, default=15, help="Max CMA-ES generations")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output", type=str, default="pilot_suite_results.json", help="Output JSON path")
    args = parser.parse_args()

    run_suite(
        model_name=args.model,
        max_gens=args.gens,
        seed=args.seed,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()

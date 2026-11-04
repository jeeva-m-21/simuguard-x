#!/usr/bin/env python3
"""SimuGuard-X Pilot Runner.

Executes neuro-symbolic specification synthesis (Track A: STL, Track B: Scenario DSL)
using Fireworks AI serverless models.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to python path for clean package imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from simuguard.benchmarks.interfaces import BENCHMARK_INTERFACES
from simuguard.config import (
    DEFAULT_MODEL,
    DEFAULT_FLASH_MODEL,
    DEFAULT_REASONING_MODEL,
    FIREWORKS_API_KEY,
)
from simuguard.llm.client import FireworksClient
from simuguard.llm.parser import extract_json
from simuguard.llm.prompts import build_track_a_stl_prompt, build_track_b_scenario_prompt


SAMPLE_REQUIREMENTS = {
    "AT1": {
        "text": "The vehicle speed shall never exceed 120 km/h within 30 seconds of simulation.",
        "model": "Autotrans_shift",
    },
    "AT2": {
        "text": "The engine rotational speed (RPM) shall never exceed 4500 RPM within 30 seconds of simulation.",
        "model": "Autotrans_shift",
    },
    "AT51": {
        "text": (
            "Whenever vehicle speed exceeds 100 km/h, the transmission gear shall shift "
            "to 4th gear within 4 seconds and remain in 4th gear while speed is above 100 km/h."
        ),
        "model": "Autotrans_shift",
    },
}


def run_pilot(
    model_name: str,
    req_id: str,
    api_key: str | None = None,
    output_file: str | None = None,
) -> None:
    if req_id not in SAMPLE_REQUIREMENTS:
        raise ValueError(f"Unknown requirement '{req_id}'. Choose from: {list(SAMPLE_REQUIREMENTS.keys())}")

    req_data = SAMPLE_REQUIREMENTS[req_id]
    model_bench = req_data["model"]
    interface = BENCHMARK_INTERFACES[model_bench]

    print("=" * 70)
    print("SIMUGUARD-X: NEURO-SYMBOLIC SPECIFICATION & SCENARIO SYNTHESIS PILOT")
    print("=" * 70)
    print(f"Target Benchmark : {model_bench}")
    print(f"Requirement ID   : {req_id}")
    print(f"Requirement Text : {req_data['text']}")
    print(f"Inference Model  : {model_name}")
    print("-" * 70)

    client = FireworksClient(api_key=api_key, default_model=model_name)

    # ----------------------------------------------------
    # TRACK A: Formal STL Specification Synthesis
    # ----------------------------------------------------
    print("\n[Track A] Synthesizing Formal STL Specification...")
    track_a_messages = build_track_a_stl_prompt(req_data["text"], model_bench, interface)
    res_a = client.chat_completion(track_a_messages, model=model_name, temperature=0.0, json_mode=True)
    stl_json = extract_json(res_a["content"])

    print(f"  > Formula: {stl_json.get('stl_formula')}")
    print(f"  > Conditional: {stl_json.get('is_conditional')}")
    if stl_json.get("antecedent_formula"):
        print(f"  > Antecedent P: {stl_json.get('antecedent_formula')}")
        print(f"  > Consequent Q: {stl_json.get('consequent_formula')}")
    print(f"  > Tokens: {res_a['total_tokens']} | Cost: ${res_a['cost_usd']:.5f} | Latency: {res_a['latency_sec']:.2f}s")

    # ----------------------------------------------------
    # TRACK B: Low-Rank Scenario Parameterization DSL
    # ----------------------------------------------------
    print("\n[Track B] Synthesizing Low-Rank Scenario Parameterization Template...")
    track_b_messages = build_track_b_scenario_prompt(req_data["text"], stl_json, model_bench, interface)
    res_b = client.chat_completion(track_b_messages, model=model_name, temperature=0.0, json_mode=True)
    scenario_json = extract_json(res_b["content"])

    print(f"  > Scenario: {scenario_json.get('scenario_name')}")
    print(f"  > Interpolation: {scenario_json.get('interpolation_type')}")
    print(f"  > Signals: {[s.get('signal_name') for s in scenario_json.get('signals', [])]}")
    print(f"  > Tokens: {res_b['total_tokens']} | Cost: ${res_b['cost_usd']:.5f} | Latency: {res_b['latency_sec']:.2f}s")

    total_tokens = res_a["total_tokens"] + res_b["total_tokens"]
    total_cost = res_a["cost_usd"] + res_b["cost_usd"]
    total_latency = res_a["latency_sec"] + res_b["latency_sec"]

    print("\n" + "=" * 70)
    print("PILOT EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Total Tokens Used : {total_tokens}")
    print(f"Total USD Cost    : ${total_cost:.5f}")
    print(f"Total LLM Latency : {total_latency:.2f} seconds")
    print("=" * 70)

    pilot_result = {
        "requirement_id": req_id,
        "model_name": model_name,
        "track_a_stl": stl_json,
        "track_b_scenario": scenario_json,
        "performance": {
            "track_a_tokens": res_a["total_tokens"],
            "track_b_tokens": res_b["total_tokens"],
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "total_latency_sec": total_latency,
        },
    }

    if output_file:
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(pilot_result, f, indent=2)
        print(f"\nSaved pilot output to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="SimuGuard-X Pilot Test Runner")
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Fireworks model ID (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--req",
        type=str,
        default="AT51",
        choices=["AT1", "AT2", "AT51"],
        help="Target requirement ID (default: AT51)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Fireworks API Key (defaults to FIREWORKS_API_KEY from .env)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="pilot_synthesis_results.json",
        help="Path to save output JSON (default: pilot_synthesis_results.json)",
    )

    args = parser.parse_args()
    run_pilot(
        model_name=args.model,
        req_id=args.req,
        api_key=args.api_key,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()

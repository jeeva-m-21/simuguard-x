"""Prompt templates and builders for SimuGuard-X neuro-symbolic tracks."""

import json
from typing import Any, Dict


def build_track_a_stl_prompt(
    requirement_text: str,
    model_name: str,
    interface: Dict[str, Any],
) -> list[dict[str, str]]:
    """Build grounded prompt for Track A: Formal Signal Temporal Logic (STL) synthesis."""
    system_prompt = (
        "You are an expert formal methods engineer specializing in cyber-physical systems, "
        "Signal Temporal Logic (STL), and FRET semantics for MATLAB/Simulink models.\n"
        "Your task is to parse a natural-language requirement into a strictly grounded STL formula.\n\n"
        "CRITICAL RULES:\n"
        "1. Every predicate MUST reference only signals explicitly declared in the interface outputs or inputs.\n"
        "2. For each predicate g_i, specify the operational span Delta_i = (u_max - u_min) for sign-preserving normalization.\n"
        "3. Explicitly identify whether the property has an antecedent precondition P and consequent Q (P => Q) "
        "to prevent antecedent-masking (vacuous satisfaction).\n"
        "4. Respond with valid JSON matching the exact schema."
    )

    user_prompt = f"""Target Model: {model_name}
Model Description: {interface.get('description', '')}
Interface Specification:
{json.dumps(interface, indent=2)}

Requirement to formalize:
"{requirement_text}"

Respond with a JSON object strictly following this structure:
{{
  "requirement_id": "string",
  "stl_formula": "string (e.g. 'always_[0, 30] (speed < 120)')",
  "is_conditional": true/false,
  "antecedent_formula": "string or null (e.g. 'speed > 100')",
  "consequent_formula": "string or null (e.g. 'eventually_[0, 4] (RPM < 4000)')",
  "predicates": [
    {{
      "name": "mu_1",
      "signal": "string (e.g. 'speed')",
      "expression": "string (e.g. 'speed - 120')",
      "operator": "< | <= | > | >=",
      "threshold": 120.0,
      "span_delta": 180.0
    }}
  ],
  "time_horizon": 30.0,
  "confidence_explanation": "Brief explanation of grounding and timing intervals"
}}
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_track_b_scenario_prompt(
    requirement_text: str,
    stl_spec: Dict[str, Any],
    model_name: str,
    interface: Dict[str, Any],
) -> list[dict[str, str]]:
    """Build grounded prompt for Track B: Low-rank scenario parameterization template."""
    system_prompt = (
        "You are a cyber-physical test generator designing falsification scenario templates for Simulink.\n"
        "Your goal is to define a low-dimensional search space (3-5 control points per input signal) "
        "that allows CMA-ES to discover inputs that violate the requirement, while enforcing physical actuator limits.\n\n"
        "CRITICAL RULES:\n"
        "1. Input control points must stay within the interface minimum and maximum bounds.\n"
        "2. Enforce max slew rate limits (maximum derivative du/dt).\n"
        "3. Prioritize input maneuvers that challenge the condition described in the STL formula.\n"
        "4. Respond with valid JSON matching the exact schema."
    )

    user_prompt = f"""Target Model: {model_name}
Interface Specification:
{json.dumps(interface.get('inputs', {}), indent=2)}

Target STL Property:
{json.dumps(stl_spec, indent=2)}

Requirement:
"{requirement_text}"

Respond with a JSON object strictly following this structure:
{{
  "scenario_name": "string",
  "interpolation_type": "pchip | cubic_spline | piecewise_linear",
  "signals": [
    {{
      "signal_name": "string (e.g. 'throttle')",
      "time_knots": [0.0, 5.0, 15.0, 30.0],
      "default_values": [0.0, 50.0, 100.0, 100.0],
      "bounds": [[0.0, 100.0], [0.0, 100.0], [0.0, 100.0], [0.0, 100.0]],
      "max_slew_rate": 50.0
    }}
  ],
  "falsification_intuition": "Brief explanation of why this parameterization stresses the requirement"
}}
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

"""JSON extraction and schema validation utilities for LLM outputs."""

import json
import re
from typing import Any, Dict


def extract_json(raw_text: str) -> Dict[str, Any]:
    """Extract valid JSON from LLM response text, handling markdown fences or extra prose."""
    text = raw_text.strip()

    # Case 1: Direct JSON parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Case 2: Extract from ```json ... ``` code fence
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    matches = re.findall(fence_pattern, text)
    for block in matches:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue

    # Case 3: Find outermost { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response:\n{raw_text[:300]}...")

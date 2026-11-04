"""Benchmark requirement definitions and specifications for ARCH-COMP CPS evaluation."""

from typing import Any, Dict


AT_BENCHMARK_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
    "AT1": {
        "id": "AT1",
        "model": "Autotrans_shift",
        "category": "Safety (Unconditional)",
        "text": "The vehicle speed shall never exceed 120 within 30 seconds of simulation.",
        "expected_falsifiable": True,
        "is_conditional": False,
        "predicates": [
            {"signal": "speed", "operator": "<=", "threshold": 120.0, "span_delta": 180.0}
        ],
    },
    "AT2": {
        "id": "AT2",
        "model": "Autotrans_shift",
        "category": "Safety (Unconditional)",
        "text": "The engine rotational speed (RPM) shall never exceed 4500 RPM within 30 seconds of simulation.",
        "expected_falsifiable": True,
        "is_conditional": False,
        "predicates": [
            {"signal": "RPM", "operator": "<=", "threshold": 4500.0, "span_delta": 6000.0}
        ],
    },
    "AT51": {
        "id": "AT51",
        "model": "Autotrans_shift",
        "category": "Response (Conditional Implication)",
        "text": (
            "Whenever vehicle speed exceeds 65, the transmission gear shall shift "
            "to 4th gear within 4 seconds and remain in 4th gear while speed is above 65."
        ),
        "expected_falsifiable": True,
        "is_conditional": True,
        "predicates": [
            {"signal": "speed", "operator": ">", "threshold": 65.0, "span_delta": 180.0}
        ],
    },
    "AT51_INV": {
        "id": "AT51_INV",
        "model": "Autotrans_shift",
        "category": "Valid Invariant (Analytical Proof)",
        "text": (
            "Whenever vehicle speed exceeds 100, the transmission gear shall shift "
            "to 4th gear and remain in 4th gear while speed is above 100."
        ),
        "expected_falsifiable": False,
        "is_conditional": True,
        "predicates": [
            {"signal": "speed", "operator": ">", "threshold": 100.0, "span_delta": 180.0}
        ],
    },
}

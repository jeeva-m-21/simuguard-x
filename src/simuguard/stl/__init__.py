"""Signal Temporal Logic (STL) specification and robustness module."""

from simuguard.stl.smooth_robustness import (
    normalize_predicate_robustness,
    smooth_robustness_always,
    smooth_robustness_eventually,
)
from simuguard.stl.evaluator import RobustnessResult, evaluate_trajectory_robustness

__all__ = [
    "normalize_predicate_robustness",
    "smooth_robustness_always",
    "smooth_robustness_eventually",
    "RobustnessResult",
    "evaluate_trajectory_robustness",
]

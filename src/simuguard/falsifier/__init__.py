"""Optimization and falsification algorithms for SimuGuard-X."""

from simuguard.falsifier.curriculum import (
    CandidateEvaluation,
    compute_regime_0_fitness,
    evaluate_three_regime_lexicographic,
)
from simuguard.falsifier.optimizer import CMAESFalsifier, FalsificationResult
from simuguard.falsifier.baselines import (
    DebConstrainedCMAES,
    DokhanchiVacuityCMAES,
    PlainCMAES,
    RandomSearchBaseline,
)

__all__ = [
    "CandidateEvaluation",
    "compute_regime_0_fitness",
    "evaluate_three_regime_lexicographic",
    "CMAESFalsifier",
    "FalsificationResult",
    "DebConstrainedCMAES",
    "DokhanchiVacuityCMAES",
    "PlainCMAES",
    "RandomSearchBaseline",
]

"""Theorem 3: Offset-Free Three-Regime Lexicographic Curriculum for CMA-ES."""

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass
class CandidateEvaluation:
    """Evaluation output for a parameter candidate in SimuGuard-X."""
    regime: int  # 0 = inadmissible, 1 = precondition search, 2 = consequent falsification
    fitness_value: float  # Scalar value within regime (lower is better for minimization)
    is_falsified: bool  # True if exact STL property is falsified (Regime 2 with f < 0)
    rho_pre: float
    rho_post: float


def compute_regime_0_fitness(
    theta: np.ndarray,
    bounds: np.ndarray,
    slew_rates: np.ndarray,
    time_knots: np.ndarray,
    alpha_damp: float = 0.2,
) -> float:
    """Regime 0: Exterior Euclidean distance penalty for out-of-bounds or slew-rate violations.

    Evaluated analytically without launching the Simulink simulation engine.
    """
    lower = bounds[:, 0]
    upper = bounds[:, 1]

    # Box constraint exterior distance
    box_violations = np.maximum(0.0, lower - theta) + np.maximum(0.0, theta - upper)
    box_penalty = float(np.sum(box_violations**2))

    # Slew rate penalty
    dt = np.diff(time_knots)
    du = np.diff(theta)
    slew_actual = np.abs(du / np.maximum(1e-6, dt))
    slew_violations = np.maximum(0.0, slew_actual - slew_rates[:-1])
    slew_penalty = float(np.sum(slew_violations**2))

    # Analytical penalty: strictly positive
    return float(box_penalty + slew_penalty)


def evaluate_three_regime_lexicographic(
    is_admissible: bool,
    regime_0_penalty: float,
    rho_pre: float,
    rho_post: float,
) -> CandidateEvaluation:
    """Theorem 3: Strict lexicographic ordering across regimes.

    Order: Regime 2 < Regime 1 < Regime 0.
    Within Regime 0: minimize penalty > 0.
    Within Regime 1: minimize rho_pre (drives rho_pre >= 0).
    Within Regime 2: minimize rho_post (falsification when rho_post < 0).
    """
    if not is_admissible or regime_0_penalty > 0:
        return CandidateEvaluation(
            regime=0,
            fitness_value=regime_0_penalty,
            is_falsified=False,
            rho_pre=rho_pre,
            rho_post=rho_post,
        )

    # If precondition is not yet met (rho_pre < 0), we are in Regime 1
    if rho_pre < 0.0:
        # We want to maximize rho_pre towards >= 0, so in minimization: -rho_pre
        return CandidateEvaluation(
            regime=1,
            fitness_value=-rho_pre,
            is_falsified=False,
            rho_pre=rho_pre,
            rho_post=rho_post,
        )

    # Precondition satisfied: enter Regime 2 to falsify consequent
    is_falsified = (rho_post < 0.0)
    return CandidateEvaluation(
        regime=2,
        fitness_value=rho_post,
        is_falsified=is_falsified,
        rho_pre=rho_pre,
        rho_post=rho_post,
    )

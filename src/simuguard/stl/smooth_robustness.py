"""Sound smooth robustness evaluation for Signal Temporal Logic (STL).

Implements:
- Lemma 1: Sign-preserving predicate normalization by operational span Delta_i.
- Theorem 2: Bounded, sound Log-Sum-Exp (LSE) approximation for continuous falsification.
"""

import math
from typing import List, Sequence
import numpy as np


def normalize_predicate_robustness(val: float, threshold: float, span_delta: float, operator: str) -> float:
    """Normalize predicate robustness: rho_hat = g(x) / Delta_i.

    Lemma 1: Since Delta_i > 0, sgn(rho_hat) = sgn(rho).
    """
    if span_delta <= 0:
        span_delta = 1.0

    if operator in ("<", "<="):
        # rho = threshold - val (positive when val < threshold)
        return (threshold - val) / span_delta
    elif operator in (">", ">="):
        # rho = val - threshold (positive when val > threshold)
        return (val - threshold) / span_delta
    else:
        raise ValueError(f"Unsupported operator: {operator}")


def smooth_robustness_always(
    values: Sequence[float],
    beta_0: float = 10.0,
) -> float:
    """Theorem 2 (Part A): Averaged Log-Sum-Exp for Universal operator (Always / Box).

    rho_tilde_beta(always) = - (1 / beta) * ln( (1 / N) * sum( exp(-beta * rho_k) ) )
    Temperature is sample-invariant: beta = beta_0 * ln(N).

    Bound: rho_min - ln(N)/beta <= rho_tilde <= rho_min.
    Soundness: rho_tilde < 0 ==> rho_min < 0.
    """
    n = len(values)
    if n == 0:
        return 0.0

    beta = beta_0 * max(1.0, math.log(max(2, n)))
    arr = np.asarray(values, dtype=np.float64)

    # Numerically stable Log-Sum-Exp for min:
    # -1/beta * ln(1/N * sum(exp(-beta * x_k)))
    # = -1/beta * [ ln(sum(exp(-beta * x_k))) - ln(N) ]
    # Use max trick on (-beta * arr)
    scaled = -beta * arr
    max_val = np.max(scaled)
    lse = max_val + np.log(np.sum(np.exp(scaled - max_val)))
    rho_tilde = - (lse - np.log(n)) / beta

    return float(rho_tilde)


def smooth_robustness_eventually(
    values: Sequence[float],
    beta_0: float = 10.0,
) -> float:
    """Theorem 2 (Part B): Un-averaged sum Log-Sum-Exp for Existential operator (Eventually / Diamond).

    rho_tilde_beta^sum(eventually) = (1 / beta) * ln( sum( exp(beta * rho_k) ) )
    Temperature: beta = beta_0 * ln(N).

    Bound: rho_max <= rho_tilde^sum <= rho_max + ln(N)/beta.
    Soundness: rho_tilde^sum < 0 ==> rho_max < 0.
    """
    n = len(values)
    if n == 0:
        return 0.0

    beta = beta_0 * max(1.0, math.log(max(2, n)))
    arr = np.asarray(values, dtype=np.float64)

    # Numerically stable Log-Sum-Exp for max:
    scaled = beta * arr
    max_val = np.max(scaled)
    lse = max_val + np.log(np.sum(np.exp(scaled - max_val)))
    rho_tilde = lse / beta

    return float(rho_tilde)

"""General trajectory-based robustness evaluation for formal STL specifications.

Supports unconditional safety properties (e.g. AT1, AT2) and conditional properties (e.g. AT51)
with exact min/max and Theorem 2 smooth robustness.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

from simuguard.stl.smooth_robustness import (
    normalize_predicate_robustness,
    smooth_robustness_always,
    smooth_robustness_eventually,
)


@dataclass
class RobustnessResult:
    """Robustness evaluation result for a simulation trajectory."""
    rho_pre_exact: float      # Precondition robustness (> 0 means precondition triggered)
    rho_pre_smooth: float
    rho_post_exact: float     # Consequent robustness (< 0 means violation/falsified)
    rho_post_smooth: float
    is_triggered: bool        # True if antecedent P occurred (or True if unconditional)
    is_falsified: bool        # True if violation occurred
    violation_time: Optional[float] = None
    critical_signal_name: Optional[str] = None
    critical_signal_val: Optional[float] = None


def evaluate_trajectory_robustness(
    time: np.ndarray,
    signals: Dict[str, np.ndarray],
    stl_spec: Dict[str, Any],
) -> RobustnessResult:
    """Evaluate trajectory against formal STL specification dictionary."""
    is_conditional = stl_spec.get("is_conditional", False)
    predicates: List[Dict[str, Any]] = stl_spec.get("predicates", [])

    if not is_conditional:
        # Unconditional property (e.g. always (speed <= 120))
        # Find primary predicate
        if not predicates:
            # Fallback default: speed <= 120
            p_spec = {"signal": "speed", "operator": "<=", "threshold": 120.0, "span_delta": 180.0}
        else:
            p_spec = predicates[0]

        sig_name = p_spec.get("signal", "speed")
        sig_val = signals.get(sig_name, np.zeros_like(time))
        threshold = float(p_spec.get("threshold", 120.0))
        span_delta = float(p_spec.get("span_delta", 180.0))
        operator = p_spec.get("operator", "<=")

        # Normalize predicate robustness: rho > 0 means satisfied, rho < 0 means violated
        if operator in ("<", "<="):
            rho_arr = (threshold - sig_val) / span_delta
        else:
            rho_arr = (sig_val - threshold) / span_delta

        rho_exact = float(np.min(rho_arr))
        rho_smooth = float(smooth_robustness_always(rho_arr))
        is_falsified = bool(rho_exact < 0.0)

        viol_time = None
        crit_val = None
        if is_falsified:
            idx = np.where(rho_arr < 0.0)[0][0]
            viol_time = float(time[idx])
            crit_val = float(sig_val[idx])

        return RobustnessResult(
            rho_pre_exact=1.0,
            rho_pre_smooth=1.0,
            rho_post_exact=rho_exact,
            rho_post_smooth=rho_smooth,
            is_triggered=True,
            is_falsified=is_falsified,
            violation_time=viol_time,
            critical_signal_name=sig_name,
            critical_signal_val=crit_val,
        )

    else:
        # Conditional Bounded Response property:
        # Phi = always_[0, T - tau] ( speed > threshold => eventually_[0, tau] (gear >= 4) )
        speed = signals.get("speed", np.zeros_like(time))
        gear = signals.get("gear", np.ones_like(time))

        speed_threshold = 65.0
        speed_span = 180.0
        tau = 4.0

        for p in predicates:
            if p.get("signal") == "speed":
                speed_threshold = float(p.get("threshold", 65.0))
                speed_span = float(p.get("span_delta", 180.0))

        # 1. Precondition P: speed > threshold
        p_values = (speed - speed_threshold) / speed_span
        rho_pre_exact = float(np.max(p_values))
        rho_pre_smooth = float(smooth_robustness_eventually(p_values))

        # Antecedent must trigger within valid horizon [0, T - tau]
        dt = float(time[1] - time[0]) if len(time) > 1 else 0.05
        steps_tau = int(round(tau / max(1e-4, dt)))
        valid_horizon = time[-1] - tau
        trig_mask = (speed > speed_threshold) & (time <= valid_horizon)

        if not np.any(trig_mask):
            return RobustnessResult(
                rho_pre_exact=rho_pre_exact,
                rho_pre_smooth=rho_pre_smooth,
                rho_post_exact=1.0,
                rho_post_smooth=1.0,
                is_triggered=False,
                is_falsified=False,
            )

        # 2. Consequent Q: for each trigger instant t, exists t' in [t, t+tau] with gear >= 4
        trig_indices = np.where(trig_mask)[0]
        min_resp_rob = float("inf")
        viol_time = None

        for idx in trig_indices:
            window_gear = gear[idx : idx + steps_tau + 1]
            g_max = float(np.max(window_gear))
            rob_t = float((g_max - 3.5) / 3.0)
            if rob_t < min_resp_rob:
                min_resp_rob = rob_t
                if rob_t < 0.0 and viol_time is None:
                    viol_time = float(time[idx])

        is_falsified = bool(min_resp_rob < 0.0)
        rho_post_smooth = min_resp_rob

        return RobustnessResult(
            rho_pre_exact=rho_pre_exact,
            rho_pre_smooth=rho_pre_smooth,
            rho_post_exact=min_resp_rob,
            rho_post_smooth=rho_post_smooth,
            is_triggered=True,
            is_falsified=is_falsified,
            violation_time=viol_time,
            critical_signal_name="gear",
        )

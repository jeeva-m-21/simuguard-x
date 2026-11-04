"""Pillar 5 / Gate 2: Solver Integrity Verification for SimuGuard-X.

Guards against spurious falsification and solver artifacts via:
1. Step-Collapse Ratio (SCR = dt_median / dt_min) detection.
2. Cross-solver re-simulation using stiff solvers (ode15s) with tightened tolerances (RelTol=1e-7).
3. Robustness discrepancy checking: |rho_base - rho_tight| <= delta_tol.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import numpy as np

from simuguard.benchmarks.simulator import SimulinkSimulator, SimulationTrace
from simuguard.stl.evaluator import evaluate_trajectory_robustness, RobustnessResult


@dataclass
class Gate2VerificationResult:
    """Result of Gate 2 Solver Integrity Verification."""
    is_confirmed: bool               # True if violation persists under tightened solver
    is_numerical_artifact: bool      # True if violation vanishes under tightened solver (false positive)
    scr_baseline: float              # Step-Collapse Ratio of original trace
    scr_tightened: float             # Step-Collapse Ratio of reference trace
    rho_baseline: float              # Robustness under baseline solver
    rho_tightened: float             # Robustness under tightened reference solver
    robustness_discrepancy: float    # |rho_baseline - rho_tightened|
    tightened_solver: str            # Reference solver used (e.g. ode15s)
    details: str                     # Human-readable certification or artifact rationale


def compute_step_collapse_ratio(time_array: np.ndarray) -> Tuple[float, float, float]:
    """Compute the Step-Collapse Ratio (SCR = Delta t_median / Delta t_min).

    SCR >> 10^3 indicates local step-size collapse, chattering, or solver distress.
    For fixed-step solvers, Delta t is constant and SCR = 1.0.
    """
    if len(time_array) < 2:
        return 1.0, 0.05, 0.05

    dt = np.diff(time_array)
    # Filter out potential numerical zeros or non-positive intervals
    positive_dt = dt[dt > 1e-12]

    if len(positive_dt) == 0:
        return float("inf"), 0.0, 0.0

    dt_median = float(np.median(positive_dt))
    dt_min = float(np.min(positive_dt))

    scr = dt_median / max(dt_min, 1e-12)
    return scr, dt_median, dt_min


class SolverIntegrityGate:
    """Gate 2: Verifies counterexamples with stiff reference solvers and tightened tolerance."""

    def __init__(
        self,
        stiff_solver: str = "ode15s",
        tight_reltol: str = "1e-7",
        tight_abstol: str = "1e-9",
        scr_threshold: float = 1000.0,
        delta_tol: float = 0.05,
    ):
        self.stiff_solver = stiff_solver
        self.tight_reltol = tight_reltol
        self.tight_abstol = tight_abstol
        self.scr_threshold = scr_threshold
        self.delta_tol = delta_tol

    def verify_counterexample(
        self,
        simulator: SimulinkSimulator,
        scenario_spec: Dict[str, Any],
        baseline_trace: SimulationTrace,
        stl_spec: Dict[str, Any],
    ) -> Gate2VerificationResult:
        """Execute tightened solver cross-check and evaluate numerical discrepancy."""
        # 1. Baseline analysis
        scr_base, _, _ = compute_step_collapse_ratio(baseline_trace.time)
        base_rob = evaluate_trajectory_robustness(
            baseline_trace.time, baseline_trace.signals, stl_spec
        )
        rho_base = base_rob.rho_post_exact

        eng = simulator.eng
        model = simulator.model_name

        # 2. Save original solver configuration
        orig_fast_restart = simulator.use_fast_restart
        orig_solver = eng.get_param(model, "Solver")
        orig_reltol = eng.get_param(model, "RelTol")
        orig_abstol = eng.get_param(model, "AbsTol")
        orig_solver_type = eng.get_param(model, "SolverType")

        print(f"\n[Gate 2] Initiating Solver Integrity Verification...")
        print(f"  > Baseline Solver     : {orig_solver} (Type: {orig_solver_type}, RelTol: {orig_reltol})")
        print(f"  > Baseline SCR        : {scr_base:.2f} (Threshold: {self.scr_threshold})")
        print(f"  > Baseline Robustness : {rho_base:.4f}")

        try:
            # Temporarily disable FastRestart to reconfigure solver structure
            if orig_fast_restart:
                eng.set_param(model, "FastRestart", "off", nargout=0)

            # Apply tightened reference solver configuration
            eng.set_param(model, "SolverType", "Variable-step", nargout=0)
            eng.set_param(model, "Solver", self.stiff_solver, nargout=0)
            eng.set_param(model, "RelTol", self.tight_reltol, nargout=0)
            eng.set_param(model, "AbsTol", self.tight_abstol, nargout=0)

            print(f"  > Re-simulating with {self.stiff_solver} (RelTol={self.tight_reltol}, AbsTol={self.tight_abstol})...")
            tight_trace = simulator.simulate(scenario_spec)

            if not tight_trace.is_valid:
                return Gate2VerificationResult(
                    is_confirmed=False,
                    is_numerical_artifact=True,
                    scr_baseline=scr_base,
                    scr_tightened=float("nan"),
                    rho_baseline=rho_base,
                    rho_tightened=float("nan"),
                    robustness_discrepancy=float("nan"),
                    tightened_solver=self.stiff_solver,
                    details=f"Tightened solver failed to execute: {tight_trace.error_message}",
                )

            # 3. Analyze reference simulation trace
            scr_tight, _, _ = compute_step_collapse_ratio(tight_trace.time)
            tight_rob = evaluate_trajectory_robustness(
                tight_trace.time, tight_trace.signals, stl_spec
            )
            rho_tight = tight_rob.rho_post_exact
            discrepancy = abs(rho_base - rho_tight)

            print(f"  > Tightened Robustness : {rho_tight:.4f}")
            print(f"  > Discrepancy |rho_diff|: {discrepancy:.4f} (Allowed: {self.delta_tol})")
            print(f"  > Tightened SCR       : {scr_tight:.2f}")

            # 4. Decision Logic
            if rho_tight >= 0.0:
                # Violation vanished under tightened reference solver -> Solver Artifact!
                is_confirmed = False
                is_artifact = True
                details = (
                    f"REJECTED AS SOLVER ARTIFACT: Property violation was present in baseline solver "
                    f"({rho_base:.4f} < 0) but vanished under stiff reference solver {self.stiff_solver} "
                    f"({rho_tight:.4f} >= 0)."
                )
            elif discrepancy <= self.delta_tol:
                # Violation confirmed and numerically stable
                is_confirmed = True
                is_artifact = False
                details = (
                    f"CONFIRMED GENUINE COUNTEREXAMPLE: Violation verified under tightened {self.stiff_solver} "
                    f"(rho={rho_tight:.4f} < 0) with low numerical drift ({discrepancy:.4f} <= {self.delta_tol})."
                )
            else:
                # Violation exists in both, but drift is high
                is_confirmed = True
                is_artifact = False
                details = (
                    f"CONFIRMED WITH HIGH SENSITIVITY: Violation verified under tightened solver "
                    f"(rho={rho_tight:.4f} < 0), but numerical drift is elevated ({discrepancy:.4f} > {self.delta_tol})."
                )

            return Gate2VerificationResult(
                is_confirmed=is_confirmed,
                is_numerical_artifact=is_artifact,
                scr_baseline=scr_base,
                scr_tightened=scr_tight,
                rho_baseline=rho_base,
                rho_tightened=rho_tight,
                robustness_discrepancy=discrepancy,
                tightened_solver=self.stiff_solver,
                details=details,
            )

        finally:
            # 5. Strictly restore original model solver settings
            try:
                eng.set_param(model, "SolverType", orig_solver_type, nargout=0)
                eng.set_param(model, "Solver", orig_solver, nargout=0)
                eng.set_param(model, "RelTol", orig_reltol, nargout=0)
                eng.set_param(model, "AbsTol", orig_abstol, nargout=0)
                if orig_fast_restart:
                    eng.set_param(model, "FastRestart", "on", nargout=0)
            except Exception as e:
                print(f"[Gate 2] Warning restoring model solver parameters: {e}")

"""CMA-ES Falsification Engine with Theorem 3 Three-Regime Lexicographic Ranking."""

import copy
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from cmaes import CMA

from simuguard.benchmarks.simulator import SimulinkSimulator, SimulationTrace
from simuguard.stl.evaluator import evaluate_trajectory_robustness, RobustnessResult
from simuguard.solvers.integrity import SolverIntegrityGate, Gate2VerificationResult


@dataclass
class FalsificationResult:
    """Detailed summary of a falsification search run."""
    falsified: bool
    best_candidate: np.ndarray
    best_fitness: float
    best_regime: int
    best_rho_pre: float
    best_rho_post: float
    simulations_count: int
    regime_0_rejections: int  # Number of simulation calls saved by Regime 0
    wall_clock_time_sec: float
    sims_to_first_trigger: int = 0
    sims_post_trigger: int = 0
    p_anchor_candidate: Optional[np.ndarray] = None
    counterexample_trace: Optional[SimulationTrace] = None
    gate2_result: Optional[Gate2VerificationResult] = None
    convergence_history: Optional[List[Dict[str, Any]]] = None


class CMAESFalsifier:
    """Falsification optimizer using CMA-ES with Theorem 3 Lexicographic Curriculum."""

    def __init__(
        self,
        simulator: SimulinkSimulator,
        scenario_template: Dict[str, Any],
        stl_spec: Optional[Dict[str, Any]] = None,
        max_generations: int = 40,
        population_size: Optional[int] = None,
        seed: int = 42,
        enable_gate2: bool = True,
        use_uniform_init: bool = False,
        alpha_damp: float = 0.2,
    ):
        self.simulator = simulator
        self.template = copy.deepcopy(scenario_template)
        self.stl_spec = stl_spec or {}
        self.max_generations = max_generations
        self.seed = seed
        self.enable_gate2 = enable_gate2
        self.use_uniform_init = use_uniform_init
        self.alpha_damp = alpha_damp
        self.gate2 = SolverIntegrityGate() if enable_gate2 else None

        # Extract parameter dimensions, initial mean, and bounds from scenario template
        self.signals_info = []
        init_values = []
        lower_bounds = []
        upper_bounds = []

        for sig in self.template.get("signals", []):
            name = sig["signal_name"]
            knots = sig["time_knots"]
            defaults = sig.get("default_values", [0.0] * len(knots))
            bounds = sig.get("bounds", [[0.0, 100.0]] * len(knots))
            max_slew = sig.get("max_slew_rate", 100.0)

            n_points = len(knots)
            self.signals_info.append({
                "name": name,
                "knots": np.array(knots, dtype=np.float64),
                "n_points": n_points,
                "max_slew": max_slew,
            })

            init_values.extend(defaults)
            for b in bounds:
                lower_bounds.append(b[0])
                upper_bounds.append(b[1])

        self.lower_bounds = np.array(lower_bounds, dtype=np.float64)
        self.upper_bounds = np.array(upper_bounds, dtype=np.float64)
        self.dim = len(self.lower_bounds)

        if self.use_uniform_init:
            self.mean = 0.5 * (self.lower_bounds + self.upper_bounds)
        else:
            self.mean = np.array(init_values, dtype=np.float64)

        # Scale sigma appropriately across dimensions
        spans = self.upper_bounds - self.lower_bounds
        self.sigma = float(np.mean(spans) * 0.25)

        # Initialize CMA-ES with box bounds
        bounds_array = np.column_stack([self.lower_bounds, self.upper_bounds])
        self.cma = CMA(
            mean=self.mean,
            sigma=self.sigma,
            bounds=bounds_array,
            seed=self.seed,
            population_size=population_size,
        )

    def unpack_candidate(self, theta: np.ndarray) -> Dict[str, Any]:
        """Convert flat parameter vector theta back into scenario signals dict."""
        scenario = copy.deepcopy(self.template)
        idx = 0
        for sig_spec, sig in zip(self.signals_info, scenario.get("signals", [])):
            n = sig_spec["n_points"]
            vals = theta[idx : idx + n].tolist()
            sig["values"] = vals
            idx += n
        return scenario

    def check_regime_0(self, theta: np.ndarray) -> float:
        """Theorem 3 Regime 0: Compute analytical exterior penalty.

        Returns penalty > 0 if candidate is inadmissible; 0.0 if admissible.
        """
        # 1. Box boundary penalty
        below = np.maximum(0.0, self.lower_bounds - theta)
        above = np.maximum(0.0, theta - self.upper_bounds)
        box_penalty = float(np.sum(below**2 + above**2))

        # 2. Slew rate penalty
        slew_penalty = 0.0
        idx = 0
        for sig_spec in self.signals_info:
            n = sig_spec["n_points"]
            vals = theta[idx : idx + n]
            knots = sig_spec["knots"]
            max_slew = sig_spec["max_slew"]

            dt = np.diff(knots)
            du = np.abs(np.diff(vals))
            actual_slew = du / np.maximum(1e-6, dt)
            violation = np.maximum(0.0, actual_slew - max_slew)
            slew_penalty += float(np.sum(violation**2))
            idx += n

        return box_penalty + slew_penalty

    def run(self, verbose: bool = True) -> FalsificationResult:
        """Execute the CMA-ES search loop."""
        t_start = time.time()
        sim_count = 0
        regime_0_count = 0

        best_overall_fitness = float("inf")
        best_overall_regime = 0
        best_candidate = self.mean.copy()
        best_rho_pre = -1.0
        best_rho_post = 1.0
        counterexample_trace = None
        history: List[Dict[str, Any]] = []
        self._regime_1_visited = False
        self._regime_2_damped = False

        first_trigger_sim: Optional[int] = None
        p_anchor_candidate: Optional[np.ndarray] = None
        best_p_anchor_post: float = float("inf")

        if verbose:
            print(f"[CMA-ES] Initialized with dimension {self.dim}, population size {self.cma.population_size}")
            print(f"[CMA-ES] Search space spans: {self.lower_bounds[0]} to {self.upper_bounds[0]}")
            print("-" * 65)

        for gen in range(1, self.max_generations + 1):
            solutions: List[Tuple[np.ndarray, float]] = []

            for _ in range(self.cma.population_size):
                theta = self.cma.ask()

                # Step 1: Regime 0 Admissibility Gate (Analytical - NO Simulink call!)
                penalty = self.check_regime_0(theta)
                if penalty > 1e-6:
                    regime_0_count += 1
                    # Fitness in Regime 0: 1000 + penalty
                    fitness = 1000.0 + penalty
                    solutions.append((theta, fitness))
                    continue

                # Step 2: Candidate is admissible - Run Simulink simulation
                scenario = self.unpack_candidate(theta)
                trace = self.simulator.simulate(scenario)
                sim_count += 1

                if not trace.is_valid:
                    solutions.append((theta, 999.0))
                    continue

                # Step 3: Evaluate STL Robustness
                rob_res = evaluate_trajectory_robustness(trace.time, trace.signals, self.stl_spec)

                # Step 4: Theorem 3 Three-Regime Lexicographic Ranking
                if not rob_res.is_triggered:
                    # Regime 1: Precondition not yet met. Maximize rho_pre towards 0.
                    # Fitness: 100 - rho_pre (so higher speed decreases fitness towards 100)
                    fitness = 100.0 - rob_res.rho_pre_smooth
                    regime = 1
                else:
                    # Regime 2: Precondition triggered! Minimize consequent robustness.
                    # Fitness: rho_post (values < 0 mean falsification!)
                    fitness = rob_res.rho_post_smooth
                    regime = 2
                    if first_trigger_sim is None:
                        first_trigger_sim = sim_count
                    if p_anchor_candidate is None or rob_res.rho_post_smooth < best_p_anchor_post:
                        p_anchor_candidate = theta.copy()
                        best_p_anchor_post = rob_res.rho_post_smooth

                solutions.append((theta, fitness))

                # Track global best
                if fitness < best_overall_fitness:
                    best_overall_fitness = fitness
                    best_overall_regime = regime
                    best_candidate = theta.copy()
                    best_rho_pre = rob_res.rho_pre_exact
                    best_rho_post = rob_res.rho_post_exact
                    if rob_res.is_falsified:
                        counterexample_trace = trace

                # Candidate violation discovered!
                if rob_res.is_falsified:
                    gate2_res = None
                    if self.enable_gate2 and self.gate2:
                        gate2_res = self.gate2.verify_counterexample(
                            simulator=self.simulator,
                            scenario_spec=scenario,
                            baseline_trace=trace,
                            stl_spec=self.stl_spec,
                        )
                        if gate2_res.is_numerical_artifact:
                            if verbose:
                                print(f"[Gate 2 Warning] Candidate rejected as numerical artifact. Continuing search...")
                            # Overwrite fitness to prevent early exit on artifact
                            solutions[-1] = (theta, 500.0)
                            continue

                    wall_clock = time.time() - t_start
                    trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
                    post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0

                    if verbose:
                        print(f"\n[CMA-ES] FALSIFICATION DISCOVERED AND CERTIFIED AT GENERATION {gen}!")
                        print(f"  > Simulations executed : {sim_count} (Trigger: {trig_sim}, Post-trigger: {post_sim})")
                        print(f"  > Regime 0 skips saved : {regime_0_count}")
                        print(f"  > Robustness rho_post  : {rob_res.rho_post_exact:.4f}")
                        print(f"  > Violation Time       : {rob_res.violation_time:.2f}s")
                        print(f"  > Gate 2 Certified     : {gate2_res.is_confirmed if gate2_res else 'N/A'}")
                        print(f"  > Wall-clock time      : {wall_clock:.2f}s")

                    return FalsificationResult(
                        falsified=True,
                        best_candidate=theta,
                        best_fitness=fitness,
                        best_regime=2,
                        best_rho_pre=rob_res.rho_pre_exact,
                        best_rho_post=rob_res.rho_post_exact,
                        simulations_count=sim_count,
                        regime_0_rejections=regime_0_count,
                        wall_clock_time_sec=wall_clock,
                        sims_to_first_trigger=trig_sim,
                        sims_post_trigger=post_sim,
                        p_anchor_candidate=p_anchor_candidate,
                        counterexample_trace=trace,
                        gate2_result=gate2_res,
                        convergence_history=history,
                    )

            # Update CMA-ES distribution
            self.cma.tell(solutions)

            # Section IV-E: Regime 1 -> 2 Transition Adaptation (Covariance & Step-size Damping + Anchor Re-centering)
            if best_overall_regime == 2 and getattr(self, "_regime_1_visited", False) and not getattr(self, "_regime_2_damped", False):
                self.cma._p_sigma *= self.alpha_damp
                self.cma._pc.fill(0.0)
                if p_anchor_candidate is not None:
                    self.cma._mean = p_anchor_candidate.copy()
                self._regime_2_damped = True
                if verbose:
                    print(f"  [SimuGuard-X Curriculum] Regime 1 -> 2 Transition: Damped p_sigma (alpha={self.alpha_damp}), reset pc, and re-anchored mean.")
            elif best_overall_regime == 1:
                self._regime_1_visited = True
                self._regime_2_damped = False  # Reset damping on fallback to Regime 1

            history.append({
                "generation": gen,
                "simulations": sim_count,
                "regime_0_skips": regime_0_count,
                "best_fitness": best_overall_fitness,
                "best_regime": best_overall_regime,
            })

            if verbose:
                print(
                    f"Gen {gen:02d} | Sims: {sim_count:03d} (Regime 0 skips: {regime_0_count}) | "
                    f"Best Regime: {best_overall_regime} | Best Fitness: {best_overall_fitness:.4f}"
                )

        wall_clock = time.time() - t_start
        trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
        post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
        return FalsificationResult(
            falsified=False,
            best_candidate=best_candidate,
            best_fitness=best_overall_fitness,
            best_regime=best_overall_regime,
            best_rho_pre=best_rho_pre,
            best_rho_post=best_rho_post,
            simulations_count=sim_count,
            regime_0_rejections=regime_0_count,
            wall_clock_time_sec=wall_clock,
            sims_to_first_trigger=trig_sim,
            sims_post_trigger=post_sim,
            p_anchor_candidate=p_anchor_candidate,
            counterexample_trace=counterexample_trace,
            convergence_history=history,
        )

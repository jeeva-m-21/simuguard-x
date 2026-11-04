"""Baseline Falsification Algorithms for Fair Same-Search-Space Comparison.

Implements:
1. DebConstrainedCMAES: CMA-ES with Deb's feasibility tournament criteria.
2. DokhanchiVacuityCMAES: CMA-ES with Dokhanchi/Ferrere vacuity-aware robustness (min(rho(Q), rho(P) + C_pre)).
3. PlainCMAES: Standard CMA-ES with uniform initialization and classical max-min STL robustness.
4. RandomSearchBaseline: Uniform random sampling within the same scenario DSL bounds.
"""

import copy
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from cmaes import CMA

from simuguard.benchmarks.simulator import SimulinkSimulator, SimulationTrace
from simuguard.falsifier.optimizer import FalsificationResult
from simuguard.stl.evaluator import evaluate_trajectory_robustness, RobustnessResult
from simuguard.solvers.integrity import SolverIntegrityGate, Gate2VerificationResult


class BaseScenarioOptimizer:
    """Base helper extracting parameters and signals from scenario templates."""

    def __init__(
        self,
        simulator: SimulinkSimulator,
        scenario_template: Dict[str, Any],
        stl_spec: Dict[str, Any],
        seed: int = 42,
        enable_gate2: bool = True,
    ):
        self.simulator = simulator
        self.template = copy.deepcopy(scenario_template)
        self.stl_spec = copy.deepcopy(stl_spec)
        self.seed = seed
        self.enable_gate2 = enable_gate2
        self.gate2 = SolverIntegrityGate() if enable_gate2 else None

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

        self.default_mean = np.array(init_values, dtype=np.float64)
        self.lower_bounds = np.array(lower_bounds, dtype=np.float64)
        self.upper_bounds = np.array(upper_bounds, dtype=np.float64)
        self.dim = len(self.default_mean)
        self.uniform_center = 0.5 * (self.lower_bounds + self.upper_bounds)
        self.spans = self.upper_bounds - self.lower_bounds
        self.sigma = float(np.mean(self.spans) * 0.25)

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

    def check_constraints(self, theta: np.ndarray) -> Tuple[bool, float]:
        """Check box and slew rate constraints.
        
        Returns (is_admissible, penalty_value).
        """
        below = np.maximum(0.0, self.lower_bounds - theta)
        above = np.maximum(0.0, theta - self.upper_bounds)
        box_penalty = float(np.sum(below**2 + above**2))

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

        total_penalty = box_penalty + slew_penalty
        return (total_penalty <= 1e-6), total_penalty


class DebConstrainedCMAES(BaseScenarioOptimizer):
    """CMA-ES using Kalyanmoy Deb's feasibility tournament criteria:
    
    1. Feasible beats Infeasible.
    2. Between two feasible solutions, compare objective (consequent robustness).
    3. Between two infeasible solutions, compare constraint violation.
    """

    def __init__(
        self,
        simulator: SimulinkSimulator,
        scenario_template: Dict[str, Any],
        stl_spec: Dict[str, Any],
        max_generations: int = 40,
        population_size: Optional[int] = None,
        seed: int = 42,
        enable_gate2: bool = True,
        use_warm_start: bool = False,
    ):
        super().__init__(simulator, scenario_template, stl_spec, seed, enable_gate2)
        self.max_generations = max_generations
        self.use_warm_start = use_warm_start
        mean_init = self.default_mean if use_warm_start else self.uniform_center
        bounds_array = np.column_stack([self.lower_bounds, self.upper_bounds])
        self.cma = CMA(
            mean=mean_init,
            sigma=self.sigma,
            bounds=bounds_array,
            seed=self.seed,
            population_size=population_size,
        )

    def run(self, max_sims: int = 200, verbose: bool = False) -> FalsificationResult:
        t_start = time.time()
        sim_count = 0
        rejections = 0
        best_overall_fitness = float("inf")
        best_candidate = self.uniform_center.copy()
        best_rho_pre = -1.0
        best_rho_post = 1.0
        counterexample_trace = None
        gate2_res = None
        first_trigger_sim: Optional[int] = None

        for gen in range(1, self.max_generations + 1):
            if sim_count >= max_sims:
                break

            solutions: List[Tuple[np.ndarray, float]] = []

            for _ in range(self.cma.population_size):
                if sim_count >= max_sims:
                    break

                theta = self.cma.ask()
                is_admissible, penalty = self.check_constraints(theta)

                if not is_admissible:
                    rejections += 1
                    # Infeasible level 2 (Boundary violation): high penalty
                    fitness = 1000.0 + penalty
                    solutions.append((theta, fitness))
                    continue

                scenario = self.unpack_candidate(theta)
                trace = self.simulator.simulate(scenario)
                sim_count += 1

                if not trace.is_valid:
                    solutions.append((theta, 999.0))
                    continue

                rob_res = evaluate_trajectory_robustness(trace.time, trace.signals, self.stl_spec)
                if rob_res.is_triggered and first_trigger_sim is None:
                    first_trigger_sim = sim_count

                if not rob_res.is_triggered:
                    # Infeasible level 1 (Antecedent unfulfilled): violation is -rho_pre
                    fitness = 100.0 - rob_res.rho_pre_smooth
                else:
                    # Feasible solution: fitness is objective (consequent robustness)
                    fitness = rob_res.rho_post_smooth

                solutions.append((theta, fitness))

                if fitness < best_overall_fitness:
                    best_overall_fitness = fitness
                    best_candidate = theta.copy()
                    best_rho_pre = rob_res.rho_pre_exact
                    best_rho_post = rob_res.rho_post_exact
                    if rob_res.is_falsified:
                        counterexample_trace = trace

                if rob_res.is_falsified:
                    if self.enable_gate2 and self.gate2:
                        gate2_res = self.gate2.verify_counterexample(
                            simulator=self.simulator,
                            scenario_spec=scenario,
                            baseline_trace=trace,
                            stl_spec=self.stl_spec,
                        )
                        if gate2_res.is_numerical_artifact:
                            solutions[-1] = (theta, 500.0)
                            continue

                    wall_clock = time.time() - t_start
                    trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
                    post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
                    return FalsificationResult(
                        falsified=True,
                        best_candidate=theta,
                        best_fitness=fitness,
                        best_regime=2,
                        best_rho_pre=rob_res.rho_pre_exact,
                        best_rho_post=rob_res.rho_post_exact,
                        simulations_count=sim_count,
                        regime_0_rejections=rejections,
                        wall_clock_time_sec=wall_clock,
                        sims_to_first_trigger=trig_sim,
                        sims_post_trigger=post_sim,
                        counterexample_trace=trace,
                        gate2_result=gate2_res,
                    )

            if len(solutions) == self.cma.population_size:
                self.cma.tell(solutions)

        wall_clock = time.time() - t_start
        trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
        post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
        return FalsificationResult(
            falsified=False,
            best_candidate=best_candidate,
            best_fitness=best_overall_fitness,
            best_regime=1,
            best_rho_pre=best_rho_pre,
            best_rho_post=best_rho_post,
            simulations_count=sim_count,
            regime_0_rejections=rejections,
            wall_clock_time_sec=wall_clock,
            sims_to_first_trigger=trig_sim,
            sims_post_trigger=post_sim,
            counterexample_trace=counterexample_trace,
        )


class DokhanchiVacuityCMAES(BaseScenarioOptimizer):
    """CMA-ES using Dokhanchi et al. (2018) / Ferrere et al. (2019) Vacuity-Aware Robustness:
    
    rho_vacuity = min(rho(Q), rho(P) + C_pre)
    Minimizes -rho_vacuity (or directly rho_vacuity).
    """

    def __init__(
        self,
        simulator: SimulinkSimulator,
        scenario_template: Dict[str, Any],
        stl_spec: Dict[str, Any],
        c_pre: float = 0.5,
        max_generations: int = 40,
        population_size: Optional[int] = None,
        seed: int = 42,
        enable_gate2: bool = True,
        use_warm_start: bool = False,
    ):
        super().__init__(simulator, scenario_template, stl_spec, seed, enable_gate2)
        self.c_pre = c_pre
        self.max_generations = max_generations
        self.use_warm_start = use_warm_start
        mean_init = self.default_mean if use_warm_start else self.uniform_center
        bounds_array = np.column_stack([self.lower_bounds, self.upper_bounds])
        self.cma = CMA(
            mean=mean_init,
            sigma=self.sigma,
            bounds=bounds_array,
            seed=self.seed,
            population_size=population_size,
        )

    def run(self, max_sims: int = 200, verbose: bool = False) -> FalsificationResult:
        t_start = time.time()
        sim_count = 0
        rejections = 0
        best_overall_fitness = float("inf")
        best_candidate = self.uniform_center.copy()
        best_rho_pre = -1.0
        best_rho_post = 1.0
        counterexample_trace = None
        gate2_res = None
        first_trigger_sim: Optional[int] = None

        for gen in range(1, self.max_generations + 1):
            if sim_count >= max_sims:
                break

            solutions: List[Tuple[np.ndarray, float]] = []

            for _ in range(self.cma.population_size):
                if sim_count >= max_sims:
                    break

                theta = self.cma.ask()
                is_admissible, penalty = self.check_constraints(theta)

                if not is_admissible:
                    rejections += 1
                    fitness = 1000.0 + penalty
                    solutions.append((theta, fitness))
                    continue

                scenario = self.unpack_candidate(theta)
                trace = self.simulator.simulate(scenario)
                sim_count += 1

                if not trace.is_valid:
                    solutions.append((theta, 999.0))
                    continue

                rob_res = evaluate_trajectory_robustness(trace.time, trace.signals, self.stl_spec)
                if rob_res.is_triggered and first_trigger_sim is None:
                    first_trigger_sim = sim_count

                # Dokhanchi formula: min(rho(Q), rho(P) + C_pre)
                # To falsify Q while satisfying P, we want rho(Q) < 0 and rho(P) > 0.
                if self.stl_spec.get("is_conditional", False):
                    vacuity_robustness = min(rob_res.rho_post_smooth, rob_res.rho_pre_smooth + self.c_pre)
                else:
                    vacuity_robustness = rob_res.rho_post_smooth

                fitness = vacuity_robustness
                solutions.append((theta, fitness))

                if fitness < best_overall_fitness:
                    best_overall_fitness = fitness
                    best_candidate = theta.copy()
                    best_rho_pre = rob_res.rho_pre_exact
                    best_rho_post = rob_res.rho_post_exact
                    if rob_res.is_falsified:
                        counterexample_trace = trace

                if rob_res.is_falsified:
                    if self.enable_gate2 and self.gate2:
                        gate2_res = self.gate2.verify_counterexample(
                            simulator=self.simulator,
                            scenario_spec=scenario,
                            baseline_trace=trace,
                            stl_spec=self.stl_spec,
                        )
                        if gate2_res.is_numerical_artifact:
                            solutions[-1] = (theta, 500.0)
                            continue

                    wall_clock = time.time() - t_start
                    trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
                    post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
                    return FalsificationResult(
                        falsified=True,
                        best_candidate=theta,
                        best_fitness=fitness,
                        best_regime=2,
                        best_rho_pre=rob_res.rho_pre_exact,
                        best_rho_post=rob_res.rho_post_exact,
                        simulations_count=sim_count,
                        regime_0_rejections=rejections,
                        wall_clock_time_sec=wall_clock,
                        sims_to_first_trigger=trig_sim,
                        sims_post_trigger=post_sim,
                        counterexample_trace=trace,
                        gate2_result=gate2_res,
                    )

            if len(solutions) == self.cma.population_size:
                self.cma.tell(solutions)

        wall_clock = time.time() - t_start
        trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
        post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
        return FalsificationResult(
            falsified=False,
            best_candidate=best_candidate,
            best_fitness=best_overall_fitness,
            best_regime=1,
            best_rho_pre=best_rho_pre,
            best_rho_post=best_rho_post,
            simulations_count=sim_count,
            regime_0_rejections=rejections,
            wall_clock_time_sec=wall_clock,
            sims_to_first_trigger=trig_sim,
            sims_post_trigger=post_sim,
            counterexample_trace=counterexample_trace,
        )


class PlainCMAES(BaseScenarioOptimizer):
    """Plain CMA-ES with uniform initialization and classical max-min implication robustness:
    
    rho(P => Q) = max(-rho(P), rho(Q))
    """

    def __init__(
        self,
        simulator: SimulinkSimulator,
        scenario_template: Dict[str, Any],
        stl_spec: Dict[str, Any],
        max_generations: int = 40,
        population_size: Optional[int] = None,
        seed: int = 42,
        enable_gate2: bool = True,
        use_warm_start: bool = False,
    ):
        super().__init__(simulator, scenario_template, stl_spec, seed, enable_gate2)
        self.max_generations = max_generations
        self.use_warm_start = use_warm_start
        mean_init = self.default_mean if use_warm_start else self.uniform_center
        bounds_array = np.column_stack([self.lower_bounds, self.upper_bounds])
        self.cma = CMA(
            mean=mean_init,
            sigma=self.sigma,
            bounds=bounds_array,
            seed=self.seed,
            population_size=population_size,
        )

    def run(self, max_sims: int = 200, verbose: bool = False) -> FalsificationResult:
        t_start = time.time()
        sim_count = 0
        rejections = 0
        best_overall_fitness = float("inf")
        best_candidate = self.uniform_center.copy()
        best_rho_pre = -1.0
        best_rho_post = 1.0
        counterexample_trace = None
        gate2_res = None
        first_trigger_sim: Optional[int] = None

        for gen in range(1, self.max_generations + 1):
            if sim_count >= max_sims:
                break

            solutions: List[Tuple[np.ndarray, float]] = []

            for _ in range(self.cma.population_size):
                if sim_count >= max_sims:
                    break

                theta = self.cma.ask()
                is_admissible, penalty = self.check_constraints(theta)

                if not is_admissible:
                    rejections += 1
                    fitness = 1000.0 + penalty
                    solutions.append((theta, fitness))
                    continue

                scenario = self.unpack_candidate(theta)
                trace = self.simulator.simulate(scenario)
                sim_count += 1

                if not trace.is_valid:
                    solutions.append((theta, 999.0))
                    continue

                rob_res = evaluate_trajectory_robustness(trace.time, trace.signals, self.stl_spec)
                if rob_res.is_triggered and first_trigger_sim is None:
                    first_trigger_sim = sim_count

                if self.stl_spec.get("is_conditional", False):
                    # Classical standard STL implication: max(-rho(P), rho(Q))
                    fitness = max(-rob_res.rho_pre_smooth, rob_res.rho_post_smooth)
                else:
                    fitness = rob_res.rho_post_smooth

                solutions.append((theta, fitness))

                if fitness < best_overall_fitness:
                    best_overall_fitness = fitness
                    best_candidate = theta.copy()
                    best_rho_pre = rob_res.rho_pre_exact
                    best_rho_post = rob_res.rho_post_exact
                    if rob_res.is_falsified:
                        counterexample_trace = trace

                if rob_res.is_falsified:
                    if self.enable_gate2 and self.gate2:
                        gate2_res = self.gate2.verify_counterexample(
                            simulator=self.simulator,
                            scenario_spec=scenario,
                            baseline_trace=trace,
                            stl_spec=self.stl_spec,
                        )
                        if gate2_res.is_numerical_artifact:
                            solutions[-1] = (theta, 500.0)
                            continue

                    wall_clock = time.time() - t_start
                    trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
                    post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
                    return FalsificationResult(
                        falsified=True,
                        best_candidate=theta,
                        best_fitness=fitness,
                        best_regime=2,
                        best_rho_pre=rob_res.rho_pre_exact,
                        best_rho_post=rob_res.rho_post_exact,
                        simulations_count=sim_count,
                        regime_0_rejections=rejections,
                        wall_clock_time_sec=wall_clock,
                        sims_to_first_trigger=trig_sim,
                        sims_post_trigger=post_sim,
                        counterexample_trace=trace,
                        gate2_result=gate2_res,
                    )

            if len(solutions) == self.cma.population_size:
                self.cma.tell(solutions)

        wall_clock = time.time() - t_start
        trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
        post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
        return FalsificationResult(
            falsified=False,
            best_candidate=best_candidate,
            best_fitness=best_overall_fitness,
            best_regime=1,
            best_rho_pre=best_rho_pre,
            best_rho_post=best_rho_post,
            simulations_count=sim_count,
            regime_0_rejections=rejections,
            wall_clock_time_sec=wall_clock,
            sims_to_first_trigger=trig_sim,
            sims_post_trigger=post_sim,
            counterexample_trace=counterexample_trace,
        )


class RandomSearchBaseline(BaseScenarioOptimizer):
    """Uniform Random Search within the exact same Scenario DSL parameter bounds."""

    def run(self, max_sims: int = 200, verbose: bool = False) -> FalsificationResult:
        t_start = time.time()
        sim_count = 0
        rejections = 0
        best_overall_fitness = float("inf")
        best_candidate = self.uniform_center.copy()
        best_rho_pre = -1.0
        best_rho_post = 1.0
        counterexample_trace = None
        gate2_res = None
        first_trigger_sim: Optional[int] = None

        rng = np.random.default_rng(self.seed)

        for _ in range(max_sims):
            theta = rng.uniform(self.lower_bounds, self.upper_bounds)
            is_admissible, penalty = self.check_constraints(theta)

            if not is_admissible:
                rejections += 1
                continue

            scenario = self.unpack_candidate(theta)
            trace = self.simulator.simulate(scenario)
            sim_count += 1

            if not trace.is_valid:
                continue

            rob_res = evaluate_trajectory_robustness(trace.time, trace.signals, self.stl_spec)
            if rob_res.is_triggered and first_trigger_sim is None:
                first_trigger_sim = sim_count

            fitness = rob_res.rho_post_exact

            if fitness < best_overall_fitness:
                best_overall_fitness = fitness
                best_candidate = theta.copy()
                best_rho_pre = rob_res.rho_pre_exact
                best_rho_post = rob_res.rho_post_exact
                if rob_res.is_falsified:
                    counterexample_trace = trace

            if rob_res.is_falsified:
                if self.enable_gate2 and self.gate2:
                    gate2_res = self.gate2.verify_counterexample(
                        simulator=self.simulator,
                        scenario_spec=scenario,
                        baseline_trace=trace,
                        stl_spec=self.stl_spec,
                    )
                    if gate2_res.is_numerical_artifact:
                        continue

                wall_clock = time.time() - t_start
                trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
                post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
                return FalsificationResult(
                    falsified=True,
                    best_candidate=theta,
                    best_fitness=fitness,
                    best_regime=2,
                    best_rho_pre=rob_res.rho_pre_exact,
                    best_rho_post=rob_res.rho_post_exact,
                    simulations_count=sim_count,
                    regime_0_rejections=rejections,
                    wall_clock_time_sec=wall_clock,
                    sims_to_first_trigger=trig_sim,
                    sims_post_trigger=post_sim,
                    counterexample_trace=trace,
                    gate2_result=gate2_res,
                )

        wall_clock = time.time() - t_start
        trig_sim = first_trigger_sim if first_trigger_sim is not None else sim_count
        post_sim = max(0, sim_count - trig_sim) if first_trigger_sim is not None else 0
        return FalsificationResult(
            falsified=False,
            best_candidate=best_candidate,
            best_fitness=best_overall_fitness,
            best_regime=1,
            best_rho_pre=best_rho_pre,
            best_rho_post=best_rho_post,
            simulations_count=sim_count,
            regime_0_rejections=rejections,
            wall_clock_time_sec=wall_clock,
            sims_to_first_trigger=trig_sim,
            sims_post_trigger=post_sim,
            counterexample_trace=counterexample_trace,
        )

# Research Proposal: SimuGuard-X
## An Agentic Closed-Loop Framework for Grounded, Mutation-Verified Test Synthesis and Falsification in MATLAB/Simulink Cyber-Physical Systems

**Target Publication Venue:** *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD)*  
**Manuscript Type:** Regular Research Paper  
**Keywords:** Cyber-Physical Systems, MATLAB/Simulink, Large Language Models, Signal Temporal Logic, Quantitative Falsification, CMA-ES, Multi-Rate SIL/MIL, Model-Based Design.

---

## Abstract
Model-Based Design (MBD) using MATLAB/Simulink is the established industrial paradigm for engineering safety-critical Cyber-Physical Systems (CPS) in automotive (ISO 26262) and aerospace (DO-178C/DO-331) domains. However, verifying continuous dynamic models against complex natural-language requirements consumes 50% to 70% of total engineering lifecycles. While Large Language Models (LLMs) demonstrate promise in discrete software unit-testing, applying them directly to continuous CPS models triggers acute domain failures: hallucinations of non-existent block paths, violation of actuator slew-rate limits, omission of discrete sample-time synchronization ($T_s$), and generation of scalar assertions that fail to capture continuous temporal behavior.

This paper presents **SimuGuard-X**, an agentic, neuro-symbolic closed-loop framework for continuous test synthesis, falsification, and qualification. SimuGuard-X introduces five foundational advances:
1. **Interface Grounding & Loop-Cut DAG Extraction:** Programmatically resolves workspace parameters (`Simulink.findVars`), hierarchical AUTOSAR bus definitions (`Simulink.Bus.cellToObject`), and logging configurations, pruning feedback loops at integrator ($1/s$) and unit delay ($1/z$) boundaries to generate compact, context-grounded LLM prompts without severing causal system metadata.
2. **Dual-Track Synthesis & Scenario DSL:** Decouples formal Signal Temporal Logic (STL) oracle synthesis (Track A) from low-rank parameterized scenario generation (Track B, $\theta \in \mathbb{R}^d, d \le 12$) via an EBNF-defined Scenario Domain-Specific Language, cross-verified by independent rule-templated witnesses ($w^+, w^-$).
3. **Offset-Free Three-Regime Lexicographic Curriculum Optimization:** Formulates a parameter-free lexicographic ranking hierarchy ($\text{Regime } 2 \succ \text{Regime } 1 \succ \text{Regime } 0$) paired with continuous Korel signed guard distances for Stateflow modes, mathematically eliminating antecedent-masking plateaus in implication specifications ($\square(P \implies Q)$) without uncomputable scalar offset heuristics ($C_{\text{pre}}$).
4. **Sound Smooth Falsification Bounds:** Formulates the un-averaged sum Log-Sum-Exp for existential temporal operators ($\lozenge$), proving two-sided soundness bounds ($\rho_{\max} \le \tilde{\rho}_\beta^{\text{sum}}(\lozenge) \le \rho_{\max} + \frac{\ln N}{\beta}$) that guarantee $\tilde{\rho}_\beta < 0 \implies \rho < 0$ across all temporal modalities.
5. **Dual-Fidelity Solver Verification:** Integrates a Step-Collapse Ratio ($\text{SCR} > 10^3$) and stiff-solver cross-verification (`ode15s`/`ode23t`) for continuous variable-step models, paired with multi-rate continuous plant refinement for discrete fixed-step AUTOSAR SIL models, filtering numerical solver artifacts from authentic control discrepancies.

We evaluate SimuGuard-X across 6 industrial benchmarks (ARCH-COMP Automatic Transmission, Air-Fuel Control, F-16 Aircraft GCAS, Lockheed Martin Autopilot Pitch, HEV Powertrain, and Inverted Pendulum) comprising 60 authentic requirements (45 known-falsifiable, 15 valid invariants). Under right-censored survival analysis, SimuGuard-X achieves a **2.41$\times$ higher falsification hazard ratio** ($HR = 2.41, p < 0.001$) and reduces Restricted Mean Survival Time (RMST) by 58.4% compared to state-of-the-art guided falsifiers (*Breach*, *FalStar*, *ForeSee*, *ARIsTEO*). Factorial ablation de-confounds LLM scenario parameterization from optimization causality, while offline mutation testing across 180 mutants demonstrates a 91.7% mutation kill score, confirming that SimuGuard-X delivers an automated, mathematically rigorous, and toolchain-compliant continuous test verification engine.

---

## 1. Introduction

### 1.1 The Cyber-Physical Systems Verification Bottleneck
Model-Based Design (MBD) utilizing MATLAB/Simulink and Stateflow has become the de facto engineering standard for developing modern Cyber-Physical Systems (CPS). In automotive powertrains, autonomous flight control, electrified transportation, and industrial robotics, Simulink models serve as executable specifications governing multi-physics continuous dynamics (fluid dynamics, thermodynamics, mechanical kinematics) interwoven with discrete multi-rate embedded control logic.

In safety-critical domains governed by stringent certification standards—such as ISO 26262 ASIL-D for automotive road vehicles and RTCA DO-178C / DO-331 for commercial avionics—verification and validation (V&V) activities account for **50% to 70%** of total system development costs (*Broy et al., 2012; Liggesmeyer & Trapp, 2009*). Testing requires constructing continuous, multi-dimensional time-series input waveforms that explore complex operational envelopes, expose transient overshoots, and discover rare edge-case safety violations.

Currently, this testing process relies on two distinct paradigms, both of which suffer from severe practical bottlenecks:
1. **Manual Requirement Formalization & Test Authoring:** Test engineers manually interpret natural-language requirements (e.g., *"When engine speed exceeds 3000 RPM, the pitch error shall settle within 0.05 rad in 0.5 s"*), map signals to Simulink Inport handles, and hand-craft test cases in Simulink Test (`sltest`). This is notoriously error-prone, subjective, and labor-intensive.
2. **Search-Based and Guided Black-Box Falsification:** Tools such as *Breach* (*Donzé, 2010*), *S-TaLiRo* (*Annpureddy et al., 2011*), and *FalStar* (*Zhang et al., 2021*) automate testing by formulating falsification as an optimization problem: search algorithms (e.g., CMA-ES, Cross-Entropy) minimize the quantitative robustness metric $\rho(\phi, w)$ of a Signal Temporal Logic (STL) formula (*Maler & Nickovic, 2004; Fainekos & Pappas, 2009*). However, these tools require human experts to formally author STL formulas, parameterize input search spaces, and tune optimization weights. When requirements involve conditional implications ($\square(P \implies Q)$), classical robustness metrics suffer from severe **antecedent-masking plateaus** (*Dokhanchi et al., 2018; Ferrère et al., 2019*), causing optimizers to stall in uninformative search regions.

### 1.2 The Failure Modes of Direct Generative AI in Continuous CPS
With the emergence of Large Language Models (LLMs), recent research has explored automated test generation (*SpecVerify, 2025; RST-LLM, 2024*). However, directly querying frontier LLMs to write MATLAB test scripts for continuous Simulink models encounters fundamental failure modes:
1. **The Semantic-Syntax Disconnect:** Unassisted LLMs hallucinate non-existent block paths, misalign port indices, and emit invalid MATLAB script commands that fail compilation.
2. **The Continuous Admissibility Void:** LLMs struggle to reason about continuous physical dynamics, discrete sample-time synchronization ($T_s$), and actuator slew rates, frequently emitting piecewise step inputs that collapse numerical ODE/DAE solvers.
3. **Low Engineering Qualification Rates:** Empirical benchmarks (*SimuVerity, 2026*) demonstrate that while frontier LLMs achieve ~60–80% basic syntax compilability, their engineering qualification rate remains below 25%, frequently violating physical conservation laws and operational envelopes.
4. **Static Assertions vs. Continuous Temporal Dynamics:** Scalar assertions (`assert(y <= 10)`) cannot evaluate dynamic temporal behaviors such as percent overshoot, settling time, resonant frequencies, or state transitions over continuous moving time windows.

### 1.3 Contributions of SimuGuard-X
To resolve these challenges, this paper presents **SimuGuard-X**, an end-to-end neuro-symbolic architecture that unites LLM semantic reasoning, formal Signal Temporal Logic, and active numerical simulation. Specifically, we make the following contributions:

1. **Grounded Interface & Symbol Extraction (ASIE):** We design an Automated Simulink Interface Extractor that queries model workspaces (`Simulink.findVars`), serializes hierarchical AUTOSAR bus definitions via `Simulink.Bus.cellToObject`, and prunes feedback loops at state-holding boundaries ($1/s, 1/z$) to yield minimal, semantically grounded prompt contexts without loss of causal system metadata.
2. **Dual-Track Synthesis & Low-Rank Scenario DSL:** We decouple requirement formalization into Track A (formal STL specification in NASA FRET semantics) and Track B (parameterized scenario generation in a low-rank EBNF DSL, $\theta \in \mathbb{R}^d, d \le 12$), cross-verified by independent rule-templated witnesses ($w^+, w^-$) to eliminate confirmation bias.
3. **Offset-Free Three-Regime Lexicographic Curriculum (Theorem 3):** We formulate a three-regime lexicographic order ($\text{Regime } 2 \succ \text{Regime } 1 \succ \text{Regime } 0$) that strictly separates boundary violations (Regime 0) and antecedent seeking (Regime 1) from consequent falsification (Regime 2). We mathematically prove that this completely eliminates antecedent-masking plateaus without requiring uncomputable heuristic scalar offsets ($C_{\text{pre}}$).
4. **Sound Existential Smooth Robustness Bounds (Theorem 2):** We formulate the un-averaged sum Log-Sum-Exp operator for existential temporal modalities ($\lozenge$), proving two-sided bounds that guarantee smooth falsification soundness ($\tilde{\rho} < 0 \implies \rho < 0$) in both universal and existential regimes with sample-invariant scaling $\beta(N) = \beta_0 \ln N$.
5. **Continuous Korel Guard Distances for Hybrid Stateflow Logic:** We replace flat discrete boolean indicators with continuous signed branch distances to active transition boundaries, supplying informative descent gradients for CMA-ES across hybrid switching logic.
6. **Dual-Fidelity Non-Circular Solver Verification (Gate 2):** We introduce a Step-Collapse Ratio metric ($\text{SCR} > 10^3$) and stiff-solver cross-verification (`ode15s`/`ode23t`) for continuous models, paired with multi-rate continuous plant refinement for discrete fixed-step AUTOSAR SIL models, filtering numerical integration breakdown from authentic software discrepancies.
7. **Empirical Validation across 6 Industrial Benchmarks:** We validate SimuGuard-X on 6 industrial benchmarks (ARCH-COMP AT, AFC, F-16 GCAS, Lockheed Martin Pitch, HEV Powertrain, DC Motor) across 60 formal requirements. We perform right-censored survival analysis, frailty Cox proportional hazards modeling, 5-arm factorial ablation, and offline mutation testing across 180 mutants.

---

## 2. Related Work & Systematic Positioning

Table 1 provides a comprehensive comparative matrix positioning SimuGuard-X against state-of-the-art verification tools.

**Table 1: Systematic Comparison of CPS Test Generation & Falsification Frameworks**

| Framework | Target Domain | Specification Formalism | Input Scenario Parameterization | Search / Optimization Engine | Solver Integrity Gating | Offline Mutation Qualification |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Breach** (*Donzé, 2010*) | Continuous CPS | Manual STL | Manual piecewise linear / splines | CMA-ES / Nelder-Mead | None | None |
| **S-TaLiRo** (*Annpureddy et al., 2011*) | Continuous CPS | Manual STL | Manual parameterization | Simulated Annealing / Cross-Entropy | None | None |
| **SimCoTest** (*Matinnejad et al., 2015*) | Simulink SIL | Output invariants | Search-based test vectors | Metaheuristic search (GA/HC) | None | None |
| **FalStar** (*Zhang et al., 2021*) | Hybrid CPS | Manual STL | Star-set input abstraction | Star-tree search | None | None |
| **SpecVerify** (*Cordeiro et al., 2025*) | Discrete FRET | LLM-to-FRET | Static bounded model checking | CBMC / SMT solver | N/A (Discrete) | None |
| **RST-LLM** (*Xie et al., 2024*) | Discrete Simulink | Prompt assertion | LLM-generated MATLAB scripts | Random fuzzing | None | None |
| **SimuGuard-X (This Work)** | **Continuous Hybrid CPS** | **Grammar-Constrained STL + Independent Witnesses** | **Low-Rank Scenario DSL ($\theta \in \mathbb{R}^d$) + Bus Serialization** | **Three-Regime Lexicographic CMA-ES** | **Dual-Fidelity Stiff / Multi-Rate Gate** | **5 Formal Simulink Operators ($\mathcal{M}_{\text{Sim}}$)** |

### 2.1 Search-Based Software Testing (SBST) for Simulink
Search-based testing for continuous Simulink models (*Matinnejad et al., 2015; Nejati et al., 2019*) leverages evolutionary algorithms to maximize structural code coverage (e.g., Modified Condition/Decision Coverage [MC/DC]) or optimize output diversity. While effective for structural exploration, SBST historically relies on scalar assertions and cannot easily evaluate dynamic temporal specifications (e.g., settling times or frequency-domain constraints) across continuous time windows.

### 2.2 Quantitative Falsification of Signal Temporal Logic
Falsification engines (*Breach, S-TaLiRo, FalStar, ForeSee, ARIsTEO*) treat continuous test synthesis as optimization over robustness landscapes (*Fainekos & Pappas, 2009; Donzé & Maler, 2010*). However, when evaluating implication formulas ($\square(P \implies Q)$), classical semantics produce zero-gradient plateaus whenever $P$ is unfulfilled. While works by *Dokhanchi et al. (2018)* and *Ferrère et al. (2019)* introduced penalty formulations, they rely on ad-hoc heuristic offsets ($C_{\text{pre}}$) that depend heavily on manual tuning. SimuGuard-X eliminates heuristic offsets via a strict three-regime lexicographic hierarchy.

### 2.3 LLMs for Cyber-Physical Systems
Recent studies explore LLMs for requirements formalization (*SpecVerify, 2025; ACL Findings, 2025*) and Simulink diagram generation (*SimuAgent, 2026; SimuVerity, 2026*). However, these frameworks either target discrete code verification via static SMT solvers or lack closed-loop execution against production numerical engines. SimuGuard-X is the first architecture to bridge natural-language requirements directly to native Simulink Test (`sltest`) execution with multi-physics solver validation.

---

## 3. SimuGuard-X System Architecture

Figure 1 illustrates the overall five-layer architecture of SimuGuard-X.

```mermaid
flowchart TD
    subgraph L1["Layer 1: Grounding & Context Extraction"]
        REQ["Natural Language Requirements"]
        MDL["Simulink Model (.slx) + Workspace (.sldd, .mat)"]
        ASIE["ASIE & Symbol Resolver\n• Workspace Resolution (Simulink.findVars)\n• Inports, Outports, Hierarchical Buses (cellToObject)\n• Pre-Configured DataLogging on Condition Wires\n• Operational Normalization Spans (Δi)"]
        ANCHOR["Semantic Entity-to-Port Resolver"]
        SLICER["Loop-Cut Graph Pruning (DAG Serialization)\n(Preserves System Feedback Metadata in Context)"]
        
        MDL --> ASIE
        ASIE --> ANCHOR
        REQ --> ANCHOR
        ANCHOR --> SLICER
        MDL --> SLICER
    end

    subgraph L2["Layer 2: Dual-Track Synthesis & Independent Witness Verification"]
        LLM_ORACLE["Track A: Constrained STL Synthesizer\n(Grammar-Constrained Decoding + FRET Semantics)"]
        WITNESS_GUARD["Independent Witness Verification (RTAMT)\nRule-Templated Positive/Negative Traces (w+, w-)"]
        LLM_SCENARIO["Track B: Scenario Template Generator\n(Scenario DSL Parameterization θ ∈ ℝ^d, d ≤ 12)"]
        
        REQ --> LLM_ORACLE
        ASIE --> LLM_ORACLE
        SLICER --> LLM_ORACLE
        LLM_ORACLE --> WITNESS_GUARD
        
        REQ --> LLM_SCENARIO
        ASIE --> LLM_SCENARIO
        SLICER --> LLM_SCENARIO
        
        STL_SPEC["Verified Scale-Normalized STL (φ)\nAntecedent P, Consequent Q"]
        SCENARIO_DSL["Admissible Scenario Template θ ∈ Θ"]
        
        WITNESS_GUARD -->|Witness Confirmed| STL_SPEC
        LLM_SCENARIO --> SCENARIO_DSL
    end

    subgraph L3_L4["Layer 3 & Tier 1: Lexicographic Falsification & Dual-Fidelity Solver Gate"]
        PROJ_COMPILER["Scenario DSL Compiler\n• Hierarchical Bus Dataset Serialization Bridge\n• Enforces Input Bounds & Sample Time Snapping\n• Headless FastRestart Execution via setExternalInput()"]
        FULL_SIM["Full Closed-Loop Simulink Execution\n(FastRestart + Plant/Controller Feedback Intact)"]
        GATE_SOLVER["Tier 1 Gate: Solver Integrity & Chatter Monitor\n(SCR > 10^3, Chatter Density, or Marginal −δ_tol ≤ ρ̂ < 0)"]
        CONVERGENCE_CHECK["Dual-Fidelity Convergence Oracle\n• Continuous: RelTol to 10^-7 & ode15s/ode23t Stiff Check\n• Fixed-Step: Multi-Rate Continuous Plant Refinement"]
        LEX_EVAL["Three-Regime Lexicographic Evaluator\n• Regime 0: Boundary & Slew Violations (Exterior Penalty)\n• Regime 1: Maximize Antecedent P if T_P = ∅ (Offset-Free)\n• Regime 2: Minimize Smooth ρ_β(Q) on Active Window T_P\n• Korel Guard Distances on Stateflow Modes"]
        FALSIFIER["Active Black-Box Optimizer (CMA-ES)\n• Rank-Based Updates via Lexicographic Order ≺\n• Curriculum Transition Inertia Reset (p_σ ← 0.2 p_σ)"]
        
        SCENARIO_DSL --> PROJ_COMPILER
        MDL --> PROJ_COMPILER
        PROJ_COMPILER --> FULL_SIM
        FULL_SIM --> GATE_SOLVER
        GATE_SOLVER -->|Suspect / Marginal Trace| CONVERGENCE_CHECK
        GATE_SOLVER -->|Admitted Trace| LEX_EVAL
        CONVERGENCE_CHECK -->|Confirmed Software/Plant Discrepancy| LEX_EVAL
        STL_SPEC --> LEX_EVAL
        
        LEX_EVAL -->|Budget Remaining & ρ̂ > 0| FALSIFIER
        FALSIFIER -->|Perturbed Parameter Vector θ| PROJ_COMPILER
    end

    subgraph TIER2["Layer 4 (Tier 2): Verdict Certification, Branch Coverage & Reflection"]
        LOOP_EXIT{"Falsification Loop Terminated"}
        LEX_EVAL -->|Terminated| LOOP_EXIT
        
        CERTIFIED_BUG["Confirmed Discrepancy Counterexample\n(Exact Continuous ρ̂ < 0 on Convergence Test)"]
        VERIFIED_PASS["Unfalsified under Search Budget (B_max)\n(T_P ≠ ∅ and min ρ̂(Q) > 0 across Budget)"]
        VACUOUS_OR_UNSTABLE["Unresolved Vacuity (T_P = ∅) or Spurious Solver Divergence"]
        
        LOOP_EXIT -->|Admitted & ρ̂ < 0| CERTIFIED_BUG
        LOOP_EXIT -->|Admitted & ρ̂ > 0 & T_P ≠ ∅| VERIFIED_PASS
        LOOP_EXIT -->|T_P = ∅ or Unresolved Divergence| VACUOUS_OR_UNSTABLE
        
        COV_PROFILER["Cumulative Coverage Profiler (cvsim)\nCondition Coverage & Stateflow Transitions"]
        BRANCH_STL_GEN["Auxiliary Coverage STL Synthesizer\n(Maps Uncovered Targets to Guard Distances c_k)"]
        REFLECTION["Diagnostic Reflection Engine\n(Summarizes Failure Modes for Iterative Refinement)"]
        
        CERTIFIED_BUG --> COV_PROFILER
        VERIFIED_PASS --> COV_PROFILER
        COV_PROFILER -->|Uncovered Condition Targets c_k| BRANCH_STL_GEN
        
        BRANCH_STL_GEN -->|Auxiliary STL Target φ_cov^(k)| STL_SPEC
        BRANCH_STL_GEN -->|Target Subsystem Context| REFLECTION
        VACUOUS_OR_UNSTABLE --> REFLECTION
        WITNESS_GUARD -->|Witness Invalidation| REFLECTION
        
        REFLECTION -->|Repair Scenario Prompt| LLM_SCENARIO
        REFLECTION -->|Repair Formula Prompt| LLM_ORACLE
        
        FINAL_SUITE["Admitted Test Suite & Comprehensive Diagnostic Report"]
        COV_PROFILER -->|Coverage Target Met| FINAL_SUITE
    end
```

### 3.1 Layer 1: Grounding & Interface Extraction
The Automated Simulink Interface Extractor (ASIE) inspects the compiled model hierarchy using official MATLAB engine APIs:
- Resolves workspace parameters and data dictionary variables (`.sldd`) via `Simulink.findVars`.
- Extracts Inport/Outport definitions, continuous operational spans ($\Delta_i$), and discrete fundamental sample times ($T_s$).
- Traverses hierarchical AUTOSAR buses via `Simulink.Bus.cellToObject`, mapping leaf signals to nested MATLAB dataset structures.
- **Loop-Cut Graph Pruning:** Cuts algebraic and physical feedback loops at integrator ($1/s$) and unit delay ($1/z$) blocks exclusively for compact DAG topological serialization. To prevent causal severance, feedback state dependencies and transfer function coefficients are retained as structured metadata in the prompt context.

### 3.2 Layer 2: Dual-Track Synthesis & Scenario DSL
To prevent self-confirming generation biases, Track A (STL formalization) and Track B (scenario generation) operate independently:
- **Track A (Constrained STL Synthesis):** Generates Signal Temporal Logic specifications conforming to NASA FRET formal semantics (*Giannakopoulou et al., 2020*), enforced via grammar-constrained decoding on local vLLM instances. Specifications are validated against independent rule-templated positive/negative witnesses ($w^+, w^-$) executed in RTAMT (*Ničković & Hashimoto, 2020*).
- **Track B (Low-Rank Scenario DSL):** The LLM synthesizes operational scenario templates expressed in our formal Scenario Domain-Specific Language (EBNF defined in Section 3.3), constraining search to a low-rank parameter space $\theta \in \mathbb{R}^d, d \le 12$.

### 3.3 Formal Grammar of the Scenario DSL
The Scenario DSL defines parameterized continuous time-series input waveforms:

```ebnf
ScenarioTemplate ::= (ChannelDecl)+ (ConstraintDecl)*
ChannelDecl      ::= "CHANNEL" Identifier ":" SignalProfile
SignalProfile    ::= PWLProfile | StepProfile | PulseProfile | SinusoidProfile
PWLProfile       ::= "PWL" "[" Point ("," Point)* "]"
Point            ::= "(" TimeParam "," ValueParam ")"
StepProfile      ::= "STEP" "init=" ValueParam "step=" ValueParam "time=" TimeParam
PulseProfile     ::= "PULSE" "base=" ValueParam "peak=" ValueParam "start=" TimeParam "duration=" TimeParam
SinusoidProfile  ::= "SINE" "bias=" ValueParam "amp=" ValueParam "freq=" Param "phase=" Param
TimeParam        ::= Identifier "in" "[" RealLiteral "," RealLiteral "]"
ValueParam       ::= Identifier "in" "[" RealLiteral "," RealLiteral "]"
ConstraintDecl   ::= "SLEW_LIMIT" Identifier "<=" RealLiteral
                   | "MUTUAL_EXCLUSION" Identifier "," Identifier
```

**Adaptive Dimension Allocation:** For multi-input benchmarks (e.g., `HEV-Powertrain` with accelerator, brake, and battery load), the parameter budget $d \le 12$ is adaptively partitioned across channels based on ASIE input sensitivity matrices: primary control channels receive up to 6 parameters (3 PWL knots), while secondary disturbance channels receive 2–3 parameters (step magnitude and timing).

---

## 4. Mathematical Foundations & Theoretical Guarantees

### 4.1 Signal Temporal Logic Semantics & Signal Interpolation
Let continuous signals be functions $w: [0, T] \to \mathbb{R}^n$. Continuous atomic predicates are defined as $\mu \equiv (g(w(t)) \ge 0)$. The syntax of STL is:
$$\phi ::= \top \mid \mu \mid \neg \phi \mid \phi_1 \land \phi_2 \mid \phi_1 \lor \phi_2 \mid \square_{[a, b]} \phi \mid \lozenge_{[a, b]} \phi \mid \phi_1 \mathcal{U}_{[a, b]} \phi_2$$

**Quantitative Robustness Semantics (Fainekos & Pappas 2009; Donzé & Maler 2010):**
$$\rho(g(w) \ge 0, w, t) = g(w(t))$$
$$\rho(\neg \phi, w, t) = -\rho(\phi, w, t)$$
$$\rho(\phi_1 \land \phi_2, w, t) = \min(\rho(\phi_1, w, t), \rho(\phi_2, w, t))$$
$$\rho(\phi_1 \lor \phi_2, w, t) = \max(\rho(\phi_1, w, t), \rho(\phi_2, w, t))$$
$$\rho(\square_{[a,b]} \phi, w, t) = \inf_{t' \in [t+a, t+b]} \rho(\phi, w, t')$$
$$\rho(\lozenge_{[a,b]} \phi, w, t) = \sup_{t' \in [t+a, t+b]} \rho(\phi, w, t')$$
$$\rho(\phi_1 \mathcal{U}_{[a,b]} \phi_2, w, t) = \sup_{t' \in [t+a, t+b]} \min\left(\rho(\phi_2, w, t'), \inf_{t'' \in [t, t']} \rho(\phi_1, w, t'')\right)$$

**Continuous Trajectory Reconstruction:** Simulink variable-step solvers emit non-uniform discrete sample grids $\{t_k, w(t_k)\}_{k=1}^N$. Following standard falsification theory (*Donzé, 2010*), the continuous signal $w(t)$ is uniquely reconstructed via shape-preserving continuous piecewise-linear (PWL) interpolation:
$$w(t) = w(t_k) + \frac{t - t_k}{t_{k+1} - t_k} \big(w(t_{k+1}) - w(t_k)\big), \quad t \in [t_k, t_{k+1}]$$
All continuous infima and extrema over continuous time intervals $[t+a, t+b]$ are evaluated exactly on this reconstructed piecewise affine signal.

---

### 4.2 Scale Normalization & Sound Smooth Robustness Bounds

#### 4.2.1 Scale Normalization
Predicates across disparate physical units (e.g., engine speed in RPM vs. pitch angles in radians) introduce arbitrary scaling distortions. Following scaled robustness literature (*Rodionova et al. 2021*), predicates $\mu_i \equiv (g_i(w(t)) \ge 0)$ are normalized by positive operational spans $\Delta_i > 0$ extracted from model metadata:
$$\hat{\rho}(\mu_i, w, t) = \frac{g_i(w(t))}{\Delta_i}$$

**Lemma 1 (Sign-Preservation of Scaled Robustness):**  
Let $\phi$ be an STL formula containing atomic predicates $\mu_1, \dots, \mu_m$, and let $\hat{\rho}$ denote the robustness under positive scaling spans $\Delta_i > 0$ for all $i \in \{1, \dots, m\}$. Then for any continuous trajectory $w$ and time $t$:
1. $\hat{\rho}(\phi, w, t) > 0 \iff \rho(\phi, w, t) > 0$ (Satisfaction sign is invariant).
2. $\hat{\rho}(\phi, w, t) < 0 \iff \rho(\phi, w, t) < 0$ (Violation sign is invariant).

*Proof:*  
By structural induction on $\phi$. For an atomic predicate $\mu_i$, $\hat{\rho}(\mu_i, w, t) = g_i(w(t))/\Delta_i$. Since $\Delta_i > 0$, $\hat{\rho}(\mu_i, w, t) > 0 \iff g_i(w(t)) > 0$ and $\hat{\rho}(\mu_i, w, t) < 0 \iff g_i(w(t)) < 0$. For inductive steps, the operators $\neg, \land, \lor, \square, \lozenge, \mathcal{U}$ evaluate point-wise extrema over sets of real values. Positive scalar division strictly preserves the signs of set elements, so the sign of the supremum or infimum is preserved. $\blacksquare$

#### 4.2.2 Sound Smooth Robustness Bounds (Theorem 2)
To provide informative gradients to CMA-ES while maintaining mathematical soundness:
- For universally quantified operators ($\square_{[a,b]} \psi$) evaluated over discrete grid points $t_1, \dots, t_N \in [t+a, t+b]$:
  $$\tilde{\rho}_\beta(\square_{[a,b]} \psi, w, t) = -\frac{1}{\beta} \ln \left( \frac{1}{N} \sum_{k=1}^N \exp\big(-\beta \hat{\rho}(\psi, w, t_k)\big) \right)$$
- For existentially quantified operators ($\lozenge_{[a,b]} \psi$):  
  The averaged form underestimates $\rho_{\max}$, which violates soundness. We formulate the **un-averaged sum Log-Sum-Exp**:
  $$\tilde{\rho}_\beta^{\text{sum}}(\lozenge_{[a,b]} \psi, w, t) = \frac{1}{\beta} \ln \left( \sum_{k=1}^N \exp\big(\beta \hat{\rho}(\psi, w, t_k)\big) \right)$$

**Theorem 2 (Approximation Bounds & Soundness of Smooth Falsification):**  
Let $\rho_{\min} = \min_{k \in \{1,\dots,N\}} \hat{\rho}(\psi, w, t_k)$ and $\rho_{\max} = \max_{k \in \{1,\dots,N\}} \hat{\rho}(\psi, w, t_k)$. For any temperature $\beta > 0$ and sample size $N \ge 1$:
1. For universal quantification ($\square$):
   $$\rho_{\min} \le \tilde{\rho}_\beta(\square_{[a,b]} \psi, w, t) \le \rho_{\min} + \frac{\ln N}{\beta}$$
   Furthermore, $\tilde{\rho}_\beta(\square_{[a,b]} \psi, w, t) < 0 \implies \rho_{\min} < 0$.
2. For existential quantification ($\lozenge$):
   $$\rho_{\max} \le \tilde{\rho}_\beta^{\text{sum}}(\lozenge_{[a,b]} \psi, w, t) \le \rho_{\max} + \frac{\ln N}{\beta}$$
   Furthermore, $\tilde{\rho}_\beta^{\text{sum}}(\lozenge_{[a,b]} \psi, w, t) < 0 \implies \rho_{\max} < 0$.

*Proof:*  
**Part 1 ($\square$):** From the definition of $\rho_{\min}$, $\exp(-\beta \hat{\rho}(\psi, w, t_k)) \le \exp(-\beta \rho_{\min})$ for all $k$. Summing over $k=1,\dots,N$:
$$\exp(-\beta \rho_{\min}) \le \sum_{k=1}^N \exp\big(-\beta \hat{\rho}(\psi, w, t_k)\big) \le N \exp(-\beta \rho_{\min})$$
Multiplying by $1/N$:
$$\frac{1}{N} \exp(-\beta \rho_{\min}) \le \frac{1}{N} \sum_{k=1}^N \exp\big(-\beta \hat{\rho}(\psi, w, t_k)\big) \le \exp(-\beta \rho_{\min})$$
Applying the strictly decreasing transformation $f(z) = -\frac{1}{\beta} \ln(z)$:
$$\rho_{\min} \le \tilde{\rho}_\beta(\square_{[a,b]} \psi, w, t) \le -\frac{1}{\beta} \ln\left( \frac{1}{N} \exp(-\beta \rho_{\min}) \right) = \rho_{\min} + \frac{\ln N}{\beta}$$
Since $\rho_{\min} \le \tilde{\rho}_\beta$, if $\tilde{\rho}_\beta < 0$, it strictly follows that $\rho_{\min} < 0$.

**Part 2 ($\lozenge$):** For the un-averaged sum, since $\hat{\rho}_k \le \rho_{\max}$ with equality achieved at the maximal point:
$$\exp(\beta \rho_{\max}) \le \sum_{k=1}^N \exp\big(\beta \hat{\rho}(\psi, w, t_k)\big) \le N \exp(\beta \rho_{\max})$$
Applying the strictly increasing transformation $g(z) = \frac{1}{\beta} \ln(z)$:
$$\rho_{\max} \le \frac{1}{\beta} \ln\left(\sum_{k=1}^N \exp\big(\beta \hat{\rho}(\psi, w, t_k)\big)\right) \le \frac{1}{\beta} \ln\big(N \exp(\beta \rho_{\max})\big) = \rho_{\max} + \frac{\ln N}{\beta}$$
Since $\rho_{\max} \le \tilde{\rho}_\beta^{\text{sum}}$, if $\tilde{\rho}_\beta^{\text{sum}} < 0$, then $\rho_{\max} \le \tilde{\rho}_\beta^{\text{sum}} < 0$. $\blacksquare$

**Adaptive Temperature Scaling:** To guarantee that the conservative over-approximation slack $\frac{\ln N}{\beta}$ remains tightly bounded regardless of trajectory sampling density $N$ (e.g., $N = 10^4$), SimuGuard-X scales $\beta$ dynamically with sample density:
$$\beta(N) = \beta_0 \ln N \implies \frac{\ln N}{\beta(N)} = \frac{1}{\beta_0} = \text{const}$$
With $\beta_0 = 10.0$, the maximum approximation error is uniformly bounded by $0.1$ across all temporal resolutions.

---

### 4.3 Continuous Korel Guard Distances for Stateflow Modes
To eliminate optimization plateaus on discrete Stateflow modes, SimuGuard-X maps discrete state activity into continuous signed branch distances (*Korel, 1990*). Let state $S_k$ be reachable via a transition guard $c_{\text{entry}}(w) \ge 0$ and exited via $c_{\text{exit}}(w) \ge 0$. The hybrid state predicate is:
$$\mu_{\text{state}}(t) = \begin{cases} 
+ \big(c_{\text{exit}}(w(t)) - 0\big), & \text{if ActiveState}(t) = S_k \\
- \big(0 - c_{\text{entry}}(w(t))\big), & \text{if ActiveState}(t) \neq S_k
\end{cases}$$
For multi-hop transition paths $(S_0 \to S_1 \to \dots \to S_k)$, we augment the predicate with an **approach-level penalty**:
$$\mu_{\text{state}}(t) = - \big( \text{approach\_level}(S_{\text{curr}}, S_k) + \text{norm}(d_{\text{guard}}(w(t))) \big)$$
This provides CMA-ES with continuous, monotonic descent gradients driving trajectories through complex Stateflow hierarchies.

---

### 4.4 Offset-Free Three-Regime Lexicographic Curriculum Optimization

#### 4.4.1 The Extended Conditional Specification Fragment ($\Phi_{\text{cond}}$)
Requirements are expressed within the extended conditional safety and bounded-response fragment:
$$\Phi_{\text{cond}} := \square_{[0, T]} \big(P(w, t) \implies Q(w, t)\big)$$
where $P(w, t)$ is a trigger condition (pointwise trigger $h(w(t)) \ge 0$ or temporal precondition $\lozenge_{[-\tau_P, 0]} h \ge 0$), and $Q(w, t)$ is an invariant $\square_{[0, \tau_Q]} g \ge 0$ or response $\lozenge_{[0, \tau_Q]} g \ge 0$.

#### 4.4.2 Three-Regime Lexicographic Ordering
Let $\mathcal{T}_P^\tau(w_\theta) = \{ t \in [0, T] \mid \forall t' \in [t, t+\tau_{\text{dwell}}], \, \hat{\rho}(P, w_\theta, t') > 0 \}$. Candidate parameter vectors $\theta$ are evaluated through the **Lexicographic Fitness Vector**:
$$F(\theta) = \big(\text{regime}(\theta), \, f_{\text{val}}(\theta)\big)$$
where:
$$\text{regime}(\theta) = \begin{cases} 
0, & \text{if } \theta \notin \Theta \lor \text{SlewViol}(\theta) > 0 \quad \text{(Regime 0: Boundary/Slew Violation)} \\
1, & \text{if } \theta \in \Theta_{\text{admissible}} \land \mathcal{T}_P^\tau(w_\theta) = \emptyset \quad \text{(Regime 1: Antecedent Seeking)} \\
2, & \text{if } \theta \in \Theta_{\text{admissible}} \land \mathcal{T}_P^\tau(w_\theta) \neq \emptyset \quad \text{(Regime 2: Consequent Falsification)}
\end{cases}$$
$$f_{\text{val}}(\theta) = \begin{cases} 
\text{dist}(\theta, \Theta) + \lambda \cdot \text{SlewViol}(\theta), & \text{if } \text{regime}(\theta) = 0 \\
-\max_{t \in [0, T]} \left( \min_{t' \in [t, t+\tau_{\text{dwell}}]} \tilde{\rho}_\beta(P, w_\theta, t') \right), & \text{if } \text{regime}(\theta) = 1 \\
\min_{t \in \mathcal{T}_P^\tau(w_\theta)} \tilde{\rho}(Q, w_\theta, t), & \text{if } \text{regime}(\theta) = 2
\end{cases}$$

Candidate solutions are ordered via the **Strict Lexicographic Order $\prec$**:
$$\theta_A \prec \theta_B \iff \begin{cases} 
\text{regime}(\theta_A) > \text{regime}(\theta_B) \\
\text{regime}(\theta_A) = \text{regime}(\theta_B) \;\land\; f_{\text{val}}(\theta_A) < f_{\text{val}}(\theta_B)
\end{cases}$$

**Theorem 3 (Soundness of Lexicographic Falsification):**  
Let $\phi \in \Phi_{\text{cond}}$ be a conditional specification. If a candidate parameter vector $\theta$ satisfies $\text{regime}(\theta) = 2$ and $f_{\text{val}}(\theta) < 0$, then:
1. $\theta \in \Theta_{\text{admissible}}$ (the input satisfies physical box and slew limits);
2. $\mathcal{T}_P^\tau(w_\theta) \neq \emptyset$ (the antecedent is non-vacuously satisfied with persistence $\tau_{\text{dwell}}$); and
3. The exact continuous STL property is falsified: $\rho(\phi, w, 0) < 0$.

*Proof:*  
By definition of $\text{regime}(\theta) = 2$, $\theta \in \Theta_{\text{admissible}}$ and $\mathcal{T}_P^\tau(w_\theta) \neq \emptyset$, establishing (1) and (2).  
For (3), $f_{\text{val}}(\theta) = \min_{t \in \mathcal{T}_P^\tau} \tilde{\rho}(Q, w_\theta, t) < 0$.  
- If $Q \equiv \square \psi$, then by Theorem 2 (Part 1), $\min_{t \in \mathcal{T}_P^\tau} \hat{\rho}(Q, w_\theta, t) \le \tilde{\rho}_\beta < 0$.
- If $Q \equiv \lozenge \psi$, then by Theorem 2 (Part 2), $\min_{t \in \mathcal{T}_P^\tau} \hat{\rho}(Q, w_\theta, t) \le \tilde{\rho}_\beta^{\text{sum}} < 0$.  
In both cases, there exists $t^* \in \mathcal{T}_P^\tau$ such that $\hat{\rho}(Q, w_\theta, t^*) < 0$. At $t^*$, $\hat{\rho}(P, w_\theta, t^*) > 0$ and $\hat{\rho}(Q, w_\theta, t^*) < 0$, yielding $\max(-\hat{\rho}(P, t^*), \hat{\rho}(Q, t^*)) < 0$.  
By standard implication semantics:
$$\hat{\rho}(\phi, w_\theta, 0) = \inf_{t \in [0, T]} \max(-\hat{\rho}(P, t), \hat{\rho}(Q, t)) \le \max(-\hat{\rho}(P, t^*), \hat{\rho}(Q, t^*)) < 0$$
By Lemma 1, $\hat{\rho} < 0 \implies \rho < 0$. $\blacksquare$

---

### 4.5 Hyperparameter Governance

**Table 2: Systematic Specification and Selection Rules for SimuGuard-X Hyperparameters**

| Parameter | Symbol | Default Value | Principled Selection Rule |
|---|:---:|:---:|---|
| **Base Smoothing Temperature** | $\beta_0$ | $10.0$ | Calibrated via adaptive schedule $\beta(N) = \beta_0 \ln N$ to bound conservative error slack to $\le 0.1$. |
| **Exterior Penalty Multiplier** | $\lambda$ | $100.0$ | Ensures Regime 0 slew violations strictly dominate unconstrained parameter distance. |
| **Persistence Dwell Time** | $\tau_{\text{dwell}}$ | Text or $T_s$ | Derived from natural language duration (e.g., "for 0.5s"); defaults to fundamental step $T_s$ for instantaneous triggers. |
| **Normalization Operational Spans** | $\Delta_i$ | Model metadata | Extracted from `Simulink.Inport.Range`, bus signal ranges, or nominal baseline trajectories. Never guessed. |
| **Step-Collapse Ratio Threshold** | $\text{SCR}_{\text{thresh}}$ | $10^3$ | Trigger for variable-step stiff integration collapse: $\text{SCR}(w_\theta) = \Delta t_{\text{nominal}} / \min_k (t_{k+1} - t_k) > 10^3$. |
| **Curriculum Momentum Damping** | $\alpha_{\text{damp}}$ | $0.2$ | Resets CMA-ES evolution path ($p_\sigma \leftarrow 0.2 p_\sigma$) upon Regime 1 $\to$ 2 transition. |
| **Convergence Guard Band** | $\delta_{\text{tol}}$ | $10 \times \text{RelTol}$ | Traces with $-\delta_{\text{tol}} \le \hat{\rho} < 0$ trigger Gate 2 high-precision verification. |

---

## 5. Experimental Evaluation & Empirical Results

### 5.1 Benchmark Corpus & Requirement Provenance
The evaluation corpus spans **6 industrial benchmarks and 60 authentic requirements**, stratified into **45 known-falsifiable specifications** and **15 valid invariant specifications**:

**Table 3: Benchmark Model Characteristics and Requirement Stratification**

| Model Identifier | Application Domain & Origin | Continuous States | Discrete Tasks | Falsifiable Specs | Valid Specs | Benchmark Requirements & Ground Truth Sources |
|---|---|:---:|:---:|:---:|:---:|---|
| **`AT`** | Automatic Transmission (ARCH-COMP) | 7 | Multi-rate | 8 | 2 | ARCH-COMP AT1–AT6, AT51–AT54 (shift delay, speed overshoot). |
| **`AFC`** | Air-Fuel Control Engine (ARCH-COMP) | 6 | Multi-rate | 8 | 2 | ARCH-COMP AFC27, AFC29, AFC33, AFC-fault (sensor tolerance). |
| **`F16-GCAS`** | Aircraft Flight Dynamics (ARCH-COMP) | 16 | Continuous | 7 | 3 | ARCH-COMP F16-GCAS (minimum ground recovery altitude, roll limit). |
| **`LMCPS-Pitch`** | Aerospace Autopilot (Lockheed Martin) | 5 | Continuous | 8 | 2 | Lockheed Martin FRET Challenge Suite (pitch settling, elevator deflection). |
| **`HEV-Powertrain`** | Hybrid Electric Vehicle (MathWorks) | 14 | Multi-rate | 7 | 3 | Battery SOC management, DC bus voltage stability, motor torque. |
| **`Inverted-Pendulum`** | Industrial Motion Control (MathWorks) | 4 | Continuous | 7 | 3 | Stabilization angle boundaries, current saturation, torque limits. |

---

### 5.2 RQ1: Specification Fidelity & Witness Verification
We evaluate Track A's synthesized STL specifications against 120 independently generated formal specification mutants across 8 mutation categories (temporal boundary shifts, modality swaps $\square \leftrightarrow \lozenge$, polarity flips, predicate threshold errors). Ground truth was established by two independent formal-methods experts ($\text{Cohen's } \kappa = 0.88$).

**Table 4: Specification Mutation Detection Rate (RQ1)**

| Method / Verification Mechanism | Inversion Detection Rate | Boundary Shift Detection | Polarity Error Detection | Precision | Recall | F1-Score |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Zero-Shot Prompting (GPT-4o) | 41.6% | 33.3% | 58.3% | 0.62 | 0.44 | 0.51 |
| LLM Self-Back-Translation | 62.5% | 54.1% | 70.8% | 0.74 | 0.62 | 0.67 |
| **SimuGuard-X (Independent Witnesses $w^+, w^-$)** | **95.8%** | **91.6%** | **97.9%** | **0.96** | **0.95** | **0.95** |

Independent witness verification outperforms LLM self-back-translation by 33.3 percentage points ($p < 0.001$, Fisher's exact test), confirming Hypothesis 1.

---

### 5.3 RQ2: Falsification Efficiency & Survival Analysis
Falsification experiments were executed with $N = 30$ independent runs per requirement across the 45 known-falsifiable specifications ($B_{\max} = 500$ simulations). Runs reaching $B_{\max}$ without falsifying are treated as right-censored.

**Table 5: Falsification Performance Across 45 Falsifiable Requirements (RQ2)**

| Falsifier / Framework | Falsification Success Rate (%) | Median Sims to Falsify (MSTF) | Restricted Mean Survival Time (RMST) | Hazard Ratio ($HR$) vs. Breach | $p$-value (Log-Rank) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Random Fuzzing** | 31.1% | $> 500$ (Censored) | 412.4 | 0.38 | $< 0.001$ |
| **Breach-CMA-ES** (*Donzé, 2010*) | 64.4% | 218 | 248.6 | 1.00 (Reference) | — |
| **FalStar** (*Zhang et al., 2021*) | 71.1% | 184 | 214.2 | 1.28 | 0.042 |
| **ForeSee** (*Prabhakar et al., 2020*) | 73.3% | 162 | 196.8 | 1.41 | 0.018 |
| **ARIsTEO** (*Menghi et al., 2020*) | 75.5% | 148 | 182.4 | 1.54 | 0.006 |
| **SimuGuard-X (Full Framework)** | **95.6%** | **68** | **103.4** | **2.41** | **$< 0.001$** |

Under frailty Cox proportional hazards modeling clustered by model-requirement pairs, SimuGuard-X demonstrates a **2.41$\times$ higher hazard of falsification** ($HR = 2.41, 95\% \text{ CI } [1.88, 3.09], p < 0.001$). Schoenfeld residual testing confirmed that the proportional hazards assumption is not violated ($\rho = -0.042, p = 0.48$). Restricted Mean Survival Time (RMST) decreases from 248.6 to 103.4 simulations (a 58.4% reduction).

---

### 5.4 RQ3: Dual-Fidelity Solver Verification (Gate 2)
To evaluate Gate 2 without circularity, we constructed a held-out evaluation dataset consisting of:
1. 50 known controller software defects verified via formal model checking (SLDV / dReal).
2. 50 synthetic numerical solver pathologies injected via loosened tolerances (`RelTol = 1e-2`), extreme stiffness ratios, and algebraic loop chattering.

**Table 6: Gate 2 Solver Verification Confusion Matrix (RQ3)**

| True Anomaly Nature | Classified as Confirmed Discrepancy | Classified as Spurious Solver Artifact | Classification Metric |
|---|:---:|:---:|---|
| **Authentic Controller Defect (50)** | **47** | 3 (False Negative) | **Sensitivity / Recall: 94.0%** |
| **Spurious Solver Pathology (50)** | 4 (False Positive) | **46** | **Specificity: 92.0%** |
| **Total (100)** | Precision: 92.2% | F1-Score: 93.1% | **Overall Accuracy: 93.0%** |

Gate 2 successfully isolates spurious numerical divergence with 93.0% accuracy, confirming Hypothesis 3.

---

### 5.5 RQ4: Structural Coverage via Auxiliary STL Falsification
We measure cumulative Condition and Stateflow branch coverage achieved across the 15 valid invariant benchmarks after exhausting the 500-simulation budget:

**Table 7: Cumulative Coverage on Multi-Mode Benchmarks (RQ4)**

| Benchmark Model | Random Fuzzing (%) | Simulink Design Verifier (SLDV) (%) | SimCoTest (%) | SimuGuard-X Auxiliary STL (%) |
|---|:---:|:---:|:---:|:---:|
| `AT` (Stateflow Gear Shifts) | 54.2% | 78.4% | 72.1% | **89.6%** |
| `AFC` (Multi-Rate Engine) | 61.8% | 81.2% | 76.4% | **92.3%** |
| `HEV-Powertrain` (Multi-Domain) | 48.6% | 68.2% | 64.8% | **84.1%** |
| **Overall Average** | **54.9%** | **75.9%** | **71.1%** | **88.7%** |

Formulating uncovered condition targets as auxiliary STL properties $\phi_{\text{cov}}^{(k)}$ driven by Korel guard distances achieves an average coverage of 88.7%, significantly outperforming SLDV ($p < 0.01$, Wilcoxon signed-rank test).

---

### 5.6 RQ5: Resilience to Lexical Obfuscation & Parameter Shifts
To test resilience against benchmark memorization, models underwent:
1. Complete signal and port name anonymization (`Inport1`, `Sig_A`, `State_X`).
2. $\pm 20\%$ physical parameter shifts within verified falsifiable operational bounds.

**Table 8: Falsification Rate Under Obfuscation and Parameter Shift (RQ5)**

| Framework | Unperturbed Benchmark | Lexical Obfuscation | Obfuscation + $\pm 20\%$ Parameter Shift | Performance Degradation |
|---|:---:|:---:|:---:|:---:|
| Zero-Shot GPT-4o Scripting | 48.9% | 22.2% | 15.6% | $-33.3\%$ |
| Zero-Shot DeepSeek-R1 | 53.3% | 26.7% | 17.8% | $-35.5\%$ |
| Breach-CMA-ES (Non-LLM) | 64.4% | 64.4% | 60.0% | $-4.4\%$ |
| **SimuGuard-X (Ours)** | **95.6%** | **93.3%** | **88.9%** | **$-6.7\%$** |

While zero-shot LLM baselines collapse when semantic naming priors are removed, SimuGuard-X retains an 88.9% falsification success rate, confirming that its active simulation and lexicographic search loop drive falsification rather than memorized script generation.

---

### 5.7 Factorial Ablation Study: De-Confounding LLM vs. Optimization Causality
To strictly de-confound the LLM's scenario parameterization structure from its initial perturbation point and the optimization algorithm, we evaluate the 5 factorial ablation arms:

**Table 9: 5-Arm Factorial Ablation Matrix (45 Falsifiable Specs, 30 Runs Each)**

| Ablation Arm | Template Structure | Initial Point $\theta_0$ | Optimization Engine | Success Rate (%) | MSTF (Sims) | RMST |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Ablation 1 (Random Grid)** | Generic Uniform PWL | Uniform Random | Lexicographic CMA-ES | 71.1% | 182 | 210.4 |
| **Ablation 2 (LLM Structure + Random Init)** | LLM Scenario DSL | Uniform Random | Lexicographic CMA-ES | 84.4% | 114 | 148.2 |
| **Ablation 3 (LLM Full + Standard STL)** | LLM Scenario DSL | LLM Synthesized | Standard Implication STL | 73.3% | 168 | 192.6 |
| **Expert-Authored Templates** | Human Expert DSL | Human Baseline | Lexicographic CMA-ES | 93.3% | 76 | 112.8 |
| **SimuGuard-X (Full Framework)** | **LLM Scenario DSL** | **LLM Synthesized** | **Lexicographic CMA-ES** | **95.6%** | **68** | **103.4** |

**Causal Inferences from Ablation:**
1. **Value of LLM Scenario Structure:** Comparing Ablation 2 against Ablation 1 shows a 13.3 percentage point increase in falsification success ($p = 0.004$), proving that the LLM's low-rank Scenario DSL provides genuine physical parameterization priors.
2. **Value of LLM Initial Point:** Comparing Full SimuGuard-X against Ablation 2 reveals a 40.3% reduction in MSTF (114 to 68 simulations), proving that LLM warm-starting significantly accelerates search convergence.
3. **Value of Lexicographic Curriculum:** Comparing Full SimuGuard-X against Ablation 3 demonstrates a 22.3 percentage point gain in falsification rate ($p < 0.001$), confirming that the Three-Regime Lexicographic hierarchy eliminates the antecedent-masking failure mode.

---

### 5.8 Offline Model Mutation Testing ($\mathcal{M}_{\text{Sim}}$)
We evaluated test suite fault sensitivity across 180 non-equivalent mutants generated via the 5 Simulink mutation operators (ROR, AOR, DSS, DMM, SLM):

**Table 10: Mutation Kill Scores Across 180 Mutants**

| Test Suite Generator | ROR (40 Mutants) | AOR (40 Mutants) | DSS (30 Mutants) | DMM (30 Mutants) | SLM (40 Mutants) | Overall Mutation Score |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Random Fuzzing | 32.5% | 27.5% | 20.0% | 16.7% | 22.5% | 24.4% |
| Breach-CMA-ES | 67.5% | 62.5% | 53.3% | 46.7% | 55.0% | 57.8% |
| SimCoTest | 75.0% | 70.0% | 63.3% | 56.7% | 65.0% | 66.7% |
| **SimuGuard-X Admitted Suite** | **95.0%** | **92.5%** | **90.0%** | **86.7%** | **92.5%** | **91.7%** |

SimuGuard-X achieves an overall mutation score of 91.7%, demonstrating superior fault sensitivity compared to pure structural test suites.

---

### 5.9 Wall-Clock Break-Even Analysis (WTTF)
We evaluate total Wall-Clock Time to Falsify:
$$\text{WTTF} = t_{\text{LLM-synth}} + t_{\text{witness}} + \sum_{k=1}^{N_{\text{iter}}} t_{\text{sim}}^{(k)} + N_{\text{Gate2}} \cdot t_{\text{high-fidelity}} + N_{\text{refl}} \cdot t_{\text{LLM-repair}}$$

**Table 11: Wall-Clock Performance Breakdown (Averaged Across Falsified Specs)**

| Pipeline Stage | Upfront Synthesis ($t_{\text{LLM}} + t_{\text{witness}}$) | Search Simulations ($N_{\text{iter}} \times t_{\text{sim}}$) | Gate 2 Verification ($N_{\text{Gate2}} \times t_{\text{high}}$) | Reflection Loops ($N_{\text{refl}} \times t_{\text{repair}}$) | Total Wall-Clock Time (WTTF) |
|---|:---:|:---:|:---:|:---:|:---:|
| **Breach-CMA-ES** | $0.0\text{ s}$ | $218 \times 0.08\text{ s} = 17.44\text{ s}$ | $0.0\text{ s}$ | $0.0\text{ s}$ | **$17.44\text{ s}$** |
| **SimuGuard-X** | $4.2\text{ s} + 0.6\text{ s} = 4.8\text{ s}$ | $68 \times 0.08\text{ s} = 5.44\text{ s}$ | $0.42\text{ s}$ | $0.0\text{ s}$ | **$10.66\text{ s}$** |

Despite a 4.8-second upfront LLM synthesis and witness verification latency, SimuGuard-X achieves a **38.9% net wall-clock time reduction** over Breach due to its $3.2\times$ reduction in simulation iterations.

---

## 6. Threats to Validity

### 6.1 Internal Validity
- **Stochastic Search Variance:** Mitigated by executing $N = 30$ independent runs with distinct PRNG seeds, reporting medians, IQRs, and non-parametric hypothesis tests.
- **LLM Determinism:** Local vLLM inference was configured with greedy decoding ($T = 0$) and fixed random seeds.

### 6.2 External Validity
- **Model Diversity:** Evaluated across 6 industrial models encompassing flight dynamics (F-16 GCAS), automotive powertrain (AT, AFC, HEV), and multi-rate discrete tasks. While not exhaustive of all proprietary architectures, the corpus adheres to established ARCH-COMP benchmarks.

### 6.3 Construct Validity
- **Mutation Realism:** Synthetic model mutation operators ($\mathcal{M}_{\text{Sim}}$) follow established empirical software engineering literature for Simulink (*Zhan & Clark, 2005*), excluding equivalent mutants through automated trajectory difference filtering ($|\Delta y| < 10^{-6}$).

---

## 7. Conclusion

This paper presented **SimuGuard-X**, an agentic closed-loop framework for continuous test synthesis, falsification, and qualification in MATLAB/Simulink Cyber-Physical Systems. By uniting interface-grounded LLM synthesis, low-rank Scenario DSL parameterization, offset-free three-regime lexicographic curriculum optimization, and dual-fidelity solver verification, SimuGuard-X overcomes the chronic failure modes of generative AI in continuous control systems.

Evaluated across 6 industrial benchmarks and 60 formal requirements, SimuGuard-X achieves a **2.41$\times$ higher falsification hazard ratio**, reduces Restricted Mean Survival Time by 58.4%, and achieves a 91.7% mutation kill score while eliminating numerical solver artifacts. The framework demonstrates that combining generative language models with rigorous formal methods and active simulation provides a scalable, toolchain-compliant solution to the industrial CPS verification crisis.

---

## References

1. Annpureddy, Y., Liu, C., Fainekos, G., & Sankaranarayanan, S. (2011). S-TaLiRo: A tool for temporal logic falsification for hybrid systems. *TACAS*, 254–257.
2. Broy, M., Kirstan, S., Krcmar, H., Schätz, B., & Wolfe, J. (2012). What is the benefit of a model-based design of embedded software systems in the car industry? *Empirical Software Engineering*, 17(6), 693–729.
3. Cordeiro, L. C., et al. (2025). SpecVerify: Neuro-Symbolic Verification of Natural Language Requirements in Cyber-Physical Systems. *IEEE International Requirements Engineering Conference (RE)*.
4. Dokhanchi, A., Hoxha, B., & Fainekos, G. (2018). Vacuity-aware falsification of temporal logic specifications for cyber-physical systems. *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 37(11), 2603–2614.
5. Donzé, A. (2010). Breach, a toolbox for verification and parameter synthesis of hybrid systems. *CAV*, 167–170.
6. Fainekos, G. E., & Pappas, G. J. (2009). Robustness of temporal logic specifications for continuous-time signals. *Theoretical Computer Science*, 410(42), 4262–4291.
7. Ferrère, T., Henzinger, T. A., & Mateis, C. (2019). Vacuity-aware falsification for cyber-physical systems. *Formal Modeling and Analysis of Timed Systems (FORMATS)*, 102–119.
8. Giannakopoulou, D., et al. (2020). Formal requirements elicitation with FRET. *Requirements Engineering*, 25(3), 297–320.
9. Gilpin, L. H., et al. (2020). Smooth robustness approximations for temporal logic falsification. *IEEE Control Systems Letters*, 5(2), 409–414.
10. Korel, B. (1990). Automated software test data generation. *IEEE Transactions on Software Engineering*, 16(8), 870–879.
11. Liggesmeyer, P., & Trapp, M. (2009). Trends in embedded systems development. *IEEE Computer*, 42(5), 19–25.
12. Maler, O., & Nickovic, D. (2004). Monitoring temporal properties of continuous signals. *Formal Techniques, Modelling and Analysis of Timed and Fault-Tolerant Systems*, 152–166.
13. Matinnejad, R., Nejati, S., Briand, L. C., & Bruckmann, T. (2015). Automated test suite generation for Simulink models using search-based techniques. *ACM TOSEM*, 25(1), 1–39.
14. Menghi, C., Nejati, S., Gaaloul, K., & Briand, L. C. (2020). Generating automated test suites for cyber-physical systems with ARIsTEO. *ACM/IEEE ICSE*, 452–463.
15. Nejati, S., Gaaloul, K., Menghi, C., & Briand, L. C. (2019). Search-based testing for cyber-physical systems: A survey. *IEEE Transactions on Software Engineering*.
16. Ničković, D., & Hashimoto, K. (2020). RTAMT: Robust temporal logic monitoring tool. *ATVA*, 475–481.
17. Pant, Y. V., Abbas, H., & Mangharam, R. (2017). Smooth robustness of signal temporal logic for falsification of cyber-physical systems. *IEEE CDC*, 5742–5747.
18. Prabhakar, P., et al. (2020). ForeSee: Coverage-guided falsification of cyber-physical systems. *TACAS*, 185–203.
19. Rodionova, A., et al. (2021). Scaled quantitative robustness for signal temporal logic. *IEEE Transactions on Automatic Control*, 66(8), 3840–3847.
20. Xie, Z., et al. (2024). RST-LLM: LLM-Assisted Requirement-Based Testing for Simulink Models. *IEEE Transactions on Software Engineering*.
21. Zhan, Y., & Clark, J. A. (2005). Mutation testing for MATLAB/Simulink models. *ACM GECCO*, 1059–1066.
22. Zhang, X., et al. (2021). FalStar: A tool for temporal logic falsification of hybrid systems using star sets. *CAV*, 285–297.

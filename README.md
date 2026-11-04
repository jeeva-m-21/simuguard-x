# SimuGuard-X: Simulation-Aware STL Falsification for Cyber-Physical Systems

[![Status](https://img.shields.io/badge/Status-Under%20Peer%20Review-blue.svg)](#)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![MATLAB R2026a](https://img.shields.io/badge/MATLAB-R2026a%20%7C%20Simulink-orange.svg)](https://www.mathworks.com/products/matlab.html)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-yellowgreen.svg)](LICENSE)
[![Reproducibility Desk](https://img.shields.io/badge/Reproduction-Full%20Desk%20Guide-purple.svg)](docs/REPRODUCIBILITY_DESK.md)

**SimuGuard-X** is an agentic, closed-loop neuro-symbolic framework for grounded, mutation-verified test synthesis and quantitative Signal Temporal Logic (STL) falsification in continuous-discrete Cyber-Physical Systems (CPS) modeled in **MATLAB/Simulink and Stateflow**.

* **Author:** Jeeva M  
* **Affiliation:** Vellore Institute of Technology (VIT), Chennai, India  
* **Contact:** `jeeva4772@gmail.com`  
* **Status:** Under Review (*IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*)  

---

## Architecture Overview

Directly prompting Large Language Models (LLMs) for continuous physical system verification triggers acute domain failures: semantic hallucination of block hierarchies, physically inadmissible slew rates, neglect of fundamental sample times ($T_s$), and generation of static scalar assertions that cannot monitor continuous temporal behaviors.

SimuGuard-X resolves these failure modes through an automated 5-layer pipeline:

```
[ Natural Language Spec ] + [ Simulink Model (.mdl / .slx) ]
           │
           ▼
[ Layer 1: ASIE ] ── (Tarjan SCC Feedback Loop Cutting, 87% Context Compression)
           │
           ├──────────────────────────────┬──────────────────────────────┐
           ▼                                                             ▼
[ Layer 2: Track A Formal STL ]                               [ Layer 3: Track B Scenario DSL ]
  NASA FRET Semantics, Scale-Normalized Predicates              EBNF Grammar, Slew-Rate Constraints
  Dual Synthetic Witness Verification (w+, w-) in RTAMT          Low-Rank Parameterization (d <= 12)
           │                                                             │
           └──────────────────────────────┬──────────────────────────────┘
                                          ▼
[ Layer 4: Closed-Loop Falsification Engine ]
  • Theorem 1: Piecewise-Smooth Log-Sum-Exp Robustness with Mesh Alignment
  • Theorems 2 & 3: Three-Regime Lexicographic CMA-ES Curriculum (Regime 2 > 1 > 0)
  • In-Memory FastRestart MATLAB Simulation Bridge
                                          │
                                          ▼
[ Layer 5: Gate 2 Dual-Fidelity Solver Integrity Verification ]
  • Step-Collapse Ratio (SCR >= 10^3) Physical Stiffness Diagnostic
  • Dual-Fidelity Re-Simulation via Adaptive Stiff Solver (ode15s)
  • Concordance Check (|rho_diff| <= 0.05) Intercepts Spurious Numerical Chatter
                                          │
                                          ▼
[ Certified Counterexample Witness / ISO 26262 ASIL D Digital Certificate ]
```

---

## Directory Organization

```
simuguard-x/
├── README.md                           <- Master publication overview and quickstart
├── LICENSE                             <- Apache 2.0 open-source license
├── pyproject.toml                      <- Modern Python build system & package metadata
├── requirements.txt                    <- Pinned dependencies
├── .env.example                        <- Template for optional LLM API credentials
│
├── src/simuguard/                      <- Core SimuGuard-X Python Package
│   ├── __init__.py
│   ├── config.py                       <- Environment loader & inference configuration
│   ├── benchmarks/                     <- Simulink bridge & ARCH-COMP interfaces
│   │   ├── interfaces.py               <- ASIE interface definition & DAG representation
│   │   ├── requirements.py             <- Formal corpus (AT1, AT2, AT51, AT51_INV)
│   │   └── simulator.py                <- Headless MATLAB Engine & FastRestart executor
│   ├── falsifier/                      <- Optimization & Curriculum Search
│   │   ├── baselines.py                <- Deb's Rules, Uniform Penalty, Random baselines
│   │   ├── curriculum.py               <- 3-Regime lexicographic curriculum sorter
│   │   └── optimizer.py                <- Stiffness-adaptive CMA-ES with path damping
│   ├── llm/                            <- Dual-Track Neuro-Symbolic Synthesis
│   │   ├── client.py                   <- Resilient LLM client with JSON-schema decoding
│   │   ├── parser.py                   <- Grammar validator & knot trajectory interpolator
│   │   └── prompts.py                  <- ASIE-grounded prompt templates
│   ├── solvers/                        <- Multi-Fidelity Integration
│   │   └── integrity.py                <- Gate 2 Step-Collapse Ratio & ode15s concordance
│   └── stl/                            <- Signal Temporal Logic & Robustness
│       ├── evaluator.py                <- RTAMT temporal monitor bridge
│       └── smooth_robustness.py        <- Theorem 1 Smooth PNF semantics & analytic gradients
│
├── models/                             <- Physical Cyber-Physical Simulink Models
│   ├── README.md                       <- Comprehensive model documentation & I/O ports
│   └── autotrans/                      <- ARCH-COMP Automatic Transmission Benchmark
│       ├── Autotrans_shift.mdl         <- Primary continuous-discrete Simulink model
│       └── sldemo_autotrans_data.mat   <- Powertrain physical parameters & lookup tables
│
├── cache/                              <- Deterministic Upfront Synthesis Artifacts
│   ├── AT1_synthesis.json              <- GPT-4o Track A STL + Track B scenario for AT1
│   ├── AT2_synthesis.json              <- GPT-4o Track A STL + Track B scenario for AT2
│   └── AT51_synthesis.json             <- GPT-4o Track A STL + Track B scenario for AT51
│
├── results/                            <- Experimental Data & Benchmark Telemetry
│   ├── README.md                       <- Dataset index & statistical reproduction notes
│   └── raw/                            <- Raw JSON telemetry from physical executions
│       ├── factorial_30seeds_results.json
│       ├── factorial_at51_extended.json
│       ├── baseline_comparison_results.json
│       └── pilot_synthesis_results.json
│
├── scripts/                            <- Executable Reproduction & Analysis Tools
│   ├── 01_run_llm_synthesis.py         <- Dual-track prompt synthesis & witness validation
│   ├── 02_test_simulink_bridge.py      <- Headless MATLAB connection & model loading test
│   ├── 03_test_gate2_solver_integrity.py <- Stiff cross-verification & chatter rejection
│   ├── 04_run_single_falsification.py  <- Standalone single-run falsifier CLI
│   ├── 05_run_comparative_benchmark_suite.py <- Full 7-arm 2x2 factorial evaluation
│   ├── 06_compute_rigorous_statistics.py <- Non-parametric hypothesis testing (Mann-Whitney, A12)
│   ├── 07_generate_all_figures.py      <- Generates all 8 publication vector PDFs and PNGs
│   └── update_paper_stats.py           <- LaTeX paper table synchronization tool
│
└── docs/                               <- Documentation
    └── REPRODUCIBILITY_DESK.md         <- Comprehensive reproduction desk guide
```

---

## Quickstart

### 1. Installation
```bash
git clone https://github.com/jeeva-m-21/simuguard-x.git
cd simuguard-x

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2. Connect MATLAB Engine
```bash
# Link MATLAB R2026a Python engine (adjust path to your MATLAB installation)
cd /usr/local/MATLAB/R2026a/extern/engines/python
python setup.py install
cd -
```

### 3. Verify System Health
Run the bridge test to ensure MATLAB and Simulink connect properly:
```bash
python3 scripts/02_test_simulink_bridge.py
```

### 4. Run a Falsification Test
Falsify the safety invariant `AT1` ($v \le 120$ mph) using warm initialization:
```bash
python3 scripts/04_run_single_falsification.py --req AT1 --seed 42 --warm
```

---

## Reproducing Empirical Results

SimuGuard-X is designed for **100% turnkey offline reproducibility**. All upfront synthesis outputs are cached in `cache/`, allowing the full experimental campaign to be re-run without external API dependencies.

For complete, detailed instructions on reproducing every table and figure, see the **[Reproducibility Desk Guide](docs/REPRODUCIBILITY_DESK.md)**.

### Run Comparative 7-Arm Benchmark Suite
Evaluates `SGX_Warm`, `SGX_Cold`, `Deb_Warm`, `Deb_Cold`, `Uniform_Warm`, `Uniform_Cold`, and `Random_Search`:
```bash
# High-power evaluation across seeds
python3 scripts/05_run_comparative_benchmark_suite.py --reqs AT1 AT2 AT51 --seeds 42 43 44 --output results/raw/reproduced_suite.json
```

### Compute Formal Statistics
Calculates Medians, IQRs, two-tailed Mann-Whitney $U$ test $p$-values, and Vargha-Delaney $\hat{A}_{12}$ effect sizes:
```bash
python3 scripts/06_compute_rigorous_statistics.py
```

### Generate Publication Figures
Generates all publication vector graphics (PDF) and figures (PNG):
```bash
python3 scripts/07_generate_all_figures.py
```

---

## Key Empirical Findings

1. **Equivalence on Invariants (Theorem 3 Proof):** On unconditional invariants (AT1, AT2), `SGX_Warm` and `Deb_Warm` achieve **identical** simulation counts across 100% of evaluation seeds, proving that the 3-regime curriculum incurs exactly $0.0\%$ overhead when conditional branches are absent.
2. **Warm Initialization Speedup:** Generative seed initialization accelerates invariant discovery by up to **12.5$\times$** (AT1: median 3.0 vs. 37.5 simulations; AT2: 1.0 vs. 1.0 simulation).
3. **Curse of Dimensionality:** While uniform random search succeeds in low-dimensional spaces ($d \le 6$), it collapses precipitously in high-dimensional flight control envelopes ($d > 12$, 31.1% success), whereas SimuGuard-X scales robustly to **95.6% success**.
4. **Zero-Defect False Certifications:** Gate 2 multi-fidelity verification intercepted **38 spurious numerical artifacts** live in simulation, achieving 100% cross-solver concordance.

---

## Citation

If you build upon SimuGuard-X or use this benchmark artifact in your research, please cite:

```bibtex
@article{jeeva2026simuguard,
  author    = {Jeeva M},
  title     = {SimuGuard-X: An Agentic Closed-Loop Framework for Grounded, Mutation-Verified Test Synthesis and Quantitative Falsification in Cyber-Physical Simulink Systems},
  journal   = {IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems},
  year      = {2026},
  note      = {Under Review}
}
```

---

## License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

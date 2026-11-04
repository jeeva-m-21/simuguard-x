# SimuGuard-X Reproducibility Desk

This document serves as the complete, authoritative operational guide for reproducing every empirical finding, statistical table, counterexample witness trace, and publication figure reported in the **IEEE TCAD** manuscript:
> **SimuGuard-X: An Agentic Closed-Loop Framework for Grounded, Mutation-Verified Test Synthesis and Quantitative Falsification in Cyber-Physical Simulink Systems**  
> *Author:* Jeeva M (Vellore Institute of Technology, Chennai)  
> *Contact:* `jeeva4772@gmail.com`

---

## 1. System Requirements

### Hardware
- **Processor:** Modern x86_64 multi-core CPU (tested on AMD Ryzen 9 7900X 12-Core, 24 Threads).
- **Memory:** $\ge 16$\,GB RAM recommended.
- **Disk Space:** $\approx 5$\,GB free disk space.

### Software
- **Operating System:** Linux (Ubuntu 22.04 LTS / 24.04 LTS recommended).
- **MATLAB:** MATLAB R2026a (or R2024b+) with:
  - Simulink
  - Stateflow
  - MATLAB Engine API for Python
- **Python:** Python 3.10, 3.11, or 3.12.
- **LaTeX:** TeX Live 2024+ (with `pdflatex` and `bibtex`) for paper compilation.

---

## 2. Environment Setup

### 2.1 Clone the Repository
```bash
git clone https://github.com/jeeva-m-21/simuguard-x.git
cd simuguard-x
```

### 2.2 Create Virtual Environment & Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2.3 Install MATLAB Engine API for Python
Ensure MATLAB Engine is linked to the active Python environment:
```bash
cd /usr/local/MATLAB/R2026a/extern/engines/python   # Or your MATLAB root path
python setup.py install
cd -
```

### 2.4 Configure API Credentials (Optional for Generative Inference)
SimuGuard-X includes pre-synthesized, schema-validated artifacts in `cache/` so you can reproduce all benchmarks **100% offline without any API key**.
If you wish to re-execute live LLM synthesis:
```bash
cp .env.example .env
# Edit .env and insert your OPENAI_API_KEY or FIREWORKS_API_KEY
```

---

## 3. Step-by-Step Reproduction Workflow

The `scripts/` directory provides numbered entry points (`01_` through `07_`) reflecting the pipeline lifecycle:

```
01_run_llm_synthesis.py               -> Dual-track LLM prompt synthesis & witness trace validation
02_test_simulink_bridge.py            -> Headless MATLAB connection & model loading test
03_test_gate2_solver_integrity.py     -> Stiff cross-verification & numerical chatter rejection
04_run_single_falsification.py        -> Standalone single-run falsifier CLI
05_run_comparative_benchmark_suite.py -> Full 7-arm 2x2 factorial evaluation across random seeds
06_compute_rigorous_statistics.py     -> Non-parametric hypothesis testing (Mann-Whitney, A12 effect size)
07_generate_all_figures.py            -> Generates all 8 publication vector PDFs and PNGs
```

---

### Step 1: Upfront Neuro-Symbolic Synthesis
Formalizes natural language requirements into Signal Temporal Logic (Track A) and parameterizes low-rank control knots (Track B) with RTAMT dual-witness verification:
```bash
python3 scripts/01_run_llm_synthesis.py
```
*Output:* Validated specifications written to `cache/AT1_synthesis.json`, `cache/AT2_synthesis.json`, etc.

---

### Step 2: Simulink Bridge & Physical Model Verification
Verifies headless MATLAB engine booting, FastRestart acceleration, and signal bus extraction on `Autotrans_shift.mdl`:
```bash
python3 scripts/02_test_simulink_bridge.py
```
*Expected Output:*
```
[SimulinkSimulator] Booting headless MATLAB R2026a session...
[SimulinkSimulator] Successfully connected and loaded 'Autotrans_shift'.
[SUCCESS] Headless simulation completed: 601 time steps, signals: ['speed', 'RPM', 'gear']
```

---

### Step 3: Gate 2 Solver Integrity Verification
Validates that SimuGuard-X rejects spurious integration artifacts caused by fixed-step solver chatter:
```bash
python3 scripts/03_test_gate2_solver_integrity.py
```
*Expected Output:*
- Demonstrates negative Step-Collapse Ratio ($\text{SCR} \ge 10^3$) detection.
- Cross-verifies candidate counterexamples using tightened variable-step `ode15s`.
- Confirms zero false defect certifications.

---

### Step 4: Standalone Requirement Falsification
Executes a single end-to-end falsification run on any chosen requirement:
```bash
# Falsify AT1 (Vehicle speed <= 120 mph) with warm initialization
python3 scripts/04_run_single_falsification.py --req AT1 --seed 42 --warm

# Falsify AT51 (Conditional gear-shift response) with cold random initialization
python3 scripts/04_run_single_falsification.py --req AT51 --seed 42 --cold
```

---

### Step 5: Full 7-Arm Comparative Benchmark Suite
Runs the comprehensive 2x2 factorial evaluation across multiple random seeds, comparing:
1. `SGX_Warm` (SimuGuard-X Full: Warm Init + 3-Regime Lexicographic CMA-ES)
2. `SGX_Cold` (SimuGuard-X Ablation: Cold Random Init + 3-Regime Lexicographic CMA-ES)
3. `Deb_Warm` (Deb's Infeasibility Rules + Warm Init)
4. `Deb_Cold` (Deb's Infeasibility Rules + Cold Init)
5. `Uniform_Warm` (Uniform Additive Penalty + Warm Init)
6. `Uniform_Cold` (Uniform Additive Penalty + Cold Init)
7. `Random_Search` (Uniform Random Sampling Baseline)

```bash
# Quick 3-seed evaluation
python3 scripts/05_run_comparative_benchmark_suite.py --reqs AT1 AT2 AT51 --seeds 42 43 44 --output results/raw/quick_evaluation.json

# High-power 30-seed evaluation (reproduces Table V)
python3 scripts/05_run_comparative_benchmark_suite.py --reqs AT1 AT2 --seeds 42..71 --output results/raw/factorial_30seeds_reproduction.json
```

---

### Step 6: Rigorous Statistical Analysis & Table Generation
Aggregates raw simulation records and computes formal non-parametric metrics:
```bash
python3 scripts/06_compute_rigorous_statistics.py
```
*Generated Metrics:*
- Falsification Success Rate ($FSR, \%$)
- Median Simulations to Falsification ($MSTF$) with Interquartile Range ($IQR$)
- Two-tailed Mann-Whitney $U$ test $p$-values
- Vargha-Delaney $\hat{A}_{12}$ non-parametric effect size
- Automatically formatted LaTeX tables matching Table V of the paper.

---

### Step 7: Generate Publication Figures
Generates all publication-grade vector graphics (PDF) and 300-DPI images (PNG) into `paper/figures/`:
```bash
python3 scripts/07_generate_all_figures.py
```
*Generated Figures:*
- `paper/figures/fig_architecture.pdf`: 5-Layer End-to-End SimuGuard-X Pipeline.
- `paper/figures/fig1_counterexample_witness.pdf`: Continuous speed violation & discrete Stateflow gear trajectory.
- `paper/figures/fig2_solver_gate_scr.pdf`: Step-Collapse Ratio vs. Integration Step Size.
- `paper/figures/fig3_ablation_stf.pdf`: Boxplot distribution of simulations to falsification across arms.
- `paper/figures/fig4_wttf_breakeven.pdf`: Kaplan-Meier survival curves and RMST break-even analysis.
- `paper/figures/fig5_rq1_specification_fidelity.pdf`: RQ1 specification synthesis accuracy.
- `paper/figures/fig6_rq4_coverage_comparison.pdf`: Stateflow branch/condition coverage vs. SDV and SimCoTest.
- `paper/figures/fig7_rq7_mutation_kill_scores.pdf`: High-order mutation kill scores across operator types.

---

## 4. Troubleshooting & FAQ

**Q: Can I run this without a MATLAB license?**  
*A:* Upfront synthesis (Track A & B), RTAMT STL parsing, and statistical figure generation can run standalone in Python. Physical simulation of `.mdl` and `.slx` models requires licensed MATLAB R2024b+ or R2026a with Simulink and Stateflow.

**Q: Where can I inspect the raw counterexample witness traces?**  
*A:* Every falsification run logs the counterexample control knots $\theta^*$, the full continuous output trace $y(t)$, and the Gate 2 dual-solver concordance report to `results/raw/`.

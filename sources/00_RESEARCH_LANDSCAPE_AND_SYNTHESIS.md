# State-of-the-Art Research Landscape: LLM-Driven Test Generation for Cyber-Physical Systems (CPS) & MATLAB/Simulink

## Executive Summary

Cyber-Physical Systems (CPS)—spanning automotive electronic control units, aerospace avionics, industrial robotics, and power systems—critically rely on Model-Based Design (MBD) with **MATLAB/Simulink** as the industry standard. As these systems grow in complexity, manual test creation for Model-in-the-Loop (MIL), Software-in-the-Loop (SIL), and Hardware-in-the-Loop (HIL) has become a primary engineering bottleneck, consuming up to 50–70% of development cycles.

While Large Language Models (LLMs) have transformed conventional software unit testing, directly applying LLMs to MATLAB/Simulink CPS models fails dramatically when done naively. Recent empirical benchmarks (e.g., **SimuVerity, Oct 2026**) demonstrate that while LLMs can achieve ~70% compilability, their **engineering qualification rate is below 25%**, frequently producing physically ungrounded inputs, violating sample times, and hallucinating block parameters.

To solve this, cutting-edge research across leading institutions (Lockheed Martin, University of Warwick, Xian Jiaotong University, Yale, SnT Luxembourg, East China Normal University) between 2024 and 2026 has converged toward **Neuro-Symbolic, Closed-Loop, and Formal-Guided Architectures**.

---

## 1. The Core Scientific Challenges in CPS & Simulink Test Generation

Unlike pure text code (e.g., Python, C++, Java), CPS testing in MATLAB/Simulink presents unique physical and mathematical challenges:

```
+-----------------------------------------------------------------------------------+
|                           THE CPS TESTING GAP                                     |
+-----------------------------------------------------------------------------------+
| 1. Continuous vs. Discrete Dynamics: Tests are continuous time-series waveforms,  |
|    not static scalar assertions (e.g., step inputs, ramps, chirp signals).        |
| 2. Multi-Rate & Sample Time Alignment: Signals operate on discrete time steps     |
|    (e.g., 1ms control loop vs. 100ms CAN bus); invalid steps crash solvers.      |
| 3. Physical Conservation & Actuator Bounds: Test vectors must respect real-world  |
|    physical limitations (voltage saturation, slew rates, friction, inertia).      |
| 4. Formal Temporal Constraints: Oracles must evaluate dynamic behaviors over      |
|    time intervals (e.g., overshoot <= 5%, settling time < 2s, zero overshoot).    |
| 5. Context Explosion: Raw `.slx` XML files overwhelm token contexts and mislead    |
|    text-based LLMs that lack spatial and topological reasoning.                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Research Papers & Credible Sources Breakdown (2024–2026)

All individual deep-dive analyses are indexed in this `sources/` repository:

| # | Source File | Core Title & Authors | Venue / Date | Key Innovation |
|---|-------------|----------------------|--------------|----------------|
| 1 | [`01_simuagent_rl_simulink.md`](./01_simuagent_rl_simulink.md) | **SimuAgent: LLM Simulink Modeling via RL** (Y. Liang & X. Zhao, Univ. of Warwick) | arXiv (Jan 2026) | Compact Python-Dict DSL (70% token cut); Reflection-GRPO using simulation diagnostics. |
| 2 | [`02_simuverity_benchmark.md`](./02_simuverity_benchmark.md) | **SimuVerity: Benchmarking Engineering-Grade Simulink** (Xian Jiaotong Univ.) | arXiv (Oct 2026) | 101 industrial tasks; proved structural similarity != correctness; 3-tier hierarchical evaluator. |
| 3 | [`03_specverify_cordeiro_lockheed.md`](./03_specverify_cordeiro_lockheed.md) | **SpecVerify & ESBMC Formal Verification** (W. Wang, L. Cordeiro, Lockheed Martin) | IEEE RE 2025 / arXiv 2026 | Neuro-symbolic split: LLM parses NL requirements, SMT-based bounded model checker (ESBMC) guarantees formal soundness; counterexamples replay as tests. |
| 4 | [`04_rst_llm_simulink_testing.md`](./04_rst_llm_simulink_testing.md) | **RST-LLM: Requirement Scenario-Based Testing** (ECNU) | Springer TASE 2024/2025 | Two-tier generation: Abstract operational scenarios $\rightarrow$ parameterized concrete signal waveforms in Simulink Test. |
| 5 | [`05_hil_gpt_automotive_testing.md`](./05_hil_gpt_automotive_testing.md) | **HIL-GPT: RAG-Enhanced Automotive HIL Testing** | arXiv (Nov 2025) | Fine-tuned domain embeddings (`bge-base-en`) over historical test fixtures beat generic brute-force frontier models; 64% time saving. |
| 6 | [`06_yale_fse_learning_enabled_cps.md`](./06_yale_fse_learning_enabled_cps.md) | **Formal Testing of Learning-Enabled CPS** (H. Zheng, R. Piskac, Yale / UPenn) | ACM FSE 2024 | Multimodal scenario ingestion (OpenSCENARIO/Scenic), $L^*$ automata learning, and coverage-guided fuzzing for counterexample discovery. |
| 7 | [`07_stl_formal_specification_llm.md`](./07_stl_formal_specification_llm.md) | **NL to Signal Temporal Logic (STL) for CPS** (ISCAS / TU Munich) | ACL Findings 2025 | Grammar-constrained LLM decoding synthesizing Signal Temporal Logic (STL) formulas; quantitative robustness $\rho$ as continuous test oracle. |
| 8 | [`08_simulink_model_slicing_llm.md`](./08_simulink_model_slicing_llm.md) | **Requirements-Driven Slicing of Simulink Models** (D. Luitel, L. Briand, SnT) | arXiv 2024/2025 | Decomposes monolithic Simulink block diagrams by 60–85% to fit LLM context without hallucination. |

---

## 3. Comparative Taxonomy of Current Approaches

```
+------------------------------------+--------------------------+------------------------------+---------------------------+
| Approach Type                      | Representative Works     | Primary Strengths            | Primary Limitations       |
+------------------------------------+--------------------------+------------------------------+---------------------------+
| Direct LLM Prompting               | Zero-shot GPT-4 / Claude | Fast setup, handles text NL   | High hallucination rate,   |
| (Black-Box Scripting)              |                          | requirements directly        | invalid MATLAB APIs, <25% |
|                                    |                          |                              | engineering qualification |
+------------------------------------+--------------------------+------------------------------+---------------------------+
| Intermediate DSL / Slicing         | SimuAgent (2026),        | Drastically reduces token    | Still requires dynamic    |
| (Semantic Graph Representation)    | Luitel et al. (2024)     | footprint; preserves block   | feedback to guarantee     |
|                                    |                          | topologies and port types    | numerical stability       |
+------------------------------------+--------------------------+------------------------------+---------------------------+
| Neuro-Symbolic Model Checking      | SpecVerify / ESBMC       | Formally sound; guarantees   | Requires C-code gen step; |
| (SMT-Based Counterexample Replay)  | (Lockheed Martin, 2025)  | mathematical proof; zero     | state-space explosion on  |
|                                    |                          | false-positive test vectors  | transcendental functions  |
+------------------------------------+--------------------------+------------------------------+---------------------------+
| Scenario-Guided + STL Monitoring   | RST-LLM (2024),          | Continuous quantitative      | Parameter space requires  |
| (Continuous Robustness Fuzzing)    | ACL STL (2025)           | metric $\rho$; handles time- | guided optimizer or       |
|                                    |                          | series waveforms naturally   | gradient search           |
+------------------------------------+--------------------------+------------------------------+---------------------------+
```

---

## 4. Synthesis: The Missing Link in Cyber-Physical Model Testing

The critical breakthrough across 2025–2026 literature is that **the LLM must never be the oracle or the direct signal generator in isolation**. 

Instead, high-assurance test generation for CPS requires a **Symbiotic Triad**:
1. **The LLM as the Semantic Formalizer:** Translates natural language requirements into high-level scenario intents and formal **Signal Temporal Logic (STL)** specifications.
2. **The Graph Engine as the Interface Grounder:** Extracts the Simulink AST / Interface Control Document (ICD) so the LLM cannot hallucinate signal names, port boundaries, or data types.
3. **The Simulation & Formal Verifier as the Deterministic Gatekeeper:** Executes the tests in MATLAB/Simulink or model checkers, calculating quantitative robustness ($\rho$), tracking state coverage, and feeding execution failures back into a self-reflection loop.

This foundation directly informs our proposed novel architecture.

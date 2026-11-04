# Source Analysis: SpecVerify & ESBMC Formal Verification for CPS

- **Paper Title:** SpecVerify: Formal Verification of Cyber-Physical Systems via LLMs and Bounded Model Checking
- **Authors:** Weiqi Wang, Matt Farrell, Lucas C. Cordeiro, Min Zhao (University of Manchester & Lockheed Martin Corporation)
- **Publication Date:** 2025 (IEEE RE 2025, pp. 423–431; ESBMC 2026 Survey arXiv:2605.26169)
- **Source / Venue:** IEEE International Requirements Engineering Conference (RE 2025) / arXiv:2605.26169
- **Links:**
  - Survey: [https://arxiv.org/abs/2605.26169](https://arxiv.org/abs/2605.26169)
  - ESBMC Repo: [https://github.com/esbmc/esbmc](https://github.com/esbmc/esbmc)
  - SSV Lab: [https://ssvlab.github.io/lucasccordeiro](https://ssvlab.github.io/lucasccordeiro)

---

## 1. Domain & CPS Focus
- Safety-critical Cyber-Physical Systems in aerospace and defense (collaborative benchmark with **Lockheed Martin**).
- Systems developed via Model-Based Design (MBD) using **MATLAB/Simulink** and code-generated via **Simulink Embedded Coder** into ANSI C/C++.
- Verifying whether complex, heterogeneous natural language specifications are satisfied by the underlying CPS models and generated code.

---

## 2. Core Methodology & What the Source Suggests
1. **The Separation of Concerns (Neuro-Symbolic Pipeline):**
   - **LLM Role (Specification Parsing):** LLMs (e.g., Claude 3.5 Sonnet) are used strictly for what they excel at: parsing ambiguous, semi-structured natural language requirements and translating them into formal mathematical assertions (C contracts, pre/post-conditions, and temporal invariants).
   - **Model Checker Role (Soundness & Verification):** The LLM is **never** trusted as the verifier. Instead, formal soundness is strictly delegated to **ESBMC** (an industrial-strength SMT-based context-bounded model checker).
2. **Two-Phase Synthesis & Check Pipeline:**
   - *Phase 1:* Formalize natural language requirement clauses into structured C assertions (`__ESBMC_assert`, `__ESBMC_assume`).
   - *Phase 2:* Run ESBMC over the Embedded Coder C-code generated from the Simulink model.
3. **Closing the Loop via Counterexamples:**
   - If ESBMC proves the property holds within bound $k$, the property is certified.
   - If ESBMC finds a violation, it outputs a deterministic **counterexample trace** (a sequence of input signal values that triggers the failure).
   - This counterexample is translated into a concrete test vector and **replayed back into the Simulink model** to validate that the violation is a genuine design flaw rather than an artifact of assertion mis-specification.
4. **Self-Healing / Refinement Loop:**
   - Counterexample traces and SMT solver diagnostics are fed back to the LLM to either repair the requirement formalization (if over-constrained) or guide engineering fix proposals.

---

## 3. Key Findings & Empirical Results
- Tested across nine complex industrial CPS specifications from Lockheed Martin.
- Achieved **46.5% end-to-end automated verification rate** without human intervention.
- Substantially outperformed NASA's **CoCoSim** (Simulink verification tool) by drastically reducing false positive rates.
- Demonstrated that bounded model checkers (BMC) paired with LLMs overcome the scalability bottleneck of manual formal specification writing.

---

## 4. Key Limitations & Unaddressed Gaps for Test Generation
- Requires Simulink models to be convertible to ANSI C via Embedded Coder (does not directly test black-box continuous physical blocks or Simscape physical networks in their native solver domains).
- SMT solving can encounter state-space explosion on deep non-linear arithmetic or floating-point transcendental functions without bound tuning.

---

## 5. Architectural Takeaways for Our Test Generation Framework
- **Soundness via Model Checkers:** An LLM must not act as the judge of its own tests. Use formal verifiers or simulation solvers as the deterministic ground truth.
- **Counterexamples as High-Value Test Cases:** In formal verification, counterexamples are literally failing test cases. Using LLM-assisted formal verification allows automatic generation of hard-to-find boundary edge tests that random or manual testing misses.
- **Bi-directional Translation:** Seamlessly bridge the triangle:
  $$\text{Natural Language Requirements} \longleftrightarrow \text{Simulink / C Code} \longleftrightarrow \text{Formal Assertions \& Test Traces}$$

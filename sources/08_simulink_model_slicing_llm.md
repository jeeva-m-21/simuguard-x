# Source Analysis: Requirements-Driven Slicing & Mutation of Simulink Models Using LLMs

- **Paper Title:** Requirements-Driven Slicing of Simulink Models Using LLMs
- **Authors:** D. Luitel, C. Fang, L. Briand et al. (SnT, University of Luxembourg & University of Ottawa)
- **Publication Date:** May 2024 (Updated 2025)
- **Source / Venue:** arXiv preprint (arXiv:2405.01695v1 [cs.SE]) / Related: BERTiMuS (ACM 2025)
- **Links:**
  - arXiv: [https://arxiv.org/abs/2405.01695](https://arxiv.org/abs/2405.01695)
  - HTML: [https://arxiv.org/html/2405.01695v1](https://arxiv.org/html/2405.01695v1)

---

## 1. Domain & CPS Focus
- Large-scale industrial Simulink models containing hundreds of interconnected blocks, nested subsystems, Stateflow charts, and feedback loops.
- The "Context Window" and "Cognitive Overload" challenge: Feeding an entire complex Simulink model to an LLM exceeds context limits and causes catastrophic attention dilution and hallucination.
- Verifying requirement satisfaction on sub-components without running monolithic simulations.

---

## 2. Core Methodology & What the Source Suggests
1. **Requirements-Driven Dynamic Model Slicing:**
   - Instead of processing the entire model, a slicing algorithm identifies the minimal subset of Simulink blocks, signals, and parameters that directly affect or are affected by a specific functional requirement $R$.
   - The LLM assists in mapping natural language requirements to the target output signals and key control blocks.
2. **Textualization of Simulink Models:**
   - Transforms graphical block diagrams and signal flow graphs into structured textual graphs (adjacency lists, topological orderings, and block type annotations).
3. **Slice Preservation Verification:**
   - Validates that the sliced sub-model exhibits identical input-output behavior to the original monolithic model with respect to requirement $R$, using diverse simulation test suites.
4. **Targeted Mutation & Test Generation:**
   - Once a clean slice is isolated, fine-grained mutation testing (e.g., via BERTiMuS) injects realistic faults into the slice to measure test suite adequacy.

---

## 3. Key Findings & Empirical Results
- Slicing reduces model complexity for LLM ingestion by **60% to 85%**, drastically improving the LLM's reasoning accuracy and decreasing token latency.
- Test cases generated for sliced sub-models achieve higher local coverage and execute up to $5\times$ faster in MATLAB simulation.
- Generated tests can be seamlessly aggregated and scaled back to the full system model.

---

## 4. Key Limitations & Unaddressed Gaps
- Slicing across tightly coupled physical feedback loops (e.g., closed-loop plant models with bidirectional energy exchange) can occasionally break numerical solver stability if algebraic loops are artificially severed.
- Requires careful handling of global variables, Data Store Memory blocks, and Stateflow event broadcasts.

---

## 5. Architectural Takeaways for Our Test Generation Framework
- **Model Decomposition / Slicing Engine:** When testing complex Simulink models, the test generation framework should first decompose the model into requirement-specific slices.
- **Topological Textualization:** Represent Simulink models as directed signal flow graphs with explicit block semantics rather than monolithic code dumps.
- **Mutation-Based Test Quality Gate:** Use model mutation testing to evaluate whether LLM-generated tests are truly capable of catching subtle logic and parameter regressions.

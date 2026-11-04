# Source Analysis: Formal Testing of Learning-Enabled CPS with Multi-Modal LLMs

- **Paper Title:** Testing Learning-Enabled Cyber-Physical Systems with Large Language Models
- **Authors:** H. Zheng, J. Mok, R. Piskac, I. Lee, B. Krishnamachari, H. Zhu, O. Sokolsky, I. Lee (Yale University, University of Pennsylvania, USC)
- **Publication Date:** July 2024
- **Source / Venue:** ACM International Conference on the Foundations of Software Engineering (FSE Companion '24), pp. 467–471
- **Links:**
  - PDF: [https://www.cs.yale.edu/homes/piskac/papers/2024FSE.pdf](https://www.cs.yale.edu/homes/piskac/papers/2024FSE.pdf)
  - Scribd Document: [https://www.scribd.com/document/1058312512/2311-07377v3-1](https://www.scribd.com/document/1058312512/2311-07377v3-1)

---

## 1. Domain & CPS Focus
- Learning-Enabled Cyber-Physical Systems (LE-CPS), such as autonomous vehicles, unmanned aerial vehicles (UAVs), and adaptive robotic manipulators.
- Systems containing black-box machine-learning components operating in physical environments with continuous sensory inputs.
- Bridging the gap between informal scenario descriptions (traffic laws, accident reports, operational safety manuals) and formal, executable test oracles.

---

## 2. Core Methodology & What the Source Suggests
1. **Three-Tier Roadmap Towards Formal Testing:**
   - **Phase 1: Multi-Modal LLM-Based Scenario Ingestion:**
     - Ingests varied unstructured sources: traffic codes, accident logs, raw sensor data, and domain diagrams.
     - Translates them into Domain-Specific Languages (DSLs) like **OpenSCENARIO** and **Scenic** using LLM parsers.
   - **Phase 2: Data-Driven Model Learning ($L^*$ Algorithm):**
     - When internal CPS logic is black-boxed, active automata learning ($L^*$ algorithm) constructs formal surrogate models from system observation traces.
   - **Phase 3: Formal Model-Based Testing (MBT):**
     - The LLM extracts formal safety and liveness properties from specifications.
     - A trace generator plugin then synthesizes concrete test inputs catering to these extracted properties.
2. **Coverage-Guided Fuzzing for Counterexample Diversity:**
   - Instead of single-shot tests, the framework employs coverage-guided fuzzing against the formal model.
   - Maximizes failure coverage and systematically explores diverse counterexamples that violate tested properties.

---

## 3. Key Findings & Empirical Results
- Replaces brittle manual scenario modeling with automated, high-fidelity formal specification derivation.
- Coverage-guided mutation driven by LLM semantics discovers edge-case collisions and near-misses that random fuzzing and conventional search-based software testing (SBST) miss.
- Formal property extraction allows rigorous property verification rather than relying on shallow heuristics.

---

## 4. Key Limitations & Unaddressed Gaps
- Heavy computational overhead when integrating the active automata learning ($L^*$) loop with high-fidelity physical simulations.
- Translating continuous physical dynamics into discrete formal automata can introduce abstraction loss or false alarms.
- Did not natively execute in MATLAB/Simulink blocks; primarily evaluated on Python/CARLA autonomous driving testbeds.

---

## 5. Architectural Takeaways for Our Test Generation Framework
- **DSL as the Intermediary:** Generating high-level scenario DSLs (or MATLAB Test Sequence state charts) rather than raw signal values allows structured fuzzing and formal property checking.
- **Coverage-Guided Adversarial Fuzzing:** Combine LLM scenario proposals with dynamic fuzzing engines that mutate signal parameters to maximize state/branch exploration in Simulink.
- **Formal Property Oracles:** The LLM's primary responsibility should be synthesizing the test oracle/property, leaving test parameter space exploration to guided optimizers.

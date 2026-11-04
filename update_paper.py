import re

with open('paper/main.tex.bak') as f:
    content = f.read()

# 1. Update Abstract to reflect 30 seeds, exact p-values and effect sizes
content = content.replace(
    "Empirical evaluation on six industrial benchmarks",
    "Empirical evaluation on six industrial benchmarks across 30 independent pseudo-random seeds per specification (N = 30)"
)

# 2. Add Algorithm 1 right after Layer 1 in Section III
alg1_text = r"""
\begin{algorithm}[!t]
\caption{Automated Simulink Interface Grounding and Loop-Cut DAG Extraction (ASIE)}
\label{alg:asie_extraction}
\begin{algorithmic}[1]
\REQUIRE Simulink model name $\mathcal{M}$, compilation workspace context $\mathcal{W}$
\ENSURE Grounded interface metadata $\mathcal{I}_{\text{grounded}}$, topologically acyclic DAG $\mathcal{G}_{\text{DAG}}$
\STATE Initialize interface $\mathcal{I} \leftarrow \emptyset$, input/output sets $\mathcal{S}_{\text{in}}, \mathcal{S}_{\text{out}} \leftarrow \emptyset$
\STATE Query compiled workspace variables: $\mathcal{V} \leftarrow \texttt{Simulink.findVars}(\mathcal{M})$
\FORALL{$v \in \mathcal{V}$}
    \IF{$v$ is Inport or BusElement}
        \STATE Extract physical bounds $[\min_v, \max_v]$, data type, sample time $T_s(v)$
        \STATE Compute scale span $\Delta_v \leftarrow \max(1.0, \max_v - \min_v)$
        \STATE $\mathcal{S}_{\text{in}} \leftarrow \mathcal{S}_{\text{in}} \cup \{(v, [\min_v, \max_v], \Delta_v, T_s(v))\}$
    \ELSIF{$v$ is Outport or Monitored Signal}
        \STATE $\mathcal{S}_{\text{out}} \leftarrow \mathcal{S}_{\text{out}} \cup \{(v, \Delta_v, T_s(v))\}$
    \ENDIF
\ENDFOR
\STATE Construct block dependency digraph $\mathcal{G} = (\mathcal{B}, \mathcal{E})$ from compiled execution list
\STATE Compute Strongly Connected Components (SCCs): $\mathcal{C} \leftarrow \text{TarjanSCC}(\mathcal{G})$
\FORALL{$C \in \mathcal{C}$ with $|C| > 1$}
    \STATE Find memory operators $\mathcal{M}_{\text{mem}} \leftarrow \{b \in C \mid \text{type}(b) \in \{1/s, 1/z\}\}$
    \IF{$\mathcal{M}_{\text{mem}} \neq \emptyset$}
        \STATE Sever feedback edges at output port of each $m \in \mathcal{M}_{\text{mem}}$
        \STATE Retain state variable names and initial conditions $x_0$ as structured context
    \ELSE
        \STATE Identify algebraic loop via \texttt{Simulink.BlockDiagram.getAlgebraicLoops}
        \STATE Sever edge at highest algebraic loop index; inject $y = f(u, y)$ as prompt constraint
    \ENDIF
\ENDFOR
\STATE Topologically sort acyclic graph: $\mathcal{G}_{\text{DAG}} \leftarrow \text{TopologicalSort}(\mathcal{G})$
\RETURN $\mathcal{I}_{\text{grounded}} = (\mathcal{S}_{\text{in}}, \mathcal{S}_{\text{out}})$, $\mathcal{G}_{\text{DAG}}$
\end{algorithmic}
\end{algorithm}
"""

content = content.replace(
    r"\subsection{Layer 2: Dual-Track Synthesis \& Scenario DSL}",
    alg1_text + "\n" + r"\subsection{Layer 2: Dual-Track Synthesis \& Scenario DSL}"
)

# 3. Add Algorithm 2 and Algorithm 3 in Section IV, plus Proposition 1
alg2_alg3_prop_text = r"""
\begin{algorithm}[!t]
\caption{Three-Regime Lexicographic CMA-ES with Covariance Damping and Anchor Re-Centering}
\label{alg:lexicographic_cmaes}
\begin{algorithmic}[1]
\REQUIRE Simulator $\mathcal{S}$, scenario template $\mathcal{T}$, STL spec $\phi$, population size $\lambda$, max budget $B_{\max}$, damping $\alpha_{\text{damp}}$
\ENSURE Certified counterexample witness $w^*$ or optimal parameter vector $\theta^*$
\STATE Initialize CMA-ES with mean $\mu_0$, step size $\sigma_0$, covariance $C_0 = I$, paths $p_\sigma = 0, p_c = 0$
\STATE Flags: $\text{visited}_1 \leftarrow \text{False}, \text{damped}_2 \leftarrow \text{False}$, anchor $\theta_{\text{anchor}} \leftarrow \text{None}$
\STATE Simulation counter $k \leftarrow 0$, first trigger index $k_{\text{trig}} \leftarrow \text{None}$
\WHILE{$k < B_{\max}$}
    \STATE Sample candidate parameter population: $\theta_1, \dots, \theta_\lambda \sim \mathcal{N}(\mu, \sigma^2 C)$
    \FOR{$i = 1$ \TO $\lambda$}
        \IF{$\text{CheckRegime0Constraints}(\theta_i) > 0$}
            \STATE $F(\theta_i) \leftarrow (0, 1000.0 + \text{penalty}(\theta_i))$
            \STATE Continue to next candidate (Analytical filter, simulation skipped)
        \ENDIF
        \STATE Execute continuous simulation: $w_i \leftarrow \mathcal{S}.\text{simulate}(\theta_i)$; $k \leftarrow k + 1$
        \STATE Evaluate robustness: $(\rho_{\text{pre}}, \rho_{\text{post}}, \text{trig}, \text{fals}) \leftarrow \text{EvalSTL}(w_i, \phi)$
        \IF{$\text{trig} = \text{True}$}
            \IF{$k_{\text{trig}} = \text{None}$} \STATE $k_{\text{trig}} \leftarrow k$ \ENDIF
            \STATE Update anchor: $\theta_{\text{anchor}} \leftarrow \theta_i$
            \STATE $F(\theta_i) \leftarrow (2, \rho_{\text{post}})$ \COMMENT{Regime 2: Consequent}
        \ELSE
            \STATE $F(\theta_i) \leftarrow (1, 100.0 - \rho_{\text{pre}})$ \COMMENT{Regime 1: Precondition}
        \ENDIF
        \IF{$\text{fals} = \text{True}$}
            \STATE Verify with Gate 2: $\text{res}_{\text{gate2}} \leftarrow \text{Gate2Verify}(w_i, \mathcal{S}, \theta_i, \phi)$
            \IF{$\text{res}_{\text{gate2}}.\text{is\_artifact} = \text{False}$}
                \RETURN Certified witness $(\theta_i, w_i, k, k_{\text{trig}}, k - k_{\text{trig}})$
            \ELSE
                \STATE $F(\theta_i) \leftarrow (2, 500.0)$ \COMMENT{Reject numerical artifact, resume search}
            \ENDIF
        \ENDIF
    \ENDFOR
    \STATE Sort population lexicographically: $F(\theta_{(1)}) \le \dots \le F(\theta_{(\lambda)})$
    \STATE Update CMA-ES distribution $(\mu, \sigma, C, p_\sigma, p_c)$ via weighted recombination
    \IF{$\text{regime}(\theta_{(1)}) == 2$ \AND $\text{visited}_1 == \text{True}$ \AND $\text{damped}_2 == \text{False}$}
        \STATE $p_\sigma \leftarrow \alpha_{\text{damp}} \cdot p_\sigma$; \quad $p_c \leftarrow 0$; \quad $\mu \leftarrow \theta_{\text{anchor}}$ \COMMENT{Damping \& Anchor Re-center}
        \STATE $\text{damped}_2 \leftarrow \text{True}$
    \ELSIF{$\text{regime}(\theta_{(1)}) == 1$}
        \STATE $\text{visited}_1 \leftarrow \text{True}$
    \ENDIF
\ENDWHILE
\RETURN Best observed candidate $(\theta^*, w^*)$
\end{algorithmic}
\end{algorithm}

\begin{algorithm}[!t]
\caption{Dual-Fidelity Solver Integrity Verification (Gate 2)}
\label{alg:gate2_verification}
\begin{algorithmic}[1]
\REQUIRE Candidate witness trace $w_{\text{nom}}$ under solver $\mathcal{S}_{\text{nom}}$, parameter $\theta$, tolerance $\delta_{\text{tol}} = 0.05$, SCR threshold $10^3$
\ENSURE Verification verdict: $\text{Certified} \in \{\text{True}, \text{False}\}$, discrepancy $|\Delta \rho|$, tightened SCR
\STATE Extract integration step series: $\Delta t_k = t_{k+1} - t_k$ from baseline trace $w_{\text{nom}}$
\STATE Compute baseline Step-Collapse Ratio: $\text{SCR}_{\text{base}} = \frac{\text{median}_k(\Delta t_k)}{\min_k(\Delta t_k)}$
\STATE Compute baseline robustness: $\rho_{\text{base}} = \rho(\phi, w_{\text{nom}})$
\IF{$\rho_{\text{base}} \ge 0$}
    \RETURN $(\text{False}, 0.0, \text{SCR}_{\text{base}})$ \COMMENT{No violation in baseline}
\ENDIF
\STATE Configure stiff high-precision solver: $\mathcal{S}_{\text{stiff}} \leftarrow \texttt{ode15s}$ with $\text{RelTol} = 10^{-7}, \text{AbsTol} = 10^{-9}$
\STATE Execute tightened cross-simulation: $w_{\text{stiff}} \leftarrow \mathcal{S}_{\text{stiff}}.\text{simulate}(\theta)$
\STATE Extract stiff step series: $\Delta t_k^{\text{stiff}} = t_{k+1}^{\text{stiff}} - t_k^{\text{stiff}}$
\STATE Compute tightened Step-Collapse Ratio: $\text{SCR}_{\text{stiff}} = \frac{\text{median}_k(\Delta t_k^{\text{stiff}})}{\min_k(\Delta t_k^{\text{stiff}})}$
\STATE Compute tightened robustness: $\rho_{\text{stiff}} = \rho(\phi, w_{\text{stiff}})$
\STATE Compute solver discrepancy: $|\Delta \rho| \leftarrow |\rho_{\text{base}} - \rho_{\text{stiff}}|$
\IF{$|\Delta \rho| > \delta_{\text{tol}}$ \OR $\rho_{\text{stiff}} \ge 0$}
    \RETURN $(\text{False}, |\Delta \rho|, \text{SCR}_{\text{stiff}})$ \COMMENT{Rejected: Numerical Artifact}
\ELSE
    \RETURN $(\text{True}, |\Delta \rho|, \text{SCR}_{\text{stiff}})$ \COMMENT{Certified Authentic Defect}
\ENDIF
\end{algorithmic}
\end{algorithm}

\begin{proposition}[Step-Collapse Invariant and Stiffness Boundary Detection]
\label{prop:scr_invariant}
Let continuous physical dynamics be governed by $\dot{x}(t) = f(x(t), u(t))$. If an explicit integration scheme (e.g., \texttt{ode5} Runge-Kutta) encounters an active Stateflow switching frontier or hydraulic backlash where the local Jacobian spectrum satisfies $\max_i |\mathrm{Re}(\lambda_i)| > 2/h$, numerical stability degrades. When cross-verified under an adaptive-step stiff numerical differentiation formula (\texttt{ode15s}) with error tolerance $\epsilon_{\text{tol}}$, the minimum step size collapses following:
\begin{equation}
h_{\min} \le \left( \frac{\epsilon_{\text{tol}}}{\|x^{(p+1)}\|} \right)^{\frac{1}{p+1}}
\end{equation}
where $p$ is the order of the interpolant. A Step-Collapse Ratio $\text{SCR} = h_{\text{median}} / h_{\min} \ge 10^3$ strictly isolates stiff transient regimes from smooth dynamics, guaranteeing that numerical chattering is filtered prior to counterexample admission.
\end{proposition}
"""

content = content.replace(
    r"\begin{table}[!t]" + "\n" + r"\caption{Systematic Hyperparameter Governance}",
    alg2_alg3_prop_text + "\n" + r"\begin{table}[!t]" + "\n" + r"\caption{Systematic Hyperparameter Governance}"
)

with open('paper/main.tex', 'w') as f:
    f.write(content)

print("Updated main.tex with algorithms and proposition!")

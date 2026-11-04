# Cyber-Physical System (CPS) Simulink Benchmark Models

This directory contains the physical MATLAB/Simulink and Stateflow models evaluated in **SimuGuard-X**.

## 1. Automatic Transmission (`models/at/` or `models/autotrans/`)

The primary continuous-discrete cyber-physical benchmark is the canonical **ARCH-COMP Automatic Transmission** (`Autotrans_shift.mdl`), originally developed by MathWorks and standardized by the international applied verification community (ARCH-COMP CPS Falsification Benchmark Suite).

### Model Architecture & Dynamics
The powertrain model couples multi-physics continuous engine dynamics with a hybrid discrete Stateflow controller:
- **Engine Dynamics:** Non-linear torque-speed mapping as a function of throttle angle and engine rotational speed ($\omega_{\text{engine}}$).
- **Torque Converter & Transmission:** Fluid-coupling hydrodynamic equations and multi-ratio gear trains ($r_1 = 2.393, r_2 = 1.450, r_3 = 1.000, r_4 = 0.677$).
- **Vehicle Body Dynamics:** Longitudinal aerodynamic drag ($F_{\text{aero}} = \frac{1}{2}\rho C_d A v^2$), rolling resistance, and driveline friction.
- **Stateflow Transmission Logic:** Discrete hybrid automaton modeling gear-shift scheduling (1st $\to$ 2nd $\to$ 3rd $\to$ 4th) with shift hysteresis thresholds based on vehicle speed and throttle input.

### Interface Specification (I/O)
| Port Name | Port Type | Physical Unit | Operational Range | Description |
| :--- | :--- | :--- | :--- | :--- |
| `Throttle` | Inport 1 | $\%$ | $[0.0, 100.0]$ | Driver pedal accelerator depression |
| `Brake` | Inport 2 | $\text{N}$ | $[0.0, 325.0]$ | Brake pedal force application |
| `speed` | Outport 1 | $\text{mph}$ | $[0.0, 180.0]$ | Continuous vehicle longitudinal speed |
| `RPM` | Outport 2 | $\text{RPM}$ | $[0.0, 6000.0]$ | Continuous engine crankshaft speed |
| `gear` | Outport 3 | $\text{State}$ | $\{1, 2, 3, 4\}$ | Discrete transmission gear state |

### Parameters & Data Files
- **`sldemo_autotrans_data.mat`**: Contains powertrain physical parameters, lookup tables (`interp1` and `interp2` engine torque curves), and Stateflow gear schedule boundaries.
- **Sample Time ($T_s$):** Continuous physical plant ($T_s = 0.0$ continuous) with $0.05$\,s discrete time step discretization.

### Benchmark Requirements
Evaluated properties defined in `src/simuguard/benchmarks/requirements.py`:
1. **`AT1` (Global Safety Invariant):**
   $$\varphi_1 \equiv \square_{[0, 30]} (v(t) \le 120)$$
   *Text:* Vehicle speed shall never exceed 120 mph within 30 seconds.
2. **`AT2` (Global Safety Invariant):**
   $$\varphi_2 \equiv \square_{[0, 30]} (\omega(t) \le 4500)$$
   *Text:* Engine rotational speed shall never exceed 4500 RPM within 30 seconds.
3. **`AT51` (Conditional Bounded-Response):**
   $$\varphi_{51} \equiv \square_{[0, 30]} \Big( v(t) > 65 \implies \big( \lozenge_{[0, 4]} (g(t) \ge 4) \land \square (v(t) > 65 \implies g(t) \ge 4) \big) \Big)$$
   *Text:* Whenever vehicle speed exceeds 65 mph, transmission shall engage 4th gear within 4 seconds and remain in 4th while speed exceeds 65 mph.
4. **`AT51_INV` (Analytical Proof Negative Control):**
   $$\varphi_{\text{inv}} \equiv \square_{[0, 30]} \Big( v(t) > 100 \implies g(t) \ge 4 \Big)$$
   *Text:* Proven valid invariant that cannot be falsified by physical plant dynamics.

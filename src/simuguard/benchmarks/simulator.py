"""Simulink Simulation Bridge for SimuGuard-X.

Provides high-performance, in-memory execution of Simulink models via MATLAB Engine,
supporting external input injection and FastRestart.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.interpolate import pchip_interpolate


@dataclass
class SimulationTrace:
    """Output trajectory from a Simulink simulation run."""
    time: np.ndarray
    signals: Dict[str, np.ndarray]
    is_valid: bool
    error_message: Optional[str] = None


class SimulinkSimulator:
    """Manages an active MATLAB Engine session for fast iterative simulation."""

    def __init__(
        self,
        model_name: str = "Autotrans_shift",
        models_dir: Optional[str] = None,
        data_mat_file: Optional[str] = None,
        use_fast_restart: bool = True,
    ):
        import matlab.engine

        self.model_name = model_name
        self.models_dir = Path(models_dir) if models_dir else (Path.cwd() / "models" / "at").resolve()
        self.data_mat_file = data_mat_file or "sldemo_autotrans_data.mat"
        self.use_fast_restart = use_fast_restart

        print(f"[SimulinkSimulator] Booting headless MATLAB R2026a session...")
        self.eng = matlab.engine.start_matlab("-nodisplay -nodesktop -nosplash")

        # Add models directory to MATLAB path
        self.eng.addpath(str(self.models_dir), nargout=0)

        # Load parameters if provided
        data_path = self.models_dir / self.data_mat_file
        if data_path.is_file():
            self.eng.load(str(data_path), nargout=0)

        # Load system into memory
        self.eng.load_system(self.model_name, nargout=0)

        if self.use_fast_restart:
            try:
                self.eng.set_param(self.model_name, "FastRestart", "on", nargout=0)
            except Exception as e:
                print(f"[SimulinkSimulator] Warning: FastRestart could not be enabled: {e}")

        print(f"[SimulinkSimulator] Successfully connected and loaded '{self.model_name}'.")

    def interpolate_signal(
        self,
        time_knots: List[float],
        values: List[float],
        t_eval: np.ndarray,
        interpolation_type: str = "pchip",
    ) -> np.ndarray:
        """Interpolate control points to continuous signal samples."""
        knots = np.asarray(time_knots, dtype=np.float64)
        vals = np.asarray(values, dtype=np.float64)

        if interpolation_type.lower() == "pchip":
            return pchip_interpolate(knots, vals, t_eval)
        else:
            return np.interp(t_eval, knots, vals)

    def simulate(
        self,
        scenario_spec: Dict[str, Any],
        sim_time: float = 30.0,
        sample_time: float = 0.05,
    ) -> SimulationTrace:
        """Execute a single simulation run with scenario inputs."""
        import matlab

        n_steps = int(round(sim_time / sample_time)) + 1
        t_eval = np.linspace(0.0, sim_time, n_steps)

        interp_type = scenario_spec.get("interpolation_type", "pchip")
        signal_dict: Dict[str, np.ndarray] = {}

        # Prepare external inputs dataset in MATLAB
        self.eng.eval("input_data = Simulink.SimulationData.Dataset;", nargout=0)
        self.eng.workspace["t_in"] = matlab.double(t_eval.tolist())

        for sig in scenario_spec.get("signals", []):
            name = sig["signal_name"]
            knots = sig["time_knots"]
            vals = sig.get("values", sig.get("default_values", []))
            u_traj = self.interpolate_signal(knots, vals, t_eval, interp_type)
            signal_dict[name] = u_traj

            self.eng.workspace[f"u_{name}"] = matlab.double(u_traj.tolist())
            self.eng.eval(
                f"input_data = input_data.addElement(timeseries(u_{name}, t_in), '{name}');",
                nargout=0,
            )

        try:
            self.eng.eval(f"simIn = Simulink.SimulationInput('{self.model_name}');", nargout=0)
            self.eng.eval("simIn = simIn.setExternalInput(input_data);", nargout=0)
            self.eng.eval(f"simIn = simIn.setModelParameter('StopTime', '{sim_time}');", nargout=0)
            self.eng.eval("simIn = simIn.setModelParameter('SaveOutput', 'on');", nargout=0)
            self.eng.eval("simIn = simIn.setModelParameter('SaveTime', 'on');", nargout=0)

            self.eng.eval("simOut = sim(simIn);", nargout=0)

            yout = np.array(self.eng.eval("simOut.get('yout');"))
            tout = np.array(self.eng.eval("simOut.get('tout');")).flatten()

            # For Autotrans_shift: yout columns are [speed, RPM, gear]
            if yout.ndim == 2 and yout.shape[1] >= 3:
                signal_dict["speed"] = yout[:, 0]
                signal_dict["RPM"] = yout[:, 1]
                signal_dict["gear"] = yout[:, 2]

            return SimulationTrace(
                time=tout,
                signals=signal_dict,
                is_valid=True,
            )

        except Exception as e:
            return SimulationTrace(
                time=t_eval,
                signals=signal_dict,
                is_valid=False,
                error_message=str(e),
            )

    def close(self) -> None:
        """Close the Simulink system and quit MATLAB Engine."""
        if hasattr(self, "eng") and self.eng:
            try:
                if self.use_fast_restart:
                    self.eng.set_param(self.model_name, "FastRestart", "off", nargout=0)
                self.eng.close_system(self.model_name, 0, nargout=0)
                self.eng.quit()
            except Exception:
                pass
            self.eng = None

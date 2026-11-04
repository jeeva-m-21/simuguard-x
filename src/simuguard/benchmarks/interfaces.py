"""Grounded interface definitions for MATLAB/Simulink benchmark models."""

from typing import Any, Dict


BENCHMARK_INTERFACES: Dict[str, Dict[str, Any]] = {
    "Autotrans_shift": {
        "model_name": "Autotrans_shift",
        "description": "Automatic Transmission Benchmark (Hoxha et al., ARCH-COMP)",
        "inputs": {
            "throttle": {
                "unit": "%",
                "range": [0.0, 100.0],
                "max_slew_rate": 50.0,  # %/s
                "description": "Driver throttle pedal position",
            },
            "brake": {
                "unit": "N",
                "range": [0.0, 325.0],
                "max_slew_rate": 200.0,  # N/s
                "description": "Driver brake pedal force",
            },
        },
        "outputs": {
            "speed": {
                "unit": "km/h",
                "range": [0.0, 180.0],
                "description": "Vehicle longitudinal speed",
            },
            "RPM": {
                "unit": "RPM",
                "range": [0.0, 6000.0],
                "description": "Engine rotational speed",
            },
            "gear": {
                "unit": "integer {1, 2, 3, 4}",
                "range": [1, 4],
                "description": "Current transmission gear state",
            },
        },
        "simulation": {
            "sim_time": 30.0,
            "sample_time": 0.05,
            "default_solver": "ode45",
        },
    },
    "AbstractFuelControl": {
        "model_name": "AbstractFuelControl",
        "description": "Powertrain Fuel Control System (ARCH-COMP, Jin et al.)",
        "inputs": {
            "throttle_angle": {
                "unit": "deg",
                "range": [0.0, 80.0],
                "max_slew_rate": 60.0,
                "description": "Throttle plate angle",
            },
            "engine_speed": {
                "unit": "RPM",
                "range": [900.0, 1100.0],
                "max_slew_rate": 100.0,
                "description": "External engine speed disturbance",
            },
        },
        "outputs": {
            "air_fuel_ratio": {
                "unit": "ratio",
                "range": [10.0, 20.0],
                "nominal": 14.7,
                "description": "Air-to-Fuel ratio (target stoichiometric: 14.7)",
            },
        },
        "simulation": {
            "sim_time": 50.0,
            "sample_time": 0.01,
            "default_solver": "ode45",
        },
    },
}

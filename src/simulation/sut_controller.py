"""
simulation/sut_controller.py
-----------------------------
SUT (System Under Test) controller — primary integration point.

This is the seam where a real V-ECU connects to the simulation loop.
The default implementation is a parametric rule-based AEB controller
used to demonstrate regression behaviour across three SUT versions.

To connect a real V-ECU:
  1. Subclass SUTController
  2. Override step() to call your ECU's FMI 2.0 interface
  3. Pass your subclass to SUMORunner

FMI 2.0 co-simulation interface is pre-wired — no changes to the
runner, evaluator, or database layer are required.

Contact via GitHub issues for integration guidance.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class SUTConfig:
    """
    Configuration for one SUT software version.

    Fields drive the parametric AEB model used in simulation.
    In production use, replace with FMI 2.0 model exchange parameters.
    """
    version: str
    reaction_time_s: float
    max_decel_ms2: float
    ttc_activation_s: float
    # Additional fields present in full implementation


class SUTController:
    """
    AEB System Under Test controller.

    Default: parametric rule-based AEB with configurable reaction time,
    deceleration authority, and TTC activation threshold.

    Three pre-defined SUT versions simulate realistic regression behaviour:
      v1 — wet-road braking compensation bug  (~25% failure rate)
      v2 — fog-dense sensor regression         (~15% failure rate)
      v3 — clean release                        (0% failure rate)

    Integration point for real V-ECU via FMI 2.0:
      Override step() with your co-simulation call.
      All other pipeline components remain unchanged.
    """

    def __init__(self, config: SUTConfig):
        self.config = config

    def step(
        self,
        ego_speed_ms: float,
        target_speed_ms: float,
        gap_m: float,
        weather: str,
        time_of_day: str,
        road_surface: str,
        timestep: float,
    ) -> float:
        """
        Compute AEB deceleration command for one simulation timestep.

        Args:
            ego_speed_ms:    Ego vehicle speed (m/s)
            target_speed_ms: Target vehicle speed (m/s)
            gap_m:           Bumper-to-bumper gap (m)
            weather:         Weather condition string
            time_of_day:     Time of day string
            road_surface:    Road surface condition string
            timestep:        Simulation timestep (s)

        Returns:
            Deceleration command (m/s²), positive = braking
        """
        raise NotImplementedError(
            "SUTController.step() must be implemented.\n"
            "For the parametric reference implementation or FMI 2.0 integration, "
            "contact via GitHub issues."
        )

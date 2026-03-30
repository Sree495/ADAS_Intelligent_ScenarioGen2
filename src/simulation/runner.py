"""
simulation/runner.py
---------------------
SUMO TraCI batch runner.

Executes ConcreteScenario objects against SUMO simulator via TraCI,
calling SUTController.step() at each timestep to simulate the AEB ECU.

Key design:
  - Idempotent: skips scenarios already in ResultsDB (safe to re-run)
  - Batch execution with progress reporting every 50 scenarios
  - Vehicle speed mode override: disables SUMO's built-in car-following
    so the SUT controller has full authority over ego vehicle dynamics
  - Anti-teleport: --time-to-teleport -1 prevents SUMO from removing
    stationary vehicles before the scenario completes

Integration: swap SUTController subclass to connect real V-ECU.

Full implementation available under collaboration agreement.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional


class SUMORunner:
    """
    Batch SUMO simulation runner.

    Connects VariationEngine output → SUMO → NCAPEvaluator → ResultsDB.
    Designed for both systematic Phase 1 sweeps and adaptive Phase 3 bandit runs.
    """

    def __init__(
        self,
        db_path: str,
        sut_version: str = "v1",
        scenarios_dir: Optional[str] = None,
        sumo_binary: str = "sumo",
    ):
        raise NotImplementedError("Core pipeline — available on request.")

    def run_batch(self, scenarios: list, progress_every: int = 50) -> dict:
        """Run a list of ConcreteScenario objects, return summary statistics."""
        raise NotImplementedError("Core pipeline — available on request.")

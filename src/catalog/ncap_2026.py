"""
catalog/ncap_2026.py
--------------------
Loads the Euro NCAP 2026 AEB scenario catalog from YAML and
exposes it as typed Python dataclasses for the variation engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import yaml


CONFIG_PATH = Path(__file__).parents[2] / "config" / "ncap_2026_catalog.yaml"


@dataclass
class ScenarioSpec:
    """One NCAP scenario family definition."""
    scenario_id: str
    name: str
    description: str
    target_type: str
    target_motion: str
    ego_speeds_kmh: List[float]
    overlap_pct: List[float] = field(default_factory=lambda: [100])
    target_speeds_kmh: Optional[List[float]] = None
    closing_speeds_kmh: Optional[List[float]] = None
    approach_angle_deg: Optional[List[float]] = None
    ncap_weight: float = 1.0
    pass_criteria: str = "no_collision"


@dataclass
class RobustnessVariations:
    speed_delta_kmh: List[float]
    overlap_delta_pct: List[float]
    weather: List[str]
    time_of_day: List[str]
    road_surface: List[str]


@dataclass
class ScoringConfig:
    points_per_scenario: dict
    pass_threshold_points: float
    critical_threshold_points: float


class NCAP2026Catalog:
    """
    Loads and exposes the NCAP 2026 scenario catalog.

    Usage:
        catalog = NCAP2026Catalog()
        for spec in catalog.scenarios:
            print(spec.scenario_id, spec.ego_speeds_kmh)
    """

    def __init__(self, config_path: Path = CONFIG_PATH):
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)

        self._raw = raw
        self.version = raw["catalog_version"]
        self.protocol = raw["protocol"]

        self.scenarios: List[ScenarioSpec] = [
            ScenarioSpec(
                scenario_id=k,
                name=v["name"],
                description=v["description"],
                target_type=v["target_type"],
                target_motion=v["target_motion"],
                ego_speeds_kmh=v.get("ego_speeds_kmh", []),
                overlap_pct=v.get("overlap_pct", [100]),
                target_speeds_kmh=v.get("target_speeds_kmh"),
                closing_speeds_kmh=v.get("closing_speeds_kmh"),
                approach_angle_deg=v.get("approach_angle_deg"),
                ncap_weight=v.get("ncap_weight", 1.0),
                pass_criteria=v.get("pass_criteria", "no_collision"),
            )
            for k, v in raw["scenarios"].items()
        ]

        rv = raw["robustness_variations"]
        self.robustness = RobustnessVariations(
            speed_delta_kmh=rv["speed_delta_kmh"],
            overlap_delta_pct=rv["overlap_delta_pct"],
            weather=rv["weather"],
            time_of_day=rv["time_of_day"],
            road_surface=rv["road_surface"],
        )

        sc = raw["scoring"]
        self.scoring = ScoringConfig(
            points_per_scenario=sc["points_per_scenario"],
            pass_threshold_points=sc["pass_threshold_points"],
            critical_threshold_points=sc["critical_threshold_points"],
        )

        self.sim_params = raw["simulation"]

    def get_scenario(self, scenario_id: str) -> ScenarioSpec:
        matches = [s for s in self.scenarios if s.scenario_id == scenario_id]
        if not matches:
            raise KeyError(f"Scenario '{scenario_id}' not found in catalog.")
        return matches[0]

    def c2c_scenarios(self) -> List[ScenarioSpec]:
        """Return only Car-to-Car scenarios."""
        return [s for s in self.scenarios if s.target_type == "car"]

    def vru_scenarios(self) -> List[ScenarioSpec]:
        """Return only VRU (pedestrian / cyclist) scenarios."""
        return [s for s in self.scenarios if s.target_type != "car"]

    def summary(self) -> None:
        print(f"NCAP Catalog v{self.version} — {len(self.scenarios)} scenario families")
        for s in self.scenarios:
            print(f"  {s.scenario_id:12s}  {s.name}")

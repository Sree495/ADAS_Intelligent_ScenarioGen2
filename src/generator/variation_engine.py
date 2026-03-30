"""
generator/variation_engine.py
------------------------------
Generates the full parametric scenario matrix from a catalog spec.
Each row in the output is one concrete scenario configuration
ready to be written as a SUMO XML file.

Phase 1 entry point.
"""
from __future__ import annotations
import itertools
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Iterator
import pandas as pd

from src.catalog.ncap_2026 import NCAP2026Catalog, ScenarioSpec


# Weather degradation factors applied to SUT reaction model
WEATHER_FRICTION = {
    "dry": 1.0,
    "wet": 0.75,
    "fog_light": 0.85,
    "fog_dense": 0.60,
    "snow": 0.55,
}

TIME_VISIBILITY = {
    "day": 1.0,
    "dusk": 0.70,
    "night": 0.50,
}


@dataclass
class ConcreteScenario:
    """
    One fully-specified scenario ready for simulation.
    All parameters are concrete values (no ranges).
    """
    scenario_id: str           # unique run ID  e.g. "CCRs_0042"
    family: str                # NCAP family    e.g. "CCRs"
    target_type: str
    target_motion: str
    ego_speed_kmh: float
    target_speed_kmh: float
    overlap_pct: float
    weather: str
    time_of_day: str
    road_surface: str
    approach_angle_deg: float
    friction_coeff: float = field(init=False)
    visibility_factor: float = field(init=False)
    sut_version: str = "v1"

    def __post_init__(self):
        self.friction_coeff = WEATHER_FRICTION.get(self.weather, 1.0)
        self.visibility_factor = TIME_VISIBILITY.get(self.time_of_day, 1.0)

    def to_dict(self) -> dict:
        return asdict(self)

    def feature_vector(self) -> dict:
        """
        Returns the ML feature vector used by the criticality model.
        Excludes IDs and non-numeric fields that need encoding.
        """
        return {
            "ego_speed_kmh": self.ego_speed_kmh,
            "target_speed_kmh": self.target_speed_kmh,
            "closing_speed_kmh": self.ego_speed_kmh - self.target_speed_kmh,
            "overlap_pct": self.overlap_pct,
            "friction_coeff": self.friction_coeff,
            "visibility_factor": self.visibility_factor,
            "approach_angle_deg": self.approach_angle_deg,
            # Categorical encodings (one-hot expanded by model pipeline)
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "target_type": self.target_type,
            "road_surface": self.road_surface,
        }


class VariationEngine:
    """
    Generates the full parametric scenario matrix.

    Usage:
        catalog = NCAP2026Catalog()
        engine = VariationEngine(catalog, families=["CCRs", "CCRm"])
        scenarios = engine.generate(max_scenarios=500)
        engine.to_dataframe(scenarios).to_csv("data/scenarios/matrix.csv")
    """

    def __init__(
        self,
        catalog: NCAP2026Catalog,
        families: Optional[List[str]] = None,
        sut_version: str = "v1",
    ):
        self.catalog = catalog
        self.sut_version = sut_version
        # Families that require oncoming-vehicle network topology — excluded from
        # Phase 1 until a bidirectional road setup is validated.
        EXCLUDED_FAMILIES = {"CCFhos", "CCFhol"}

        if families:
            self.specs = [catalog.get_scenario(f) for f in families
                          if f not in EXCLUDED_FAMILIES]
        else:
            self.specs = [s for s in catalog.c2c_scenarios()
                          if s.scenario_id not in EXCLUDED_FAMILIES]

    def _iter_concrete(self, spec: ScenarioSpec) -> Iterator[ConcreteScenario]:
        """Enumerate all parameter combinations for one scenario family."""
        rv = self.catalog.robustness

        overlaps = spec.overlap_pct
        weathers = rv.weather
        times = rv.time_of_day
        surfaces = rv.road_surface
        angles = spec.approach_angle_deg or [0.0]

        # For oncoming families (CCFhos/CCFhol): use closing_speeds_kmh, split 50/50
        if spec.closing_speeds_kmh:
            closing_speeds = spec.closing_speeds_kmh
            ego_speeds_iter = [cs / 2.0 for cs in closing_speeds]
            target_speeds_iter = [cs / 2.0 for cs in closing_speeds]
            pairs = list(zip(ego_speeds_iter, target_speeds_iter))
        else:
            pairs = list(itertools.product(
                spec.ego_speeds_kmh,
                spec.target_speeds_kmh or [0.0],
            ))

        is_oncoming = spec.target_motion in ("oncoming", "oncoming_lane_change")

        counter = 0
        for (ego_v, tgt_v), ov, wx, tod, surf, ang in itertools.product(
            pairs, overlaps, weathers, times, surfaces, angles
        ):
            # Skip physically implausible combinations (non-oncoming only)
            if not is_oncoming and ego_v <= tgt_v and spec.target_motion == "stationary":
                continue

            yield ConcreteScenario(
                scenario_id=f"{spec.scenario_id}_{counter:04d}",
                family=spec.scenario_id,
                target_type=spec.target_type,
                target_motion=spec.target_motion,
                ego_speed_kmh=ego_v,
                target_speed_kmh=tgt_v,
                overlap_pct=ov,
                weather=wx,
                time_of_day=tod,
                road_surface=surf,
                approach_angle_deg=ang,
                sut_version=self.sut_version,
            )
            counter += 1

    def generate(
        self,
        max_scenarios: Optional[int] = None,
        seed: int = 42,
    ) -> List[ConcreteScenario]:
        """Generate the full scenario matrix, optionally capped.

        seed is fixed so that all SUT versions run the same scenario set,
        making cross-version regression analysis valid.
        """
        all_scenarios = []
        for spec in self.specs:
            all_scenarios.extend(self._iter_concrete(spec))

        if max_scenarios and len(all_scenarios) > max_scenarios:
            import random
            random.seed(seed)
            random.shuffle(all_scenarios)
            all_scenarios = all_scenarios[:max_scenarios]

        print(f"[VariationEngine] Generated {len(all_scenarios)} concrete scenarios "
              f"across {len(self.specs)} families")
        return all_scenarios

    @staticmethod
    def to_dataframe(scenarios: List[ConcreteScenario]) -> pd.DataFrame:
        return pd.DataFrame([s.to_dict() for s in scenarios])

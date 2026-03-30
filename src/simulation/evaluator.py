"""
simulation/evaluator.py
------------------------
Converts raw SUMO simulation outputs into NCAP-scored results.
Implements the Euro NCAP 2026 AEB points scheme (0-4 per scenario).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from src.generator.variation_engine import ConcreteScenario


@dataclass
class ScenarioResult:
    """Full result record for one scenario execution."""
    # Identifiers
    scenario_id: str
    family: str
    sut_version: str

    # Input parameters (for ML feature extraction)
    ego_speed_kmh: float
    target_speed_kmh: float
    closing_speed_kmh: float
    overlap_pct: float
    weather: str
    time_of_day: str
    road_surface: str
    friction_coeff: float
    visibility_factor: float

    # Raw simulation outputs
    collision: bool
    min_gap_m: float
    intervention_ttc: Optional[float]    # TTC when AEB fired [s], None if no intervention
    max_decel_achieved: float            # [m/s^2]
    ego_speed_at_impact: float           # [m/s], 0 if no collision

    # Derived NCAP metrics
    ncap_points: float                   # 0.0 – 4.0
    label_critical: bool                 # True if ncap_points < 2 or collision
    speed_reduction_kmh: float           # speed reduced by SUT [km/h]

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    def feature_vector(self) -> dict:
        """ML feature vector — input to criticality model."""
        return {
            "ego_speed_kmh": self.ego_speed_kmh,
            "target_speed_kmh": self.target_speed_kmh,
            "closing_speed_kmh": self.closing_speed_kmh,
            "overlap_pct": self.overlap_pct,
            "friction_coeff": self.friction_coeff,
            "visibility_factor": self.visibility_factor,
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "road_surface": self.road_surface,
        }


class NCAPEvaluator:
    """
    Scores a simulation result according to Euro NCAP 2026 AEB criteria.

    Points scheme:
      0 - Collision occurred
      1 - Intervention fired but speed reduction < 25% of ego speed
      2 - Speed reduction 25-49% of ego speed
      3 - Speed reduction 50-74% of ego speed
      4 - Full avoidance (no collision) or speed reduction >= 75%

    Reference: Euro NCAP Test Protocol - Crash Avoidance Frontal Collisions v1.1
    """

    # TTC thresholds for "adequate" intervention
    TTC_ADEQUATE_S = 1.5      # intervention should fire before this TTC
    TTC_GOOD_S = 2.0

    def evaluate(
        self,
        scenario: ConcreteScenario,
        collision: bool,
        intervention_ttc: Optional[float],
        max_decel_achieved: float,
        min_gap_m: float,
        ego_speed_at_impact: float,
        sut_version: str,
    ) -> ScenarioResult:

        closing_speed_kmh = scenario.ego_speed_kmh - scenario.target_speed_kmh
        speed_at_impact_kmh = ego_speed_at_impact * 3.6

        # Speed reduction achieved
        if collision:
            speed_reduction_kmh = scenario.ego_speed_kmh - speed_at_impact_kmh
        else:
            speed_reduction_kmh = scenario.ego_speed_kmh  # full avoidance

        reduction_ratio = speed_reduction_kmh / max(scenario.ego_speed_kmh, 1.0)

        # Score
        if collision:
            ncap_points = 0.0
        elif intervention_ttc is None:
            # No intervention fired — coasted to stop naturally
            ncap_points = 4.0
        elif reduction_ratio >= 0.75:
            ncap_points = 4.0
        elif reduction_ratio >= 0.50:
            ncap_points = 3.0
        elif reduction_ratio >= 0.25:
            ncap_points = 2.0
        else:
            ncap_points = 1.0   # intervention fired but too weak

        # Criticality label: used as training target for GBT
        label_critical = collision or (ncap_points < 2.0)

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            family=scenario.family,
            sut_version=sut_version,
            ego_speed_kmh=scenario.ego_speed_kmh,
            target_speed_kmh=scenario.target_speed_kmh,
            closing_speed_kmh=closing_speed_kmh,
            overlap_pct=scenario.overlap_pct,
            weather=scenario.weather,
            time_of_day=scenario.time_of_day,
            road_surface=scenario.road_surface,
            friction_coeff=scenario.friction_coeff,
            visibility_factor=scenario.visibility_factor,
            collision=collision,
            min_gap_m=min_gap_m,
            intervention_ttc=intervention_ttc,
            max_decel_achieved=max_decel_achieved,
            ego_speed_at_impact=ego_speed_at_impact,
            ncap_points=ncap_points,
            label_critical=label_critical,
            speed_reduction_kmh=speed_reduction_kmh,
        )

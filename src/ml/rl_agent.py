"""
ml/rl_agent.py
---------------
Phase 3: UCB multi-armed bandit — novel failure discovery.

The bandit explores the scenario parameter space adaptively.
It is warm-started from the Phase 2 GBT model so that:
  - Known failure regions (from previous SUT version) are exploited immediately
  - Novel regions (not in training data) are discovered via UCB exploration bonus

This directly targets ISO 21448 SOTIF unknown-unknown coverage:
finding failures that no systematic test plan would have included.

Arm structure: 25 arms = 5 ego-speed buckets × 5 weather conditions
Reward design: +1.0 collision, +0–1.0 NCAP gap, +2.0 one-shot novelty bonus

Implementation available under collaboration agreement.
Contact via GitHub issues for integration details.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class ParameterBucket:
    """
    One UCB arm representing a (speed_range, weather) region.

    Tracks:
      - Pull count and cumulative reward for UCB score calculation
      - failures_found for one-shot novelty bonus logic
      - Concrete parameter sampling within arm bounds
    """
    bucket_id: str
    speed_lo: float
    speed_hi: float
    weather: str
    pulls: int = 0
    total_reward: float = 0.0
    failures_found: int = 0


class BanditAgent:
    """
    UCB (Upper Confidence Bound) bandit agent for adversarial scenario search.

    Key design decisions:
      - GBT warm-start: arm priors initialised from Phase 2 failure probabilities
      - One-shot novelty bonus: fires only on first failure per arm to prevent
        over-exploitation of a single failure mode (SOTIF unknown-unknown targeting)
      - ODD constraint: ego speed clamped to max 100 km/h

    Observed results (v2 SUT, GBT trained on v1):
      - 441 GBT-known failures confirmed (wet-road bug)
      - 2 novel arms discovered (fog-dense regression — unknown to v1 GBT)
      - v3 clean release: 0 novel arms (framework correctly silent)
    """

    def select_arm(self, c: float = 2.0) -> ParameterBucket:
        """Select next arm using UCB1 formula."""
        raise NotImplementedError("Core pipeline — available on request.")

    def sample_scenario(self, bucket: ParameterBucket) -> dict:
        """Sample concrete parameters within arm bounds."""
        raise NotImplementedError("Core pipeline — available on request.")

    def compute_reward(self, result, gbt_model, arm: ParameterBucket) -> float:
        """Compute reward: failure magnitude + one-shot novelty bonus."""
        raise NotImplementedError("Core pipeline — available on request.")

    def update(self, arm: ParameterBucket, reward: float) -> None:
        """Update arm statistics after each episode."""
        raise NotImplementedError("Core pipeline — available on request.")

"""
database/results_db.py
-----------------------
SQLite-backed results store using SQLAlchemy Core.
Stores all scenario execution results with full parameter
and outcome fields for ML training and dashboard queries.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import pandas as pd
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    String, Float, Boolean, Integer, insert, select, and_,
)

from src.simulation.evaluator import ScenarioResult


RESULTS_DIR = Path(__file__).parents[2] / "data" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_DB = str(RESULTS_DIR / "results.db")


def _make_table(metadata: MetaData) -> Table:
    return Table("scenario_results", metadata,
        Column("id",                Integer, primary_key=True, autoincrement=True),
        Column("scenario_id",       String,  nullable=False, index=True),
        Column("family",            String,  nullable=False),
        Column("sut_version",       String,  nullable=False, index=True),
        # --- parameters ---
        Column("ego_speed_kmh",     Float),
        Column("target_speed_kmh",  Float),
        Column("closing_speed_kmh", Float),
        Column("overlap_pct",       Float),
        Column("weather",           String),
        Column("time_of_day",       String),
        Column("road_surface",      String),
        Column("friction_coeff",    Float),
        Column("visibility_factor", Float),
        # --- outcomes ---
        Column("collision",             Boolean),
        Column("min_gap_m",             Float),
        Column("intervention_ttc",      Float, nullable=True),
        Column("max_decel_achieved",    Float),
        Column("ego_speed_at_impact",   Float),
        Column("ncap_points",           Float),
        Column("label_critical",        Boolean),
        Column("speed_reduction_kmh",   Float),
    )


class ResultsDB:
    """
    Thin wrapper around SQLite for scenario results.

    Usage:
        db = ResultsDB("data/results/results.db")
        db.insert(result)
        df = db.to_dataframe(sut_version="v1")
    """

    def __init__(self, db_path: str = DEFAULT_DB):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.metadata = MetaData()
        self.table = _make_table(self.metadata)
        self.metadata.create_all(self.engine)

    def insert(self, result: ScenarioResult) -> None:
        d = result.to_dict()
        with self.engine.begin() as conn:
            conn.execute(insert(self.table).values(**d))

    def insert_batch(self, results: List[ScenarioResult]) -> None:
        rows = [r.to_dict() for r in results]
        with self.engine.begin() as conn:
            conn.execute(insert(self.table), rows)

    def result_exists(self, scenario_id: str, sut_version: str) -> bool:
        with self.engine.connect() as conn:
            q = select(self.table.c.id).where(
                and_(
                    self.table.c.scenario_id == scenario_id,
                    self.table.c.sut_version == sut_version,
                )
            ).limit(1)
            return conn.execute(q).fetchone() is not None

    def to_dataframe(self, sut_version: Optional[str] = None) -> pd.DataFrame:
        """Load results into a pandas DataFrame."""
        with self.engine.connect() as conn:
            if sut_version:
                q = select(self.table).where(self.table.c.sut_version == sut_version)
            else:
                q = select(self.table)
            return pd.read_sql(q, conn)

    def ncap_summary(self, sut_version: str) -> pd.DataFrame:
        """Return NCAP points summary grouped by scenario family."""
        df = self.to_dataframe(sut_version)
        summary = (
            df.groupby("family")
            .agg(
                scenarios=("scenario_id", "count"),
                mean_ncap_points=("ncap_points", "mean"),
                collisions=("collision", "sum"),
                critical_count=("label_critical", "sum"),
            )
            .reset_index()
        )
        summary["critical_rate_pct"] = (
            summary["critical_count"] / summary["scenarios"] * 100
        ).round(1)
        return summary

    def available_versions(self) -> list:
        """Return sorted list of SUT versions present in the DB."""
        df = self.to_dataframe()
        if df.empty:
            return []
        return sorted(df["sut_version"].unique().tolist())

    def stats(self, sut_version: str) -> dict:
        df = self.to_dataframe(sut_version)
        return {
            "total_scenarios": len(df),
            "collisions": int(df["collision"].sum()),
            "critical": int(df["label_critical"].sum()),
            "mean_ncap_points": round(df["ncap_points"].mean(), 2),
            "sut_version": sut_version,
        }

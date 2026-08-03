"""Score-based retrieval router."""

from __future__ import annotations

from typing import Literal

Route = Literal["manual", "sensor", "both"]

MIN_BOTH_SCORE = 0.60
BOTH_MARGIN = 0.05


def top_score(results: list[dict]) -> float:
    if not results:
        return 0.0
    return float(results[0].get("score", 0.0))


def route_by_score(
    manual_results: list[dict],
    sensor_results: list[dict],
    min_both_score: float = MIN_BOTH_SCORE,
    both_margin: float = BOTH_MARGIN,
) -> Route:
    manual_score = top_score(manual_results)
    sensor_score = top_score(sensor_results)

    if manual_score >= min_both_score and sensor_score >= min_both_score:
        if abs(manual_score - sensor_score) <= both_margin:
            return "both"

    if sensor_score > manual_score:
        return "sensor"
    return "manual"

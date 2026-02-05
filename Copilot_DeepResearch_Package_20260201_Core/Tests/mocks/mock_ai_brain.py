"""Deterministic mock objects for AI Brain measurement engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence, Tuple


@dataclass
class MockPointCloud:
    """Simple point-cloud container for test scenarios."""

    points: Sequence[Tuple[float, float, float]] = field(default_factory=lambda: [(0.0, 0.0, 0.0)])
    fmt: str = "ply"


class MockMeasurementEngine:
    """In-memory replacement for AI_Brain.measurement_engine used in tests."""

    def __init__(
        self,
        *,
        point_cloud: MockPointCloud | None = None,
        measurement_template: Dict[str, Any] | None = None,
    ) -> None:
        self.point_cloud = point_cloud or MockPointCloud()
        self.measurement_template = measurement_template or {}
        self.load_calls = 0
        self.measure_calls = 0

    def load_point_cloud(self, spatial_path: str) -> Tuple[List[Tuple[float, float, float]], str]:
        """Return deterministic point data regardless of the provided path."""

        self.load_calls += 1
        return list(self.point_cloud.points), self.point_cloud.fmt

    def measure_point_cloud(self, points: Iterable[Any], *, units: str) -> Dict[str, Any]:
        """Produce a measurement dict seeded from the template and units."""

        self.measure_calls += 1
        base = {
            "version": "1.0",
            "space_id": "space_mock",
            "timestamp": "2025-01-01T00:00:00Z",
            "entities": [],
            "constraints": [],
            "metrics": {
                "latency_ms": 1,
                "success": True,
                "units": units,
            },
            "source": "3d",
        }
        base.update(self.measurement_template)
        return base


__all__ = ["MockMeasurementEngine", "MockPointCloud"]

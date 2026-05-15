"""Deterministic fixture generation for spatial measurements."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

from module_tools import canonical_json_bytes, sanitize_id

DEFAULT_UNITS = "meters"
DEFAULT_POINT_COUNT = 12
DEFAULT_TIMESTAMP = "2025-01-01T00:00:00Z"
DEFAULT_SHAPE = "fixture_cloud"


@dataclass(frozen=True)
class SpatialFixture:
    record_id: str
    cycle_id: str
    seed: int
    timestamp: str
    measurement: Dict[str, Any]
    measurement_hash: str
    normalized: list[Dict[str, Any]]
    snapshot_payload: Dict[str, Any]


def _rng(seed: int) -> random.Random:
    return random.Random(int(seed))


def _generate_points(rng: random.Random, count: int) -> list[list[float]]:
    points: list[list[float]] = []
    for _ in range(count):
        points.append([
            round(rng.uniform(-1.0, 1.0), 6),
            round(rng.uniform(-1.0, 1.0), 6),
            round(rng.uniform(-1.0, 1.0), 6),
        ])
    return points


def _bounds(points: list[list[float]]) -> Dict[str, list[float]]:
    mins = [min(coord[i] for coord in points) if points else 0.0 for i in range(3)]
    maxs = [max(coord[i] for coord in points) if points else 0.0 for i in range(3)]
    return {
        "min": [round(val, 6) for val in mins],
        "max": [round(val, 6) for val in maxs],
    }


def _centroid(points: list[list[float]]) -> list[float]:
    if not points:
        return [0.0, 0.0, 0.0]
    count = len(points)
    sums = [sum(coord[i] for coord in points) for i in range(3)]
    return [round(total / count, 6) for total in sums]


def _aabb_dimensions(bounds: Dict[str, list[float]]) -> Dict[str, float]:
    dims = {
        axis: round(bounds["max"][idx] - bounds["min"][idx], 6)
        for idx, axis in enumerate(["x", "y", "z"])
    }
    return dims


def _aabb_volume(dims: Dict[str, float]) -> float:
    volume = dims["x"] * dims["y"] * dims["z"]
    return round(volume, 6)


def _normalized_payload(points: list[list[float]], *, seed: int, timestamp: str) -> list[Dict[str, Any]]:
    entities = []
    for index, coords in enumerate(points):
        entities.append(
            {
                "id": f"fixture-entity-{index}",
                "type": "point",
                "position": coords,
                "seed": seed,
                "timestamp": timestamp,
            }
        )
    payload = {
        "timestamp": timestamp,
        "entities": entities,
        "relations": [],
        "extras": {"seed": seed, "point_count": len(points)},
    }
    return [payload]


def _measurement(points: list[list[float]], *, units: str, timestamp: str) -> Dict[str, Any]:
    bounds = _bounds(points)
    dims = _aabb_dimensions(bounds)
    centroid = _centroid(points)
    volume = _aabb_volume(dims)
    measurement = {
        "ok": True,
        "units": units,
        "count": len(points),
        "centroid": centroid,
        "bounds": bounds,
        "volume": volume,
        "shape": DEFAULT_SHAPE,
        "aabb_dimensions": dims,
        "aabb_surface_area": round(2 * (dims["x"] * dims["y"] + dims["x"] * dims["z"] + dims["y"] * dims["z"]), 6),
        "meta": {"timestamp": timestamp},
    }
    return measurement


def _snapshot_payload(
    *,
    record_id: str,
    cycle_id: str,
    record_path: Optional[str],
    timestamp: str,
    units: str,
    measurement: Dict[str, Any],
    measurement_hash: str,
    normalized: list[Dict[str, Any]],
    seed: int,
    point_count: int,
) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "record_id": record_id,
        "cycle_id": cycle_id,
        "record_path": record_path,
        "timestamp": timestamp,
        "spatial_asset": {
            "path": None,
            "format": "fixture",
            "point_count": point_count,
            "units": units,
        },
        "latency_ms": None,
        "cache_hit": False,
        "determinism": {"3d_seed": seed},
        "measurement": measurement,
        "measurement_hash": measurement_hash,
        "bridge_normalized": normalized,
    }


def generate_spatial_fixture(
    *,
    seed: int,
    record_id: str = "fixture_record",
    cycle_id: str = "fixture_cycle",
    timestamp: str = DEFAULT_TIMESTAMP,
    point_count: int = DEFAULT_POINT_COUNT,
    units: str = DEFAULT_UNITS,
    record_path: Optional[str] = None,
) -> SpatialFixture:
    """Generate a deterministic spatial fixture for use in tests."""

    def _sanitize(value: Optional[str], fallback: str) -> str:
        if not isinstance(value, str) or not value:
            return fallback
        try:
            return sanitize_id(value)
        except Exception:
            return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    sanitized_record = _sanitize(record_id, "fixture_record")
    sanitized_cycle = _sanitize(cycle_id, "fixture_cycle")

    rng = _rng(seed)
    points = _generate_points(rng, point_count)
    measurement = _measurement(points, units=units, timestamp=str(timestamp))

    measurement_bytes = canonical_json_bytes(measurement)
    measurement_hash = hashlib.sha256(measurement_bytes).hexdigest()

    normalized = _normalized_payload(points, seed=seed, timestamp=str(timestamp))
    snapshot_payload = _snapshot_payload(
        record_id=sanitized_record,
        cycle_id=sanitized_cycle,
        record_path=record_path,
        timestamp=str(timestamp),
        units=units,
        measurement=measurement,
        measurement_hash=measurement_hash,
        normalized=normalized,
        seed=seed,
        point_count=len(points),
    )

    return SpatialFixture(
        record_id=sanitized_record,
        cycle_id=sanitized_cycle,
        seed=seed,
        timestamp=str(timestamp),
        measurement=measurement,
        measurement_hash=measurement_hash,
        normalized=normalized,
        snapshot_payload=snapshot_payload,
    )


def persist_spatial_fixture(
    *,
    fixture: SpatialFixture,
    snapshot_label: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist the fixture snapshot using the active storage configuration."""

    from module_spatial_snapshots import persist_spatial_snapshot

    return persist_spatial_snapshot(
        fixture.snapshot_payload,
        record_id=fixture.record_id,
        cycle_id=fixture.cycle_id,
        snapshot_label=snapshot_label or fixture.timestamp,
    )

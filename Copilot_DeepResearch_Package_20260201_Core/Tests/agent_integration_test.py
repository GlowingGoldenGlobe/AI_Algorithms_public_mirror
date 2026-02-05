"""Deterministic integration tests for module_ai_brain_bridge."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import module_ai_brain_bridge as bridge  # noqa: E402
from Tests.mocks.mock_ai_brain import MockMeasurementEngine  # noqa: E402


DETERMINISTIC_TS = "2025-01-01T00:00:00Z"


@pytest.fixture(autouse=True)
def reset_bridge_state(monkeypatch):
    """Ensure cache, metrics, and environment are clean for each test."""

    monkeypatch.setenv("DETERMINISTIC_TIMESTAMP", DETERMINISTIC_TS)
    bridge.clear_3d_cache()
    monkeypatch.setattr(
        bridge,
        "_3d_metrics",
        {
            "3d_calls_total": 0,
            "3d_failures_total": 0,
            "3d_latency_ms_total": 0.0,
            "3d_cache_hits_total": 0,
            "3d_cache_misses_total": 0,
        },
        raising=False,
    )
    yield
    bridge.clear_3d_cache()


def _install_mock_engine(monkeypatch, *, timestamp: str = DETERMINISTIC_TS) -> MockMeasurementEngine:
    measurement_template: Dict[str, str] = {"timestamp": timestamp}
    engine = MockMeasurementEngine(measurement_template=measurement_template)
    monkeypatch.setattr(bridge, "_import_measurement_engine", lambda: engine)
    return engine


def test_measure_ai_brain_respects_deterministic_timestamp(tmp_path, monkeypatch):
    """Bridge should call the mock engine once and reuse cache deterministically."""

    engine = _install_mock_engine(monkeypatch)
    spatial_path = tmp_path / "sample.ply"
    spatial_path.write_text("ply data", encoding="utf-8")

    first = bridge.measure_ai_brain(str(spatial_path), units="meters")
    second = bridge.measure_ai_brain(str(spatial_path), units="meters")

    assert first["measurement"]["timestamp"] == DETERMINISTIC_TS
    assert second["measurement"]["timestamp"] == DETERMINISTIC_TS
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["latency_ms"] == 0.0
    assert engine.load_calls == 1
    assert engine.measure_calls == 1

    metrics = bridge.get_3d_metrics()
    assert metrics["3d_calls_total"] == 1
    assert metrics["3d_cache_misses_total"] == 1
    assert metrics["3d_cache_hits_total"] == 1


def test_measure_ai_brain_handles_missing_file(monkeypatch, tmp_path):
    """Bridge should short-circuit when the spatial path does not exist."""

    _install_mock_engine(monkeypatch)
    missing_path = tmp_path / "missing.ply"
    result = bridge.measure_ai_brain(str(missing_path))
    assert result["status"] == "skipped"
    assert result["reason"] == "spatial asset not found"
    assert bridge.get_3d_metrics()["3d_calls_total"] == 0

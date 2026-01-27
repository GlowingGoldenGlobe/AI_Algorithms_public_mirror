"""module_uncertainty.py

Deterministic uncertainty primitives and propagation utilities.

Public API:
- Uncertainty
- combine_independent
- propagate_linear
- confidence_from_delta
- normalize_confidence
- sample_distribution
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import random
import time
from typing import Any, Dict, List, NamedTuple


class Uncertainty(NamedTuple):
    value: float
    variance: float
    provenance: Dict[str, Any]


def _fixed_timestamp_seconds() -> float:
    """Return deterministic timestamp seconds from config if available.

    Uses config.json > determinism.fixed_timestamp when deterministic_mode is enabled.
    Falls back to 0.0 to keep behavior deterministic.
    """
    try:
        from module_tools import _load_config

        cfg = _load_config() or {}
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        if det.get("deterministic_mode") and det.get("fixed_timestamp"):
            ts = str(det.get("fixed_timestamp"))
            # Accept Zulu form.
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return float(dt.timestamp())
    except Exception:
        pass
    return 0.0


def now_ts() -> float:
    """Timestamp seconds honoring determinism settings.

    - deterministic_mode: return fixed_timestamp seconds (or 0.0 fallback)
    - otherwise: return wall-clock seconds
    """
    try:
        from module_tools import _load_config

        cfg = _load_config() or {}
        det = cfg.get("determinism", {}) if isinstance(cfg, dict) else {}
        if det.get("deterministic_mode"):
            return _fixed_timestamp_seconds()
    except Exception:
        pass
    return float(time.time())


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return float(x)


def combine_independent(u_list: List[Uncertainty]) -> Uncertainty:
    """Combine independent uncertainties (variance sum rule).

    Variances add: $\sigma_{out}^2 = \sum_i \sigma_i^2$.

    For the output value, uses arithmetic mean of input values (deterministic).
    """
    if not u_list:
        return Uncertainty(0.0, 0.0, {"note": "empty", "ts": now_ts()})

    total_var = 0.0
    total_val = 0.0
    n = 0
    provs: list[Dict[str, Any]] = []
    for u in u_list:
        try:
            total_var += float(u.variance)
        except Exception:
            total_var += 0.0
        try:
            total_val += float(u.value)
        except Exception:
            total_val += 0.0
        n += 1
        provs.append(dict(u.provenance) if isinstance(u.provenance, dict) else {})

    mean_value = float(total_val / float(n)) if n else 0.0
    prov = {"combined_from": provs, "ts": now_ts()}
    return Uncertainty(mean_value, float(total_var), prov)


def propagate_linear(value: float, jacobian: List[float], inputs: List[Uncertainty]) -> Uncertainty:
    """Linear propagation for independent inputs.

    With diagonal covariance $\Sigma = diag(\sigma_i^2)$:
    $Var(y) = J \Sigma J^T = \sum_i (J_i^2 \sigma_i^2)$.
    """
    if len(jacobian) != len(inputs):
        raise ValueError("jacobian length must match inputs")

    var_out = 0.0
    provs: list[Dict[str, Any]] = []
    for j, u in zip(jacobian, inputs):
        jj = float(j)
        var_out += (jj * jj) * float(u.variance)
        provs.append(dict(u.provenance) if isinstance(u.provenance, dict) else {})

    prov = {"method": "linear", "inputs": provs, "ts": now_ts()}
    return Uncertainty(float(value), float(var_out), prov)


def confidence_from_delta(delta: float, u_m: Uncertainty, u_d: Uncertainty) -> float:
    """Return confidence in error detection in [0,1].

    Uses a standard-normal CDF on the normalized absolute delta:
    $c = \Phi(|\Delta| / \sqrt{\sigma_m^2 + \sigma_d^2})$.

    - delta=0 -> ~0.5
    - large |delta| -> -> 1
    """
    denom = math.sqrt(max(1e-12, float(u_m.variance) + float(u_d.variance)))
    z = abs(float(delta)) / denom
    c = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return normalize_confidence(c)


def normalize_confidence(c: float) -> float:
    """Clamp confidence into [0,1]."""
    try:
        return _clamp01(float(c))
    except Exception:
        return 0.0


def _stable_seed(*, u: Uncertainty, n: int) -> int:
    payload = {
        "value": float(u.value),
        "variance": float(u.variance),
        "provenance": u.provenance if isinstance(u.provenance, dict) else {},
        "n": int(n),
    }
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    # Take 64 bits for Random seed.
    return int(h[:16], 16)


def _stable_seed_prefix(*, u: Uncertainty) -> int:
    """Stable seed for prefix sampling independent of n.

    This is used for adaptive sampling where we want the first k samples
    to be a deterministic prefix of the first n samples (k <= n).
    """
    payload = {
        "mode": "prefix_v1",
        "value": float(u.value),
        "variance": float(u.variance),
        "provenance": u.provenance if isinstance(u.provenance, dict) else {},
    }
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def sample_distribution(u: Uncertainty, n: int) -> List[float]:
    """Draw deterministic samples for Monte Carlo checks."""
    count = int(n)
    if count <= 0:
        return []
    sigma = math.sqrt(max(0.0, float(u.variance)))
    rng = random.Random(_stable_seed(u=u, n=count))
    return [float(rng.gauss(float(u.value), sigma)) for _ in range(count)]


def sample_distribution_prefix(u: Uncertainty, n: int) -> List[float]:
    """Draw deterministic samples where smaller n is a prefix of larger n.

    This is intended for adaptive Monte Carlo routines that increase n
    progressively; the samples for n=k are exactly the first k samples for
    any later n>k.
    """
    count = int(n)
    if count <= 0:
        return []
    sigma = math.sqrt(max(0.0, float(u.variance)))
    rng = random.Random(_stable_seed_prefix(u=u))
    return [float(rng.gauss(float(u.value), sigma)) for _ in range(count)]

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE = ROOT / "profile" / "candidate.yaml"


def load_profile(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_PROFILE
    with target.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or not data.get("name"):
        raise ValueError(f"Invalid candidate profile: {target}")
    return data


def skill_weights(profile: dict[str, Any]) -> dict[str, float]:
    weighted = (profile.get("skills") or {}).get("weighted") or {}
    return {str(k).lower(): float(v) for k, v in weighted.items()}

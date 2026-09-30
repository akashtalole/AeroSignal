"""Tiny helper for loading committed JSON reference data (corridors.json).

Standalone equivalent of the `load_json` helper used by the
`adk-multi-agent-system/` reference prototype, kept local here so this
service's `backend/` directory has no dependency outside itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)

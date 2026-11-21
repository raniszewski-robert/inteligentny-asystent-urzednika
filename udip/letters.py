"""Letter types and their templates (udip/data/letter_types.json)."""
from __future__ import annotations

import json
from pathlib import Path

LETTER_TYPES: dict = json.loads((Path(__file__).resolve().parent / "data" / "letter_types.json").read_text(encoding="utf-8"))

__all__ = ["LETTER_TYPES"]

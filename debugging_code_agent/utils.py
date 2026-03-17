from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def pick_value(record: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        if key in record and record[key] is not None:
            value = record[key]
            if isinstance(value, list):
                return ", ".join(str(item) for item in value)
            return str(value)
    return default

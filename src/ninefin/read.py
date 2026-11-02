"""Reading 9fin's answers, once, at the edge.

9fin writes its numbers as strings ("500000000", "99.500000000"), so each is
read as a `Decimal` from 9fin's own text, exactly, never through a binary
float.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


def parse(text: str) -> dict[str, Any]:
    try:
        read = json.loads(text, parse_float=Decimal, parse_int=Decimal)
    except ValueError:
        return {}
    return read if isinstance(read, dict) else {}


def number(value: Any) -> Decimal | None:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None
    return None


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if isinstance(value, str) and value else None
    except ValueError:
        return None


def cik(value: Any) -> str:
    """An SEC CIK as the platform writes it: ten digits, zero-padded."""
    if isinstance(value, Decimal | int) and not isinstance(value, bool) and int(value) > 0:
        return f"{int(value):010d}"
    return ""

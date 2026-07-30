"""Prevent accidental execution of superseded V27 reconstruction searches."""

from __future__ import annotations

import os


def require_historical_rerun(operation: str) -> None:
    if os.environ.get("SILVERHAND_ALLOW_HISTORICAL_V27") == "1":
        return
    raise RuntimeError(
        f"{operation}: V27_HISTORICAL_RERUN_BLOCKED; "
        "actionable_reason=the active workflow is V28 authored wearable "
        "panels, not V27 micro-repair refinement; set "
        "SILVERHAND_ALLOW_HISTORICAL_V27=1 only to reproduce frozen "
        "historical evidence"
    )

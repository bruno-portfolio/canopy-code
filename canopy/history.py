"""Run history for trend tracking.

A small JSON file next to the output SVG records one entry per run day.
The score delta against the previous run feeds the grade badge, turning
the diagram from a snapshot into a trend.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_MAX_ENTRIES = 104

HISTORY_FILENAME = "canopy-history.json"


def history_path_for(svg_path: str) -> Path:
    return Path(svg_path).parent / HISTORY_FILENAME


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return entries if isinstance(entries, list) else []


def record_run(
    path: Path,
    *,
    score: float,
    grade: str,
    modules: int,
    lines: int,
    date: str | None = None,
) -> float | None:
    """Append a run entry and return the score delta vs the previous run.

    A same-day re-run replaces the previous entry for that day, so CI runs
    do not pollute the history. Returns ``None`` on the very first run.
    """
    entries = _load(path)
    today = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if entries and entries[-1].get("date") == today:
        entries.pop()
    previous = entries[-1].get("score") if entries else None
    delta = round(score - previous, 1) if isinstance(previous, int | float) else None
    entries.append(
        {"date": today, "score": score, "grade": grade, "modules": modules, "lines": lines}
    )
    entries = entries[-_MAX_ENTRIES:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    return delta

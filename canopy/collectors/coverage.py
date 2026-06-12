"""Optional coverage collector.

Reads an existing coverage report if one is present in the project root —
``coverage.json`` (coverage.py JSON report) or ``coverage.xml`` (Cobertura).
Never runs tests itself; absence of a report simply means no coverage
signal, and the score skips that factor.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from canopy.collectors import RawCoverageResult, normalize_path

_JSON_NAMES = ("coverage.json",)
_XML_NAMES = ("coverage.xml",)


def _parse_json(path: Path) -> list[RawCoverageResult]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    results: list[RawCoverageResult] = []
    for file_path, info in data.get("files", {}).items():
        summary = info.get("summary", {})
        statements = summary.get("num_statements", 0)
        covered = summary.get("covered_lines", 0)
        if statements > 0:
            results.append(
                RawCoverageResult(
                    path=normalize_path(file_path),
                    covered=covered,
                    statements=statements,
                )
            )
    return results


def _parse_xml(path: Path) -> list[RawCoverageResult]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return []

    results: list[RawCoverageResult] = []
    for cls in root.iter("class"):
        filename = cls.get("filename")
        if not filename:
            continue
        lines = cls.find("lines")
        if lines is None:
            continue
        statements = 0
        covered = 0
        for line in lines.iter("line"):
            statements += 1
            if int(line.get("hits", "0")) > 0:
                covered += 1
        if statements > 0:
            results.append(
                RawCoverageResult(
                    path=normalize_path(filename),
                    covered=covered,
                    statements=statements,
                )
            )
    return results


def collect_coverage(project_dir: str) -> list[RawCoverageResult]:
    root = Path(project_dir)
    for name in _JSON_NAMES:
        candidate = root / name
        if candidate.is_file():
            return _parse_json(candidate)
    for name in _XML_NAMES:
        candidate = root / name
        if candidate.is_file():
            return _parse_xml(candidate)
    return []

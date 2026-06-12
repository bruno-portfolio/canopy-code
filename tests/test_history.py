from __future__ import annotations

import json

from canopy.history import HISTORY_FILENAME, history_path_for, record_run


class TestHistoryPathFor:
    def test_next_to_svg(self):
        path = history_path_for("docs/canopy.svg")
        assert path.name == HISTORY_FILENAME
        assert path.parent.name == "docs"


class TestRecordRun:
    def test_first_run_no_delta(self, tmp_path):
        path = tmp_path / "canopy-history.json"
        delta = record_run(path, score=80.0, grade="B", modules=10, lines=5000, date="2026-06-12")
        assert delta is None
        entries = json.loads(path.read_text(encoding="utf-8"))
        assert len(entries) == 1
        assert entries[0]["score"] == 80.0
        assert entries[0]["grade"] == "B"

    def test_second_run_returns_delta(self, tmp_path):
        path = tmp_path / "canopy-history.json"
        record_run(path, score=80.0, grade="B", modules=10, lines=5000, date="2026-06-11")
        delta = record_run(path, score=83.5, grade="B", modules=10, lines=5100, date="2026-06-12")
        assert delta == 3.5

    def test_negative_delta(self, tmp_path):
        path = tmp_path / "canopy-history.json"
        record_run(path, score=80.0, grade="B", modules=10, lines=5000, date="2026-06-11")
        delta = record_run(path, score=75.0, grade="C", modules=10, lines=5200, date="2026-06-12")
        assert delta == -5.0

    def test_same_day_rerun_replaces_entry(self, tmp_path):
        path = tmp_path / "canopy-history.json"
        record_run(path, score=80.0, grade="B", modules=10, lines=5000, date="2026-06-11")
        record_run(path, score=82.0, grade="B", modules=10, lines=5000, date="2026-06-12")
        delta = record_run(path, score=85.0, grade="B", modules=10, lines=5000, date="2026-06-12")
        entries = json.loads(path.read_text(encoding="utf-8"))
        assert len(entries) == 2
        assert entries[-1]["score"] == 85.0
        assert delta == 5.0

    def test_corrupt_file_starts_fresh(self, tmp_path):
        path = tmp_path / "canopy-history.json"
        path.write_text("{not json", encoding="utf-8")
        delta = record_run(path, score=80.0, grade="B", modules=10, lines=5000, date="2026-06-12")
        assert delta is None
        assert len(json.loads(path.read_text(encoding="utf-8"))) == 1

    def test_caps_entries(self, tmp_path):
        path = tmp_path / "canopy-history.json"
        for i in range(120):
            record_run(
                path, score=80.0, grade="B", modules=10, lines=5000, date=f"2026-01-{i:03d}"
            )
        entries = json.loads(path.read_text(encoding="utf-8"))
        assert len(entries) == 104

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "canopy-history.json"
        record_run(path, score=80.0, grade="B", modules=10, lines=5000, date="2026-06-12")
        assert path.exists()

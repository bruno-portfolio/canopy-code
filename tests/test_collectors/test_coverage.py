from __future__ import annotations

import json
import textwrap

from canopy.collectors.coverage import collect_coverage


def _write_json_report(tmp_path, files):
    (tmp_path / "coverage.json").write_text(json.dumps({"files": files}), encoding="utf-8")


_COBERTURA_XML = textwrap.dedent("""\
    <?xml version="1.0" ?>
    <coverage version="7.6">
      <packages>
        <package name="agrobr">
          <classes>
            <class name="cache.py" filename="agrobr/cache/__init__.py" line-rate="0.5">
              <lines>
                <line number="1" hits="1"/>
                <line number="2" hits="1"/>
                <line number="3" hits="0"/>
                <line number="4" hits="0"/>
              </lines>
            </class>
          </classes>
        </package>
      </packages>
    </coverage>
""")


class TestCollectCoverageJson:
    def test_parses_summary(self, tmp_path):
        _write_json_report(
            tmp_path,
            {"agrobr/cache/__init__.py": {"summary": {"covered_lines": 40, "num_statements": 50}}},
        )
        results = collect_coverage(str(tmp_path))
        assert len(results) == 1
        assert results[0].path == "agrobr/cache/__init__.py"
        assert results[0].covered == 40
        assert results[0].statements == 50

    def test_skips_zero_statement_files(self, tmp_path):
        _write_json_report(
            tmp_path,
            {"agrobr/__init__.py": {"summary": {"covered_lines": 0, "num_statements": 0}}},
        )
        assert collect_coverage(str(tmp_path)) == []

    def test_corrupt_json_returns_empty(self, tmp_path):
        (tmp_path / "coverage.json").write_text("{broken", encoding="utf-8")
        assert collect_coverage(str(tmp_path)) == []


class TestCollectCoverageXml:
    def test_parses_line_hits(self, tmp_path):
        (tmp_path / "coverage.xml").write_text(_COBERTURA_XML, encoding="utf-8")
        results = collect_coverage(str(tmp_path))
        assert len(results) == 1
        assert results[0].path == "agrobr/cache/__init__.py"
        assert results[0].covered == 2
        assert results[0].statements == 4

    def test_corrupt_xml_returns_empty(self, tmp_path):
        (tmp_path / "coverage.xml").write_text("<broken", encoding="utf-8")
        assert collect_coverage(str(tmp_path)) == []


class TestCollectCoverageAbsent:
    def test_no_report_returns_empty(self, tmp_path):
        assert collect_coverage(str(tmp_path)) == []

    def test_json_takes_precedence_over_xml(self, tmp_path):
        _write_json_report(
            tmp_path,
            {"a.py": {"summary": {"covered_lines": 1, "num_statements": 2}}},
        )
        (tmp_path / "coverage.xml").write_text(_COBERTURA_XML, encoding="utf-8")
        results = collect_coverage(str(tmp_path))
        assert results[0].path == "a.py"

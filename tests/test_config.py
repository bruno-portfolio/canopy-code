from __future__ import annotations

import textwrap

import pytest

from canopy.config import (
    Config,
    LayerConfig,
    load_config,
    resolve_project_name,
    validate_config,
)
from canopy.exceptions import ConfigError


class TestLoadConfig:
    def test_full_config(self, tmp_config_file):
        path = tmp_config_file(
            textwrap.dedent("""\
            project: agrobr
            source: src/agrobr
            module_depth: 2
            layers:
              core:
                modules: ["_core"]
              infra:
                modules: ["_cache", "_validation"]
                label: Infrastructure
            vulture:
              min_confidence: 60
              exclude_types: ["attribute"]
            git:
              churn_days: 30
            thresholds:
              mi_healthy: 40
              mi_moderate: 20
              churn_high: 20
              min_loc: 50
            output:
              path: docs/canopy.svg
              width: 1000
              height: 800
            ignore:
              - "tests/**"
        """)
        )
        cfg = load_config(path)
        assert cfg.project == "agrobr"
        assert cfg.source == "src/agrobr"
        assert cfg.module_depth == 2
        assert "core" in cfg.layers
        assert cfg.layers["infra"].label == "Infrastructure"
        assert cfg.vulture.min_confidence == 60
        assert cfg.git.churn_days == 30
        assert cfg.thresholds.mi_healthy == 40
        assert cfg.output.path == "docs/canopy.svg"
        assert cfg.ignore == ["tests/**"]

    def test_empty_file(self, tmp_config_file):
        path = tmp_config_file("")
        cfg = load_config(path)
        assert cfg == Config()

    def test_no_file_zero_config(self, tmp_path):
        cfg = load_config(project_dir=str(tmp_path))
        assert cfg == Config()

    def test_explicit_path_not_found(self):
        with pytest.raises(ConfigError, match="Config file not found"):
            load_config("/nonexistent/canopy.yml")

    def test_missing_vulture_section(self, tmp_config_file):
        path = tmp_config_file("project: test\n")
        cfg = load_config(path)
        assert cfg.vulture.min_confidence == 60
        assert cfg.vulture.exclude_types == ["attribute"]

    def test_missing_git_section(self, tmp_config_file):
        path = tmp_config_file("project: test\n")
        cfg = load_config(path)
        assert cfg.git.churn_days == 30

    def test_missing_thresholds_section(self, tmp_config_file):
        path = tmp_config_file("project: test\n")
        cfg = load_config(path)
        assert cfg.thresholds.mi_healthy == 40
        assert cfg.thresholds.mi_moderate == 20

    def test_missing_output_section(self, tmp_config_file):
        path = tmp_config_file("project: test\n")
        cfg = load_config(path)
        assert cfg.output.path == "canopy.svg"
        assert cfg.output.width == 1000
        assert cfg.output.height == 800

    def test_auto_discover_yml(self, tmp_path):
        (tmp_path / "canopy.yml").write_text("project: found_yml\n", encoding="utf-8")
        cfg = load_config(project_dir=str(tmp_path))
        assert cfg.project == "found_yml"

    def test_auto_discover_yaml(self, tmp_path):
        (tmp_path / "canopy.yaml").write_text("project: found_yaml\n", encoding="utf-8")
        cfg = load_config(project_dir=str(tmp_path))
        assert cfg.project == "found_yaml"

    def test_yml_takes_precedence_over_yaml(self, tmp_path):
        (tmp_path / "canopy.yml").write_text("project: yml_wins\n", encoding="utf-8")
        (tmp_path / "canopy.yaml").write_text("project: yaml_loses\n", encoding="utf-8")
        cfg = load_config(project_dir=str(tmp_path))
        assert cfg.project == "yml_wins"

    def test_partial_vulture_config(self, tmp_config_file):
        path = tmp_config_file("vulture:\n  min_confidence: 80\n")
        cfg = load_config(path)
        assert cfg.vulture.min_confidence == 80
        assert cfg.vulture.exclude_types == ["attribute"]


class TestUnknownKeys:
    def test_top_level_unknown_keys_ignored(self, tmp_config_file):
        path = tmp_config_file("project: test\nfoo: bar\nbaz: 123\n")
        cfg = load_config(path)
        assert cfg.project == "test"

    def test_sub_level_unknown_keys_ignored(self, tmp_config_file):
        path = tmp_config_file(
            textwrap.dedent("""\
            vulture:
              min_confidence: 80
              unknown_setting: true
            git:
              churn_days: 60
              extra: value
        """)
        )
        cfg = load_config(path)
        assert cfg.vulture.min_confidence == 80
        assert cfg.git.churn_days == 60


class TestLayerConfig:
    def test_order_preserved(self, tmp_config_file):
        path = tmp_config_file(
            textwrap.dedent("""\
            layers:
              core:
                modules: ["_core"]
              infra:
                modules: ["_cache"]
              data:
                modules: ["comexstat"]
        """)
        )
        cfg = load_config(path)
        assert list(cfg.layers.keys()) == ["core", "infra", "data"]

    def test_label_default_empty(self, tmp_config_file):
        path = tmp_config_file(
            textwrap.dedent("""\
            layers:
              core:
                modules: ["_core"]
        """)
        )
        cfg = load_config(path)
        assert cfg.layers["core"].label == ""

    def test_label_explicit(self, tmp_config_file):
        path = tmp_config_file(
            textwrap.dedent("""\
            layers:
              infra:
                modules: ["_cache"]
                label: Infrastructure
        """)
        )
        cfg = load_config(path)
        assert cfg.layers["infra"].label == "Infrastructure"

    def test_empty_layer_value(self, tmp_config_file):
        path = tmp_config_file(
            textwrap.dedent("""\
            layers:
              core:
        """)
        )
        cfg = load_config(path)
        assert cfg.layers["core"] == LayerConfig()


class TestResolveProjectName:
    def test_from_config(self):
        cfg = Config(project="agrobr")
        assert resolve_project_name(cfg, "/some/path") == "agrobr"

    def test_from_directory(self):
        cfg = Config()
        name = resolve_project_name(cfg, "/some/my-project")
        assert name == "my-project"

    def test_trailing_slash(self):
        cfg = Config()
        name = resolve_project_name(cfg, "/some/my-project/")
        assert name == "my-project"


class TestValidateConfig:
    def test_source_not_found(self, tmp_path):
        cfg = Config(source="nonexistent")
        with pytest.raises(ConfigError, match="Source directory not found"):
            validate_config(cfg, str(tmp_path))

    def test_source_exists(self, tmp_path):
        (tmp_path / "src").mkdir()
        cfg = Config(source="src")
        validate_config(cfg, str(tmp_path))

    def test_negative_depth(self, tmp_path):
        cfg = Config(module_depth=0)
        with pytest.raises(ConfigError, match="module_depth must be >= 1"):
            validate_config(cfg, str(tmp_path))

    def test_dot_source_valid(self, tmp_path):
        cfg = Config(source=".")
        validate_config(cfg, str(tmp_path))

    def test_threshold_ordering(self, tmp_path):
        from canopy.config import ThresholdsConfig

        cfg = Config(thresholds=ThresholdsConfig(mi_healthy=20, mi_moderate=20))
        with pytest.raises(ConfigError, match="mi_healthy.*must be greater than.*mi_moderate"):
            validate_config(cfg, str(tmp_path))

    def test_output_dimensions_zero(self, tmp_path):
        from canopy.config import OutputConfig

        cfg = Config(output=OutputConfig(width=0, height=800))
        with pytest.raises(ConfigError, match="output.width must be > 0"):
            validate_config(cfg, str(tmp_path))

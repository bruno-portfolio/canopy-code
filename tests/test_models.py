from __future__ import annotations

import pytest

from canopy.models import Dependency, Layer, Module, ProjectData


class TestModule:
    def test_creation_all_fields(self):
        m = Module(
            name="agrobr.cepea",
            lines=270,
            funcs=5,
            mi=41.35,
            cc=3.3,
            dead=1,
            churn=9,
            layer="market",
            desc="Price indicators",
        )
        assert m.name == "agrobr.cepea"
        assert m.lines == 270
        assert m.funcs == 5
        assert m.mi == 41.35
        assert m.cc == 3.3
        assert m.dead == 1
        assert m.churn == 9
        assert m.layer == "market"
        assert m.desc == "Price indicators"

    def test_defaults(self):
        m = Module(name="x", lines=10, funcs=1, mi=50.0, cc=1.0)
        assert m.dead == 0
        assert m.churn == 0
        assert m.layer == ""
        assert m.desc == ""

    def test_frozen(self):
        m = Module(name="x", lines=10, funcs=1, mi=50.0, cc=1.0)
        with pytest.raises(AttributeError):
            m.name = "y"  # type: ignore[misc]

    def test_mi_preserves_float(self):
        m = Module(name="x", lines=10, funcs=1, mi=21.35, cc=1.0)
        assert m.mi == 21.35
        assert isinstance(m.mi, float)

    def test_cc_preserves_float(self):
        m = Module(name="x", lines=10, funcs=1, mi=50.0, cc=3.75)
        assert m.cc == 3.75
        assert isinstance(m.cc, float)


class TestDependency:
    def test_creation(self):
        d = Dependency(from_module="_core", to_module="cepea", weight=0.8)
        assert d.from_module == "_core"
        assert d.to_module == "cepea"
        assert d.weight == 0.8

    def test_weight_default(self):
        d = Dependency(from_module="a", to_module="b")
        assert d.weight == 1.0

    def test_frozen(self):
        d = Dependency(from_module="a", to_module="b")
        with pytest.raises(AttributeError):
            d.weight = 2.0  # type: ignore[misc]


class TestLayer:
    def test_creation(self):
        layer = Layer(name="core", ring=0, label="Core")
        assert layer.name == "core"
        assert layer.ring == 0
        assert layer.label == "Core"

    def test_frozen(self):
        layer = Layer(name="core", ring=0, label="Core")
        with pytest.raises(AttributeError):
            layer.ring = 1  # type: ignore[misc]


class TestProjectData:
    def test_creation(self):
        m = Module(name="x", lines=10, funcs=1, mi=50.0, cc=1.0)
        d = Dependency(from_module="x", to_module="y")
        layer = Layer(name="core", ring=0, label="Core")
        pd = ProjectData(
            modules=[m],
            dependencies=[d],
            layers=[layer],
            project_name="test",
        )
        assert len(pd.modules) == 1
        assert len(pd.dependencies) == 1
        assert len(pd.layers) == 1
        assert pd.project_name == "test"

    def test_defaults(self):
        pd = ProjectData()
        assert pd.modules == []
        assert pd.dependencies == []
        assert pd.layers == []
        assert pd.project_name == ""

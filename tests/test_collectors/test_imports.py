from __future__ import annotations

import warnings

from canopy.collectors import RawImportEdge
from canopy.collectors.imports import collect_imports


class TestAbsoluteImport:
    def test_absolute_import_internal(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text("import mypkg.beta\n")
        (pkg / "beta.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("alpha", "mypkg.beta")]


class TestRelativeImport:
    def test_relative_import_level_one(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text("from . import beta\n")
        (pkg / "beta.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("alpha", "mypkg.beta")]

    def test_relative_import_level_two(self, tmp_path):
        pkg = tmp_path / "mypkg"
        sub = pkg / "sub"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (sub / "deep.py").write_text("from .. import utils\n")
        (pkg / "utils.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("sub.deep", "mypkg.utils")]


class TestInitFile:
    def test_init_file_as_package(self, tmp_path):
        pkg = tmp_path / "mypkg"
        sub = pkg / "sub"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("from .core import something\n")
        (sub / "core.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("sub", "mypkg.sub.core")]


class TestFiltering:
    def test_stdlib_filtered(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text("import os\nimport sys\n")

        edges = collect_imports(str(pkg))

        assert edges == []

    def test_external_filtered(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text("import click\nimport yaml\n")

        edges = collect_imports(str(pkg))

        assert edges == []

    def test_future_filtered(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text("from __future__ import annotations\n")

        edges = collect_imports(str(pkg))

        assert edges == []

    def test_self_import_filtered(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text("import mypkg.alpha\n")

        edges = collect_imports(str(pkg))

        assert edges == []


class TestEdgeCases:
    def test_syntax_error_skipped(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "bad.py").write_text("def broken(\n")
        (pkg / "good.py").write_text("import mypkg.bad\n")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            edges = collect_imports(str(pkg))

        assert len(edges) == 1
        assert edges[0].source_module == "good"
        assert len(w) == 1

    def test_empty_directory(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()

        edges = collect_imports(str(pkg))

        assert edges == []

    def test_star_import(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text("from mypkg.beta import *\n")
        (pkg / "beta.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("alpha", "mypkg.beta")]


class TestTypeCheckingImports:
    def test_type_checking_import_ignored(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text(
            "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from mypkg import beta\n"
        )
        (pkg / "beta.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == []

    def test_typing_attribute_form_ignored(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text(
            "import typing\nif typing.TYPE_CHECKING:\n    from mypkg import beta\n"
        )
        (pkg / "beta.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == []

    def test_else_branch_still_counted(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text(
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from mypkg import beta\n"
            "else:\n    from mypkg.gamma import helper\n"
        )
        (pkg / "beta.py").write_text("")
        (pkg / "gamma.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("alpha", "mypkg.gamma")]

    def test_lazy_import_inside_function_still_counted(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text(
            "def build():\n    from mypkg.beta import helper\n    return helper\n"
        )
        (pkg / "beta.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("alpha", "mypkg.beta")]

    def test_runtime_import_after_type_checking_block_counted(self, tmp_path):
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "alpha.py").write_text(
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from mypkg import beta\n"
            "from mypkg.gamma import helper\n"
        )
        (pkg / "beta.py").write_text("")
        (pkg / "gamma.py").write_text("")

        edges = collect_imports(str(pkg))

        assert edges == [RawImportEdge("alpha", "mypkg.gamma")]

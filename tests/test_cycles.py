from __future__ import annotations

from canopy.cycles import cycle_groups, find_cycle_edges
from canopy.models import Dependency


def _dep(src: str, tgt: str) -> Dependency:
    return Dependency(from_module=src, to_module=tgt, weight=1.0)


class TestFindCycleEdges:
    def test_no_cycle(self):
        deps = [_dep("pkg.a", "pkg.b"), _dep("pkg.b", "pkg.c")]
        assert find_cycle_edges(deps) == frozenset()

    def test_two_node_cycle(self):
        deps = [_dep("pkg.a", "pkg.b"), _dep("pkg.b", "pkg.a")]
        assert find_cycle_edges(deps) == frozenset({("pkg.a", "pkg.b"), ("pkg.b", "pkg.a")})

    def test_three_node_cycle(self):
        deps = [_dep("pkg.a", "pkg.b"), _dep("pkg.b", "pkg.c"), _dep("pkg.c", "pkg.a")]
        assert find_cycle_edges(deps) == frozenset(
            {("pkg.a", "pkg.b"), ("pkg.b", "pkg.c"), ("pkg.c", "pkg.a")}
        )

    def test_edge_into_cycle_not_marked(self):
        deps = [_dep("pkg.x", "pkg.a"), _dep("pkg.a", "pkg.b"), _dep("pkg.b", "pkg.a")]
        edges = find_cycle_edges(deps)
        assert ("pkg.x", "pkg.a") not in edges
        assert ("pkg.a", "pkg.b") in edges

    def test_two_separate_cycles(self):
        deps = [
            _dep("pkg.a", "pkg.b"),
            _dep("pkg.b", "pkg.a"),
            _dep("pkg.c", "pkg.d"),
            _dep("pkg.d", "pkg.c"),
        ]
        assert len(find_cycle_edges(deps)) == 4

    def test_cross_scc_edge_not_marked(self):
        deps = [
            _dep("pkg.a", "pkg.b"),
            _dep("pkg.b", "pkg.a"),
            _dep("pkg.b", "pkg.c"),
            _dep("pkg.c", "pkg.d"),
            _dep("pkg.d", "pkg.c"),
        ]
        edges = find_cycle_edges(deps)
        assert ("pkg.b", "pkg.c") not in edges
        assert ("pkg.a", "pkg.b") in edges
        assert ("pkg.c", "pkg.d") in edges

    def test_empty(self):
        assert find_cycle_edges([]) == frozenset()

    def test_diamond_no_cycle(self):
        deps = [
            _dep("pkg.a", "pkg.b"),
            _dep("pkg.a", "pkg.c"),
            _dep("pkg.b", "pkg.d"),
            _dep("pkg.c", "pkg.d"),
        ]
        assert find_cycle_edges(deps) == frozenset()

    def test_root_package_reexport_cycle_ignored(self):
        # __init__.py re-exporting submodules while they import from the
        # root is idiomatic API surface, not an architecture smell
        deps = [_dep("pkg", "pkg.a"), _dep("pkg.a", "pkg"), _dep("pkg", "pkg.b")]
        assert find_cycle_edges(deps) == frozenset()

    def test_submodule_cycle_survives_root_filter(self):
        deps = [
            _dep("pkg", "pkg.a"),
            _dep("pkg.a", "pkg"),
            _dep("pkg.a", "pkg.b"),
            _dep("pkg.b", "pkg.a"),
        ]
        assert find_cycle_edges(deps) == frozenset({("pkg.a", "pkg.b"), ("pkg.b", "pkg.a")})


class TestCycleGroups:
    def test_no_groups(self):
        assert cycle_groups([_dep("pkg.a", "pkg.b")]) == []

    def test_single_group_sorted(self):
        deps = [_dep("pkg.b", "pkg.a"), _dep("pkg.a", "pkg.b")]
        assert cycle_groups(deps) == [["pkg.a", "pkg.b"]]

    def test_multiple_groups(self):
        deps = [
            _dep("pkg.a", "pkg.b"),
            _dep("pkg.b", "pkg.a"),
            _dep("pkg.x", "pkg.y"),
            _dep("pkg.y", "pkg.x"),
        ]
        assert cycle_groups(deps) == [["pkg.a", "pkg.b"], ["pkg.x", "pkg.y"]]

    def test_root_cycle_not_reported(self):
        deps = [_dep("pkg", "pkg.a"), _dep("pkg.a", "pkg")]
        assert cycle_groups(deps) == []

    def test_large_chain_no_recursion_error(self):
        deps = [_dep(f"pkg.m{i}", f"pkg.m{i + 1}") for i in range(5000)]
        assert cycle_groups(deps) == []

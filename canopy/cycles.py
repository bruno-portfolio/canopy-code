"""Import cycle detection over the module dependency graph.

Tarjan's strongly connected components, iterative to avoid recursion
limits. An edge participates in a cycle when both endpoints belong to
the same SCC of size > 1.

The root package node (no dot in its name) is excluded: ``__init__.py``
re-exporting submodules while submodules do ``from pkg import x`` is
idiomatic Python API surface, not an architecture smell. Only cycles
between submodules are reported.
"""

from __future__ import annotations

from canopy.models import Dependency


def _submodule_deps(dependencies: list[Dependency]) -> list[Dependency]:
    return [d for d in dependencies if "." in d.from_module and "." in d.to_module]


def _build_graph(deps: list[Dependency]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for dep in deps:
        graph.setdefault(dep.from_module, []).append(dep.to_module)
        graph.setdefault(dep.to_module, [])
    return graph


def _tarjan_sccs(graph: dict[str, list[str]]) -> list[list[str]]:
    index_counter = 0
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []

    for start in graph:
        if start in index:
            continue
        work: list[tuple[str, int]] = [(start, 0)]
        while work:
            node, child_i = work[-1]
            if child_i == 0:
                index[node] = index_counter
                lowlink[node] = index_counter
                index_counter += 1
                stack.append(node)
                on_stack.add(node)
            recurse = False
            children = graph.get(node, [])
            for i in range(child_i, len(children)):
                child = children[i]
                if child not in index:
                    work[-1] = (node, i + 1)
                    work.append((child, 0))
                    recurse = True
                    break
                if child in on_stack:
                    lowlink[node] = min(lowlink[node], index[child])
            if recurse:
                continue
            work.pop()
            if lowlink[node] == index[node]:
                scc: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    scc.append(member)
                    if member == node:
                        break
                sccs.append(scc)
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])

    return sccs


def find_cycle_edges(dependencies: list[Dependency]) -> frozenset[tuple[str, str]]:
    deps = _submodule_deps(dependencies)
    graph = _build_graph(deps)

    scc_of: dict[str, int] = {}
    for i, scc in enumerate(_tarjan_sccs(graph)):
        if len(scc) > 1:
            for node in scc:
                scc_of[node] = i

    return frozenset(
        (dep.from_module, dep.to_module)
        for dep in deps
        if dep.from_module in scc_of and scc_of.get(dep.to_module) == scc_of[dep.from_module]
    )


def cycle_groups(dependencies: list[Dependency]) -> list[list[str]]:
    """SCCs with more than one module, sorted for stable CLI output."""
    graph = _build_graph(_submodule_deps(dependencies))
    groups = [sorted(scc) for scc in _tarjan_sccs(graph) if len(scc) > 1]
    groups.sort()
    return groups

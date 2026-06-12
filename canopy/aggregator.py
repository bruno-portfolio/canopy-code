from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from canopy import config, models
from canopy.collectors import (
    RawChurnResult,
    RawCoverageResult,
    RawImportEdge,
    RawRadonResult,
    RawVultureResult,
    normalize_path,
)
from canopy.score import compute_score, risk_index, score_factors

_MI_DEFAULT = 100.0
_CC_DEFAULT = 0.0


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    pattern = normalize_path(pattern)
    i = 0
    out: list[str] = []
    while i < len(pattern):
        char = pattern[i]
        if char == "*":
            if pattern[i : i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
            elif pattern[i : i + 2] == "**":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif char == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(char))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _compile_ignore(patterns: list[str]) -> list[re.Pattern[str]]:
    return [_glob_to_regex(p) for p in patterns]


def _is_ignored(
    relative_path: str,
    ignore_res: list[re.Pattern[str]],
    source_prefix: str,
) -> bool:
    if not ignore_res:
        return False
    candidates = (relative_path, source_prefix + relative_path)
    return any(rx.match(c) for rx in ignore_res for c in candidates)


@dataclass
class _RadonAccum:
    mi_weighted_sum: float = 0.0
    mi_weight_total: int = 0
    func_complexities: list[int] = field(default_factory=list)


def _source_prefix(cfg: config.Config) -> str:
    source = normalize_path(cfg.source)
    if source == ".":
        return ""
    return source.rstrip("/") + "/"


def _root_package(source_path: str) -> str:
    return Path(source_path).name


def _truncate(module_name: str, depth: int) -> str:
    parts = module_name.split(".")
    return ".".join(parts[:depth])


def _strip_source_prefix(path: str, source_prefix: str, source_path: str = "") -> str:
    normalized = normalize_path(path)
    # Handle absolute paths from collectors by making them relative to source_path
    if source_path:
        norm_source = normalize_path(source_path).rstrip("/") + "/"
        if normalized.startswith(norm_source):
            return normalized[len(norm_source) :]
    if source_prefix and normalized.startswith(source_prefix):
        return normalized[len(source_prefix) :]
    return normalized


def _relative_path_to_module(
    relative_path: str,
    root_package: str,
    depth: int,
) -> str:
    path = normalize_path(relative_path)
    if path.endswith(".py"):
        path = path[:-3]
    if path.endswith("/__init__") or path == "__init__":
        path = path.rsplit("/__init__", 1)[0] if "/__init__" in path else ""
    module = root_package + "." + path.replace("/", ".") if path else root_package
    return _truncate(module, depth)


def _path_to_module(
    path: str,
    source_prefix: str,
    root_package: str,
    depth: int,
    source_path: str = "",
) -> str:
    stripped = _strip_source_prefix(path, source_prefix, source_path)
    return _relative_path_to_module(stripped, root_package, depth)


def _discover_files(
    source_path: str,
    ignore_res: list[re.Pattern[str]] | None = None,
    source_prefix: str = "",
) -> dict[str, int]:
    result: dict[str, int] = {}
    root = Path(source_path)
    for py_file in sorted(root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        relative = normalize_path(str(py_file.relative_to(root)))
        if ignore_res and _is_ignored(relative, ignore_res, source_prefix):
            continue
        try:
            line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            line_count = 0
        result[relative] = line_count
    return result


def _process_radon(
    radon_results: list[RawRadonResult],
    file_lines: dict[str, int],
    source_prefix: str,
    root_package: str,
    depth: int,
    source_path: str = "",
) -> dict[str, _RadonAccum]:
    accum: dict[str, _RadonAccum] = {}
    for result in radon_results:
        relative = _strip_source_prefix(result.path, source_prefix, source_path)
        module = _relative_path_to_module(relative, root_package, depth)
        lines = file_lines.get(relative, 0)

        if module not in accum:
            accum[module] = _RadonAccum()
        acc = accum[module]
        acc.mi_weighted_sum += result.mi * lines
        acc.mi_weight_total += lines

        func_max: dict[str, int] = {}
        for func in result.functions:
            key = f"{func.classname}.{func.name}" if func.classname else func.name
            func_max[key] = max(func_max.get(key, 0), func.complexity)

        acc.func_complexities.extend(func_max.values())

    return accum


def _process_vulture(
    vulture_results: list[RawVultureResult],
    source_prefix: str,
    root_package: str,
    depth: int,
    source_path: str = "",
    exclude_types: frozenset[str] = frozenset(),
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in vulture_results:
        if result.kind in exclude_types:
            continue
        module = _path_to_module(result.path, source_prefix, root_package, depth, source_path)
        counts[module] = counts.get(module, 0) + 1
    return counts


def _process_churn(
    churn_results: list[RawChurnResult],
    source_prefix: str,
    root_package: str,
    depth: int,
    source_path: str = "",
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for result in churn_results:
        module = _path_to_module(result.path, source_prefix, root_package, depth, source_path)
        totals[module] = totals.get(module, 0) + result.commit_count
    return totals


def _process_coverage(
    coverage_results: list[RawCoverageResult],
    source_prefix: str,
    root_package: str,
    depth: int,
    source_path: str = "",
) -> dict[str, float]:
    covered: dict[str, int] = {}
    statements: dict[str, int] = {}
    for result in coverage_results:
        module = _path_to_module(result.path, source_prefix, root_package, depth, source_path)
        covered[module] = covered.get(module, 0) + result.covered
        statements[module] = statements.get(module, 0) + result.statements
    return {module: covered[module] / total for module, total in statements.items() if total > 0}


def _filter_ignored(
    results: list,
    ignore_res: list[re.Pattern[str]],
    source_prefix: str,
    source_path: str,
) -> list:
    if not ignore_res:
        return results
    return [
        r
        for r in results
        if not _is_ignored(
            _strip_source_prefix(r.path, source_prefix, source_path),
            ignore_res,
            source_prefix,
        )
    ]


def _process_imports(
    imports: list[RawImportEdge],
    root_package: str,
    depth: int,
) -> list[models.Dependency]:
    edge_counts: dict[tuple[str, str], int] = {}
    for edge in imports:
        if edge.source_module:
            source = _truncate(root_package + "." + edge.source_module, depth)
        else:
            source = _truncate(root_package, depth)
        target = _truncate(edge.target_module, depth)

        if source == target:
            continue

        key = (source, target)
        edge_counts[key] = edge_counts.get(key, 0) + 1

    return [
        models.Dependency(from_module=src, to_module=tgt, weight=float(count))
        for (src, tgt), count in sorted(edge_counts.items())
    ]


def aggregate(
    *,
    cfg: config.Config,
    source_path: str,
    imports: list[RawImportEdge],
    radon: list[RawRadonResult],
    vulture: list[RawVultureResult],
    churn: list[RawChurnResult],
    coverage: list[RawCoverageResult] | None = None,
) -> models.ProjectData:
    prefix = _source_prefix(cfg)
    root = _root_package(source_path)
    depth = cfg.module_depth
    ignore_res = _compile_ignore(cfg.ignore or [])

    file_data = _discover_files(source_path, ignore_res, prefix)

    radon = _filter_ignored(radon, ignore_res, prefix, source_path)
    vulture = _filter_ignored(vulture, ignore_res, prefix, source_path)
    churn = _filter_ignored(churn, ignore_res, prefix, source_path)
    coverage = _filter_ignored(coverage or [], ignore_res, prefix, source_path)

    module_lines: dict[str, int] = {}
    for rel_path, lines in file_data.items():
        module = _relative_path_to_module(rel_path, root, depth)
        module_lines[module] = module_lines.get(module, 0) + lines

    radon_data = _process_radon(radon, file_data, prefix, root, depth, source_path)
    vulture_data = _process_vulture(
        vulture,
        prefix,
        root,
        depth,
        source_path,
        exclude_types=frozenset(cfg.vulture.exclude_types or []),
    )
    churn_data = _process_churn(churn, prefix, root, depth, source_path)
    coverage_data = _process_coverage(coverage, prefix, root, depth, source_path)
    deps = _process_imports(imports, root, depth)

    all_modules = set(module_lines.keys())
    # churn_data may contain modules outside the source tree (tests/, scripts/
    # picked up by git log); only real modules may set the normalisation max
    churn_max = max((churn_data.get(name, 0) for name in all_modules), default=0)

    modules: list[models.Module] = []
    for name in sorted(all_modules):
        lines = module_lines.get(name, 0)

        radon_acc = radon_data.get(name)
        if lines == 0 and not (radon_acc and radon_acc.func_complexities):
            continue
        if radon_acc and radon_acc.mi_weight_total > 0:
            mi = radon_acc.mi_weighted_sum / radon_acc.mi_weight_total
        else:
            mi = _MI_DEFAULT

        complexities = radon_acc.func_complexities if radon_acc else []
        cc = sum(complexities) / len(complexities) if complexities else _CC_DEFAULT
        funcs = len(complexities)
        cc_max = max(complexities, default=0)
        n_cc_over = sum(1 for c in complexities if c > cfg.score.cc_threshold)
        dead = vulture_data.get(name, 0)
        module_churn = churn_data.get(name, 0)
        module_coverage = coverage_data.get(name)

        factors = score_factors(
            funcs=funcs,
            n_cc_over=n_cc_over,
            cc_max=cc_max,
            dead=dead,
            coverage=module_coverage,
            cc_threshold=cfg.score.cc_threshold,
            complexity_spread=cfg.score.complexity_spread,
            worst_function=cfg.score.worst_function,
            dead_ratio=cfg.score.dead_ratio,
            coverage_weight=cfg.score.coverage_weight,
        )
        score = compute_score(factors)

        modules.append(
            models.Module(
                name=name,
                lines=lines,
                funcs=funcs,
                mi=round(mi, 2),
                cc=round(cc, 2),
                dead=dead,
                churn=module_churn,
                score=score,
                cc_max=cc_max,
                n_cc_over=n_cc_over,
                coverage=module_coverage,
                risk=risk_index(module_churn, churn_max, score),
                factors=factors,
            )
        )

    return models.ProjectData(modules=modules, dependencies=deps)

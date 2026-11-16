"""Which Python files of a workload the profiler reads."""

from __future__ import annotations

from pathlib import Path


def ignored_path(path: Path) -> bool:
    ignored = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "build",
        "dist",
        "*.egg-info",
    }
    parts = set(path.parts)
    if parts & (ignored - {"*.egg-info"}):
        return True
    return any(part.endswith(".egg-info") for part in path.parts)


def workload_source_files(root: Path) -> list[Path]:
    source_roots = [root / "src", root]
    files: list[Path] = []
    seen: set[Path] = set()
    for source_root in source_roots:
        if not source_root.is_dir():
            continue
        for path in sorted(source_root.rglob("*.py")):
            if ignored_path(path) or "tests" in path.parts or path.name.startswith("test_"):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(resolved)
    return files

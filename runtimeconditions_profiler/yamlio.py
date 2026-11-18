from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import RuntimeConditionsError

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover - dependency error path
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


class Yaml:
    @staticmethod
    def load_text(text: str) -> dict[str, Any]:
        if yaml is None:
            raise RuntimeConditionsError(f"PyYAML is required: {YAML_IMPORT_ERROR}")
        data = yaml.safe_load(text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise RuntimeConditionsError("YAML document must be a mapping")
        return data

    @staticmethod
    def load(path: Path) -> dict[str, Any]:
        return Yaml.load_text(path.read_text(encoding="utf-8"))


if yaml is not None:

    class _Dumper(yaml.SafeDumper):
        def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
            # Indent a list under its key, as the other profilers do: "  - item", not "- item".
            return super().increase_indent(flow, False)


def dump_yaml(data: dict[str, Any]) -> str:
    if yaml is None:
        raise RuntimeConditionsError(f"PyYAML is required: {YAML_IMPORT_ERROR}")
    # Keep non-ASCII names as written, and never fold a long value over several lines.
    return yaml.dump(
        data, Dumper=_Dumper, sort_keys=False, default_flow_style=False, allow_unicode=True, width=2**31 - 1,
    )


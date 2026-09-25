"""Dependency-free deterministic YAML renderer for the presentation schema."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from ..models import CanonicalCase
from ..presentation import EvidenceView, ensure_view
from ..transform_guard import integrity_guarded
from .base import artifact
from .json_renderer import _payload


def _yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    # JSON string quoting is valid YAML and avoids ambiguous scalars.
    return json.dumps(str(value), ensure_ascii=False)


def _emit(value, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, Mapping):
        lines: list[str] = []
        for key in sorted(value):
            item = value[key]
            if isinstance(item, (Mapping, list, tuple)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_emit(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_yaml_scalar(item)}")
        return lines
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        lines = []
        if not value:
            return [f"{prefix}[]"]
        for item in value:
            if isinstance(item, Mapping):
                keys = sorted(item)
                if not keys:
                    lines.append(f"{prefix}- {{}}")
                    continue
                first = keys[0]
                first_value = item[first]
                if isinstance(first_value, (Mapping, list, tuple)):
                    lines.append(f"{prefix}- {first}:")
                    lines.extend(_emit(first_value, indent + 4))
                else:
                    lines.append(f"{prefix}- {first}: {_yaml_scalar(first_value)}")
                for key in keys[1:]:
                    child = item[key]
                    if isinstance(child, (Mapping, list, tuple)):
                        lines.append(f"{' ' * (indent + 2)}{key}:")
                        lines.extend(_emit(child, indent + 4))
                    else:
                        lines.append(f"{' ' * (indent + 2)}{key}: {_yaml_scalar(child)}")
            elif isinstance(item, (list, tuple)):
                lines.append(f"{prefix}-")
                lines.extend(_emit(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_yaml_scalar(item)}")
        return lines
    return [f"{prefix}{_yaml_scalar(value)}"]


@integrity_guarded
def render_yaml(case: CanonicalCase, view: EvidenceView | None = None):
    view = ensure_view(case, view)
    content = "\n".join(_emit(_payload(view))) + "\n"
    return artifact(view, "yaml", content)

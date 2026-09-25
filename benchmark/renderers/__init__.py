"""Deterministic presentation renderers."""

from .event_log import render_event_log
from .json_renderer import render_json
from .prose import render_prose
from .table import render_table
from .yaml_renderer import render_yaml

RENDERERS = {
    "prose": render_prose,
    "json": render_json,
    "yaml": render_yaml,
    "table": render_table,
    "event_log": render_event_log,
}

__all__ = [
    "RENDERERS",
    "render_prose",
    "render_json",
    "render_yaml",
    "render_table",
    "render_event_log",
]

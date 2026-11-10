"""Presets and key bindings, read from a TOML file."""
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import layout

DEFAULT_PATH = Path("/etc/alienfx-elc/config.toml")
BUNDLED_PATH = Path(__file__).with_name("default_config.toml")

KEY_CODES = {
    "macro_preset_cycle": 0x2B2,
    "macro1": 0x290,
    "macro2": 0x291,
    "macro3": 0x292,
    "macro4": 0x293,
    "macro5": 0x294,
}


def _rgb(text):
    text = text.removeprefix("#")
    if len(text) != 6:
        raise ValueError(f"colour must be RRGGBB: {text!r}")
    return tuple(bytes.fromhex(text))


def frame(zone_colors):
    """Full assignment for one look: every managed zone off unless the preset lights it.

    Returns [(rgb, [zone ids])], one entry per distinct colour.
    """
    colors = {zone: (0, 0, 0) for zone in layout.MANAGED_ZONES}
    for name, color in zone_colors.items():
        for zone in layout.resolve(name):
            colors[zone] = _rgb(color)
    groups = {}
    for zone, rgb in colors.items():
        groups.setdefault(rgb, []).append(zone)
    return list(groups.items())


@dataclass
class Preset:
    name: str
    kind: str
    frames: list
    timeout: float = 0.0
    off_frame: list = field(default_factory=lambda: frame({}))


def _preset(name, table):
    kind = table.get("type", "static")
    if kind == "static":
        return Preset(name, kind, [frame(table.get("zones", {}))])
    if kind == "steps":
        steps = table.get("steps")
        if not steps:
            raise ValueError(f"preset {name}: 'steps' needs at least one step")
        return Preset(name, kind, [frame(step) for step in steps])
    if kind == "auto":
        timeout = float(table.get("timeout", 10))
        if timeout <= 0:
            raise ValueError(f"preset {name}: timeout must be positive")
        return Preset(name, kind, [frame(table.get("zones", {}))], timeout=timeout)
    raise ValueError(f"preset {name}: unknown type {kind!r}")


@dataclass
class Config:
    keyboard: str
    startup: str
    presets: dict
    bindings: dict


def parse(data):
    presets = {name: _preset(name, table) for name, table in data.get("presets", {}).items()}
    startup = data.get("startup", "default")
    if startup not in presets:
        raise ValueError(f"startup preset {startup!r} is not defined")
    bindings = {}
    for key, preset in data.get("keys", {}).items():
        if key not in KEY_CODES:
            raise ValueError(f"unknown key {key!r}; known: {', '.join(KEY_CODES)}")
        if preset not in presets:
            raise ValueError(f"key {key} points to undefined preset {preset!r}")
        bindings[KEY_CODES[key]] = preset
    return Config(data.get("keyboard", "AT Translated Set 2 keyboard"), startup, presets, bindings)


def load(path=None):
    if path is None:
        path = DEFAULT_PATH if DEFAULT_PATH.exists() else BUNDLED_PATH
    with open(path, "rb") as f:
        return parse(tomllib.load(f))

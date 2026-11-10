"""Zone layout of the Alienware 15 R4 (AW-ELC platform 0x0104), mapped by hand."""

PLATFORM = 0x0104

ZONES = {
    "alien_head": 0x00,
    "wordmark": 0x01,
    "touchpad": 0x02,
    "power_button": 0x03,
    "keyboard_right": 0x04,
    "keyboard_center_right": 0x05,
    "keyboard_center_left": 0x06,
    "keyboard_left": 0x07,
    "base_left": 0x08,
    "base_right": 0x09,
    "lid_left": 0x0A,
    "lid_right": 0x0B,
    "macro_keys": 0x0C,
    "unused": 0x0D,
}

GROUPS = {
    "keyboard": ["keyboard_right", "keyboard_center_right", "keyboard_center_left", "keyboard_left", "macro_keys"],
    "strips": ["base_left", "base_right", "lid_left", "lid_right"],
    "all": [name for name in ZONES if name != "power_button"],
}

# The firmware's power animation drives the power button; painting it too makes the two alternate.
MANAGED_ZONES = [zone for name, zone in ZONES.items() if name != "power_button"]


def resolve(name):
    if name in GROUPS:
        return [ZONES[member] for member in GROUPS[name]]
    if name in ZONES:
        return [ZONES[name]]
    raise ValueError(f"unknown zone or group: {name}")

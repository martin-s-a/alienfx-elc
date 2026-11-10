import re
import tomllib
import unittest
from pathlib import Path

from alienfx_elc import config, layout
from alienfx_elc.lighting import Lighting

POWER_BUTTON = layout.ZONES["power_button"]


def zones_by_color(groups):
    return {rgb: sorted(zones) for rgb, zones in groups}


class FakeElc:
    def __init__(self):
        self.played = []

    def play(self, groups):
        self.played.append(zones_by_color(groups))


class FrameTest(unittest.TestCase):
    def test_unlisted_zones_are_off_and_power_button_is_left_alone(self):
        groups = zones_by_color(config.frame({"keyboard": "606060"}))
        keyboard = sorted(layout.resolve("keyboard"))
        self.assertEqual(groups[(0x60, 0x60, 0x60)], keyboard)
        everything = sorted(z for zones in groups.values() for z in zones)
        self.assertNotIn(POWER_BUTTON, everything)
        self.assertEqual(everything, sorted(layout.MANAGED_ZONES))

    def test_power_button_is_painted_only_when_named(self):
        groups = zones_by_color(config.frame({"power_button": "0000ff"}))
        self.assertEqual(groups[(0, 0, 0xFF)], [POWER_BUTTON])


INPUT_HEADER = Path("/usr/include/linux/input-event-codes.h")


@unittest.skipUnless(INPUT_HEADER.exists(), "kernel headers not installed")
class KeyCodesTest(unittest.TestCase):
    def test_key_codes_match_the_kernel_header(self):
        defines = dict(re.findall(r"#define\s+(KEY_\w+)\s+(0x[0-9a-fA-F]+|\d+)", INPUT_HEADER.read_text()))
        for name, code in config.KEY_CODES.items():
            self.assertEqual(int(defines["KEY_" + name.upper()], 0), code, name)


class BundledConfigTest(unittest.TestCase):
    def test_bundled_config_parses_and_binds_the_macro_keys(self):
        cfg = config.load(config.BUNDLED_PATH)
        self.assertEqual(cfg.bindings[config.KEY_CODES["macro_preset_cycle"]], "default")
        self.assertEqual(cfg.bindings[config.KEY_CODES["macro3"]], "auto")
        self.assertNotIn(config.KEY_CODES["macro4"], cfg.bindings)

    def test_binding_to_undefined_preset_is_rejected(self):
        data = tomllib.loads('[presets.default]\n[keys]\nmacro1 = "nope"\n')
        with self.assertRaises(ValueError):
            config.parse(data)


def make_lighting():
    cfg = config.load(config.BUNDLED_PATH)
    elc = FakeElc()
    return Lighting(elc, cfg.presets), elc


def keyboard_color(played):
    keyboard_zone = layout.ZONES["keyboard_left"]
    return next(rgb for rgb, zones in played.items() if keyboard_zone in zones)


class LightingTest(unittest.TestCase):
    def test_steps_advance_on_repeat_and_wrap(self):
        lighting, elc = make_lighting()
        for _ in range(5):
            lighting.select("brightness", 0)
        levels = [keyboard_color(p)[0] for p in elc.played]
        self.assertEqual(levels, [0x40, 0x80, 0xC0, 0xFF, 0x40])

    def test_steps_restart_after_another_preset(self):
        lighting, elc = make_lighting()
        lighting.select("brightness", 0)
        lighting.select("brightness", 0)
        lighting.select("night", 0)
        lighting.select("brightness", 0)
        self.assertEqual(keyboard_color(elc.played[-1])[0], 0x40)

    def test_auto_goes_dark_after_timeout_and_wakes_on_typing(self):
        lighting, elc = make_lighting()
        lighting.select("auto", 100)
        lighting.activity(105)
        lighting.tick(114)
        self.assertEqual(keyboard_color(elc.played[-1]), (0x60, 0x60, 0x60))
        lighting.tick(115)
        self.assertEqual(keyboard_color(elc.played[-1]), (0, 0, 0))
        lighting.activity(200)
        self.assertEqual(keyboard_color(elc.played[-1]), (0x60, 0x60, 0x60))
        self.assertEqual(lighting.deadline(), 210)

    def test_typing_while_lit_sends_nothing(self):
        lighting, elc = make_lighting()
        lighting.select("auto", 0)
        for t in range(1, 6):
            lighting.activity(t)
        self.assertEqual(len(elc.played), 1)

    def test_reapply_pushes_the_current_look_again(self):
        lighting, elc = make_lighting()
        lighting.select("night", 0)
        lighting.reapply(config.load(config.BUNDLED_PATH).presets)
        self.assertEqual(len(elc.played), 2)
        self.assertEqual(elc.played[0], elc.played[1])


if __name__ == "__main__":
    unittest.main()

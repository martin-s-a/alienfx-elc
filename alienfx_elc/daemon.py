"""Listen to the laptop keyboard and drive the lighting presets."""
import os
import select
import signal
import struct
import sys
import time

from . import config as config_mod
from .elc import Elc, HidrawTransport
from .lighting import Lighting

EVENT = struct.Struct("llHHi")
EV_KEY = 0x01
KEY_PRESS = 1


def find_keyboard(name):
    for entry in sorted(os.listdir("/sys/class/input")):
        if not entry.startswith("event"):
            continue
        with open(f"/sys/class/input/{entry}/device/name") as f:
            if f.read().strip() == name:
                return f"/dev/input/{entry}"
    raise RuntimeError(f"keyboard {name!r} not found")


def key_presses(fd):
    data = os.read(fd, EVENT.size * 64)
    for offset in range(0, len(data) - EVENT.size + 1, EVENT.size):
        _, _, etype, code, value = EVENT.unpack_from(data, offset)
        if etype == EV_KEY and value == KEY_PRESS:
            yield code


def run(config_path=None):
    cfg = config_mod.load(config_path)
    lighting = Lighting(Elc(HidrawTransport()), cfg.presets)
    lighting.select(cfg.startup, time.monotonic())

    keyboard = os.open(find_keyboard(cfg.keyboard), os.O_RDONLY | os.O_NONBLOCK)
    wake_r, wake_w = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    signal.set_wakeup_fd(wake_w)
    reload_requested = False

    def on_hup(signum, frame):
        nonlocal reload_requested
        reload_requested = True

    signal.signal(signal.SIGHUP, on_hup)
    print(f"alienfx-elc: running, preset {cfg.startup}", flush=True)

    while True:
        deadline = lighting.deadline()
        timeout = None if deadline is None else max(0.0, deadline - time.monotonic())
        ready, _, _ = select.select([keyboard, wake_r], [], [], timeout)

        if wake_r in ready:
            os.read(wake_r, 64)
        if reload_requested:
            reload_requested = False
            try:
                cfg = config_mod.load(config_path)
            except (OSError, ValueError) as error:
                print(f"alienfx-elc: keeping previous config: {error}", file=sys.stderr, flush=True)
            lighting.reapply(cfg.presets)

        if keyboard in ready:
            for code in key_presses(keyboard):
                now = time.monotonic()
                preset = cfg.bindings.get(code)
                if preset:
                    lighting.select(preset, now)
                else:
                    lighting.activity(now)

        lighting.tick(time.monotonic())

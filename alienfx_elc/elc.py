"""Alienware AW-ELC (USB 187c:0550) lighting controller, spoken to over hidraw.

The packet layout follows OpenRGB's AlienwareController.
"""
import fcntl
import glob
import os
import time

HID_ID = "0000187C:00000550"
REPORT_SIZE = 34

CMD_REPORT = 0x20
CMD_ANIMATION = 0x21
CMD_SELECT_ZONES = 0x23
CMD_ADD_ACTION = 0x24

REPORT_FIRMWARE = 0x00
REPORT_CONFIG = 0x02

ANIM_NEW = 0x0001
ANIM_FINISH_SAVE = 0x0002
ANIM_FINISH_PLAY = 0x0003
ANIM_REMOVE = 0x0004
ANIM_SET_DEFAULT = 0x0006
ANIM_SET_STARTUP = 0x0007

SLOT_VOLATILE = 0xFFFF
SLOT_DEFAULT = 0x0061

MODE_COLOR = 0x00
ACTION_DURATION = 2000
ACTION_TEMPO = 0x00FA
MAX_ZONES_PER_PACKET = 25

PAUSE = 0.002
PAUSE_AFTER_SAVE = 1.0


def _ioc_readwrite(nr, size):
    return (3 << 30) | (size << 16) | (ord("H") << 8) | nr


HIDIOCSFEATURE = _ioc_readwrite(0x06, REPORT_SIZE)
HIDIOCGFEATURE = _ioc_readwrite(0x07, REPORT_SIZE)


class ElcError(Exception):
    pass


def find_hidraw():
    for node in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        with open(os.path.join(node, "device", "uevent")) as f:
            if HID_ID in f.read().upper():
                return "/dev/" + os.path.basename(node)
    raise ElcError("AW-ELC controller (187c:0550) not found")


class HidrawTransport:
    def __init__(self, path=None):
        self._fixed_path = path
        self.fd = None
        self._open()

    def _open(self):
        if self.fd is not None:
            os.close(self.fd)
        self.fd = os.open(self._fixed_path or find_hidraw(), os.O_RDWR)

    def exchange(self, payload, pause):
        report = bytearray(REPORT_SIZE)
        report[1] = 0x03
        report[2 : 2 + len(payload)] = payload
        try:
            fcntl.ioctl(self.fd, HIDIOCSFEATURE, bytes(report))
        except OSError:
            # The controller re-enumerates after suspend, leaving the old node stale.
            self._open()
            fcntl.ioctl(self.fd, HIDIOCSFEATURE, bytes(report))
        time.sleep(pause)
        response = bytearray(REPORT_SIZE)
        fcntl.ioctl(self.fd, HIDIOCGFEATURE, response)
        return bytes(response)


def _u16(value):
    return [value >> 8, value & 0xFF]


class Elc:
    def __init__(self, transport):
        self.transport = transport

    def _send(self, payload, pause=None):
        response = self.transport.exchange(bytes(payload), PAUSE if pause is None else pause)
        if response[1] != 0x03:
            raise ElcError(f"controller did not acknowledge command 0x{payload[0]:02x}")
        return response

    def _animation(self, subcommand, slot):
        pause = PAUSE_AFTER_SAVE if subcommand == ANIM_FINISH_SAVE else None
        return self._send([CMD_ANIMATION, *_u16(subcommand), *_u16(slot), 0, 0], pause)

    def _select(self, zones):
        for start in range(0, len(zones), MAX_ZONES_PER_PACKET):
            chunk = zones[start : start + MAX_ZONES_PER_PACKET]
            self._send([CMD_SELECT_ZONES, 1, *_u16(len(chunk)), *chunk])

    def _color(self, rgb):
        self._send([CMD_ADD_ACTION, MODE_COLOR, *_u16(ACTION_DURATION), *_u16(ACTION_TEMPO), *rgb])

    def _program(self, slot, groups):
        """groups: [(rgb, [zone ids])]; zones left out keep whatever drives them."""
        self._animation(ANIM_NEW, slot)
        for rgb, zones in groups:
            self._select(list(zones))
            self._color(rgb)

    def play(self, groups):
        self._program(SLOT_VOLATILE, groups)
        self._animation(ANIM_FINISH_PLAY, SLOT_VOLATILE)

    def save_default(self, groups):
        """Store groups in flash as the default and power-on animation."""
        self._animation(ANIM_REMOVE, SLOT_DEFAULT)
        self._program(SLOT_DEFAULT, groups)
        self._animation(ANIM_FINISH_SAVE, SLOT_DEFAULT)
        self._animation(ANIM_SET_DEFAULT, SLOT_DEFAULT)
        self._animation(ANIM_SET_STARTUP, SLOT_DEFAULT)

    def info(self):
        config = self._send([CMD_REPORT, REPORT_CONFIG])
        firmware = self._send([CMD_REPORT, REPORT_FIRMWARE])
        return {
            "platform": config[4] << 8 | config[5],
            "zones": config[6],
            "firmware": f"{firmware[4]}.{firmware[5]}.{firmware[6]}",
        }

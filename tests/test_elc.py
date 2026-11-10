import unittest

from alienfx_elc.elc import Elc, ElcError


class RecordingTransport:
    def __init__(self, ack=0x03):
        self.sent = []
        self.ack = ack

    def exchange(self, payload, pause):
        self.sent.append(bytes(payload))
        response = bytearray(34)
        response[1] = self.ack
        return bytes(response)


class PlayTest(unittest.TestCase):
    def test_volatile_animation_selects_each_group_then_plays(self):
        transport = RecordingTransport()
        Elc(transport).play([((0, 0, 0), [0, 1]), ((0x60, 0x60, 0x60), [4])])
        self.assertEqual(
            transport.sent,
            [
                bytes([0x21, 0x00, 0x01, 0xFF, 0xFF, 0, 0]),
                bytes([0x23, 1, 0, 2, 0, 1]),
                bytes([0x24, 0x00, 0x07, 0xD0, 0x00, 0xFA, 0, 0, 0]),
                bytes([0x23, 1, 0, 1, 4]),
                bytes([0x24, 0x00, 0x07, 0xD0, 0x00, 0xFA, 0x60, 0x60, 0x60]),
                bytes([0x21, 0x00, 0x03, 0xFF, 0xFF, 0, 0]),
            ],
        )

    def test_long_zone_list_is_split_across_select_packets(self):
        transport = RecordingTransport()
        Elc(transport).play([((1, 2, 3), list(range(30)))])
        selects = [p for p in transport.sent if p[0] == 0x23]
        self.assertEqual([p[3] for p in selects], [25, 5])

    def test_unacknowledged_command_raises(self):
        with self.assertRaises(ElcError):
            Elc(RecordingTransport(ack=0x00)).play([((0, 0, 0), [0])])


class SaveDefaultTest(unittest.TestCase):
    def test_writes_default_slot_and_marks_it_default_and_startup(self):
        transport = RecordingTransport()
        Elc(transport).save_default([((0, 0, 0), [0])])
        animation = [p[1:5] for p in transport.sent if p[0] == 0x21]
        self.assertEqual(
            animation,
            [
                bytes([0x00, 0x04, 0x00, 0x61]),
                bytes([0x00, 0x01, 0x00, 0x61]),
                bytes([0x00, 0x02, 0x00, 0x61]),
                bytes([0x00, 0x06, 0x00, 0x61]),
                bytes([0x00, 0x07, 0x00, 0x61]),
            ],
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Synthetic fragmented USB exchanges; never import PyUSB or access hardware."""
import struct
import unittest
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import trial_usb as usb


def reply(cookie=123, function=0, text='', status=0, command=65):
    data = bytearray(252)
    struct.pack_into('<III', data, 0, command, function, cookie)
    struct.pack_into('<I', data, 16, status)
    encoded = text.encode('utf-8')
    data[20:20+len(encoded)] = encoded
    struct.pack_into('<I', data, 12, usb.crc16(data[16:]))
    return usb.REPLY_HEADER + data


class Endpoint:
    def __init__(self, packets=(), short=False):
        self.packets = list(packets)
        self.ready = False
        self.writes = 0
        self.short = short

    def read(self, count, timeout):
        if self.ready and self.packets:
            return self.packets.pop(0)
        raise TimeoutError('timed out')

    def write(self, packet, timeout):
        self.writes += 1
        self.ready = True
        return len(packet) - int(self.short)


class TransportTests(unittest.TestCase):
    def test_crc_and_request_bounds(self):
        self.assertEqual(usb.crc16(b'123456789'), 0x31C3)
        packet = usb.request('x'*231, 123)
        self.assertEqual(len(packet), 257)
        self.assertEqual(packet[:5], bytes.fromhex('0a000805fc'))
        self.assertEqual(packet[-1], 0)
        for command in ['x'*232, 'echo\0id', '相机']:
            with self.assertRaises(usb.UsbFactoryError):
                usb.request(command, 123)

    def test_noise_corruption_fragmentation_and_cookie(self):
        bad = bytearray(reply(text='bad', function=4)); bad[-1] ^= 1
        stream = b'noise' + bad + reply(cookie=122, function=4, text='stale') + reply(function=4, text='你好\n') + reply()
        endpoint = Endpoint([bytes([byte]) for byte in stream])
        client = usb.ExistingInterface(); client.in_ep = client.out_ep = endpoint
        with patch.object(usb.secrets, 'randbits', return_value=123):
            self.assertEqual(client.factory_shell('echo hello', capture_ms=1000), '你好\n')
        self.assertEqual(endpoint.writes, 1)

    def test_nonzero_status_and_no_execution_retry(self):
        for endpoint in [Endpoint([reply(status=7)]), Endpoint(short=True), Endpoint([reply(cookie=124)])]:
            client = usb.ExistingInterface(); client.in_ep = client.out_ep = endpoint
            with patch.object(usb.secrets, 'randbits', return_value=123):
                with self.assertRaises(usb.UsbFactoryError):
                    client.factory_shell('echo hello', capture_ms=5)
            self.assertEqual(endpoint.writes, 1)

    def test_frame_header_split_and_bounded_noise_buffer(self):
        data = bytearray(b'noise'*100 + usb.REPLY_HEADER[:3])
        self.assertEqual(usb.extract_frames(data), [])
        self.assertLessEqual(len(data), 4)
        data.extend(reply()[3:])
        self.assertEqual(usb.extract_frames(data), [reply()])

    def test_close_releases_claim_and_resources_once(self):
        from unittest.mock import Mock
        client = usb.ExistingInterface(); client.util = Mock()
        device = object(); client.device = device; client.claimed = True
        client.close(); client.close()
        client.util.release_interface.assert_called_once_with(device, 3)
        client.util.dispose_resources.assert_called_once_with(device)

    def test_close_after_disconnect_still_disposes_and_clears(self):
        from unittest.mock import Mock
        client = usb.ExistingInterface(); client.util = Mock()
        device = object(); client.device = device; client.claimed = True
        client.util.release_interface.side_effect = OSError('disconnected')
        with self.assertRaises(OSError):
            client.close()
        client.close()
        client.util.dispose_resources.assert_called_once_with(device)
        self.assertIsNone(client.device)


if __name__ == '__main__':
    unittest.main()

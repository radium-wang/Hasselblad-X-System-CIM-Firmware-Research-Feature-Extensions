"""纯数据和宿主门禁测试；绝不启动 Unicorn 或访问相机。"""
import builtins
import contextlib
import io
import json
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import emulate_original_frame_adapter as adapter


class FrameAdapterTests(unittest.TestCase):
    def test_converter_core_cannot_be_enqueued_as_full_record(self):
        for size in (0, 0x68, 0x83, 0x85):
            with self.subTest(size=size), self.assertRaises(ValueError):
                adapter.require_complete_frame_record(bytes(size))
        record = bytes(range(0x84))
        self.assertEqual(adapter.require_complete_frame_record(record), record)

    def test_descriptor_mapping(self):
        old, size = adapter.fixture()
        new = adapter.adapt_descriptor_for_converter(old, size)
        self.assertEqual(len(new), 0xb8)
        self.assertEqual(new[:0x40], old[:0x40])
        for i in range(2):
            self.assertEqual(new[0x40 + 28*i:0x48 + 28*i], old[0x40 + 16*i:0x48 + 16*i])
            self.assertEqual(adapter.u32(new, 0x4c + 28*i), adapter.u32(old, 0x48 + 16*i))
        self.assertEqual(struct.unpack_from('<II', new, 0xb0), (2, 123))

    def test_invalid_planes_rejected(self):
        old, size = adapter.fixture()
        for offset, value in ((0x28, 99), (0x80, 5), (0x38, 1279),
                              (0x40, 1), (0x48, 1), (0x54, 256)):
            changed = bytearray(old)
            struct.pack_into('<I', changed, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                adapter.adapt_descriptor_for_converter(changed, size)
        for bad_size in (0, size - 1, 0x100000000):
            with self.subTest(size=bad_size), self.assertRaises(ValueError):
                adapter.adapt_descriptor_for_converter(old, bad_size)
        with self.assertRaises(ValueError):
            adapter.adapt_descriptor_for_converter(old[:0x80], size)

    def test_host_gate_precedes_native_import(self):
        original_import = builtins.__import__

        def forbid_native(name, *args, **kwargs):
            if name.split('.')[0] in ('unicorn', 'elftools'):
                self.fail('native/ELF import before host gate: ' + name)
            return original_import(name, *args, **kwargs)

        with patch.object(adapter.platform, 'system', return_value='Darwin'), \
             patch('builtins.__import__', side_effect=forbid_native):
            for arch in ('arm64', 'aarch64', 'ARM64'):
                with patch.object(adapter.platform, 'machine', return_value=arch), \
                     self.assertRaises(adapter.EmulationUnavailable):
                    adapter.execute_original(b'', b'')

    def test_cli_gate_is_clean_exit_before_file_read(self):
        with patch.object(adapter.platform, 'system', return_value='Darwin'), \
             patch.object(adapter.platform, 'machine', return_value='arm64'), \
             patch.object(sys, 'argv', ['adapter', '--source-dji-ml', '/nonexistent']), \
             contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(adapter.main(), 2)
        self.assertIn('SIGILL', error.getvalue())

    def test_descriptor_only_does_not_enter_emulator(self):
        with patch.object(sys, 'argv', ['adapter', '--descriptor-only']), \
             patch.object(adapter, 'execute_original', side_effect=AssertionError), \
             patch.object(adapter, 'require_safe_emulation_host', side_effect=AssertionError), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(adapter.main(), 0)
        report = json.loads(output.getvalue())
        self.assertFalse(report['original_converter_executed'])
        self.assertFalse(report['device_accessed'])


if __name__ == '__main__':
    unittest.main()

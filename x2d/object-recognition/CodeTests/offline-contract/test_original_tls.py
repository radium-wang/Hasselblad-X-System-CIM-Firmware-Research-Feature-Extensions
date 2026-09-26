"""纯离线 TLS 元数据适配测试；真实固件由显式环境变量提供，不随库分发。"""
import io
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from elftools.elf.elffile import ELFFile
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from adapt_original_tls import adapt, align, elf_hash, PROVIDER, VERSION, SYMBOL
from audit_native_bundle import needed, version_surface


class AdapterUnitTests(unittest.TestCase):
    def test_wrong_input_rejected(self):
        for name in ('dji_ml', 'libnn_framework.so', 'unknown.so'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                adapt(b'not original firmware', name)

    def test_alignment(self):
        self.assertEqual(align(0x12345, 0x10000), 0x20000)
        self.assertEqual(align(0x20000, 0x10000), 0x20000)

    def test_elf_hash(self):
        self.assertEqual(elf_hash('printf'), 0x77905a6)


@unittest.skipUnless(os.environ.get('X2D_SOURCE_SYSTEM_ROOT'), 'explicit original firmware root required')
class OriginalFirmwareTests(unittest.TestCase):
    def test_both_pinned_files(self):
        root = Path(os.environ['X2D_SOURCE_SYSTEM_ROOT'])
        for relative in ('bin/dji_ml', 'lib64/libnn_framework.so'):
            with self.subTest(relative=relative), TemporaryDirectory() as directory:
                source = root / relative
                data = source.read_bytes()
                output, report = adapt(data, source.name)
                destination = Path(directory) / source.name
                destination.write_bytes(output)
                before, after = ELFFile(io.BytesIO(data)), ELFFile(io.BytesIO(output))
                self.assertEqual(source.read_bytes(), data)
                self.assertFalse(report['device_execution_approved'])
                self.assertEqual(needed(source), needed(destination))
                old, old_exports = version_surface(source)
                new, new_exports = version_surface(destination)
                self.assertEqual(new_exports, old_exports)
                self.assertEqual(new, [(s, PROVIDER, VERSION) if s == SYMBOL else (s, p, v)
                                       for s, p, v in old])
                for section in before.iter_sections():
                    if section['sh_flags'] & 4:
                        self.assertEqual(section.data(), after.get_section_by_name(section.name).data())
                old_loads = [s.header for s in before.iter_segments() if s['p_type'] == 'PT_LOAD']
                new_loads = [s.header for s in after.iter_segments() if s['p_type'] == 'PT_LOAD']
                self.assertEqual(new_loads[:len(old_loads)], old_loads)
                for i, segment in enumerate(new_loads):
                    self.assertLessEqual(segment['p_filesz'], segment['p_memsz'])
                    self.assertLessEqual(segment['p_offset'] + segment['p_filesz'], len(output))
                    self.assertEqual(segment['p_offset'] % segment['p_align'],
                                     segment['p_vaddr'] % segment['p_align'])
                    if i:
                        previous = new_loads[i - 1]
                        self.assertGreaterEqual(segment['p_vaddr'], previous['p_vaddr'] + previous['p_memsz'])
                if source.name == 'dji_ml':
                    self.assertEqual(len(output), len(data))
                    self.assertEqual(sum(a != b for a, b in zip(data, output)), 1)
                else:
                    self.assertEqual(len(new_loads), len(old_loads) + 1)
                    self.assertEqual(new_loads[-1]['p_flags'], 4)


if __name__ == '__main__':
    unittest.main()

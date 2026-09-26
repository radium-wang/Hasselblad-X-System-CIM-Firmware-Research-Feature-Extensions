"""离线验证诊断副本的初始化禁用；不接设备。"""
import importlib.util
import io
import os
import unittest
from pathlib import Path
from elftools.elf.elffile import ELFFile

path = Path(__file__).resolve().parents[1] / 'native-loader-probe/prepare.py'
spec = importlib.util.spec_from_file_location('native_loader_prepare', path)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


@unittest.skipUnless(os.environ.get('X2D_SOURCE_SYSTEM_ROOT'), 'explicit firmware root required')
class NativeLoaderProbeTests(unittest.TestCase):
    def test_initializers_disabled_without_code_changes(self):
        root = Path(os.environ['X2D_SOURCE_SYSTEM_ROOT'])
        for name in ('libcnntk_cbb.so', 'libnn_framework.so', 'libduml_fastrtps.so'):
            with self.subTest(name=name):
                source = (root / 'lib64' / name).read_bytes()
                modified, tags = prepare.no_initializers(source)
                old, new = ELFFile(io.BytesIO(source)), ELFFile(io.BytesIO(modified))
                self.assertIn('DT_INIT_ARRAYSZ', tags)
                for section in old.iter_sections():
                    if section['sh_flags'] & 4:
                        self.assertEqual(section.data(), new.get_section_by_name(section.name).data())
                for tag in new.get_section_by_name('.dynamic').iter_tags():
                    if tag.entry.d_tag in tags:
                        self.assertEqual(tag.entry.d_val, 0)
                self.assertEqual(len(source), len(modified))


if __name__ == '__main__':
    unittest.main()

"""原厂模型容器试验的离线门禁；不执行固件或连接相机。"""
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('model_probe', TOOLS / 'prepare_model_container_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ModelContainerTests(unittest.TestCase):
    def test_rejects_unpinned_or_truncated_model(self):
        for data in (b'', b'IM*H', bytes(probe.MODEL_SIZE)):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                probe.validate_model(data)
        with self.assertRaises(ValueError):
            probe.validate_model(b'', 'arbitrary')
        with self.assertRaises(ValueError):
            probe.validate_model(bytes(746144), 'stock-face')

    @unittest.skipUnless(os.environ.get('X2D_TARGET_VENDOR_ROOT'), 'explicit vendor input required')
    def test_stock_control_model_is_separately_pinned(self):
        root = Path(os.environ['X2D_TARGET_VENDOR_ROOT'])
        data = (root / probe.MODELS['stock-face'][2]).read_bytes()
        probe.validate_model(data, 'stock-face')
        with self.assertRaises(ValueError):
            probe.validate_model(data, 'donor-pet')

    def test_script_is_bounded_and_removes_only_own_payload(self):
        script = probe.device_script()
        subprocess.run(['/bin/sh', '-n'], input=script, text=True, check=True)
        self.assertIn('timeout -s KILL 12', script)
        self.assertIn('env -u LD_PRELOAD -u LD_LIBRARY_PATH', script)
        self.assertIn('trap cleanup EXIT', script)
        self.assertIn('|| exit 72', script)
        self.assertNotIn('rm -rf', script)
        self.assertNotIn('/system/lib64', script)

    def test_stale_package_rejected_before_reading_payload(self):
        with self.assertRaisesRegex(ValueError, 'revision'):
            probe.validate_package(Path('/nonexistent'), {})
        with self.assertRaisesRegex(ValueError, 'stale'):
            probe.validate_package(Path('/nonexistent'), {'probe_revision': probe.REVISION})

    def test_donor_variant_payload_and_cleanup_are_explicit(self):
        self.assertEqual(probe.payload_files('donor-ca') - probe.payload_files('stock'), {'libfw_util_ca.so'})
        script = probe.device_script('donor-ca')
        subprocess.run(['/bin/sh', '-n'], input=script, text=True, check=True)
        self.assertIn('"$base/libfw_util_ca.so"', script)
        self.assertNotIn('LD_PRELOAD=', script)
        with self.assertRaises(ValueError):
            probe.payload_files('unknown')

    @unittest.skipUnless(os.environ.get('X2D_SOURCE_SYSTEM_ROOT') and
                         os.environ.get('X2D_TARGET_SYSTEM_ROOT'), 'explicit firmware inputs required')
    def test_original_donor_ca_got_and_dependencies(self):
        report = probe.audit_donor_ca(Path(os.environ['X2D_TARGET_SYSTEM_ROOT']),
                                      Path(os.environ['X2D_SOURCE_SYSTEM_ROOT']))
        self.assertEqual(report['library_count'], 25)
        self.assertEqual(report['versioned_import_failures'], [])
        self.assertFalse(report['system_libraries_replaced'])

    @unittest.skipUnless(os.environ.get('X2D_SOURCE_VENDOR_ROOT') and
                         os.environ.get('X2D_TARGET_SYSTEM_ROOT'), 'explicit firmware inputs required')
    def test_real_original_input_and_dependency_closure(self):
        vendor = Path(os.environ['X2D_SOURCE_VENDOR_ROOT'])
        target = Path(os.environ['X2D_TARGET_SYSTEM_ROOT'])
        probe.validate_model((vendor / 'model/ml/yolov8-n-pet.json.eng.enc').read_bytes())
        for name, digest in probe.PINNED.items():
            self.assertEqual(probe.digest(target / name), digest)
        names = {entry['name'] for entry in probe.stock_dependencies(target)}
        self.assertTrue({'libfw_util.so', 'libfw_util_ca.so', 'libteec.so', 'libion.so'} <= names)
        self.assertNotIn('libnn_framework.so', names)
        self.assertNotIn('libcnntk_cbb.so', names)


if __name__ == '__main__':
    unittest.main()

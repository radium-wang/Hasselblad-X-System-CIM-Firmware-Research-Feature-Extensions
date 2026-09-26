"""Offline name/version gate tests: no firmware execution or camera access."""
import sys
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from audit_native_bundle import check_versions, validate_source_libraries, library_selection, audit
from unittest.mock import patch


class NativeVersionTests(unittest.TestCase):
    def test_conflicting_library_selection_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'lib64').mkdir()
            (root / 'lib64/libtest.so').touch()
            with self.assertRaises(ValueError):
                library_selection(root, root, ['libtest.so'], ['libtest.so'])

    def test_pin_does_not_silently_replace_target_for_symbol_closure(self):
        with TemporaryDirectory() as directory:
            source, target = Path(directory) / 'source', Path(directory) / 'target'
            for root in (source, target):
                (root / 'lib64').mkdir(parents=True)
                (root / 'lib64/libtest.so').write_bytes(b'fixture')
            (source / 'bin').mkdir()
            (source / 'bin/dji_ml').write_bytes(b'fixture')

            def surface(path):
                if path.name == 'dji_ml':
                    return {'new_api'}, set()
                return set(), ({'new_api'} if path.parent.parent == source else set())

            with patch('audit_native_bundle.library_exports', return_value={'libtest.so': {'new_api'}}), \
                 patch('audit_native_bundle.dynamic_symbols', side_effect=surface), \
                 patch('audit_native_bundle.needed', side_effect=lambda p: ['libtest.so'] if p.name == 'dji_ml' else []), \
                 patch('audit_native_bundle.version_surface', return_value=([], set())):
                normal = audit(source, target)
                pinned = audit(source, target, retained_target_libraries=['libtest.so'])
            self.assertTrue(normal['unversioned_symbol_closure'])
            self.assertEqual(normal['source_libraries'], ['libtest.so'])
            self.assertFalse(pinned['unversioned_symbol_closure'])
            self.assertEqual(pinned['unresolved_by_consumer'], {'dji_ml': ['new_api']})
            self.assertEqual(pinned['source_libraries'], [])
            entry = next(x for x in pinned['original_file_manifest'] if x['name'] == 'libtest.so')
            self.assertEqual(entry['origin'], 'X2D-4.2.0')
            self.assertFalse(pinned['device_execution_approved'])

    def test_matching(self):
        self.assertEqual(check_versions({'app': ([('f', 'liba', 'V1')], set()),
                                         'liba': ([], {('f', 'V1')})}), [])

    def test_wrong_version_rejected(self):
        result = check_versions({'app': ([('f', 'liba', 'V2')], set()),
                                 'liba': ([], {('f', 'V1')})})
        self.assertEqual(result[0]['version'], 'V2')

    def test_wrong_provider_rejected(self):
        self.assertTrue(check_versions({'app': ([('f', 'liba', 'V1')], set()),
                                        'libb': ([], {('f', 'V1')})}))

    def test_unversioned_export_not_enough(self):
        self.assertTrue(check_versions({'app': ([('f', 'liba', 'V1')], set()),
                                        'liba': ([], {('f', None)})}))

    def test_source_library_validation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'lib64').mkdir()
            (root / 'lib64/libtest.so').touch()
            self.assertEqual(validate_source_libraries(root, ['libtest.so']), {'libtest.so'})
            for invalid in ('../libtest.so', '/libtest.so', 'libabsent.so', 'lib64/libtest.so'):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    validate_source_libraries(root, [invalid])


if __name__ == '__main__':
    unittest.main()

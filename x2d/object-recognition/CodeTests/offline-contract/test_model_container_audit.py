"""只读容器边界、字段最小化和固定原厂错误分支测试。"""
import hashlib
import importlib.util
import os
import struct
import unittest
from pathlib import Path

tool = Path(__file__).resolve().parents[2] / 'tools/audit_model_containers.py'
spec = importlib.util.spec_from_file_location('container_audit', tool)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def fixture():
    data = bytearray(224 + 384 + 32)
    data[:4] = b'IM*H'
    for offset, value in ((4, 2), (8, len(data)), (16, 224), (20, 384), (24, 32),
                          (36, 0x40003), (156, 1), (196, 0), (200, 24)):
        struct.pack_into('<I', data, offset, value)
    data[40:48] = b'PRAKTBIE'
    data[48:64] = b'PRIVATE-SENTINEL'
    data[160:192] = hashlib.sha256(data[608:]).digest()
    return data


class ContainerAuditTests(unittest.TestCase):
    def test_valid_digest_is_not_signature_verification(self):
        result = audit.inspect_container(fixture())
        self.assertTrue(result['stored_payload_sha256_matches'])
        self.assertFalse(result['signature_verified'])
        self.assertFalse(result['decrypted'])
        self.assertNotIn('PRIVATE-SENTINEL', str(result))
        self.assertNotIn('scram_key', result)

    def test_payload_corruption_is_reported(self):
        data = fixture()
        data[-1] ^= 1
        self.assertFalse(audit.inspect_container(data)['stored_payload_sha256_matches'])

    def test_bad_bounds_rejected(self):
        for offset, value in ((8, 1), (16, 0xffffffff), (156, 1025), (196, 33), (200, 33)):
            data = fixture()
            struct.pack_into('<I', data, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                audit.inspect_container(data)
        with self.assertRaises(ValueError):
            audit.inspect_container(b'IM*H')

    @unittest.skipUnless(os.environ.get('X2D_SOURCE_SYSTEM_ROOT') and
                         os.environ.get('X2D_SOURCE_VENDOR_ROOT') and
                         os.environ.get('X2D_TARGET_VENDOR_ROOT'), 'explicit firmware inputs required')
    def test_fixed_original_corpus_and_related_error(self):
        old = audit.audit_models(Path(os.environ['X2D_TARGET_VENDOR_ROOT']))
        new = audit.audit_models(Path(os.environ['X2D_SOURCE_VENDOR_ROOT']))
        self.assertEqual((len(old), len(new)), (23, 22))
        for row in old + new:
            self.assertEqual(row['auth_algorithm_low16'], 3)
            self.assertTrue(row['stored_payload_sha256_matches'])
        related = audit.audit_related_error_branch(Path(os.environ['X2D_SOURCE_SYSTEM_ROOT']))
        self.assertEqual(related['signature_failure_return'], -10)
        self.assertFalse(related['actual_tee_error_meaning_proven'])


if __name__ == '__main__':
    unittest.main()

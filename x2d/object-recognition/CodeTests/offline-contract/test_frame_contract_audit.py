"""固定版本指令契约，不执行原厂代码或访问设备。"""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from audit_original_frame_contract import audit, CHECKS, transport_extent_contract


class FrameContractAuditTests(unittest.TestCase):
    def test_transport_offset_and_missing_tail_remain_explicit(self):
        c = transport_extent_contract()
        self.assertEqual(c['event_prefix_bytes'] + c['node_body_offset'],
                         c['receiver_body_offset'])
        self.assertEqual(c['x2d_node_bytes_in_event'], 0x388)
        self.assertEqual(c['x2d2_node_bytes_in_event'], 0x4a0)
        self.assertEqual(c['donor_metadata_read_end'], 0x4a4)
        self.assertEqual(c['donor_metadata_bytes_beyond_explicit_copy'], 4)
        self.assertFalse(c['receiver_tail_initialization_proven'])
        self.assertFalse(c['live_use_authorized_by_this_contract'])

    def test_unrecognized_input_fails_closed(self):
        for model in ('x2d', 'x2d2', 'unknown'):
            with self.subTest(model=model), self.assertRaises(ValueError):
                audit(b'not firmware', model)

    @unittest.skipUnless(os.environ.get('X2D_SOURCE_SYSTEM_ROOT') and
                         os.environ.get('X2D_TARGET_SYSTEM_ROOT'), 'explicit firmware roots required')
    def test_original_instruction_contract(self):
        for model, variable, relative in [
                ('x2d', 'X2D_TARGET_SYSTEM_ROOT', 'bin/dji_ml'),
                ('x2d2', 'X2D_SOURCE_SYSTEM_ROOT', 'bin/dji_ml'),
                ('x2d_duml', 'X2D_TARGET_SYSTEM_ROOT', 'lib64/libduml_frwk.so'),
                ('x2d2_duml', 'X2D_SOURCE_SYSTEM_ROOT', 'lib64/libduml_frwk.so'),
                ('x2d2_cnntk', 'X2D_SOURCE_SYSTEM_ROOT', 'lib64/libcnntk_cbb.so'),
                ('x2d_ml_sender', 'X2D_TARGET_SYSTEM_ROOT',
                 'lib64/camera/plugins/stream_filter/libdcam_x2d_ml_stream_filter.so'),
                ('x2d2_ml_sender', 'X2D_SOURCE_SYSTEM_ROOT',
                 'lib64/camera/plugins/stream_filter/libdcam_x2d_ml_stream_filter.so')]:
            with self.subTest(model=model):
                result = audit((Path(os.environ[variable]) / relative).read_bytes(), model)
                self.assertEqual(set(result['verified_instructions']), set(CHECKS[model]))


if __name__ == '__main__':
    unittest.main()

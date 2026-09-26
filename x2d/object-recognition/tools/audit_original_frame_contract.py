#!/usr/bin/env python3
"""只读核对两代原厂帧生命周期关键指令；不导入模拟器或访问设备。"""
import argparse
import hashlib
import io
import json
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

HASHES = {
    'x2d': '60d73e138fd091fce49454f7a7806c4945e74a8ca2dcf2b1af902e5d9e6cd90a',
    'x2d2': '98351d0906f3056cf780c5bf2adce65f544bb258c18dd62cfadb01607bdb1788',
    'x2d_duml': 'bb110a2c94e6ed5b69a99048f3a30db5760754ec12ff4d1bdd7f6f431139b81d',
    'x2d2_duml': 'c37925331335c70e2624f987c670afe133ac18e4ae4e22ef47a1ca31b9a07906',
    'x2d2_cnntk': '0fa098f400839955d700b342492e64b72aacfb996f27568dfb9520a409522b73',
    'x2d_ml_sender': '75151520377cf40683a0a85efb150fe62d7f77e1b945b80c8246d37f1cc0c563',
    'x2d2_ml_sender': 'f7e5ce1b4676c25b2f71f7154805eb6e4f1572abaca0706a669596c424519b7e',
}
# 每项断言绑定原始文件哈希；地址仅作离线分析，不是内存写入清单。
CHECKS = {
    'x2d_ml_sender': {
        'input_tail_zero_start': (0x850c, 'add', 'x0, x9, #0x218'),
        'input_tail_zero_size': (0x8510, 'mov', 'w2, #0x60'),
        'input_tail_zero': (0x851c, 'bl', '#0x3e90'),
        'source_frame_copy_size': (0x8520, 'mov', 'w2, #0x218'),
        'source_frame_copy': (0x852c, 'bl', '#0x3e40'),
        'outgoing_node_zero_size': (0x8530, 'mov', 'w2, #0x510'),
        'outgoing_frame_copy_size': (0x855c, 'mov', 'w2, #0x278'),
        'destination_channel_constant': (0x8554, 'mov', 'w9, #2'),
        'destination_channel_store': (0x8568, 'str', 'w9, [sp, #0x38c]'),
        'outgoing_frame_copy': (0x8598, 'bl', '#0x3e40'),
        'dsh_send': (0x85b4, 'bl', '#0x42f0'),
    },
    'x2d2_ml_sender': {
        'input_tail_zero_start': (0xa278, 'add', 'x0, x9, #0x330'),
        'input_tail_zero_size': (0xa27c, 'mov', 'w2, #0x60'),
        'input_tail_zero': (0xa288, 'bl', '#0x40c8'),
        'source_frame_copy_size': (0xa28c, 'mov', 'w2, #0x330'),
        'source_frame_copy': (0xa298, 'bl', '#0x4038'),
        'outgoing_node_zero_size': (0xa29c, 'mov', 'w2, #0x910'),
        'outgoing_frame_copy_size': (0xa2c4, 'mov', 'w2, #0x390'),
        'destination_channel_constant': (0xa2b0, 'mov', 'w9, #2'),
        'destination_channel_store': (0xa2c8, 'str', 'w9, [sp, #0x4dc]'),
        'sender_channel_id': (0xa81c, 'mov', 'w1, #0x65'),
        'outgoing_frame_copy': (0xa300, 'bl', '#0x4038'),
        'dsh_send': (0xa31c, 'bl', '#0x4538'),
    },
    'x2d_duml': {
        'sender_shared_handle': (0xf7480, 'str', 'x8, [x28, #0x70]'),
        'sender_shared_payload_source_size': (0xf7488, 'ldr', 'w8, [x20, #0x108]'),
        'sender_shared_payload_header_size': (0xf748c, 'add', 'x2, x8, #0x90'),
        'sender_shared_payload_copy': (0xf7490, 'bl', '#0x2cf68'),
        'receiver_payload_source': (0xf6770, 'add', 'x19, x21, #0x94'),
        'shared_node_zero_size': (0xf960c, 'mov', 'w2, #0x510'),
        'shared_node_zero': (0xf9618, 'bl', '#0x2d248'),
        'event_node_length': (0xf7e68, 'add', 'w8, w8, #0x110'),
        'event_node_destination': (0xf7ee8, 'add', 'x0, x24, #0x14'),
        'event_node_copy': (0xf7ef8, 'bl', '#0x2cf68'),
        'receive_payload_size': (0xf67b0, 'mov', 'w2, #0x490'),
        'receive_payload_destination': (0xf67b8, 'add', 'x0, x24, #0x80'),
        'receive_payload_copy': (0xf67bc, 'bl', '#0x2cf68'),
        'receive_memory_handle_source': (0xf67ec, 'ldur', 'x8, [x21, #0x84]'),
        'receive_memory_handle_store': (0xf67f4, 'str', 'x8, [x24, #0x70]'),
        'receive_mapping_handle_store': (0xf67f8, 'str', 'x9, [x24, #0xf8]'),
        'release_implementation_call': (0xf5bd8, 'bl', '#0xf98c0'),
    },
    'x2d2_duml': {
        'sender_shared_handle': (0x147820, 'str', 'x8, [x28, #0x70]'),
        'sender_shared_payload_source_size': (0x147828, 'ldr', 'w8, [x20, #0x108]'),
        'sender_shared_payload_header_size': (0x14782c, 'add', 'x2, x8, #0x90'),
        'sender_shared_payload_copy': (0x147830, 'bl', '#0x3f7a0'),
        'receiver_payload_source': (0x14dfd8, 'add', 'x20, x21, #0x94'),
        'shared_node_zero_size': (0x149ecc, 'mov', 'w2, #0x910'),
        'shared_node_zero': (0x149ed8, 'bl', '#0x3faa0'),
        'event_node_length': (0x1482e8, 'add', 'w8, w8, #0x110'),
        'event_node_destination': (0x148368, 'add', 'x0, x24, #0x14'),
        'event_target_channel_read': (0x148364, 'ldr', 'w9, [x21, #4]'),
        'event_target_channel_store': (0x148374, 'str', 'w9, [x20, #0x78]'),
        'event_node_copy': (0x148378, 'bl', '#0x3f7a0'),
        'receive_payload_size': (0x14e018, 'mov', 'w2, #0x890'),
        'receive_payload_destination': (0x14e020, 'add', 'x0, x23, #0x80'),
        'receive_payload_copy': (0x14e024, 'bl', '#0x3f7a0'),
        'receive_memory_handle_source': (0x14e054, 'ldur', 'x8, [x21, #0x84]'),
        'receive_memory_handle_store': (0x14e05c, 'str', 'x8, [x23, #0x70]'),
        'receive_mapping_handle_store': (0x14e060, 'str', 'x9, [x23, #0xf8]'),
        'receive_register_free_callback': (0x14de48, 'bl', '#0x41720'),
        'release_implementation_call': (0x14cfe0, 'bl', '#0x14a210'),
    },
    'x2d2_cnntk': {
        'tof_roi_empty': (0x524f4, 'mov', 'w0, wzr'),
        'tof_roi_return': (0x524f8, 'ret', ''),
        'tof_depth_unavailable': (0x524fc, 'fmov', 's0, #-1.00000000'),
        'tof_depth_return': (0x52500, 'ret', ''),
        'tof_null_input_branch': (0x5247c, 'cbz', 'x1, #0x524dc'),
        'tof_null_input_clear_flag': (0x524dc, 'mov', 'w8, wzr'),
        'tof_null_input_status': (0x524e0, 'mov', 'w0, #1'),
        'tof_store_flag': (0x524e4, 'strb', 'w8, [x19]'),
    },
    'x2d': {
        'pool_descriptor_copy_size': (0xbc588, 'mov', 'w2, #0x218'),
        'pool_keeps_owner_and_frame': (0xbc5f4, 'stp', 'x21, x20, [x25, #0x38]'),
        'pool_entry_stride': (0xbc76c, 'add', 'x20, x20, #0x258'),
        'pool_entries_per_channel': (0xbc728, 'mov', 'w22, #0x1e'),
        'expiry_constant_low': (0xbc71c, 'mov', 'w23, #0x49f0'),
        'expiry_constant_high': (0xbc72c, 'movk', 'w23, #2, lsl #16'),
        'expired_frame_release_args': (0xbc754, 'ldp', 'x0, x1, [x25, #0x38]'),
        'expired_frame_release': (0xbc758, 'bl', '#0x707f0'),
        'lookup_copies_descriptor': (0xbc840, 'mov', 'w2, #0x218'),
        'lookup_does_not_acquire_at_copy': (0xbc84c, 'bl', '#0x71370'),
        'channel1_logical_id': (0xbd51c, 'mov', 'w0, wzr'),
        'channel2_logical_id': (0xbd590, 'mov', 'w0, #1'),
        'channel3_logical_id': (0xbd5e0, 'mov', 'w0, #2'),
        'target_ion_device_open': (0xa2044, 'bl', '#0x70a00'),
        'target_ion_device_start': (0xa2084, 'bl', '#0x71250'),
        'target_memory_import_call': (0xa299c, 'bl', '#0x70f90'),
        'target_memory_free_call': (0xa2afc, 'bl', '#0x71060'),
        'target_memory_share_call': (0xa334c, 'bl', '#0x71420'),
    },
    'x2d2': {
        'channel1_logical_id': (0x113a88, 'mov', 'w0, #1'),
        'channel2_logical_id': (0x113afc, 'mov', 'w0, #2'),
        'channel3_logical_id': (0x113b4c, 'mov', 'w0, #3'),
        'callback_full_image_zero_size': (0x134728, 'mov', 'w2, #0x84'),
        'callback_appended_metadata': (0x134794, 'add', 'x2, x23, #0x68'),
        'callback_channel_byte': (0x1347ac, 'strb', 'w20, [sp, #0xc8]'),
        'callback_memory_handle_input': (0x134738, 'ldr', 'x1, [x19, #0x70]'),
        'callback_import_helper': (0x134744, 'bl', '#0x1133c4'),
        'helper_import_call': (0x1137d4, 'bl', '#0x2956dc'),
        'hal_import_call': (0x29571c, 'bl', '#0x6c3b0'),
        'donor_ion_device_open': (0x293c4c, 'bl', '#0x6bb50'),
        'donor_ion_device_start': (0x293c8c, 'bl', '#0x6c6a0'),
        'hal_size_check_call': (0x295760, 'bl', '#0x6c830'),
        'hal_free_call': (0x295698, 'bl', '#0x6c480'),
        'metadata_source_block': (0x11338c, 'ldur', 'q0, [x0, #7]'),
        'metadata_destination_block': (0x113398, 'stur', 'q0, [x2, #4]'),
        'metadata_source_tail': (0x11339c, 'ldur', 'x8, [x0, #0x2f]'),
        'metadata_destination_tail': (0x1133a0, 'stur', 'x8, [x2, #0x14]'),
        'push_reads_full_image': (0x13fb24, 'mov', 'w2, #0x84'),
        'push_copy_call': (0x13fb40, 'bl', '#0x6c840'),
        'dsh_push_reads_full_image': (0x140308, 'mov', 'w2, #0x84'),
        'dsh_push_copy_call': (0x140324, 'bl', '#0x6c840'),
        'free_register_stub': (0x136c54, 'mov', 'w0, wzr'),
        'free_register_stub_return': (0x136c58, 'ret', ''),
    },
}


def audit(data, generation):
    if generation not in HASHES or hashlib.sha256(data).hexdigest() != HASHES[generation]:
        raise ValueError('拒绝非固定版本的原始 ELF')
    elf = ELFFile(io.BytesIO(data))
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    verified = {}
    for name, (address, mnemonic, operands) in CHECKS[generation].items():
        segment = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
                       and s['p_vaddr'] <= address
                       and address + 4 <= s['p_vaddr'] + s['p_filesz'])
        offset = address - segment['p_vaddr']
        ins = next(decoder.disasm(segment.data()[offset:offset + 4], address))
        if (ins.mnemonic, ins.op_str) != (mnemonic, operands):
            raise ValueError('指令契约不符：' + name)
        verified[name] = {'address': hex(address), 'instruction': (mnemonic + ' ' + operands).strip()}
    # PLT 地址必须解析到真正的导入，而不是依赖肉眼推断函数身份。
    plt = elf.get_section_by_name('.plt')
    relocs = elf.get_section_by_name('.rela.plt')
    syms = elf.get_section_by_name('.dynsym')
    names = {plt['sh_addr'] + 32 + 16*i: syms.get_symbol(r['r_info_sym']).name
             for i, r in enumerate(relocs.iter_relocations())}
    expected = {
        'x2d': {0x707f0: 'duss_dsh_data_release', 0x71370: 'memcpy',
                0x70a00: 'duss_hal_device_open', 0x71250: 'duss_hal_device_start',
                0x70f90: 'duss_hal_mem_import', 0x71060: 'duss_hal_mem_free',
                0x71420: 'duss_hal_mem_share'},
        'x2d2': {0x6c840: 'memcpy', 0x6c3b0: 'duss_hal_mem_import',
                 0x6bb50: 'duss_hal_device_open', 0x6c6a0: 'duss_hal_device_start',
                 0x6c830: 'duss_hal_mem_get_size', 0x6c480: 'duss_hal_mem_free'},
        'x2d_duml': {0x2cf68: 'memcpy', 0x2d248: 'memset'},
        'x2d2_duml': {0x3f7a0: 'memcpy', 0x3faa0: 'memset',
                      0x41720: 'duss_hal_mem_register_free_cb'},
        'x2d2_cnntk': {},
        'x2d_ml_sender': {0x3e40: 'memcpy', 0x3e90: 'memset',
                          0x42f0: '_ZN3Dsh4sendERKP16duss_dsh_channelP17duss_dsh_shm_node'},
        'x2d2_ml_sender': {0x4038: 'memcpy', 0x40c8: 'memset',
                           0x4538: '_ZN3Dsh4sendERKP16duss_dsh_channelP17duss_dsh_shm_node'},
    }[generation]
    for address, symbol in expected.items():
        if names.get(address) != symbol:
            raise ValueError('PLT 导入不符：' + symbol)
    return {'generation': generation, 'sha256': HASHES[generation],
            'verified_instructions': verified, 'verified_imports': expected}


def transport_extent_contract():
    """Static arithmetic only; copied extent is not receiver buffer capacity."""
    return {
        'event_prefix_bytes': 0x14,
        'receiver_body_offset': 0x94,
        'node_body_offset': 0x80,
        'x2d_node_bytes_in_event': 0x278 + 0x110,
        'x2d2_node_bytes_in_event': 0x390 + 0x110,
        'donor_metadata_read_end': 0x43c + 0x64 + 4,
        'donor_metadata_bytes_beyond_explicit_copy':
            (0x43c + 0x64 + 4) - (0x390 + 0x110),
        'receiver_tail_initialization_proven': False,
        'live_use_authorized_by_this_contract': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-dji-ml', type=Path, required=True)
    parser.add_argument('--source-dji-ml', type=Path, required=True)
    parser.add_argument('--target-duml-frwk', type=Path)
    parser.add_argument('--source-duml-frwk', type=Path)
    parser.add_argument('--source-cnntk', type=Path)
    parser.add_argument('--target-ml-sender', type=Path)
    parser.add_argument('--source-ml-sender', type=Path)
    args = parser.parse_args()
    report = {'evidence': [audit(args.target_dji_ml.read_bytes(), 'x2d'),
                           audit(args.source_dji_ml.read_bytes(), 'x2d2')],
        'level': 'static_instruction_contract', 'device_accessed': False,
        'original_functions_executed': False, 'ready_for_live_frames': False,
        'blockers': ['两代均有 ION 导入／释放路径，但尚未证明跨进程帧租约与异步消费期间的独立所有权',
                     '0x68 转换核心不是 0x84 完整入队记录',
                     '二代 ShareFrameFreeRegister 为返回零空实现，不能作为释放注册依据',
                     '同名通道回调编号不同，须核对实际图像来源后映射'],
        'static_candidate': {
            'dsh_handle_field_same_offset': 'frame+0x70 in both generations',
            'donor_imports_handle_before_enqueue': True,
            'target_receiver_copied_end_exclusive': 'frame+0x510',
            'donor_metadata_largest_read_end_exclusive': 'frame+0x4a4',
            'metadata_meaning_verified': False,
            'independent_lifetime_verified': False}}
    for path, key in ((args.target_duml_frwk, 'x2d_duml'),
                      (args.source_duml_frwk, 'x2d2_duml'),
                      (args.source_cnntk, 'x2d2_cnntk'),
                      (args.target_ml_sender, 'x2d_ml_sender'),
                      (args.source_ml_sender, 'x2d2_ml_sender')):
        if path is not None:
            report['evidence'].append(audit(path.read_bytes(), key))
    report['blockers'].append('DSH 接收复制长度 0x490/0x890 不同；禁止直接接入二代接收器')
    if args.target_ml_sender is not None and args.source_ml_sender is not None:
        report['sender_contract'] = {
            'x2d_input_frame_copy': '0x218',
            'x2d_outgoing_frame_copy': '0x278',
            'x2d2_input_frame_copy': '0x330',
            'x2d2_outgoing_frame_copy': '0x390',
            'both_input_tails_explicitly_zeroed': '0x60 bytes',
            'donor_tail_zero_range_in_node': '[0x43c, 0x49c)',
            'extra_bytes_proven_semantically_compatible': False,
        }
        report['blockers'].append('原厂 ML 发送端两代输入/发送结构均差 0x118 字节；尾部语义未证实')
        if args.target_duml_frwk is not None and args.source_duml_frwk is not None:
            report['transport_extent_contract'] = transport_extent_contract()
            report['blockers'].append('二代该发送路径显式复制到节点 +0x4a0；回调读到 +0x4a4，末 4 字节来源未证实')
    report['lidar_free_pipeline_verified'] = False
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()

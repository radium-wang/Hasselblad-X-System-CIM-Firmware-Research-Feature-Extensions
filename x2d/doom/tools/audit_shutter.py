#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Version-bound stock shutter routing checks; local ARM64 branch emulation only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from firmware_image import FirmwareElf, instruction
def check(condition, message):
    if not condition: raise ValueError(message)

def defined(binary, name):
    found = [s for s in binary.symbols if s.name == name and s['st_value'] and s['st_size']]
    check(len(found) == 1, '预期唯一的已定义符号：' + name)
    return found[0]


def enum_table(binary, data_name, strings_name, revision):
    data = defined(binary, data_name)
    strings = defined(binary, strings_name)
    raw = binary.read(data['st_value'], data['st_size'])
    values = struct.unpack('<' + 'I' * (len(raw) // 4), raw)
    check(values[0] == revision, 'Qt 元数据版本不匹配')

    def string(index):
        check(index * 8 + 8 <= strings['st_size'], 'Qt 字符串索引越界')
        offset, size = struct.unpack('<II', binary.read(strings['st_value'] + index * 8, 8))
        check(offset + size <= strings['st_size'], 'Qt 字符串内容越界')
        return binary.read(strings['st_value'] + offset, size).decode('utf-8')

    result = {}
    # 本次两份构建的枚举均使用五个 uint 的记录及 32 位数值。
    for i in range(values[8]):
        row = values[values[9] + 5 * i:values[9] + 5 * (i + 1)]
        check(len(row) == 5, 'Qt 枚举记录越界')
        name, _, flags, count, offset = row
        check(not flags & 4, '未支持的 64 位 Qt 枚举')
        check(offset + count * 2 <= len(values), 'Qt 枚举内容越界')
        result[string(name)] = {
            string(values[offset + j * 2]): values[offset + j * 2 + 1]
            for j in range(count)
        }
    return result



HASHES = {
    'camera-gui': '16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0',
    'camera-service': 'fbcf828f73bca13f0c8b95e7dd0b95ac483ae36954ec06179098c8a1a65f9f82',
}


def emulator(binary):
    from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_SP, UC_ARM64_REG_PC, UC_ARM64_REG_LR
    from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X19, UC_ARM64_REG_W1, UC_ARM64_REG_W21
    uc = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
    uc.mem_map(0, 0x1000000)
    for segment in binary.elf.iter_segments():
        if segment['p_type'] == 'PT_LOAD': uc.mem_write(segment['p_vaddr'], segment.data())
    uc.mem_map(0x40000000, 0x10000)
    uc.mem_map(0x41000000, 0x10000)
    return uc


def dispatch_case(binary, mode, key, pressed, last_release=False):
    from unicorn import UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_SP, UC_ARM64_REG_PC, UC_ARM64_REG_LR
    from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X19, UC_ARM64_REG_W1, UC_ARM64_REG_W21
    uc = emulator(binary); obj = 0x41000000; stack = 0x40008000
    uc.reg_write(UC_ARM64_REG_SP, stack); uc.reg_write(UC_ARM64_REG_X19, obj)
    uc.reg_write(UC_ARM64_REG_W21, int(last_release))
    uc.mem_write(obj + 0x39, bytes([mode]))
    uc.mem_write(stack + 0x1c, struct.pack('<I', key))
    uc.mem_write(stack + 0x20, bytes([pressed]))
    calls = []
    def hook(engine, address, size, data):
        if address in (0xade28, 0xade90, 0x1ad990):
            value = engine.reg_read(UC_ARM64_REG_W1)
            name = {0xade28: 'halfPress', 0xade90: 'fullPress', 0x1ad990: 'setForwardMode'}[address]
            calls.append([name, value])
            if name == 'setForwardMode': engine.mem_write(obj + 0x39, bytes([value]))
            engine.reg_write(UC_ARM64_REG_PC, engine.reg_read(UC_ARM64_REG_LR))
    uc.hook_add(UC_HOOK_CODE, hook)
    # Execute the original dispatch instructions after queue bookkeeping, with explicit prior state.
    uc.emu_start(0x1aa270, 0x1aa2d0, count=150)
    return calls, uc.mem_read(obj + 0x39, 1)[0]


def defer_case(binary, held):
    from unicorn import UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_SP, UC_ARM64_REG_PC, UC_ARM64_REG_LR
    from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_W0, UC_ARM64_REG_W1
    uc = emulator(binary); obj = 0x41000000; table = 0x41001000; active = 0x41002000
    getter = 0x40000100; end = 0x40000200
    uc.mem_write(obj, struct.pack('<Q', table))
    uc.mem_write(table + 0x70, struct.pack('<Q', getter))
    uc.mem_write(obj + 0x38, bytes([3, 3]))
    if held:
        uc.mem_write(obj + 0x18, struct.pack('<Q', active))
        uc.mem_write(active + 8, struct.pack('<Q', 1))
    uc.reg_write(UC_ARM64_REG_SP, 0x40008000); uc.reg_write(UC_ARM64_REG_LR, end)
    uc.reg_write(UC_ARM64_REG_X0, obj); uc.reg_write(UC_ARM64_REG_X1, 0)
    calls = []
    def hook(engine, address, size, data):
        if address == getter:
            engine.reg_write(UC_ARM64_REG_W0, engine.mem_read(obj + 0x38, 1)[0])
            engine.reg_write(UC_ARM64_REG_PC, engine.reg_read(UC_ARM64_REG_LR))
        elif address == 0xaddc8:
            engine.reg_write(UC_ARM64_REG_PC, engine.reg_read(UC_ARM64_REG_LR))
        elif address == 0x1ad990:
            value = engine.reg_read(UC_ARM64_REG_W1); calls.append(value)
            engine.mem_write(obj + 0x39, bytes([value]))
            engine.reg_write(UC_ARM64_REG_PC, engine.reg_read(UC_ARM64_REG_LR))
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(0x1ad8f0, end, count=150)
    return calls, list(uc.mem_read(obj + 0x38, 2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--emulate', action='store_true', help='Explicit host emulation; use a compatible Unicorn runtime')
    a = p.parse_args()
    if a.out.resolve().is_relative_to(a.system.resolve()): p.error('Output must be separate from inputs')
    binaries = {}
    for name, sha in HASHES.items():
        raw = (a.system / 'bin' / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha: raise ValueError('Unsupported ' + name)
        binaries[name] = FirmwareElf(raw)
    gui, service = binaries['camera-gui'], binaries['camera-service']
    enums = enum_table(service, '_ZL22qt_meta_data_HblmTypes', '_ZN12_GLOBAL__N_128qt_meta_stringdata_HblmTypesE', 10)
    expected = {'E_CameraKeyOption_None': 0, 'E_CameraKeyOption_Listen': 1,
                'E_CameraKeyOption_OverrideHalfPress': 2, 'E_CameraKeyOption_Override': 3,
                'E_CameraKeyOption_Max': 255}
    assert enums['E_CameraKeyOption'] == expected
    assert gui.read(0x1541248, 12) == b'keyOverride\0'
    assert gui.read(0x14e88e0, 21) == b'forward_input_events\0'
    funcs = [('camera-gui', '_ZNK15KeyFocusHandler16checkKeyOverrideEPK10QQuickItem', 0x33a0c0),
             ('camera-gui', '_ZN15CameraProxyDbus23setForward_input_eventsEN9HblmTypes17E_CameraKeyOptionE', 0xa8dcd8),
             ('camera-service', '_ZN12InputControl4pumpEv', 0x1aa180),
             ('camera-service', '_ZN21InputControlInterface28setForwardInputEventsSettingEN9HblmTypes17E_CameraKeyOptionE', 0x1ad8f0)]
    functions = []
    for file, name, address in funcs:
        s = defined(binaries[file], name); assert s['st_value'] == address
        functions.append({'file': file, 'symbol': name, 'address': hex(address),
            'codeSha256': hashlib.sha256(binaries[file].read(address, s['st_size'])).hexdigest()})
    checks = {
        'camera-gui': {0x33a2fc: ('bl', '#0x33a0c0'), 0x33a320: ('ldr', 'x8, [x8, #0x7d8]'),
            0x33aba8: ('bl', '#0xae5550'), 0x33abac: ('tbnz', 'w0, #0, #0x33ad00'),
            0x351780: ('mov', 'w0, wzr'), 0x351784: ('ret', '')},
        'camera-service': {0x1aa274: ('cmp', 'w8, #0x45'), 0x1aa27c: ('cmp', 'w8, #0x41'),
            0x1aa2ac: ('cmp', 'w8, #2'), 0x1aa2b0: ('b.hi', '#0x1aa2c0'),
            0x1aa2bc: ('bl', '#0xade90'), 0x1aa2cc: ('bl', '#0x1ad990'),
            0x1ad954: ('cbz', 'w21, #0x1ad964'), 0x1ad970: ('cbnz', 'x8, #0x1ad920')},
    }
    verified = []
    for file, entries in checks.items():
        for address, expected_instruction in entries.items():
            i = instruction(binaries[file], address)
            assert (i.mnemonic, i.op_str) == expected_instruction
            verified.append({'file': file, 'address': hex(address), 'instruction': ' '.join(expected_instruction)})
    if not a.emulate:
        report = {'model': 'X2D 100C', 'firmware': '4.2.0 build 24849', 'deviceAccess': False,
                  'level': 'static only', 'hashes': HASHES, 'routingEnum': expected,
                  'fullPressQtKey': 69, 'halfPressQtKey': 65, 'functions': functions,
                  'instructions': verified, 'emulationRun': False}
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'level': report['level'], 'instructions': len(verified), 'deviceAccess': False}))
        return
    results = []
    for mode in range(4):
        for pressed in (0, 1):
            calls, current = dispatch_case(service, mode, 0x45, pressed)
            assert calls == ([] if mode == 3 else [['fullPress', pressed]])
            results.append({'mode': mode, 'fullPressed': bool(pressed), 'calls': calls})
    for pressed in (0, 1):
        calls, _ = dispatch_case(service, 3, 0x41, pressed); assert calls == []
    held_calls, held_state = defer_case(service, True)
    released_calls, released_state = defer_case(service, False)
    assert held_calls == [] and held_state == [0, 3]
    assert released_calls == [0] and released_state == [0, 0]
    calls, mode = dispatch_case(service, 3, 0x45, 0, last_release=True)
    assert calls == [['setForwardMode', 0]] and mode == 0
    report = {'model': 'X2D 100C', 'firmware': '4.2.0 build 24849', 'deviceAccess': False,
        'level': 'static + original ARM64 branch emulation with callbacks stubbed', 'hashes': HASHES,
        'routingEnum': expected, 'fullPressQtKey': 69, 'halfPressQtKey': 65,
        'functions': functions, 'instructions': verified, 'dispatchCases': results,
        'override3SuppressesFullAndHalfCallbacks': True,
        'exitWhileHeldDefersStockCaptureUntilRelease': True,
        'lastReleaseSuppressedThenModeCleared': True,
        'hardwareCaptureSuppressionValidated': False}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['level', 'override3SuppressesFullAndHalfCallbacks',
        'exitWhileHeldDefersStockCaptureUntilRelease', 'lastReleaseSuppressedThenModeCleared', 'deviceAccess']}))


if __name__ == '__main__': main()

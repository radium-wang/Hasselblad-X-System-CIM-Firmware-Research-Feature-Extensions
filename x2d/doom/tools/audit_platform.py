#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Read explicit, local X2D 4.2.0 files; never import a device transport."""
import argparse
import hashlib
import json
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile

HASHES = {
    'bin/camera-gui': '16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0',
    'lib64/libwayland-client.so': 'fc9bd40a0c0abd0af78241145eff27c3d228c4509c919adb92f454a8fd13c6e4',
    'lib64/libweston.so': '6dcda1cb8fd02ac8609ef8c9b3110af205cdc1b8ccef27389bc36c76210089e6',
    'lib64/weston/eagle-shell.so': 'e6c7e863df6ac6148d1d34ea7692c33215503a30770295ea62e70d13b669e272',
    'lib64/weston/eagle-backend.so': 'a0ac02a51d87d08fa61fd0d1e79af15db248af4b5b32603b9483d09f9b7f6217',
    'lib64/libQt6Core.so.6': 'ab64228f088d7404835e59f97185e14cea904d301dfefd29b78a9a5d76e657c4',
}
GUI_FUNCTIONS = {
    'imageProvider': ('_ZN10QQmlEngine16addImageProviderERK7QStringP21QQmlImageProviderBase', 0x6a8038),
    'providerConstructor': ('_ZN19QQuickImageProviderC2EN21QQmlImageProviderBase9ImageTypeE6QFlagsINS0_4FlagEE', 0xde32f8),
    'bmpReader': ('_ZN11QBmpHandler4readEP6QImage', 0xca9918),
    'inputFilter': ('_ZN16InputEventFilter11eventFilterEP7QObjectP6QEvent', 0x33ab08),
    'keyHandler': ('_ZN17KeyHandlerForeign8instanceEv', 0x33adb0),
    'x2dButtons': ('_ZN13KeyHandlerX2d16addCustomButtonsEv', 0xae94f0),
    'keyPressed': ('_ZN18QQuickKeysAttached10keyPressedEP9QKeyEventb', 0xd5e5d0),
    'touchArea': ('_ZN25QQuickMultiPointTouchArea10touchEventEP11QTouchEvent', 0xf1b7c8),
    'wakeupButton': ('_ZNK14KeyHandlerBase14isWakeupButtonEij', 0xae84e8),
    'displayOffButton': ('_ZNK14KeyHandlerBase18isDisplayOffButtonEij', 0xae8550),
}


def inspect(root):
    report = {'model': 'X2D 100C', 'firmware': '4.2.0 build 24849',
              'level': 'static/offline', 'deviceAccess': False, 'files': {}, 'gui': {}}
    for rel, expected in HASHES.items():
        path = root / rel
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError('Unsupported firmware input: ' + rel)
        with path.open('rb') as handle:
            elf = ELFFile(handle)
            assert elf['e_machine'] == 'EM_AARCH64'
            dyn = elf.get_section_by_name('.dynsym')
            dynamic = elf.get_section_by_name('.dynamic')
            report['files'][rel] = {'sha256': digest, 'elf': 'AArch64',
                'needed': [t.needed for t in dynamic.iter_tags() if t.entry.d_tag == 'DT_NEEDED']}
            if rel != 'bin/camera-gui':
                exports = {s.name for s in dyn.iter_symbols() if s['st_shndx'] != 'SHN_UNDEF'}
                want = ['wl_display_connect', 'wl_shm_interface', 'wl_shell_interface',
                        'wl_touch_interface', 'eagle_shm_interface', 'wet_shell_init']
                report['files'][rel]['protocolExports'] = sorted(exports.intersection(want))
                continue
            symbols = {s.name: s for s in elf.get_section_by_name('.symtab').iter_symbols()}
            dynamic_exports = {s.name for s in dyn.iter_symbols() if s['st_shndx'] != 'SHN_UNDEF'}
            for label, (name, address) in GUI_FUNCTIONS.items():
                sym = symbols[name]
                assert sym['st_value'] == address and sym['st_size'] > 0
                seg = next(s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'
                           and s['p_vaddr'] <= address < s['p_vaddr'] + s['p_filesz'])
                offset = address - seg['p_vaddr']
                code = seg.data()[offset:offset + sym['st_size']]
                report['gui'][label] = {'symbol': name, 'address': hex(address),
                    'bytes': len(code), 'binding': sym['st_info']['bind'],
                    'dynamicallyExported': name in dynamic_exports,
                    'codeSha256': hashlib.sha256(code).hexdigest()}
                if label == 'inputFilter':
                    cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
                    instructions = {i.address: (i.mnemonic, i.op_str) for i in cs.disasm(code, address)}
                    checks = {
                        0x33ab48: ('cmp', 'w9, #7'),
                        0x33abc4: ('cmp', 'w8, #6'),
                        0x33abcc: ('bl', '#0x33adb0'),
                        0x33abd0: ('ldr', 'w22, [x19, #0x40]'),
                        0x33abf0: ('ldr', 'x8, [x8, #0xa0]'),
                        0x33ac20: ('ldr', 'x8, [x8, #0xa8]'),
                        0x33ac28: ('tbnz', 'w22, #0, #0x33ad00'),
                        0x33ad58: ('mov', 'w0, #1'),
                    }
                    for location, expected_instruction in checks.items():
                        assert instructions[location] == expected_instruction, hex(location)
                    report['inputFilterInstructions'] = [
                        {'address': hex(a), 'instruction': ' '.join(v)} for a, v in checks.items()]
            report['staticQtQuick'] = not any('Qt6Quick' in n for n in report['files'][rel]['needed'])
            report['bmpPresent'] = True
    props = dict(line.split('=', 1) for line in (root / 'build.prop').read_text().splitlines()
                 if '=' in line and not line.startswith('#'))
    for key, value in {'ro.build.version.sdk': '28', 'ro.build.version.incremental': '24849',
                       'ro.product.cpu.abilist': 'arm64-v8a', 'ro.product.cpu.abilist32': ''}.items():
        assert props[key] == value, key
    report['runtimeProperties'] = {k: props[k] for k in (
        'ro.build.version.sdk', 'ro.build.version.release', 'ro.build.version.incremental',
        'ro.product.cpu.abilist', 'ro.product.cpu.abilist32')}
    assert b'Qt 6.4.1 (arm64-little_endian-lp64' in (root / 'lib64/libQt6Core.so.6').read_bytes()
    report['qtVersion'] = '6.4.1'
    rc = (root / 'etc/init/camera-gui.rc').read_text()
    assert 'service camera-gui /system/bin/camera-gui -platform wayland-egl --fullscreen' in rc
    assert 'setenv XDG_RUNTIME_DIR /tmp' in rc
    report['waylandGuiService'] = True
    input_script = (root / 'bin/debug_gui_input.sh').read_text()
    assert 'gui_buttons' in input_script and 'BTN_TOUCH' in input_script
    report['stockInputNames'] = ['gui_buttons', 'touch (keyword, not a fixed event number)']
    report['absentFromSystemFileInventory'] = [label for label, pattern in (
        ('SDL', '*SDL*'), ('Qt6Quick shared library', '*Qt6Quick*.so*'),
        ('QtWebEngine', '*WebEngine*')) if not any(root.rglob(pattern))]
    report['hardwarePerformanceMeasured'] = False
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system', type=Path, required=True)
    p.add_argument('--out', type=Path)
    args = p.parse_args()
    if args.out and args.out.resolve().is_relative_to(args.system.resolve()):
        p.error('Output must be separate from firmware input')
    result = inspect(args.system)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(serialized)
    print(serialized)


if __name__ == '__main__':
    main()

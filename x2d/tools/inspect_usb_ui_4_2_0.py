"""复核 USB 终端承载与原厂简单 UI；只读固件，不生成或发送设备请求。"""
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from firmware_image import system_file, system_elf, instruction
from qml_resource import GUI_SHA, resource


def main():
    inputs = {
        '/bin/camera-gui': GUI_SHA,
        '/bin/camera-test': 'e2621b84391d0e5601d9a22f9da460e982f7028bf5380e9f9d401a91380bb7b0',
        '/bin/msg2dbus': 'c02c2cd83ec9e5d7862659f05328927b7faa3e57789dd4aa0fd9bc427ad13a43',
        '/lib64/weston/eagle-backend.so': 'a0ac02a51d87d08fa61fd0d1e79af15db248af4b5b32603b9483d09f9b7f6217',
        '/lib64/libwayland-client.so': 'fc9bd40a0c0abd0af78241145eff27c3d228c4509c919adb92f454a8fd13c6e4',
    }
    binaries = {path: system_elf(path, digest) for path, digest in inputs.items()}
    gui = binaries['/bin/camera-gui']
    test = binaries['/bin/camera-test']
    bridge = binaries['/bin/msg2dbus']
    backend = binaries['/lib64/weston/eagle-backend.so']
    client = binaries['/lib64/libwayland-client.so']
    checks = []

    def check(name, result):
        if not result:
            raise AssertionError(name)
        checks.append(name)

    def ins(binary, address, mnemonic, operands):
        current = instruction(binary, address)
        check(f'{address:#x}: {mnemonic} {operands}', (current.mnemonic, current.op_str) == (mnemonic, operands))

    ins(bridge, 0x10ae60, 'cmp', 'w8, #0xa')
    ins(bridge, 0x10ae64, 'b.eq', '#0x10ae9c')
    ins(bridge, 0x10ae9c, 'ldrb', 'w1, [x20, #4]')
    ins(bridge, 0x10aeb8, 'bl', '#0xa84d8')
    ins(test, 0x4fca4, 'bl', '#0x4def0')
    ins(test, 0x527a8, 'cmp', 'w9, #0xfc')
    ins(test, 0x4df2c, 'bl', '#0x4ae78')
    ins(test, 0x4df38, 'b.ne', '#0x4df74')
    ins(test, 0x4e130, 'ldr', 'x0, [x0, #0x10]')
    ins(test, 0x4e140, 'ldr', 'x8, [x8, #0x70]')
    ins(test, 0x4e144, 'blr', 'x8')
    check('活跃 HblShell 的接收虚函数', struct.unpack('<Q', test.read(0x1b6618 + 0x80, 8))[0] == 0x967d0)
    ins(test, 0x96014, 'add', 'x20, x20, #0x14')
    ins(test, 0x9601c, 'bl', '#0x362e0')
    ins(test, 0x961c4, 'strb', 'w9, [x8, #0x48]')
    check('Shell 两种启动模式', test.read(0x142aa3, 6) == b'-i\0-c\0')
    ins(test, 0x96804, 'cmp', 'w8, #1')
    ins(test, 0x9680c, 'add', 'x20, x1, #0x14')
    ins(test, 0x96b5c, 'bl', '#0x95818')
    ins(test, 0x95840, 'bl', '#0x36660')
    ins(test, 0x9585c, 'bl', '#0x372e0')
    ins(test, 0x950f4, 'cbz', 'w20, #0x95100')
    ins(test, 0x95100, 'bl', '#0x459e8')
    ins(test, 0x971b4, 'bl', '#0x4ec20')
    ins(bridge, 0x10c568, 'mov', 'w1, #9')

    confirm = resource(gui, 0x1b5d6f3, 0x1b5d74b, 0x1b5d7a1, 3, 'confirmtest_main.qml')
    picture = resource(gui, 0x1b56f56, 0x1b56fae, 0x1b56ffc, 3, 'imagetest_main.qml')
    check('确认页显示传入文字与按钮', 'text: textMessage' in confirm and 'text: buttonText' in confirm)
    check('确认页释放按钮退出', 'onReleased: Qt.quit()' in confirm)
    check('确认页使用 GUI 窗口角色', 'title: "gui"' in confirm)
    check('参数 button', gui.read(0x153a282, 12).decode('utf-16-le') == 'button')
    check('参数 textmsg', gui.read(0x153a290, 14).decode('utf-16-le') == 'textmsg')
    ins(gui, 0x333198, 'mov', 'w8, #0x3e8')
    ins(gui, 0x3331a0, 'mul', 'w22, w22, w8')
    ins(gui, 0x3331d0, 'bl', '#0x901ea8')
    ins(gui, 0x333fdc, 'b', '#0x8c2410')
    check('图片页支持 PNG 和 JPG', 'urlLower.endsWith("png")' in picture and 'urlLower.endsWith("jpg")' in picture)
    check('图片页按键返回状态', 'Keys.onPressed' in picture and 'Qt.exit(1)' in picture and 'Qt.exit(0)' in picture)
    check('普通动态程序的解释器', any(segment['p_type'] == 'PT_INTERP' and segment.data() == b'/system/bin/linker64\0' for segment in gui.elf.iter_segments()))
    needed = [tag.needed for tag in gui.elf.get_section_by_name('.dynamic').iter_tags() if tag.entry.d_tag == 'DT_NEEDED']
    check('GUI 不依赖外部 Qt Quick 动态库', not any(name.startswith('libQt6') for name in needed))
    ins(backend, 0x948a8, 'bl', '#0x7c978')
    ins(backend, 0x948c0, 'bl', '#0x7c988')
    ins(backend, 0x948d4, 'cbz', 'w0, #0x949c8')
    ins(backend, 0x948d8, 'cmp', 'w0, #1')
    exports = {symbol.name for symbol in client.elf.get_section_by_name('.dynsym').iter_symbols() if symbol['st_value']}
    check('系统具备标准 Wayland 客户端接口', {'wl_display_connect', 'wl_display_dispatch', 'wl_shell_interface', 'wl_shm_interface', 'wl_seat_interface'} <= exports)
    scripts = {
        '/bin/test_lcd_module_link.sh': 'b8c4f7d750c4d9a663e4e1a74d3268b5419e06cf1ace92b613f428e69eeefff8',
        '/bin/test_usb_device_enumeration.sh': 'a38f7c74b4595e51464b15b8ae165e0452562cb4ecfc426661f19fca590a64e2',
    }
    for path, digest in scripts.items():
        check(path + ' 哈希', hashlib.sha256(system_file(path)).hexdigest() == digest)
    check('原厂确认页可选无应用 DBus', b'--confirmtest -b none' in system_file('/bin/test_lcd_module_link.sh'))
    check('原厂脚本实际调用自定义文字页', b'--confirmtest --textmsg' in system_file('/bin/test_usb_device_enumeration.sh'))
    print(json.dumps({
        'model': 'X2D 100C', 'firmware': '4.2.0', 'source': 'official-firmware-static',
        'preferredTransport': 'USB', 'deviceAccesses': 0, 'result': 'pass', 'checks': checks,
        'generatedUtc': datetime.now(timezone.utc).isoformat(),
        'scriptSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'inputSha256': inputs | scripts,
        'limitations': ['USB 维护消息未实机联调', '编码分段上传尚未实现', '未核实可写可执行目录', '没有机内显示与输入实测', '没有可装载程序'],
    }, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()

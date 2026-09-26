"""从固定 4.2.0 提取最小原厂网格测试材料；仅本地，不访问设备。"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
sys.path.insert(0, str(D.parent))
from inspect_menu_resources import GUI_SHA, load_gui, resources

FILES = ['mainmenu/MainScreen.qml', 'components/Background.qml',
         'components/CustomGridView.qml', 'components/BounceGridView.qml',
         'components/ViewHelper.qml', 'components/GridNavigation.qml',
         'components/ScaledImage.qml', 'components/buttons/FramedImage.qml',
         'components/buttons/FramedItem.qml', 'scripts/Keys.js']


def main():
    target = D / '.stock-host'
    manifest = {}
    for name, content in resources(load_gui()):
        relative = name.removeprefix(':/app/qml/')
        if relative not in FILES:
            continue
        path = target / 'qml' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        manifest[relative] = hashlib.sha256(content).hexdigest()
    assert set(manifest) == set(FILES)
    (target / 'manifest.json').write_text(json.dumps(dict(
        firmware='4.2.0', guiSha256=GUI_SHA, unmodifiedResources=manifest), indent=2))
    print('Extracted and hashed', len(manifest), 'unmodified resources for local host testing')


if __name__ == '__main__':
    main()

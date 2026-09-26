"""Build offline QML sidecars for the direct-GUI experiment; no device I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import re

D = Path(__file__).resolve().parent
PARENT = D.parent
GUI_SHA = "16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0"
MAIN_CLONE_SHA = "cc35325bead73358bdca313219e22d7b698b8cf7e9c8260015dc51ea77d207a5"
NAMES = {
    "Bootstrap": "X2dNativeMenuBootstrap",
    "PlayMenuModel": "X2dNativeMenuModel",
    "PlayMenuRoute": "X2dNativeMenuRoute",
    "ResidentPlayHost": "X2dNativeMenuHost",
    "PlayPage": "X2dPlayPage",
    "AfcMenuController": "X2dAfcMenuController",
}
PROBE_ROOT = "/blackbox/.codex-x2d-direct-probe"


def change_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Expected one occurrence of {old!r}, got {source.count(old)}")
    return source.replace(old, new)


def source_for(name):
    if name == "PlayPage":
        return (D / "PlaySettingsPage.qml").read_text(encoding="utf-8")
    if name == "AfcMenuController":
        return (D / "AfcMenuController.qml").read_text(encoding="utf-8")
    return (PARENT / (name + ".qml")).read_text(encoding="utf-8")


def transform(name, source, blackbox_probe=False):
    if name == "Bootstrap" and "AfcMenuController {" not in source:
        source = change_once(source,
            "    PlayMenuRoute {\n        id: route",
            "    AfcMenuController {\n"
            "        id: afcController\n"
            "        controlViewModel: root.drawer ? root.drawer.controlScreenViewModel : null\n"
            "    }\n"
            "    PlayMenuRoute {\n        id: route\n"
            "        featureController: afcController")
    elif name == "PlayMenuRoute" and "property var featureController" not in source:
        source = change_once(source,
            "    property bool stockSubmenuActive: false",
            "    property bool stockSubmenuActive: false\n"
            "    property var featureController: null")
        source = change_once(source,
            "        stockSubmenuActive: root.stockSubmenuActive",
            "        stockSubmenuActive: root.stockSubmenuActive\n"
            "        featureController: root.featureController")
    elif name == "ResidentPlayHost" and "property var featureController" not in source:
        source = change_once(source,
            "    property bool playOpen: false",
            "    property bool playOpen: false\n"
            "    property var featureController: null")
        source = change_once(source,
            "        pageActive: root.showing",
            "        pageActive: root.showing\n"
            "        featureController: root.featureController")
    if blackbox_probe:
        source = source.replace("file:///system/etc/X2dPlayIcon",
                                "file://" + PROBE_ROOT + "/X2dPlayIcon")
    pattern = r"\b(" + "|".join(NAMES) + r")\b"
    return re.sub(pattern, lambda match: NAMES[match.group(0)], source)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--blackbox-probe", action="store_true",
                        help="Prepare references for /blackbox without /system writes")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("output directory must be absent or empty; refusing to overwrite")
    output.mkdir(parents=True, exist_ok=True)

    manifest = []
    for source_name, output_name in NAMES.items():
        content = transform(source_name, source_for(source_name), args.blackbox_probe).encode("utf-8")
        path = output / (output_name + ".qml")
        path.write_bytes(content)
        manifest.append({"name": path.name,
                         "target": (PROBE_ROOT if args.blackbox_probe else "/system/etc") + "/" + path.name,
                         "sha256": hashlib.sha256(content).hexdigest()})
    icon = PARENT / "assets/ic_main_menu_play.svg"
    icon_content = icon.read_bytes()
    icon_target = output / "X2dPlayIcon.svg"
    icon_target.write_bytes(icon_content)
    manifest.append({"name": icon_target.name,
                     "target": (PROBE_ROOT if args.blackbox_probe else "/system/etc") + "/" + icon_target.name,
                     "sha256": hashlib.sha256(icon_content).hexdigest()})
    (output / "manifest.NOT_FOR_DEVICE.json").write_text(json.dumps({
        "sourceGuiSha256": GUI_SHA,
        "requiredMainScreenCloneSha256": MAIN_CLONE_SHA,
        "files": manifest,
        "installable": False,
        "deviceValidated": False,
        "afcRuntimeModelMutationValidated": False,
        "blackboxProbe": args.blackbox_probe,
        "note": "Offline sources only. Do not copy to /system or replace camera-gui.",
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output), "qmlFiles": len(NAMES),
                      "installable": False, "deviceValidated": False}))


if __name__ == "__main__":
    main()

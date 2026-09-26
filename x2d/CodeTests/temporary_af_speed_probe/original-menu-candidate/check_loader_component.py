"""Check the public MainScreen Loader and twelfth-entry SVG offline."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOADER = ROOT / "X2dNativeMenuLoader.qml"
BOOTSTRAP = ROOT / "Bootstrap.qml"
ICON = ROOT / "assets" / "ic_main_menu_play.svg"


def main() -> None:
    loader = LOADER.read_text(encoding="utf-8")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    icon = ICON.read_text(encoding="utf-8")

    for marker in (
        "Loader {",
        'objectName: "X2dNativeMenuLoader"',
        "property Item stockScreen",
        "property Item stockDrawer",
        'property url bootstrapSource: Qt.resolvedUrl("Bootstrap.qml")',
        "onLoaded:",
        "item.screen = stockScreen",
        "item.drawer = stockDrawer",
    ):
        assert marker in loader, marker
    assert 'objectName: "X2dNativeMenuExtension"' in bootstrap
    assert 'playLabel: "耍起功能"' in bootstrap
    assert "<svg" in icon and "</svg>" in icon
    assert "X2dPlayIcon" not in icon
    assert "https://" not in icon and "file://" not in icon
    print("PUBLIC MENU LOADER CHECK PASSED")


if __name__ == "__main__":
    main()

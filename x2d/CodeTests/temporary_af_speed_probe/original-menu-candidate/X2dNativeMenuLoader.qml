import QtQuick

// Source-level Loader for the stock MainScreen integration point.
//
// The generated MainScreen QML unit and the runtime preload/install package
// are intentionally not published. A host that already owns an authorized
// stock MainScreen can instantiate this Loader as its child and pass the
// corresponding screen and ControlDrawer objects explicitly.
Loader {
    id: root
    objectName: "X2dNativeMenuLoader"

    // These are deliberately explicit: guessing parent relationships can
    // attach the extension to the wrong GUI surface after a vendor update.
    property Item stockScreen: null
    property Item stockDrawer: null
    property url bootstrapSource: Qt.resolvedUrl("Bootstrap.qml")
    property bool attachWhenReady: true

    active: attachWhenReady && stockScreen !== null && stockDrawer !== null
    source: active ? bootstrapSource : ""

    onLoaded: {
        if (!item)
            return
        // Bootstrap.qml also performs a parent-based fallback for the
        // desktop fixture. Explicit references take precedence on a host.
        item.screen = stockScreen
        item.drawer = stockDrawer
    }
}

import QtQuick
import QtQml.Models

// 保留原厂 FavoriteModel 的所有项目和行为，只在受支持的 4x3 布局末尾追加“耍起功能”。
DelegateModel {
    id: root
    objectName: "PlayMenuModel"
    property var sourceModel: null
    property Component stockDelegate: null
    property bool supportedLayout: true
    property bool extensionEnabled: true
    property string playLabel: "耍起功能"
    // 原厂 SVG provider 接受不带 .svg 后缀的 file URL。
    property string playIcon: "file:///system/etc/X2dPlayIcon"
    readonly property string extensionName: "x2dPlayUi"
    property bool reconciling: false
    property bool ready: false
    property bool extensionPresent: false
    property string rejectionReason: "not-ready"
    model: sourceModel
    delegate: stockDelegate

    function itemEnabled(ix) {
        if (ix < 0 || ix >= items.count)
            return false
        var entry = items.get(ix)
        if (entry.isUnresolved)
            return extensionPresent && extensionEnabled && entry.model.menuName === extensionName
        return sourceModel !== null && sourceModel.itemEnabled(ix)
    }

    function requestReconcile() {
        if (ready && !reconciling)
            Qt.callLater(reconcile)
    }

    function reconcile() {
        if (!ready || reconciling)
            return
        reconciling = true
        var tail = -1
        var originals = 0
        var collision = false
        for (var i = 0; i < items.count; ++i) {
            var entry = items.get(i)
            if (entry.isUnresolved && entry.model.menuName === extensionName)
                tail = i
            else {
                originals++
                if (entry.model.menuName === extensionName)
                    collision = true
            }
        }
        var reason = sourceModel === null ? "no-source" :
                     !supportedLayout ? "unsupported-layout" :
                     collision ? "reserved-name-collision" :
                     originals !== 11 ? "source-count-not-eleven" : ""
        if (reason !== "") {
            if (tail >= 0)
                items.remove(tail, 1)
            extensionPresent = false
        } else {
            if (tail < 0) {
                items.insert(items.count, {
                    label: playLabel, labelContext: "X2dMenuExtension",
                    iconSrc: playIcon, itemEnabled: extensionEnabled,
                    menuName: extensionName
                })
            } else {
                if (tail !== items.count - 1)
                    items.move(tail, items.count - 1, 1)
                var data = items.get(items.count - 1).model
                data.label = playLabel
                data.iconSrc = playIcon
                data.itemEnabled = extensionEnabled
            }
            extensionPresent = true
        }
        rejectionReason = reason
        reconciling = false
    }

    items.onChanged: requestReconcile()
    property Connections sourceChanges: Connections {
        target: root.sourceModel
        ignoreUnknownSignals: true
        function onDataChanged() { root.requestReconcile() }
    }
    onSourceModelChanged: requestReconcile()
    onSupportedLayoutChanged: requestReconcile()
    onExtensionEnabledChanged: requestReconcile()
    onPlayLabelChanged: requestReconcile()
    onPlayIconChanged: requestReconcile()
    Component.onCompleted: { ready = true; requestReconcile() }
}

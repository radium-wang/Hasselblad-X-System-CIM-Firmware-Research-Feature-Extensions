/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
import QtQuick
import QtQuick.Window

Item {
    id: root
    objectName: "X2dDoomBootstrap"
    function attach() {
        var window = Window.window
        if (!window || !window.contentItem) return false
        var host = window.contentItem
        for (var i = 0; i < host.children.length; ++i)
            if (host.children[i].objectName === "DoomCameraPage") return true
        var previous = window.activeFocusItem
        var component = Qt.createComponent("file:///tmp/x2d-doom-trial/DoomCameraPage.qml", Component.PreferSynchronous)
        if (component.status !== Component.Ready) {
            console.warn("X2D_DOOM_ATTACH_FAILED", component.errorString()); return false
        }
        var game = component.createObject(host, {
            width: Qt.binding(function() { return host.width }),
            height: Qt.binding(function() { return host.height }),
            ipcRoot: "file:///blackbox/.x2d-doom-trial-stage/ram/",
            returnFocusItem: previous, z: 10000
        })
        if (!game) return false
        game.forceActiveFocus()
        console.log("X2D_DOOM_PAGE_ATTACHED")
        return true
    }
    Timer { interval:50; repeat:true; running:true; onTriggered: if (root.attach()) stop() }
}

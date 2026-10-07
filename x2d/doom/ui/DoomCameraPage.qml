/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
import QtQuick
import QtQuick.Window
import com.hasselblad.proxies
import com.hasselblad.types

DoomPage {
    id: root
    objectName: "DoomCameraPage"
    property var returnFocusItem: null
    // KeyFocusHandler walks the focused item's parents and applies this stock routing option.
    keyOverride: HblmTypes.E_CameraKeyOption_Override
    controlsReady: activeFocus && Camera.forward_input_events === HblmTypes.E_CameraKeyOption_Override
    shutterInputEnabled: controlsReady && !exiting
    function restoreFocus() {
        if (returnFocusItem) returnFocusItem.forceActiveFocus()
        else if (Window.window) Window.window.contentItem.forceActiveFocus()
    }
    onExitingChanged: if (exiting) restoreFocus()
    onVisibleChanged: if (!visible) restoreFocus()
    Component.onCompleted: forceActiveFocus()
}

/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
import QtQuick
import QtQuick.Window

Item {
    id: root
    objectName: "DoomOfflinePage"
    width: 1024; height: 768
    focus: true
    // Explicit caller-owned directory. This component neither starts nor installs an engine.
    property string ipcRoot: ""
    property int frameNumber: -1
    readonly property int imageStatus: screen.status
    property int touchMask: 0
    property bool shutterHeld: false
    property int firePressCount: 0
    property double lookTotal: 0
    property var dragState: ({})
    property bool shutterInputEnabled: false
    property bool controlsReady: true
    property int keyOverride: 0
    readonly property int controlMask: touchMask | (shutterHeld ? 16 : 0)
    property double sequence: Date.now()
    property bool readPending: false
    property bool exiting: false
    property bool displayActive: visible && (!Window.window || Window.window.active)
    property var buttons: [
        {x:90,y:622,w:90,h:60,bit:1,label:"↑"},
        {x:90,y:692,w:90,h:60,bit:2,label:"↓"},
        {x:0,y:692,w:80,h:60,bit:4,label:"←"},
        {x:190,y:692,w:80,h:60,bit:8,label:"→"},
        {x:850,y:622,w:160,h:130,bit:16,label:"FIRE"},
        {x:680,y:692,w:150,h:60,bit:32,label:"USE"},
        {x:380,y:692,w:130,h:60,bit:64,label:"ENTER"},
        {x:520,y:692,w:130,h:60,bit:128,label:"MENU"},
        {x:280,y:692,w:90,h:60,bit:256,label:"STRAFE"},
        {x:680,y:622,w:150,h:60,bit:512,label:"RUN"}
    ]
    function put(name, text) {
        if (!ipcRoot) return
        var r = new XMLHttpRequest()
        r.open("PUT", ipcRoot + name); r.send(text)
    }
    function sendInput() { put("input", (++sequence) + " " + controlMask + " " + firePressCount + " " + lookTotal + " 27182\n") }
    function releaseAll() { touchMask = 0; shutterHeld = false; dragState = ({}); sendInput() }
    function shutterEvent(event, pressed) {
        // The stock X2D 4.2.0 service routes FullPress as Qt Key_E and HalfPress as Key_A.
        if (event.key !== Qt.Key_E && event.key !== Qt.Key_A) return
        event.accepted = true
        if (event.key === Qt.Key_A || event.isAutoRepeat) return
        if (!pressed) { shutterHeld = false; sendInput(); return }
        if (!shutterInputEnabled || !controlsReady || !displayActive || exiting) return
        if (!shutterHeld) { firePressCount++; shutterHeld = true; sendInput() }
    }
    function hit(x, y) {
        if (x >= 930 && y < 64) return -1
        for (var i = 0; i < buttons.length; ++i) {
            var b = buttons[i]
            if (x >= b.x && x < b.x+b.w && y >= b.y && y < b.y+b.h) return b.bit
        }
        return 0
    }
    function updateTouches() {
        var points = [t0,t1,t2,t3,t4], value = 0, next = ({})
        for (var i = 0; i < points.length; ++i) {
            if (!points[i].pressed) continue
            var old = dragState[i]
            var isLook = old ? old.look : (points[i].x >= screen.x && points[i].x < screen.x+screen.width && points[i].y >= screen.y && points[i].y < screen.y+screen.height)
            next[i] = {look:isLook, x:points[i].x}
            if (isLook) {
                if (old && displayActive && controlsReady && !exiting)
                    lookTotal += Math.round(Math.max(-200, Math.min(200, points[i].x-old.x))*5)
                continue
            }
            var bit = hit(points[i].x, points[i].y)
            if (bit === -1) { requestExit(); return }
            value |= bit
        }
        dragState = next
        touchMask = displayActive && controlsReady && !exiting ? value : 0
        sendInput()
    }
    function refresh() {
        if (!ipcRoot || readPending || exiting || !visible) return
        readPending = true
        var r = new XMLHttpRequest()
        r.onreadystatechange = function() {
            if (r.readyState !== XMLHttpRequest.DONE) return
            readPending = false
            try {
                var data = JSON.parse(r.responseText)
                if (data.frame !== frameNumber) {
                    frameNumber = data.frame
                    screen.source = ipcRoot + "frame.bmp?frame=" + frameNumber
                }
            } catch (e) {}
        }
        r.open("GET", ipcRoot + "state.json?request=" + Date.now()); r.send()
    }
    function requestExit() {
        if (exiting) return
        releaseAll(); exiting = true
        put("exit.request", "X2D_DOOM_EXIT\n")
    }
    onDisplayActiveChanged: if (!displayActive) releaseAll()
    onShutterInputEnabledChanged: if (!shutterInputEnabled) { shutterHeld = false; sendInput() }
    onControlsReadyChanged: if (!controlsReady) releaseAll()
    Component.onDestruction: releaseAll()
    Keys.priority: Keys.BeforeItem
    Keys.onPressed: function(event) { root.shutterEvent(event, true) }
    Keys.onReleased: function(event) { root.shutterEvent(event, false) }
    Rectangle { anchors.fill: parent; color: "#101010" }
    Image {
        id: screen
        objectName: "DoomFrame"
        x:112; y:8; width:800; height:600
        fillMode: Image.Stretch // Original 320x200 pixels corrected to 4:3 display.
        cache:false; asynchronous:false; smooth:false
    }
    Repeater {
        model: root.buttons
        Rectangle {
            x:modelData.x; y:modelData.y; width:modelData.w; height:modelData.h
            radius:8; color:root.controlMask & modelData.bit ? "#a45722" : "#303030"
            Text { anchors.centerIn:parent; text:modelData.label; color:"white"; font.pixelSize:22 }
        }
    }
    Rectangle {
        x:930; y:0; width:94; height:64; radius:8; color:"#493232"
        Text {anchors.centerIn:parent; text:"EXIT"; color:"white"; font.pixelSize:22}
    }
    Text {x:290; y:632; text:"DOOM"; color:"#c6c6c6"; font.pixelSize:24}
    Text {x:290; y:663; text:"左右滑动转向"; color:"#c6c6c6"; font.pixelSize:18}
    Text {anchors.centerIn:parent; visible:!root.controlsReady; text:"准备中…"; color:"white"; font.pixelSize:28}
    MultiPointTouchArea {
        anchors.fill:parent; minimumTouchPoints:1; maximumTouchPoints:5
        mouseEnabled:true; enabled:!root.exiting
        touchPoints: [TouchPoint{id:t0},TouchPoint{id:t1},TouchPoint{id:t2},TouchPoint{id:t3},TouchPoint{id:t4}]
        onPressed:root.updateTouches()
        onReleased:root.updateTouches()
        onUpdated:root.updateTouches()
        onCanceled:root.releaseAll()
    }
    Timer {interval:30; repeat:true; running:root.visible&&!root.exiting; onTriggered:root.refresh()}
    Timer {interval:100; repeat:true; running:root.visible&&!root.exiting; onTriggered:root.sendInput()}
}

import QtQuick 2.12

/*
 * Camera-independent source component. The host owns state and connects
 * zoomRequested() to a verified backend/controller adapter. This file imports
 * no vendor module and performs no device or filesystem operation.
 */
Item {
    id: root

    property bool featureEnabled: false
    property bool shooting: false
    property bool interactionEnabled: true
    property real selectedZoom: 1.0
    property real fullFrameEquivalentZoom: 1.27
    property color foregroundColor: "white"
    property color accentColor: "#ffb800"
    property color railColor: "#80000000"

    readonly property real minimumZoom: 1.0
    readonly property real maximumZoom: 2.0
    readonly property var zoomStops: [
        { "label": "1.0", "value": 1.0 },
        { "label": "FF eq.", "value": fullFrameEquivalentZoom },
        { "label": "1.5", "value": 1.5 },
        { "label": "2.0", "value": 2.0 }
    ]

    signal zoomRequested(real zoom)

    visible: featureEnabled && shooting
    implicitWidth: 92
    implicitHeight: 360

    function clampZoom(value) {
        return Math.max(minimumZoom, Math.min(maximumZoom, value))
    }

    function zoomToTrackY(value) {
        var usable = Math.max(1, track.height - handle.height)
        return handle.height / 2 + (maximumZoom - clampZoom(value))
                / (maximumZoom - minimumZoom) * usable
    }

    function requestFromPanelY(y) {
        var usable = Math.max(1, track.height - handle.height)
        var trackY = y - track.y
        var fraction = Math.max(0, Math.min(1, (trackY - handle.height / 2) / usable))
        var value = maximumZoom - fraction * (maximumZoom - minimumZoom)
        zoomRequested(Math.round(value * 100) / 100)
    }

    Rectangle {
        id: panel
        anchors.fill: parent
        radius: width / 2
        color: root.railColor

        Rectangle {
            id: track
            width: 4
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: 30
            anchors.bottomMargin: 30
            anchors.horizontalCenter: parent.horizontalCenter
            radius: 2
            color: "#80ffffff"

            Repeater {
                model: root.zoomStops

                delegate: Item {
                    width: panel.width
                    height: 32
                    x: -width / 2 + track.width / 2
                    y: root.zoomToTrackY(modelData.value) - height / 2

                    Rectangle {
                        width: 14
                        height: 2
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: root.foregroundColor
                    }

                    Text {
                        anchors.left: parent.horizontalCenter
                        anchors.leftMargin: 13
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        color: root.foregroundColor
                        font.pixelSize: 13
                    }

                    MouseArea {
                        anchors.fill: parent
                        enabled: root.interactionEnabled
                        onClicked: root.zoomRequested(root.clampZoom(modelData.value))
                    }
                }
            }
        }

        Rectangle {
            id: handle
            width: 24
            height: 24
            radius: 12
            anchors.horizontalCenter: track.horizontalCenter
            y: track.y + root.zoomToTrackY(root.selectedZoom) - height / 2
            color: root.accentColor
            border.width: 2
            border.color: root.foregroundColor
        }

        MouseArea {
            anchors.fill: track
            anchors.margins: -24
            enabled: root.interactionEnabled
            preventStealing: true
            onPressed: root.requestFromPanelY(mouse.y + y)
            onPositionChanged: {
                if (pressed)
                    root.requestFromPanelY(mouse.y + y)
            }
        }
    }
}

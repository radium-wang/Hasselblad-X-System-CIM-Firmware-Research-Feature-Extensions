// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
Item {
    id: root
    width: 1024; height: 768
    required property string dataRoot
    required property string controlRoot
    required property string assetRoot
    property int menuClicks: 0
    Rectangle { anchors.fill: parent; color: "#345067" }
    MouseArea { anchors.fill: parent; onClicked: root.menuClicks++ }
    Text { x: 30; y: 70; color: "white"; font.pixelSize: 24
        text: "Desktop menu fixture — clicks: " + root.menuClicks }
    PetOverlay {
        anchors.fill: parent
        dataRoot: root.dataRoot; controlRoot: root.controlRoot; assetRoot: root.assetRoot
    }
}

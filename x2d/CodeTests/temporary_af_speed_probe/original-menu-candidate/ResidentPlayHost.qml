import QtQuick

// 常驻页面容器：打开/返回只切换显隐，不执行 shell、对焦、拍照或其他后端操作。
FocusScope {
    id: root
    objectName: "ResidentPlayHost"
    property bool menuActive: false
    property bool mediaProcessing: false
    property bool stockSubmenuActive: false
    property bool playOpen: false
    property var featureController: null
    readonly property alias page: play
    readonly property bool showing: menuActive && playOpen && !stockSubmenuActive
    visible: showing
    enabled: showing
    focus: showing
    signal mainMenuRequested()

    function openPlay() {
        if (!menuActive || mediaProcessing || stockSubmenuActive)
            return false
        playOpen = true
        forceActiveFocus()
        return true
    }
    function dismiss() { playOpen = false }
    function back() {
        if (showing)
            play.requestBack()
    }
    onMenuActiveChanged: { if (!menuActive) dismiss() }
    onStockSubmenuActiveChanged: { if (stockSubmenuActive) dismiss() }
    Keys.onPressed: (event) => {
        if (showing && (event.key === Qt.Key_Escape || event.key === Qt.Key_Back)) {
            back()
            event.accepted = true
        } else {
            event.accepted = false
        }
    }

    PlayPage {
        id: play
        anchors.fill: parent
        pageActive: root.showing
        featureController: root.featureController
        onBackRequested: {
            root.dismiss()
            root.mainMenuRequested()
        }
    }
}

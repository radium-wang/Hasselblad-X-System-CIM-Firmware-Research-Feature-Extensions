import QtQuick
import com.hasselblad.constants
import "qrc:/app/qml/mainmenu" as StockMenu

// 与原厂设置页共用页眉、列表行和开关组件。开关状态来自控制器回读，
// 不能把一次触摸直接视为 AF-C 已经加入对焦模式列表。
FocusScope {
    id: root
    objectName: "PlayPageRoot"
    property bool pageActive: false
    property bool masterEnabled: false
    property var featureController: null
    property bool requestPending: false
    readonly property bool featureLoaded: featureController !== null && featureController.loaded
    readonly property bool featureBusy: featureController !== null && featureController.busy
    readonly property bool backendAvailable: featureController !== null && featureController.ready &&
                                             !featureController.faulted
    readonly property string statusMessage: !masterEnabled ? "耍起功能已关闭" :
                                            featureController === null ? "AF-C 控制器尚未就绪" :
                                            !backendAvailable && !featureLoaded ? "AF-C 条件未满足，暂不可用" :
                                            featureController.statusMessage
    signal backRequested()

    function requestBack() { backRequested() }

    function requestMasterToggle() {
        if (!pageActive || requestPending || featureBusy)
            return false
        if (masterEnabled) {
            // AF-C 当前仍被选中、弹窗未关闭或列表回读失败时，拒绝总开关假关。
            if (featureLoaded && (!featureController || !featureController.setEnabled(false)))
                return false
            masterEnabled = false
        } else {
            masterEnabled = true
        }
        return true
    }

    function requestAfcToggle() {
        if (!pageActive || !masterEnabled || !backendAvailable || featureBusy || requestPending)
            return false
        requestPending = true
        try {
            return featureController.setEnabled(!featureLoaded)
        } catch (error) {
            console.error("X2D_AFC_TOGGLE_EXCEPTION", error)
            return false
        } finally {
            requestPending = false
        }
    }

    Rectangle { anchors.fill: parent; color: Constants.menuBackgroundColor }

    StockMenu.MenuHeader {
        id: header
        objectName: "X2dPlaySettingsHeader"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        showSeparator: !settingsList.atYBeginning
        text: [{ context: "MENUS", text: "耍起功能",
                 color: Constants.settingsMenuHeaderSuffixFontColor }]
        onClose: root.backRequested()
    }

    Flickable {
        id: settingsList
        objectName: "X2dPlaySettingsList"
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
        interactive: root.pageActive && contentHeight > height
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: settingsColumn.height

        Column {
            id: settingsColumn
            width: settingsList.width
            spacing: 0

            Item {
                objectName: "X2dPlayMasterSwitchRow"
                width: parent.width
                height: Constants.menuListItemDefaultHeight
                StockMenu.MenuBoolSelector {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: Constants.settingsMenuSettingLeftMargin
                    anchors.rightMargin: Constants.settingsMenuSettingRightMargin
                    anchors.verticalCenter: parent.verticalCenter
                    text: "耍起功能"
                    value: root.masterEnabled
                    itemEnabled: root.pageActive && !root.featureBusy && !root.requestPending
                    highlighted: masterTouch.pressed
                    showSwitch: true
                    fontWeight: Font.Medium
                }
                MouseArea {
                    id: masterTouch
                    anchors.fill: parent
                    enabled: root.pageActive
                    onClicked: root.requestMasterToggle()
                }
            }

            Rectangle {
                width: parent.width
                height: Constants.menuListDividerHeight
                color: Constants.menuListDividerColor
            }

            Item {
                objectName: "X2dPlayAfcSwitchRow"
                width: parent.width
                height: Constants.menuListItemDefaultHeight
                StockMenu.MenuBoolSelector {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: Constants.settingsMenuSettingLeftMargin
                    anchors.rightMargin: Constants.settingsMenuSettingRightMargin
                    anchors.verticalCenter: parent.verticalCenter
                    text: "开启 AF-C"
                    value: root.featureLoaded
                    itemEnabled: root.pageActive && root.masterEnabled && root.backendAvailable &&
                                 !root.featureBusy && !root.requestPending
                    highlighted: afcTouch.pressed
                    showSwitch: true
                    fontWeight: Font.Medium
                }
                MouseArea {
                    id: afcTouch
                    anchors.fill: parent
                    enabled: root.pageActive && root.masterEnabled && root.backendAvailable
                    onClicked: root.requestAfcToggle()
                }
            }

            Rectangle {
                width: parent.width
                height: Constants.menuListDividerHeight
                color: Constants.menuListDividerColor
            }

            Text {
                objectName: "X2dPlayLoadStatus"
                width: parent.width - 2 * Constants.settingsMenuSettingLeftMargin
                x: Constants.settingsMenuSettingLeftMargin
                topPadding: 24 * Constants.scaleFactorY
                bottomPadding: 24 * Constants.scaleFactorY
                wrapMode: Text.WordWrap
                color: Constants.menuItemColor
                font.family: Constants.settingsMenuSettingSwitchFontName
                font.pixelSize: Constants.settingsMenuSettingSwitchFontSize
                text: root.featureBusy ? "正在切换 AF-C…" : root.statusMessage
            }

            Text {
                width: parent.width - 2 * Constants.settingsMenuSettingLeftMargin
                x: Constants.settingsMenuSettingLeftMargin
                topPadding: 24 * Constants.scaleFactorY
                bottomPadding: 24 * Constants.scaleFactorY
                wrapMode: Text.WordWrap
                color: Constants.menuItemColor
                font.family: Constants.settingsMenuSettingSwitchFontName
                font.pixelSize: Constants.settingsMenuSettingSwitchFontSize
                text: "先开启上方总开关，再开启 AF-C。关闭 AF-C 前请先切回 AF-S 或 MF。"
            }

            Item { width: parent.width; height: Math.max(0, settingsList.height * 0.35) }
        }
    }

    // 仅左缘明显右滑可返回；纵向手势留给原厂风格的可滚动列表。
    MouseArea {
        id: edgeBack
        objectName: "PlayExitGesture"
        z: 2
        anchors.left: parent.left
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        width: Math.min(64, root.width * 0.12)
        enabled: root.pageActive
        property real startX: 0
        property real startY: 0
        onPressed: (mouse) => { startX = mouse.x; startY = mouse.y }
        onReleased: (mouse) => {
            var dx = mouse.x - startX
            var dy = mouse.y - startY
            if (dx >= Math.max(60, root.width * 0.12) && Math.abs(dy) < root.height * 0.15)
                root.backRequested()
        }
    }

    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Escape || event.key === Qt.Key_Back) {
            root.backRequested()
            event.accepted = true
        } else if (event.key === Qt.Key_Up) {
            settingsList.contentY = Math.max(0, settingsList.contentY - 80)
            event.accepted = true
        } else if (event.key === Qt.Key_Down) {
            settingsList.contentY = Math.min(Math.max(0, settingsList.contentHeight - settingsList.height),
                                             settingsList.contentY + 80)
            event.accepted = true
        } else {
            event.accepted = false
        }
    }
}

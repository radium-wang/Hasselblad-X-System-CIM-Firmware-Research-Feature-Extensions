import QtQuick
import com.hasselblad.constants
import "qrc:/app/qml/mainmenu" as StockMenu

// Offline page candidate. The controller owns the actual feature state;
// this page does not perform I/O or treat a tap as a successful load.
FocusScope {
    id: root
    objectName: "X2dPlaySettingsPage"
    focus: true

    property bool pageActive: false
    property var featureController: null
    readonly property bool backendAvailable: featureController !== null && !featureController.faulted &&
                                             (featureController.ready || featureController.loaded)
    readonly property bool featureLoaded: featureController !== null && featureController.loaded
    readonly property bool featureBusy: featureController !== null && featureController.busy
    property bool requestPending: false
    readonly property string statusMessage: featureController !== null ?
                                                featureController.statusMessage :
                                                "尚未接入运行时加载器"

    signal backRequested()

    function requestBack() { backRequested() }

    function requestToggle() {
        if (!pageActive || !backendAvailable || featureBusy || requestPending)
            return false
        requestPending = true
        try {
            return featureController.setEnabled(!featureLoaded)
        } catch (error) {
            console.error("X2D_FEATURE_TOGGLE_EXCEPTION", error)
            return false
        } finally {
            requestPending = false
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Constants.menuBackgroundColor
    }

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
                id: masterRow
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
                    value: root.featureLoaded
                    itemEnabled: root.backendAvailable && !root.featureBusy && !root.requestPending
                    highlighted: toggleTouch.pressed
                    showSwitch: true
                    fontWeight: Font.Medium
                }
                MouseArea {
                    id: toggleTouch
                    objectName: "X2dPlayMasterSwitchTouch"
                    anchors.fill: parent
                    enabled: root.pageActive
                    onClicked: root.requestToggle()
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
                text: root.featureBusy ? "正在切换功能…" : root.statusMessage
            }

            Rectangle {
                width: parent.width
                height: Constants.menuListDividerHeight
                color: Constants.menuListDividerColor
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
                text: "首项功能：AF-C 对焦模式菜单扩展。仅当加载器确认生效后，上方开关才显示为开启。"
            }
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

import QtQuick
import com.hasselblad.keys
import "qrc:/app/qml/scripts/Keys.js" as MKeys

// 由 MainScreen 中新增的 Loader 创建，稍后挂到原厂 ControlDrawer。
Item {
    id: root
    objectName: "X2dNativeMenuExtension"
    anchors.fill: parent
    z: 20
    visible: route.playShowing
    enabled: visible
    property var screen: null
    property var drawer: null
    property var menu: null
    property var grid: null
    property var originalModel: null
    property Component originalDelegate: null
    property var originalLoader: null
    property var originalSwipe: null
    property var drawerList: null
    property var playButton: null
    property bool attached: false
    readonly property bool menuActive: attached && drawer.mainState === "main_menu"
                                      && drawer.mainViewState === "main_menu" && !drawer.drawerAtTop

    function findItem(item, name) {
        if (!item) return null
        if (item.objectName === name) return item
        for (var i = 0; i < item.children.length; ++i) {
            var result = findItem(item.children[i], name)
            if (result) return result
        }
        return null
    }
    function attach() {
        if (attached || !screen || !screen.mainMenu || !screen.viewModel) return
        menu = screen.mainMenu
        drawer = menu.parent
        if (!drawer || drawer.objectName !== "ControlDrawer_root") return
        grid = findItem(screen, "MainScreen_grid")
        originalLoader = findItem(menu, "menu_loader")
        originalSwipe = findItem(menu, "MainMenu_swipeArea")
        drawerList = findItem(drawer, "ControlDrawer_list")
        if (!grid || !originalLoader || !originalSwipe || !drawerList) return
        // ControlDrawer.onLoaded 原文把信号接到这个具名函数；不能仅旁听。
        try { screen.loadSubMenuItem.disconnect(menu.loadSubmenu) }
        catch (error) { console.warn("X2D_NATIVE_MENU_ROUTE_NOT_READY"); return }
        originalModel = screen.viewModel.favoriteModel
        adapter.sourceModel = originalModel
        originalDelegate = grid.delegate
        adapter.stockDelegate = originalDelegate
        screen.loadSubMenuItem.connect(dispatch)
        screen.viewModel.favoriteModel = adapter
        parent = drawer
        attached = true
        screen.viewModel.inMenu = Qt.binding(function() { return originalLoader.active || route.playShowing })
        screen.viewModel.preventSwipe = Qt.binding(function() { return originalSwipe.preventSwipe || route.playShowing })
        drawerList.interactive = Qt.binding(function() { return !drawerList.blockSwipe && !route.playShowing })
        console.info("X2D_NATIVE_MENU_ATTACHED")
    }
    function dispatch(name, sub, open, shortcut) { route.dispatch(name, sub, open, shortcut) }
    function refreshPlayButton() {
        playButton = attached && adapter.extensionPresent && grid.count === 12
                    ? findItem(grid.itemAtIndex(11), "FramedItem_root") : null
    }
    function detach() {
        if (!attached) return
        route.dismiss()
        screen.loadSubMenuItem.disconnect(dispatch)
        screen.loadSubMenuItem.connect(menu.loadSubmenu)
        screen.viewModel.favoriteModel = originalModel
        grid.delegate = originalDelegate
        screen.viewModel.inMenu = Qt.binding(function() { return originalLoader.active })
        screen.viewModel.preventSwipe = Qt.binding(function() { return originalSwipe.preventSwipe })
        drawerList.interactive = Qt.binding(function() { return !drawerList.blockSwipe })
        attached = false
        playButton = null
    }
    PlayMenuModel {
        id: adapter
        supportedLayout: root.screen !== null && !root.screen.viewModel.sparseFavoritesGrid
        playLabel: "耍起功能"
        playIcon: "file:///system/etc/X2dPlayIcon.svg"
        onExtensionPresentChanged: Qt.callLater(root.refreshPlayButton)
    }
    // 未解析的扩展项没有源模型 index。原厂 onPressed 使用该值会恢复旧高亮；
    // 在同次 pressed 信号内用实际显示位置纠正，保留原厂按钮和高亮计时逻辑。
    Connections {
        target: root.playButton
        function onPressed() {
            if (root.attached && adapter.extensionPresent && root.playButton.selectable)
                root.grid.highlightIndex(11)
        }
    }
    Connections {
        target: root.grid
        function onCountChanged() { Qt.callLater(root.refreshPlayButton) }
    }
    Connections {
        target: root.grid ? root.grid.contentItem : null
        function onChildrenChanged() { Qt.callLater(root.refreshPlayButton) }
    }
    // 消费页面空白处触摸；半按等未处理按键继续交给原厂。
    MouseArea { anchors.fill: parent; onPressed: (mouse) => { mouse.accepted = true } }
    AfcMenuController {
        id: afcController
        controlViewModel: root.drawer ? root.drawer.controlScreenViewModel : null
        focusPopoverOpen: root.drawer !== null && root.drawer.mainState === "focus_mode"
    }
    PlayMenuRoute {
        id: route
        anchors.fill: parent
        menuActive: root.menuActive
        mediaProcessing: root.screen !== null && root.screen.viewModel.mediaProcessing
        stockSubmenuActive: root.menu !== null && root.menu.state === "menu"
        featureController: afcController
        onStockRequested: (name, sub, open, shortcut) => root.menu.loadSubmenu(name, sub, open, shortcut)
        onMainMenuRequested: { if (root.menuActive) root.screen.forceActiveFocus() }
    }
    Connections {
        target: root.drawer
        function onMainMenuExited() { route.dismiss() }
    }
    Connections {
        target: root.screen ? root.screen.viewModel : null
        function onCloseMenu() { route.dismiss() }
    }
    Keys.onPressed: (event) => {
        if (route.playShowing && MKeys.pressedFnListAcc([KeyFn.Escape, KeyFn.JstkEscape, KeyFn.Menu], event))
            route.back()
        else if (route.playShowing && MKeys.pressedFnListAcc([KeyFn.NavKey, KeyFn.Square, KeyFn.Cross], event)) {}
        else event.accepted = false
    }
    Component.onCompleted: {
        screen = parent ? parent.parent : null
        Qt.callLater(attach)
    }
    Component.onDestruction: detach()
}

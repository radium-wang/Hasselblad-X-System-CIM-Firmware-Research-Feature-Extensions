"""原厂 MainScreen/网格/按钮原文的桌面行为验证；机身服务和图像提供器为替身。"""
import hashlib
import json
import sys
from pathlib import Path

# 复用已锁定 Python/Qt 的离线运行环境和无设备源模型。
from check_flash_menu_model import (
    D, SourceModel, ORDER, QGuiApplication, QQmlApplicationEngine, QTest,
    QUrl, Qt, QPoint, QQuickItem, getCppPointer, qVersion)

F = D / '.stock-host'


def write(relative, contents):
    path = F / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding='utf-8')


def main():
    manifest = json.loads((F / 'manifest.json').read_text())
    for name, digest in manifest['unmodifiedResources'].items():
        assert hashlib.sha256((F / 'qml' / name).read_bytes()).hexdigest() == digest
    # 明确替身边界：无真实机身服务、无实际硬件键码、无图像着色器。
    write('qml/common/qmldir', '')
    write('imports/com/hasselblad/favoritemodel/qmldir', 'module com.hasselblad.favoritemodel\nUnused 1.0 Unused.qml\n')
    write('imports/com/hasselblad/favoritemodel/Unused.qml', 'import QtQuick\nQtObject {}')
    write('imports/com/hasselblad/constants/qmldir',
          'module com.hasselblad.constants\nsingleton Constants 1.0 Constants.qml\n')
    write('imports/com/hasselblad/constants/Constants.qml', '''pragma Singleton
import QtQuick
QtObject {
 property real scaleFactor: 1
 property real scaleFactorX: 1
 property real scaleFactorY: 1
 property color mainBackgroundColor: "black"
 property color popupTextColor: "white"
 property color colorWhite: "white"
 property color highlightColor: "red"
 property string menuItemFontName: "Arial"
 property int wheelTimeoutTimeMs: 3000
}''')
    write('imports/com/hasselblad/keys/qmldir',
          'module com.hasselblad.keys\nsingleton KeyFn 1.0 KeyFn.qml\n')
    write('imports/com/hasselblad/keys/KeyFn.qml', '''pragma Singleton
import QtQuick
QtObject {
 enum Function { Square, Afd, Select, NavKey, Cross, JstkUp, JstkDown, Left, Up, Right, Down, Escape, JstkEscape, Menu }
 function isFn(key, modifiers, fn) {
   var keys = [Qt.Key_F1,Qt.Key_F2,Qt.Key_Return,Qt.Key_F3,Qt.Key_Escape,
               Qt.Key_Up,Qt.Key_Down,Qt.Key_Left,Qt.Key_PageUp,Qt.Key_Right,Qt.Key_PageDown,Qt.Key_Escape,Qt.Key_Back,Qt.Key_Menu]
   return key === keys[fn]
 }
}''')
    write('qml/mainmenu/MainMenuViewModel.qml', '''import QtQuick
Item { property var favoriteModel: null; property bool sparseFavoritesGrid: false
       property bool screenEVF: false }''')
    write('qml/mainmenu/MainMenu.qml', 'import QtQuick\nItem {}')
    write('qml/components/UiImage.qml', '''import QtQuick
Item {
 property url source
 property size sourceSize: Qt.size(160,160)
 property bool asynchronous: true
 property int fillMode: Image.PreserveAspectFit
 width: 160; height: 100
}''')
    app = QGuiApplication([])
    cache = None
    if '--cached-bootstrap' in sys.argv:
        from host_cached_unit import HostCache
        write('Bootstrap.qml', 'import QtQuick\nItem { objectName: "BootstrapProof" }')
        cache = HostCache(D / 'main-screen-bootstrap-host.bin')
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(F / 'imports'))
    source = SourceModel()
    engine.rootContext().setContextProperty('stockSource', source)
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend(str(w) for w in ws))
    engine.loadData(b'''import QtQuick
import QtQuick.Window
import ".stock-host/qml/mainmenu" as Stock
Window {
 id: window; width: 1024; height: 768; visible: false
 property var clicks: []
 property alias showing: route.playShowing
 property alias evf: vm.screenEVF
 property alias sparse: vm.sparseFavoritesGrid
 property alias stockState: menu.state
 property var grid: null
 function findGrid(item) {
   if (item.objectName === "MainScreen_grid") return item
   for (var i=0; i<item.children.length; ++i) {
     var result = findGrid(item.children[i]); if (result) return result
   }
   return null
 }
 function attach() {
   grid = findGrid(screen)
   adapter.stockDelegate = grid.delegate
   vm.favoriteModel = adapter
 }
 function clickPoint(ix) {
   var item = grid.itemAtIndex(ix)
   var p = item.mapToItem(contentItem, item.width/2, 40)
   return JSON.stringify({x:p.x,y:p.y})
 }
 function select(ix) { grid.highlightIndex(ix); screen.forceActiveFocus() }
 function navRight() { grid.moveRight() }
 function index() { return grid.currentIndex }
 function count() { return grid.count }
 Stock.MainMenuViewModel { id: vm; favoriteModel: stockSource }
 Stock.MainMenu { id: menu }
 PlayMenuModel {
   id: adapter; sourceModel: stockSource; supportedLayout: !vm.sparseFavoritesGrid
 }
 Stock.MainScreen {
   id: screen; anchors.fill: parent; viewModel: vm; mainMenu: menu
   visible: !route.playShowing
   onLoadSubMenuItem: (name, sub, open, shortcut) => route.dispatch(name, sub, open, shortcut)
 }
 PlayMenuRoute {
   id: route; anchors.fill: parent; menuActive: true
   onStockRequested: (name, sub, open, shortcut) => window.clicks.push(name)
   onMainMenuRequested: screen.forceActiveFocus()
 }
}''', QUrl.fromLocalFile(str(D / 'stock-grid-test.qml')))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    window.setVisible(True)
    QTest.qWait(80)
    window.attach()
    QTest.qWait(80)
    assert window.count() == 12, warnings
    if cache is not None:
        assert cache.hits > 0
        assert window.findChild(QQuickItem, 'BootstrapProof') is not None, warnings

    def click(ix):
        p = json.loads(window.clickPoint(ix))
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(round(p['x']),round(p['y'])))
        QTest.qWait(20)

    for ix in range(11):
        click(ix)
    assert window.property('clicks').toVariant() == ORDER
    page = window.findChild(QQuickItem, 'PlayPageRoot')
    address = getCppPointer(page)[0]
    click(11)
    assert window.property('showing'), warnings
    QTest.keyClick(window, Qt.Key_Escape)
    QTest.qWait(20)
    assert not window.property('showing')
    # 实际原厂 delegate 键盘点击，不只调用替身路由。
    window.select(11)
    QTest.keyClick(window, Qt.Key_Return)
    assert window.property('showing'), warnings
    QTest.keyClick(window, Qt.Key_Escape)
    source.change(10, itemEnabled=False)
    QTest.qWait(20)
    window.select(9)
    window.navRight()
    assert window.index() == 11
    window.setProperty('evf', True)
    click(11)
    assert not window.property('showing')
    window.setProperty('evf', False)
    window.setProperty('stockState', 'menu')
    click(11)
    assert not window.property('showing')
    window.setProperty('stockState', '')
    for _ in range(20):
        click(11)
        assert window.property('showing')
        QTest.keyClick(window, Qt.Key_Escape)
        assert not window.property('showing')
        assert getCppPointer(page)[0] == address
    window.setProperty('sparse', True)
    QTest.qWait(20)
    assert window.count() == 11
    assert source.rowCount() == 11
    assert not warnings, warnings
    result = dict(result='PASS', firmware='4.2.0', qt=qVersion(),
                  compiledBootstrapLoaded=cache is not None,
                  unmodifiedStockResources=manifest['unmodifiedResources'],
                  stockDelegateMouseAndKeyboard=True, originalRoutesPreserved=True,
                  disabledNavigationAndEvfTouchRespected=True,
                  stockDoubleClickGateRespected=True, samePageAfter20Returns=True,
                  cameraAccesses=0, deployed=False,
                  limitations=['Native FavoriteModel, MainMenu state and key mapping are host substitutes.',
                               'UiImage is a geometry stub; this is not visual or performance validation.',
                               'Stock-process attachment, compiled-cache integration and persistence remain unimplemented.'])
    (D / 'stock-grid-validation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()

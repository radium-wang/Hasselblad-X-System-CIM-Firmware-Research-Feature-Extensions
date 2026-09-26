"""执行真实编译单元 Loader 和 Bootstrap；原厂服务/外层状态仍为替身。"""
import json
from check_flash_menu_model import *
from check_stock_grid import F, write
from host_cached_unit import HostCache


def main():
    # 先运行 check_stock_grid 生成并验证原厂资源与模块替身。
    assert (F/'manifest.json').exists()
    for name in ('PlayMenuModel.qml', 'PlayMenuRoute.qml', 'ResidentPlayHost.qml', 'PlayPage.qml', 'Bootstrap.qml'):
        text = (D/name).read_text(encoding='utf-8')
        if name == 'Bootstrap.qml':
            text = text.replace('qrc:/app/qml/scripts/Keys.js', (F/'qml/scripts/Keys.js').as_uri())
        write(name, text)
    if '--packaged' in sys.argv:
        manifest=json.loads((D/'native-package/package.json').read_text())
        for entry in manifest['files']:
            if not entry['source'].endswith('.qml'): continue
            content=(D/'native-package'/entry['source']).read_text(encoding='utf-8')
            content=content.replace('qrc:/app/qml/scripts/Keys.js',(F/'qml/scripts/Keys.js').as_uri())
            write(entry['source'],content)
            if entry['source']=='X2dNativeMenuBootstrap.qml': write('Bootstrap.qml',content)
    write('qml/mainmenu/MainMenuViewModel.qml', '''import QtQuick
Item { property var favoriteModel: null; property bool sparseFavoritesGrid: false
       property bool screenEVF: false; property bool mediaProcessing: false
       property bool inMenu: false; property bool preventSwipe: false
       signal closeMenu() }''')
    write('qml/mainmenu/MainMenu.qml', '''import QtQuick
Item { signal stockRequested(string name)
       function loadSubmenu(name, sub, open, shortcut) { stockRequested(name) }
       Item { objectName: "menu_loader"; property bool active: false }
       Item { objectName: "MainMenu_swipeArea"; property bool preventSwipe: false } }''')
    app = QGuiApplication([])
    cache = HostCache(D/'main-screen-bootstrap-host.bin')
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(F/'imports'))
    source = SourceModel()
    engine.rootContext().setContextProperty('stockSource', source)
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend(str(w) for w in ws))
    engine.loadData(b'''import QtQuick
import QtQuick.Window
import ".stock-host/qml/mainmenu" as Stock
Window {
 id: window; width:1024; height:768; visible:true
 property var clicks: []
 property alias inMenu: vm.inMenu
 property alias swipeBlocked: vm.preventSwipe
 property alias mainState: drawer.mainState
 property alias mediaBusy: vm.mediaProcessing
 property alias listInteractive: list.interactive
 function exitMenu() { drawer.mainMenuExited() }
 function closeMenu() { vm.closeMenu() }
 Item {
   id: drawer; objectName: "ControlDrawer_root"; anchors.fill: parent
   property string mainState: "main_menu"
   property string mainViewState: "main_menu"
   property bool drawerAtTop: false
   signal mainMenuExited()
   Item { id:list; objectName:"ControlDrawer_list"; property bool blockSwipe:false; property bool interactive:true }
   Stock.MainMenuViewModel { id:vm; favoriteModel:stockSource }
   Stock.MainMenu { id:menu; onStockRequested: (name)=>window.clicks.push(name) }
   Stock.MainScreen {
     id:screen; anchors.fill:parent; viewModel:vm; mainMenu:menu
     Component.onCompleted: loadSubMenuItem.connect(menu.loadSubmenu)
   }
 }
}''', QUrl.fromLocalFile(str(D/'bootstrap-attach-test.qml')))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    QTest.qWait(150)
    extension = window.findChild(QQuickItem, 'X2dNativeMenuExtension')
    assert extension is not None and extension.property('attached'), warnings
    grid = window.findChild(QQuickItem,'MainScreen_grid')
    assert grid.property('count') == 12
    page = window.findChild(QQuickItem,'PlayPageRoot')
    address = getCppPointer(page)[0]

    def click(index):
        # 原厂固定三行四列的 cell 中心，上方图标区。
        x = grid.x() + (index%4+.5)*grid.property('cellWidth')
        y = grid.y() + (index//4)*grid.property('cellHeight') + 40
        point=QPoint(round(x),round(y))
        QTest.mousePress(window,Qt.LeftButton,Qt.NoModifier,point)
        QTest.qWait(1)
        if not extension.isVisible() and not window.property('mediaBusy'):
            assert grid.property('currentIndex') == index, ('pressed highlight',index,grid.property('currentIndex'))
        QTest.mouseRelease(window,Qt.LeftButton,Qt.NoModifier,point)
        QTest.qWait(10)

    for i in range(11): click(i)
    assert window.property('clicks').toVariant() == ORDER
    assert not window.property('inMenu')
    for i in range(30):
        click(11)
        assert extension.isVisible() and window.property('inMenu')
        assert window.property('swipeBlocked') and not window.property('listInteractive')
        if i%3 == 0: QTest.keyClick(window, Qt.Key_Escape)
        elif i%3 == 1: window.closeMenu()
        else: window.exitMenu()
        QTest.qWait(10)
        assert not extension.isVisible() and not window.property('inMenu')
        assert not window.property('swipeBlocked') and window.property('listInteractive')
        assert getCppPointer(page)[0] == address
    click(11)
    window.setProperty('mainState', 'liveview')
    assert not extension.isVisible()
    window.setProperty('mainState','main_menu')
    assert not extension.isVisible()
    window.setProperty('mediaBusy',True)
    click(11)
    assert not extension.isVisible()
    window.setProperty('mediaBusy',False)
    assert window.property('clicks').toVariant() == ORDER, 'extension leaked to stock route'
    extension.detach()
    QTest.qWait(20)
    assert grid.property('count') == 11, (grid.property('count'), source.rowCount(), extension.property('attached'), warnings)
    click(0)
    assert window.property('clicks').toVariant() == ORDER+[ORDER[0]]
    assert not warnings, warnings
    result=dict(result='PASS', compiledBootstrapLoaded=True, packagedFiles='--packaged' in sys.argv, extensionAutomaticallyAttached=True,
                stockSignalDisconnectedAndRestored=True, originalClicksOnce=True,
                extensionNotSentToStockRoute=True, stateAndSwipeBindings=True,
                samePageAfter30Returns=True, pressedHighlightMatchesEachItem=True,
                deviceValidated=False, cameraAccesses=0,
                limitation='Qt desktop only; outer stock state/services and graphics are substitutes.')
    (D/'bootstrap-attach-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__': main()

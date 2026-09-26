"""Qt 6.4.1 下实际执行模型与路由候选；源模型为替身，不访问设备。"""
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
if sys.version_info[:2] != (3, 11):
    raise SystemExit('Use py -3.11 -B')
D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path.insert(0, str(ROOT / 'x2d/outputs/4.2.0/temporary-wifi-button/qt-runtime'))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_QUICK_BACKEND'] = 'software'
os.environ['QML_DISABLE_DISK_CACHE'] = '1'
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot, QUrl, QPoint, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from shiboken6 import getCppPointer

ROLE_NAMES = ['label', 'labelContext', 'iconSrc', 'itemEnabled', 'menuName']
ORDER = ['exposureMenu', 'focusMenu', 'qualityMenu', 'cropModesMenu', 'flashMenu',
         'displayMenu', 'powerMenu', 'storageMenu', 'ibisMenu', 'wifiMenu', 'generalMenu']


class SourceModel(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.rows = [dict(label=k, labelContext='Test', iconSrc=k,
                          itemEnabled=True, menuName=k) for k in ORDER]

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def roleNames(self):
        return {int(Qt.UserRole) + 1 + i: n.encode() for i, n in enumerate(ROLE_NAMES)}

    def data(self, index, role):
        name = self.roleNames().get(role)
        if name and index.isValid() and index.row() < len(self.rows):
            return self.rows[index.row()][name.decode()]
        return None

    @Slot(int, result=bool)
    def itemEnabled(self, ix):
        return 0 <= ix < len(self.rows) and self.rows[ix]['itemEnabled']

    def change(self, row, **values):
        self.rows[row].update(values)
        roles = [r for r, n in self.roleNames().items() if n.decode() in values]
        self.dataChanged.emit(self.index(row), self.index(row), roles)

    def resize(self, count):
        self.beginResetModel()
        self.rows = [dict(label=k, labelContext='Test', iconSrc=k, itemEnabled=True,
                          menuName=k) for k in (ORDER + ['extra'])[:count]]
        self.endResetModel()


def main():
    app = QGuiApplication([])
    source = SourceModel()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('stockSource', source)
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend(str(w) for w in ws))
    qml = '''import QtQuick
import QtQuick.Window
Window {
    id: window; width: 1024; height: 768; visible: false
    property bool menuActive: true
    property bool mediaBusy: false
    property bool stockOpen: false
    property bool supported: true
    property bool playEnabled: true
    property var clicks: []
    property int blockedCount: 0
    property int returnedCount: 0
    property alias modelCount: grid.count
    property alias hasExtension: adapter.extensionPresent
    property alias playShowing: route.playShowing
    property alias rejection: adapter.rejectionReason
    function summary() {
        var result = []
        for (var i=0; i<adapter.items.count; ++i) {
            var entry = adapter.items.get(i)
            result.push({name: entry.model.menuName, label: entry.model.label,
                         enabled: entry.model.itemEnabled, selectable: adapter.itemEnabled(i)})
        }
        return JSON.stringify(result)
    }
    function go(name, sub, open, shortcut) { return route.dispatch(name, sub, open, shortcut) }
    function back() { route.back() }
    PlayMenuModel {
        id: adapter; sourceModel: stockSource
        supportedLayout: window.supported; extensionEnabled: window.playEnabled
        stockDelegate: Component {
            Rectangle {
                objectName: "entry_" + model.menuName
                width: 256; height: 256; color: "black"
                property string roleLabel: model.label
                Text { anchors.centerIn: parent; text: model.label; color: "white" }
                MouseArea {
                    anchors.fill: parent; enabled: model.itemEnabled
                    onClicked: route.dispatch(model.menuName, "", false, false)
                }
            }
        }
    }
    GridView { id: grid; anchors.fill: parent; cellWidth: 256; cellHeight: 256
               model: adapter; visible: !route.playShowing; interactive: false }
    PlayMenuRoute {
        id: route; anchors.fill: parent
        menuActive: window.menuActive; mediaProcessing: window.mediaBusy
        stockSubmenuActive: window.stockOpen
        onStockRequested: (name, sub, open, shortcut) => {
            window.clicks.push({name: name, sub: sub, open: open, shortcut: shortcut})
        }
        onBlocked: window.blockedCount++
        onMainMenuRequested: window.returnedCount++
    }
}'''
    engine.loadData(qml.encode(), QUrl.fromLocalFile(str(D / 'model-test.qml')))
    assert engine.rootObjects(), warnings
    window = engine.rootObjects()[0]
    window.setVisible(True)
    QTest.qWait(100)

    def rows():
        return json.loads(window.summary())

    def settle():
        QTest.qWait(15)

    assert window.property('modelCount') == 12, (window.property('modelCount'), warnings)
    assert [r['name'] for r in rows()[:11]] == ORDER
    assert rows()[11]['name'] == 'x2dPlayUi'
    assert rows()[11]['label'] == '耍起功能'
    assert source.rowCount() == 11
    assert all(r['enabled'] and r['selectable'] for r in rows())
    assert not window.property('playShowing')
    for k in ORDER:
        assert window.go(k, 'child', True, True) is False
    clicks = window.property('clicks').toVariant()
    assert [x['name'] for x in clicks] == ORDER
    assert all(x['sub'] == 'child' and x['open'] and x['shortcut'] for x in clicks)

    source.change(2, label='changed', itemEnabled=False)
    settle()
    assert rows()[2] == dict(name=ORDER[2], label='changed', enabled=False, selectable=False)
    for count in (10, 12, 11):
        source.resize(count)
        settle()
        assert window.property('modelCount') == (12 if count == 11 else count)
        assert window.property('hasExtension') == (count == 11)
    window.setProperty('supported', False)
    settle()
    assert window.property('modelCount') == 11
    window.setProperty('supported', True)
    settle()
    assert window.property('modelCount') == 12
    source.change(0, menuName='x2dPlayUi')
    settle()
    assert window.property('modelCount') == 11
    assert window.property('rejection') == 'reserved-name-collision'
    source.change(0, menuName=ORDER[0])
    settle()
    assert window.property('modelCount') == 12
    window.setProperty('playEnabled', False)
    settle()
    assert not rows()[11]['enabled'] and not rows()[11]['selectable']
    window.setProperty('playEnabled', True)
    settle()

    page = window.findChild(QQuickItem, 'PlayPageRoot')
    assert page is not None
    address = getCppPointer(page)[0]
    window.setProperty('mediaBusy', True)
    assert window.go('x2dPlayUi', '', False, False) is True
    assert not window.property('playShowing')
    window.setProperty('mediaBusy', False)

    # 使用实际 Qt 鼠标事件点击最后一格，验证数据到 delegate 再到路由。
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(896, 640))
    settle()
    assert window.property('playShowing')
    assert len(window.property('clicks').toVariant()) == 11
    QTest.keyClick(window, Qt.Key_Escape)
    assert not window.property('playShowing')
    for _ in range(100):
        window.go('x2dPlayUi', '', False, False)
        assert window.property('playShowing')
        window.back()
        assert not window.property('playShowing')
        assert getCppPointer(page)[0] == address
    window.go('x2dPlayUi', '', False, False)
    window.setProperty('menuActive', False)
    assert not window.property('playShowing')
    window.setProperty('menuActive', True)
    assert not window.property('playShowing')
    assert not warnings, warnings
    report = dict(result='PASS', qt=qVersion(), originalRows=11, displayedRows=12,
                  sourceUnmodified=True, sourceRoleChangesPropagate=True,
                  roleChangeCollisionSuppressesExtension=True,
                  unsupportedCountsSuppressExtension=True, originalRoutesPreserved=True,
                  playLabelAndRoute=True, actualMouseClick=True, actualEscape=True, samePageAfter100Returns=True,
                  cameraAccesses=0, deployed=False,
                  limitation='Source model and grid are desktop substitutes; stock process injection and state bridging are not implemented.')
    (D / 'model-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()

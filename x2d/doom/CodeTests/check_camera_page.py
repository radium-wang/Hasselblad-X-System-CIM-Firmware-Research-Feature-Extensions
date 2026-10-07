#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Offline Qt 6.4.1 camera page routing/focus checks with explicit service mocks."""
import argparse, json, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / "ui"

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    os.environ.update(QT_QPA_PLATFORM='offscreen',QML_XHR_ALLOW_FILE_READ='1',QML_XHR_ALLOW_FILE_WRITE='1')
    from PySide6.QtCore import QUrl, Qt, qVersion
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickItem
    from PySide6.QtTest import QTest
    assert qVersion()=='6.4.1'
    for module,typ,body in [('proxies','Camera','property int forward_input_events: 0'),('types','HblmTypes','enum CameraKeyOption { E_CameraKeyOption_Override = 3 }')]:
        d=out/'imports/com/hasselblad'/module;d.mkdir(parents=True,exist_ok=True)
        (d/'qmldir').write_text(f'module com.hasselblad.{module}\nsingleton {typ} 1.0 {typ}.qml\n')
        (d/(typ+'.qml')).write_text('pragma Singleton\nimport QtQml\nQtObject {'+body+'}\n')
    for n in ['DoomPage.qml','DoomCameraPage.qml']:(out/n).write_bytes((ROOT/n).read_bytes())
    boot=(ROOT/'Bootstrap.qml').read_text().replace('file:///tmp/x2d-doom-trial/DoomCameraPage.qml',QUrl.fromLocalFile(str(out/'DoomCameraPage.qml')).toString()).replace('file:///blackbox/.x2d-doom-trial-stage/ram/',QUrl.fromLocalFile(str(out)+'/').toString())
    (out/'Bootstrap.qml').write_text(boot)
    app=QGuiApplication([]);engine=QQmlApplicationEngine();engine.addImportPath(str(out/'imports'));errors=[]
    engine.warnings.connect(lambda es:errors.extend(e.toString() for e in es))
    engine.loadData(b'''import QtQuick
import QtQuick.Window
import com.hasselblad.proxies
Window { id:w; width:1024;height:768;visible:true
 Item {id:prior;objectName:"PriorFocus";focus:true;anchors.fill:parent}
 Loader {id:boot;active:false;source:"Bootstrap.qml"}
 function begin() {prior.forceActiveFocus();boot.active=true}
 function route(v) {Camera.forward_input_events=v}
 function repeatAttach() {boot.item.attach()}
}''',QUrl.fromLocalFile(str(out/'Harness.qml')))
    assert engine.rootObjects(),errors
    w=engine.rootObjects()[0];w.requestActivate();QTest.qWait(50);w.begin();QTest.qWait(250)
    game=w.findChild(QQuickItem,'DoomCameraPage');prior=w.findChild(QQuickItem,'PriorFocus')
    assert game is not None and game.hasActiveFocus(),errors
    assert game.property('keyOverride')==3 and not game.property('controlsReady')
    QTest.keyClick(w,Qt.Key_E);QTest.qWait(20);assert game.property('firePressCount')==0
    w.route(3);QTest.qWait(20);assert game.property('controlsReady') and game.property('shutterInputEnabled')
    QTest.keyClick(w,Qt.Key_A);assert game.property('firePressCount')==0
    QTest.keyPress(w,Qt.Key_E);assert game.property('shutterHeld') and game.property('firePressCount')==1
    w.route(0);QTest.qWait(20);assert not game.property('shutterHeld') and game.property('controlMask')==0
    QTest.keyRelease(w,Qt.Key_E);w.route(3);QTest.qWait(20)
    w.repeatAttach();QTest.qWait(160)
    assert len([c for c in w.contentItem().childItems() if c.objectName()=='DoomCameraPage'])==1
    game.requestExit();QTest.qWait(60)
    assert prior.hasActiveFocus() and (out/'exit.request').exists(), (w.activeFocusItem().objectName(),str(game.property('returnFocusItem')),(out/'exit.request').exists())
    assert not game.property('controlsReady') and not game.property('shutterHeld')
    report=dict(level='host/service mocks',qt=qVersion(),deviceAccess=False,routingAckRequired=True,
        halfPressIgnored=True,routingLossReleases=True,exitRestoresFocus=True,singleOverlay=True,qmlWarnings=errors)
    assert not errors,errors
    (out/'checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));w.close()
if __name__=='__main__':main()

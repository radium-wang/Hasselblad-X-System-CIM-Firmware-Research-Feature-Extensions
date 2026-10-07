#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Real host Doom + Qt 6.4.1 file bridge checks; never connect to a camera."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1] / "ui"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine', type=Path, required=True)
    p.add_argument('--wad', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--audio-sink', type=Path, required=True)
    a = p.parse_args()
    engine = a.engine.resolve(); wad = a.wad.resolve(); out = a.out.resolve()
    metadata = json.loads(engine.with_name(engine.name + '.json').read_text())
    assert metadata['sha256'] == hashlib.sha256(engine.read_bytes()).hexdigest(), 'Engine changed since build'
    for name, field in [('doomgeneric_x2d_file.c', 'backendSha256'),
                        ('doom_sound.c', 'soundSourceSha256'), ('audio_ring.h', 'ringHeaderSha256')]:
        assert metadata[field] == hashlib.sha256((ROOT.parent/'native'/name).read_bytes()).hexdigest(), 'Rebuild engine: ' + name
    out.mkdir(parents=True, exist_ok=True)
    # Caller-provided output is for this experiment only; stale commands could abort the engine.
    if any((out / n).exists() for n in ['input', 'exit.request', 'engine.done']):
        p.error('Use a fresh output directory')
    os.environ.update(QT_QPA_PLATFORM='offscreen', QML_XHR_ALLOW_FILE_READ='1',
                      QML_XHR_ALLOW_FILE_WRITE='1')
    from PySide6.QtCore import QUrl, QPoint, Qt, qVersion, QCoreApplication, QEvent
    from PySide6.QtGui import QGuiApplication, QColor, QImage, QKeyEvent
    from PySide6.QtQuick import QQuickView, QQuickItem
    from PySide6.QtTest import QTest
    assert qVersion() == '6.4.1', qVersion()
    app = QGuiApplication([])
    env = dict(os.environ, X2D_DOOM_IPC=str(out), X2D_DOOM_SECONDS='25', X2D_DOOM_FRAMES='1400')
    errors = []
    with (out / 'engine.log').open('w') as log:
        proc = subprocess.Popen([str(engine), '-iwad', str(wad), '-warp', '1', '1',
                                 '-nomusic', '-config', str(out / 'doom.cfg'),
                                 '-extraconfig', str(out / 'extra.cfg')],
                                cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT)
        audio_log = (out/'audio-sink.log').open('w')
        sink = subprocess.Popen([str(a.audio_sink.resolve()), str(out/'audio-ring.bin'), str(out/'sound.s16le')], stdout=audio_log, stderr=subprocess.STDOUT)
        try:
            view = QQuickView(); view.resize(1024, 768); view.setColor(QColor('black'))
            view.engine().warnings.connect(lambda es: errors.extend(e.toString() for e in es))
            view.setInitialProperties({'ipcRoot': QUrl.fromLocalFile(str(out) + '/').toString()})
            view.setResizeMode(QQuickView.SizeRootObjectToView)
            view.setSource(QUrl.fromLocalFile(str(ROOT / 'DoomPage.qml')))
            assert view.status() == QQuickView.Ready, view.errors()
            view.show()
            scene = view.rootObject()
            deadline = time.monotonic() + 8
            while scene.property('frameNumber') < 30 and time.monotonic() < deadline:
                QTest.qWait(30)
                assert proc.poll() is None, (out / 'engine.log').read_text()
            assert scene.property('frameNumber') >= 30, errors
            # Doom's initial screen wipe draws frames without normal tic input sampling.
            # Let the level transition finish before checking live gameplay controls.
            QTest.qWait(2500)
            screen = scene.findChild(QQuickItem, 'DoomFrame')
            assert scene.property('imageStatus') == 1, errors
            bmp = QImage(str(out / 'frame.bmp'))
            assert not bmp.isNull() and bmp.width() == 320 and bmp.height() == 200
            bmp.save(str(out / 'native-frame.png'))
            view.grabWindow().save(str(out / 'page.png'))
            # Shutter stays disabled until the camera wrapper has read back stock override mode 3.
            QTest.keyClick(view, Qt.Key_E); QTest.qWait(180)
            assert scene.property('firePressCount') == 0
            scene.setProperty('shutterInputEnabled', True)
            before = json.loads((out / 'state.json').read_text())['clipAmmo']
            QTest.keyPress(view, Qt.Key_A); QTest.qWait(180)
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 0
            # Real swipe events must change the actual player's view angle, including a second movement finger.
            touch = QTest.createTouchDevice()
            gesture = QTest.touchEvent(view, touch, False)
            angle = json.loads((out/'state.json').read_text())['viewAngle']
            gesture.press(0, QPoint(400,300), view).commit(); QTest.qWait(40)
            gesture.move(0, QPoint(520,300), view).commit(); QTest.qWait(120)
            gesture.release(0, QPoint(520,300), view).commit(); QTest.qWait(120)
            state=json.loads((out/'state.json').read_text())
            assert state['lookTotal']>0 and state['lookEvents']>0 and state['viewAngle']!=angle, state
            angle=state['viewAngle']
            gesture.press(0,QPoint(130,650),view).press(1,QPoint(520,300),view).commit(); QTest.qWait(40)
            gesture.stationary(0).move(1,QPoint(420,300),view).commit(); QTest.qWait(120)
            state=json.loads((out/'state.json').read_text());assert state['inputMask']==1 and state['viewAngle']!=angle,state
            gesture.release(0,QPoint(130,650),view).release(1,QPoint(420,300),view).commit(); QTest.qWait(120)
            stable=json.loads((out/'state.json').read_text())['viewAngle'];QTest.qWait(180)
            assert json.loads((out/'state.json').read_text())['viewAngle']==stable
            assert scene.property('firePressCount') == 0
            QTest.keyRelease(view, Qt.Key_A)
            QTest.keyPress(view, Qt.Key_E); QTest.qWait(180)
            assert scene.property('shutterHeld') and scene.property('firePressCount') == 1
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 16
            assert json.loads((out / 'state.json').read_text())['clipAmmo'] < before
            repeat = QKeyEvent(QEvent.KeyPress, Qt.Key_E, Qt.NoModifier, 'E', True, 1)
            QCoreApplication.sendEvent(view, repeat)
            assert scene.property('firePressCount') == 1
            QTest.keyRelease(view, Qt.Key_E); QTest.qWait(180)
            assert not scene.property('shutterHeld')
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 0
            # Press/release in one Qt call must still fire the actual pistol, even if the held snapshot is missed.
            # Respect Doom's pistol animation/cooldown; a tap during cooldown need not fire.
            QTest.qWait(650)
            before = json.loads((out / 'state.json').read_text())['clipAmmo']
            QTest.keyClick(view, Qt.Key_E); QTest.qWait(350)
            assert scene.property('firePressCount') == 2
            assert json.loads((out / 'state.json').read_text())['clipAmmo'] < before
            QTest.qWait(180)
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 0
            # Real pointer input enters QML touch processing and reaches the native game state.
            QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, QPoint(130, 650))
            QTest.qWait(180)
            assert scene.property('controlMask') == 1, scene.property('controlMask')
            state = json.loads((out / 'state.json').read_text())
            assert state['inputMask'] == 1, state
            QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(130, 650))
            QTest.qWait(180)
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 0
            # Two independent real Qt touch points: movement and firing must coexist.
            touch = QTest.createTouchDevice()
            gesture = QTest.touchEvent(view, touch, False)
            gesture.press(0, QPoint(130, 650), view).press(1, QPoint(920, 680), view).commit()
            QTest.qWait(180)
            assert scene.property('controlMask') == 17
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 17
            gesture.release(0, QPoint(130, 650), view).release(1, QPoint(920, 680), view).commit()
            QTest.qWait(180)
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 0
            QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, QPoint(920, 680))
            QTest.qWait(180)
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 16
            # Simulate a lost UI heartbeat without changing the engine's input file.
            ipc_url = scene.property('ipcRoot')
            scene.setProperty('ipcRoot', '')
            QTest.qWait(1100)
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 0
            scene.setProperty('ipcRoot', ipc_url)
            QTest.qWait(180)
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 16
            # Page becoming invisible releases controls rather than leaving FIRE held.
            scene.setVisible(False); QTest.qWait(180)
            assert scene.property('controlMask') == 0
            assert json.loads((out / 'state.json').read_text())['inputMask'] == 0
            QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(920, 680))
            scene.setVisible(True); QTest.qWait(150)
            QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(970, 30))
            QTest.qWait(100)
            assert scene.property('exiting')
            assert (out / 'exit.request').read_text() == 'X2D_DOOM_EXIT\n'
            assert proc.wait(timeout=3) == 0
            assert sink.wait(timeout=3) == 0
            audio_log.close()
            audio=json.loads((out/'audio-sink.log').read_text())
            assert audio['soundStarts']>=2 and audio['nonzeroFrames']>100 and audio['failures']==0,audio
            assert (out / 'engine.done').exists()
            assert not errors, errors
            result = {'level': 'host/offline', 'qt': qVersion(), 'deviceAccess': False,
                'actualDoomCore': True, 'wadSha256': hashlib.sha256(wad.read_bytes()).hexdigest(),
                'engineSha256': hashlib.sha256(engine.read_bytes()).hexdigest(),
                'sourceSha256': {name: hashlib.sha256((ROOT/name if name.endswith('.qml') else ROOT.parent/'native'/name).read_bytes()).hexdigest()
                    for name in ['DoomPage.qml', 'doomgeneric_x2d_file.c', 'doom_sound.c', 'audio_ring.h']},
                'bmpDecoded': [bmp.width(), bmp.height()], 'qmlRendered': True,
                'pointerMovementToNativeEngine': True, 'fireToNativeEngine': True,
                'twoTouchMovementAndFire': True,
                'hiddenPageReleasesKeys': True, 'exitEndsEngine': True,
                'lostHeartbeatReleasesKeysDuringGameplay': True,
                'shutterDisabledBeforeRoutingAck': True, 'halfPressDoesNotFire': True,
                'fullPressFiresActualPistol': True, 'fullReleaseStopsFire': True,
                'autoRepeatDoesNotCreatePresses': True, 'fastShutterTapFiresActualPistol': True,
                'swipeChangesActualViewAngle': True, 'movementAndSwipeSimultaneously': True,
                'swipeReleaseStopsTurning': True, 'actualWadSoundEffectsPcm': True, 'audio': audio,
                'cameraFpsMeasured': False, 'qmlWarnings': errors}
            (out / 'checks.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result))
            view.close()
        finally:
            if proc.poll() is None:
                proc.terminate(); proc.wait(timeout=3)
            if sink.poll() is None:
                sink.terminate(); sink.wait(timeout=3)
            audio_log.close()


if __name__ == '__main__':
    main()

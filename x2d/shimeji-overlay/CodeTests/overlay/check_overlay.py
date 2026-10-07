#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Qt 6.4.1 desktop check, synthetic images/state only; no hardware/engine needed."""
import json
import os
import sys
import tempfile
from pathlib import Path
os.environ.update(QT_QPA_PLATFORM="offscreen", QML_XHR_ALLOW_FILE_READ="1", QML_XHR_ALLOW_FILE_WRITE="1")
from PySide6.QtCore import QUrl, QPoint, Qt, qVersion
from PySide6.QtGui import QGuiApplication, QImage, QColor
from PySide6.QtQuick import QQuickView, QQuickItem
from PySide6.QtTest import QTest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from alpha_masks import generate

def main():
    assert qVersion() == "6.4.1", "Requires the recorded Qt version"
    app = QGuiApplication([])
    errors = []
    with tempfile.TemporaryDirectory(prefix="shimeji-overlay-check-") as directory:
        state = Path(directory)
        images = state / "img"; images.mkdir()
        image = QImage(128, 128, QImage.Format_RGBA8888)
        image.fill(Qt.transparent)
        for y in range(32, 96):
            for x in range(16, 64):
                image.setPixelColor(x, y, QColor("white"))
        assert image.save(str(images / "shime1.png"))
        masks = generate(images)
        (state / "hit-masks.json").write_text(json.dumps(masks))
        native = {"tick": 1, "input": -1, "x": 360, "y": 220, "ax": 64, "ay": 128,
                  "image": "/shime1.png", "visible": True, "right": False, "mirror": False, "dragging": False}
        def write_state():
            next_file = state / "state.next"
            next_file.write_text(json.dumps(native)); next_file.replace(state / "state.json")
        write_state()
        view = QQuickView()
        view.engine().warnings.connect(lambda es: errors.extend(e.toString() for e in es))
        url = QUrl.fromLocalFile(str(state) + "/").toString()
        view.setInitialProperties({"dataRoot": url, "controlRoot": url,
                                   "assetRoot": QUrl.fromLocalFile(str(images)).toString()})
        view.setSource(QUrl.fromLocalFile(str(ROOT / "ui/qml/DesktopHarness.qml")))
        assert view.status() == QQuickView.Ready, errors
        view.resize(1024, 768); view.show(); QTest.qWait(200)
        scene = view.rootObject()
        overlay = scene.findChild(QQuickItem, "X2dShimejiTrial")
        sprite = scene.findChild(QQuickItem, "ShimejiSprite")
        assert overlay.property("tickNumber") == 1
        def click_sprite(x, y):
            p = sprite.mapToScene(QPoint(x, y))
            QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(round(p.x()), round(p.y())))
            QTest.qWait(20)
        QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(50, 200)); QTest.qWait(20)
        click_sprite(1, 1)
        assert scene.property("menuClicks") == 2, "Background/transparent padding blocked menu"
        native.update(tick=2, mirror=True); write_state(); QTest.qWait(80)
        click_sprite(24, 64) # Originally opaque; mirrored sprite makes it transparent.
        assert scene.property("menuClicks") == 3, "Mirrored alpha hit test failed"
        point = sprite.mapToScene(QPoint(96, 64))
        start = QPoint(round(point.x()), round(point.y()))
        QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, start); QTest.qWait(1)
        assert overlay.property("dragging")
        QTest.mouseMove(view, QPoint(700, 400)); QTest.qWait(1)
        assert overlay.property("dragMoves") > 0
        assert abs(sprite.x() - overlay.property("dragLeft")) < .1
        assert abs(sprite.y() - overlay.property("dragTop")) < .1
        QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(700, 400)); QTest.qWait(30)
        assert overlay.property("dragHold"), "Released position should wait for engine acknowledgment"
        fields = (state / "input").read_text().split()
        native.update(tick=3, input=int(fields[0]), dragging=False,
                      x=float(fields[5])+64, y=float(fields[6])+128)
        write_state(); QTest.qWait(80)
        assert not overlay.property("dragHold"), "Acknowledgment failed"
        capture = overlay.grabToImage(); QTest.qWait(100)
        assert capture.image().pixelColor(10, 400).alpha() == 0, "Overlay has an opaque fill"
        QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(975, 34)); QTest.qWait(50)
        assert (state / "exit.request").read_text() == "X2D_SHIMEJI_EXIT\n"
        assert overlay.property("exiting") and view.isVisible(), "Exit must leave the parent GUI alive"
        clicks = scene.property("menuClicks")
        QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(50, 200)); QTest.qWait(20)
        assert scene.property("menuClicks") == clicks+1
        assert not (state / "preview.png").exists(), "Unexpected screen capture"
        assert not errors, errors
        view.close()
    print(json.dumps({"qt": qVersion(), "hostOnly": True, "syntheticFixtures": True,
                      "menuClickThrough": True, "mirroredAlphaMask": True,
                      "directDrag": True, "releaseAcknowledgment": True,
                      "exitKeepsParentAlive": True, "deviceValidated": False}))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Desktop-only demo; owns the engine child and one preview window."""
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--character", type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "outputs/desktop")
    p.add_argument("--seconds", type=int, default=600, help="Demo time limit, 1..600 seconds")
    a = p.parse_args()
    if not 1 <= a.seconds <= 600:
        p.error("--seconds must be 1..600")
    if not a.engine.is_file() or not (a.character / "actions.xml").is_file():
        p.error("Supply a built host engine and character directory")
    os.environ.update(QML_XHR_ALLOW_FILE_READ="1", QML_XHR_ALLOW_FILE_WRITE="1")
    from PySide6.QtCore import QTimer, QUrl, qVersion
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickView, QQuickItem
    from alpha_masks import generate
    if qVersion() != "6.4.1":
        p.error("Use PySide6 Essentials 6.4.1 for this version-bound demo")
    app = QGuiApplication([])
    a.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="state-", dir=a.output) as directory:
        state = Path(directory)
        (state / "hit-masks.json").write_text(json.dumps(generate(a.character / "img")))
        with (a.output / "engine.log").open("w") as log:
            child = subprocess.Popen([str(a.engine.resolve()), str(a.character.resolve()), str(state)],
                                     stdout=log, stderr=subprocess.STDOUT)
            try:
                view = QQuickView()
                view.setInitialProperties({"dataRoot": QUrl.fromLocalFile(str(state) + "/").toString(),
                    "controlRoot": QUrl.fromLocalFile(str(state) + "/").toString(),
                    "assetRoot": QUrl.fromLocalFile(str((a.character / "img").resolve())).toString()})
                view.setResizeMode(QQuickView.SizeRootObjectToView)
                view.setSource(QUrl.fromLocalFile(str(ROOT / "ui/qml/DesktopHarness.qml")))
                if view.status() != QQuickView.Ready:
                    raise RuntimeError("Desktop QML failed to load")
                overlay = view.rootObject().findChild(QQuickItem, "X2dShimejiTrial")
                overlay.setProperty("secondsLeft", a.seconds)
                timer = QTimer()
                def poll():
                    if (state / "exit.request").exists() or child.poll() is not None:
                        view.close(); app.quit() # Only this demo's application, never a stock GUI.
                timer.timeout.connect(poll); timer.start(50)
                view.resize(1024, 768); view.show()
                return app.exec()
            finally:
                if child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        child.kill(); child.wait()

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import re
import unittest
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[2]
QML = MODULE_ROOT / "ui" / "qml" / "ZoomRail.qml"


class QmlContractTest(unittest.TestCase):
    def test_component_is_fail_closed_and_vendor_independent(self) -> None:
        source = QML.read_text(encoding="utf-8")
        imports = re.findall(r"^import\s+([^\s]+)", source, flags=re.MULTILINE)
        self.assertEqual(imports, ["QtQuick"])
        self.assertIn("property bool featureEnabled: false", source)
        self.assertIn("visible: featureEnabled && shooting", source)
        self.assertIn("signal zoomRequested(real zoom)", source)
        self.assertIn("var trackY = y - track.y", source)
        self.assertIn("y: track.y + root.zoomToTrackY", source)
        self.assertEqual(source.count("Math.max(1, track.height - handle.height)"), 2)
        self.assertNotIn("SensorWindow", source)
        self.assertNotIn("CameraObject", source)

    def test_component_exposes_expected_stops(self) -> None:
        source = QML.read_text(encoding="utf-8")
        for label in ('"1.0"', '"FF eq."', '"1.5"', '"2.0"'):
            self.assertIn(label, source)


if __name__ == "__main__":
    unittest.main()

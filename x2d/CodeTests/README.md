# X2D Code Tests

This public subset contains only selected source and offline tests:

- `temporary_af_speed_probe/pdaf-scan-type1-candidate/`: AF-S scan request candidate.
- `temporary_af_speed_probe/standalone_handoff/`: offline extraction and validation helpers.
- `temporary_af_speed_probe/original-menu-candidate/`: menu/page source, the public `X2dNativeMenuLoader.qml` integration component, the twelfth-entry SVG icon, and desktop checks.
- `x2d-afc-research/`: offline AF-C gate patcher and public status summary.
- `factory-debug-ui/`: bounded ADB state inspector for the stock GUI's factory debug-UI finding.
- `shutter-animation-preview/`: browser/QML animation, read-only timing analysis and offline tests.

Device installation, arbitrary shell, ADB enablement, process-memory modification and system-partition tooling are intentionally absent. The factory-debug-ui tool assumes an already-authorized ADB endpoint and only reads fixed state or explicitly restarts the stock GUI.

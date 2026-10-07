# X2D Code Tests

This public subset contains only selected source and offline tests:

- `temporary_af_speed_probe/pdaf-scan-type1-candidate/`: AF-S scan request candidate.
- `temporary_af_speed_probe/standalone_handoff/`: offline extraction and validation helpers.
- `temporary_af_speed_probe/original-menu-candidate/`: menu/page source, the public `X2dNativeMenuLoader.qml` integration component, the twelfth-entry SVG icon, and desktop checks.
- `x2d-afc-research/`: offline AF-C gate patcher and public status summary.
- `factory-debug-ui/`: bounded ADB state inspector for the stock GUI's factory debug-UI finding.
- [ui-response](ui-response/README.md)：本地轨迹解析器的合成时钟、CPU 与统计边界测试。
- `shutter-animation-preview/`: browser/QML animation, read-only timing analysis and offline tests.

Device installation, arbitrary shell, ADB enablement, process-memory modification and system-partition tooling are intentionally absent. The factory-debug-ui tool assumes an already-authorized ADB endpoint and only reads fixed state or explicitly restarts the stock GUI. See the [factory-debug reproduction boundary](../research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md) for the exact hand-off point and the reason archival runtime commands are not runnable from a clean clone.

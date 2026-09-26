# X2D 100C Research

The X2D tree covers firmware 4.2.0 unless a document states otherwise.

- [AF-S Type1 scan candidate](CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md): exact-version offline patch generator and benchmark rules; not device-tested.
- [Menu extension](CodeTests/temporary_af_speed_probe/original-menu-candidate/README.md): source QML, icon and offline checks for the twelfth menu entry.
- [AF-C research](CodeTests/x2d-afc-research/README.md): public summary and exact-version offline gate patcher.
- [Object recognition](object-recognition/README.md): compatibility audit, frame adapter and offline contract tests; not a deployable port.
- [Factory debug UI](CodeTests/factory-debug-ui/README.md): [research finding](research/4.2.0/FACTORY-DEBUG-UI-FINDINGS.md), stock GUI lock-state evidence, and a bounded ADB state inspector; it does not enable ADB or install a payload.
- [Shutter animation](CodeTests/shutter-animation-preview/README.md): browser/QML visual candidate, read-only timing analysis and audio source.
- [Firmware tools](tools/README.md): offline firmware and QML analysis helpers.
- [Research notes](research/): selected sanitized findings and validation limits.
- [External research references](references/EXTERNAL-RESEARCH.md): citation-only provenance, including the X2D CIM notes that inspired the AF-C investigation.

The public tree does not include vendor inputs, generated QML units, runtime preload packages, device installation scripts or exploit-ready factory/root tooling.

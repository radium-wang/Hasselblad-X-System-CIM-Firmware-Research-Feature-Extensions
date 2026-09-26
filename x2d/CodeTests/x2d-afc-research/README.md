# X2D 100C 4.2.0 AF-C Research

## Result

Static analysis and a controlled runtime experiment showed that the stock 4.2.0 backend contains an AF-C state machine. A device test observed transition into continuous-focus state and return to AF-S after release.

The stock Control Screen contains only AF-S and MF objects. Therefore changing the `CameraUI.canChangeAfc` Boolean alone does not create a complete three-item UI. A separate three-item model and popover layout were required by the temporary menu candidate.

## Research provenance

The investigation was initially motivated by the public [x2d-cim-notes](../../references/EXTERNAL-RESEARCH.md) research notes. That project is cited as an external lead and acknowledgement only; the AF-C state-machine observation, gate analysis, and runtime conclusions here come from this project's own evidence, and no source code was copied from it.

## Included tool

`patch_x2d_4_2_0_afc.py` is an offline, exact-hash patcher for the dormant compiled-QML gate in a user-supplied 4.2.0 `camera-gui`. It does not connect to a camera, install files, build an OTA/CIM, or overwrite its input. The generated complete executable must remain local and must not be committed.

## Limits

- The gate patch is not a complete Control Screen AF-C port.
- No persistent public installation package is provided.
- Long-running AF-C stability, lens coverage, sleep/wake, power, heat and reboot behavior are not established.
- X2D II AF libraries and configuration are not compatible drop-in replacements for the first-generation camera.

# X2D Shutter Animation and Audio Research

## Included work

- `index.html`: standalone browser preview of the four-stage 400 ms animation.
- `X2dShutterAnimation.qml`: source QML candidate.
- `analyze_blackout.py` and tests: offline analysis of a sanitized event list.
- `Measure-Blackout.ps1`: bounded read-only event collection; it does not trigger a capture or install files.
- `audio_preview.c`, `build_audio.py`, `prepare_audio.py`: source and local-build helpers. Audio material and compiled artifacts are not included.

## Results

The visual candidate closes, holds, opens and completes the star motion in four 100 ms stages. Device software logs yielded complete hide-to-show request samples of 995 ms and 663 ms in different sessions. These are software events, not optical display-blackout measurements.

An early direct-PCM audio approach interfered with stock notification audio. The later design used the stock audio-client path, and the user confirmed a one-shot preview was audible. Cold-start behavior, capture-event integration and long-term coexistence with stock sounds remain incomplete.

The referenced audio material is not distributed because redistribution permission has not been established.


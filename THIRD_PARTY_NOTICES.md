# Third-Party Notices

This file is a release checklist, not a claim that every referenced dependency is redistributed.

## Public references used by the research

- `WeiCheng97/Hasselblad-X2d-series-5g-unlock` — public X2D protocol reference; upstream repository reports an MIT license. Before release, record the exact commit used and identify any files that contain copied or adapted code.
- `YuHaoyua/hasselblad-cim-firmware-extractor` — public CIM extraction reference; upstream repository reports an MIT license. Record the exact commit and retained notices before release.
- Qt Declarative 6.4.1 — compiled-QML format and API reference. Qt components may use different commercial, LGPL, GPL or third-party licenses; this repository does not redistribute Qt binaries.
- PyUSB, pyelftools, Capstone, Unicorn, Pillow, NumPy, SoundFile, dissect.extfs, brotli and pycryptodome may be optional local tools. They are not vendored here; users should review the license of the version they install.

## Release requirement

Before making the GitHub repository public, replace each general entry above with an exact version/commit, the files that use or adapt it, the nature of the modification and the required copyright/license text. Do not use the project MIT license to overwrite third-party notices.


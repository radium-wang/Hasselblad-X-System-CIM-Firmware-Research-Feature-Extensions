# Third-Party Notices

This file is a release checklist, not a claim that every referenced dependency is redistributed.

The citation-only external research records are maintained in
[`x2d/references/EXTERNAL-RESEARCH.md`](x2d/references/EXTERNAL-RESEARCH.md).
They document provenance and acknowledgement; they are not vendored into this
repository.

## Public references used by the research

- `WeiCheng97/Hasselblad-X2d-series-5g-unlock` — public X2D protocol reference; upstream repository reports an MIT license. Before release, record the exact commit used and identify any files that contain copied or adapted code.
- `YuHaoyua/hasselblad-cim-firmware-extractor` — public CIM extraction reference; upstream repository reports an MIT license. Record the exact commit and retained notices before release.
- `YuHaoyua/hasselblad-x1d-reverse-engineering` — related X1D reverse-engineering reference only; it is outside the current X2D/X2D II implementation scope. Verify its exact license before reuse.
- `Konamill-bot/x2d-pdaf-sim` — related X2D 100C 4.2.0 PDAF simulation reference; upstream README reports an MIT license. No source or generated output is copied here.
- `Konamill-bot/x2d-cim-notes` — primary inspiration for the X2D AF-C investigation; documentation reports CC BY-SA 4.0 and diagnostic tools report MIT. No source or documentation is copied here.
- Qt Declarative 6.4.1 — compiled-QML format and API reference. Qt components may use different commercial, LGPL, GPL or third-party licenses; this repository does not redistribute Qt binaries.
- PyUSB, pyelftools, Capstone, Unicorn, Pillow, NumPy, SoundFile, dissect.extfs, brotli and pycryptodome may be optional local tools. They are not vendored here; users should review the license of the version they install.

## Release requirement

Before making the GitHub repository public, replace each general entry above with an exact version/commit, the files that use or adapt it, the nature of the modification and the required copyright/license text. Do not use the project MIT license to overwrite third-party notices.

## Shimeji 模块的固定依赖（2026-10-07）

[x2d/shimeji-overlay](x2d/shimeji-overlay/README.md) 的新增引擎适配、QML 与模块工具按 GPL-3.0-or-later 授权，附独立 LICENSE；此处没有复制第三方引擎、Qt 或角色素材。

- libshijima：pixelomer，提交 `361f452f3e89cdfaf04624db1c7641e3db410da9`，GPL-3.0-or-later。native/engine.cc 使用其 API；上游源码由使用者提供，构建脚本校验版本。
- pugixml：Arseny Kapoulkine，提交 `27b68329de32cf9c601ca8eb6c588fd639960c40`，MIT，libshijima 的固定子模块；分发构建结果须保留其原始 LICENSE.md。
- Duktape 2.7.0：Duktape authors，MIT，libshijima 内的解释器依赖；分发构建结果须保留 duktape.cc 内的 LICENSE.txt/AUTHORS.rst 及相关版权说明。
- Qt / PySide6 Essentials 6.4.1：电脑端验证依赖，未随仓库分发；使用安装包对应的 Qt/PySide 和第三方许可。
- Neuron：来自 qingchenyouforcc/NeurolingsCE-Qt 提交 `b76816fbe52c51d617a4b5e1aa16c0e026f9e02f` 的 mascot_pack/Neuron；来源 README 声明官方包 CC-BY-NC-SA-4.0。info.json 署名 Paccha（https://linktr.ee/paccha_），配置 promote、dalekcraft。只记录来源，不复制 XML/PNG 或预览。角色非商业素材许可与 GPL/MIT 源码授权分开，不能把角色素材宣称为本仓库 MIT 开源内容。

相应固定版本来源链接及构建步骤见模块 README。若自行分发引擎或素材，须另带所分发版本的完整第三方版权/许可及对应源码，不把本仓库的许可文件代替上游声明。

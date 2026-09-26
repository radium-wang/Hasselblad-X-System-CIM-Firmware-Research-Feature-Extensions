# External Research References

## English

This page records public repositories that informed the research. It is a
citation and acknowledgement index, not a vendored dependency list. The
repositories below are not copied into this project, and this project does
not claim ownership of their code, documentation, firmware, models, or data.

The links currently point to each upstream `main` branch. Before a public
release that relies on a specific upstream passage or implementation, record
the exact commit, consulted file, and applicable license text. The access date
for this review is 2026-09-26.

### Primary inspiration for the X2D AF-C investigation

**Konamill-bot.** *Hasselblad X2D CIM Firmware — Reverse Engineering Notes*.
GitHub. <https://github.com/Konamill-bot/x2d-cim-notes>

This repository was the direct research inspiration for asking whether the
X2D 100C's in-camera firmware contains an AF-C capability or a disabled AF-C
path. It motivated the present project's independent symbol, state-machine,
menu-gate, and restricted hardware checks. Its negative software-only results
and its hypotheses are a research lead, not proof of the results reported in
this repository. The present project did not copy or adapt its source code.

The upstream README states that its documentation is under CC BY-SA 4.0 and
its diagnostic tool source is under the MIT License. Any future quotation or
adaptation must preserve the applicable attribution and share-alike terms.

### CIM container extraction reference

**YuHaoyua.** *Hasselblad CIM Firmware Decryptor & Extractor*.
GitHub. <https://github.com/YuHaoyua/hasselblad-cim-firmware-extractor>

This is a public reference for CIM container structure and extraction
terminology used when organizing the offline firmware-format work. No
firmware, key material, extracted output, or source file from that repository
is included here. GitHub identifies the upstream repository as MIT-licensed;
pin the exact commit and retain the upstream notice before adapting any code.

### Related X1D reverse-engineering reference

**YuHaoyua.** *Hasselblad X1D Reverse Engineering*.
GitHub. <https://github.com/YuHaoyua/hasselblad-x1d-reverse-engineering>

This repository is a related historical and methodological reference only.
X1D is outside the current X2D/X2D II implementation scope, and its addresses,
images, device observations, and conclusions are not reused as X2D evidence.
The upstream repository contains a license file; verify its exact terms before
copying or adapting anything. No material from it is redistributed here.

### PDAF simulation reference

**Konamill-bot.** *x2d-pdaf-sim: An open PDAF autofocus decision-policy
simulation*. GitHub. <https://github.com/Konamill-bot/x2d-pdaf-sim>

This is a related simulation reference for the X2D 100C 4.2.0 PDAF decision
policy and is useful context for the AF-S speed model. A simulation result is
not a camera-side measurement and is not used here as proof of AF-C support.
The upstream README identifies the project as MIT-licensed. No source or
generated output is copied into this repository.

### Factory-diagnostic-channel reference

**WeiCheng97.** *Hasselblad X2D-series 5G unlock*.
GitHub. <https://github.com/WeiCheng97/Hasselblad-X2d-series-5g-unlock>

This is an adjacent reference for observations involving the camera's factory
diagnostic channel and local device communication. It is not evidence for the
AF-S, AF-C, face/eye, or object-recognition conclusions in this project. The
upstream repository identifies its code as MIT-licensed and contains its own
radio-regulatory disclaimer; local use remains subject to applicable law and
device authorization. No code or device data is copied here.

### Citation and relationship boundary

These references document research provenance and help readers reproduce the
reasoning path. They do not mean that the upstream authors endorse this
project, that the projects share code, or that the upstream claims have been
independently confirmed here. The current research results remain bounded by
the evidence levels and limitations in [`RESEARCH_RESULTS.md`](../../RESEARCH_RESULTS.md).

## 中文

本页记录对研究形成启发或提供方法背景的公开仓库。它是引用和致谢索引，
不是把外部仓库作为依赖 vendoring 进来。本项目没有复制下列仓库，也不主张
拥有其中的代码、文档、固件、模型或数据。

当前链接指向各上游仓库的 `main` 分支。正式公开前，如果研究结论依赖某个
上游段落或实现，应记录确切 commit、实际查阅文件和适用的许可证文本。本次
核对日期为 2026-09-26。

### X2D AF-C 调查的主要启发来源

**Konamill-bot。**《Hasselblad X2D CIM Firmware — Reverse Engineering Notes》。
GitHub：<https://github.com/Konamill-bot/x2d-cim-notes>

这个仓库是本项目提出“X2D 100C 机内固件是否存在 AF-C 能力或被关闭的 AF-C
路径”问题的直接启发来源。它促使本项目进一步做独立的符号、状态机、菜单 gate
和受限实机检查。它的纯软件负面结果及假设只是研究线索，不是本仓库结论的证据。
本项目没有复制或改写它的源码。

上游 README 说明其文档使用 CC BY-SA 4.0，诊断工具源码使用 MIT 许可证。未来如
引用或改编，必须保留相应署名及相同方式共享要求。

### CIM 容器解包参考

**YuHaoyua。**《Hasselblad CIM Firmware Decryptor & Extractor》。
GitHub：<https://github.com/YuHaoyua/hasselblad-cim-firmware-extractor>

这是整理离线固件格式工作时使用的 CIM 容器结构和解包术语参考。仓库没有收录其
固件、密钥材料、解包结果或源码文件。GitHub 页面将上游仓库标为 MIT 许可证；若
未来改编代码，应先固定确切 commit 并保留上游声明。

### X1D 逆向相关参考

**YuHaoyua。**《Hasselblad X1D Reverse Engineering》。
GitHub：<https://github.com/YuHaoyua/hasselblad-x1d-reverse-engineering>

这是相关的历史和方法参考。X1D 不属于当前 X2D/X2D II 的实现范围，其地址、镜像、
设备观察和结论不会被当作 X2D 证据复用。上游仓库有许可证文件，但在复制或改编前
仍需核对确切条款。本项目不再分发其中任何材料。

### PDAF 仿真参考

**Konamill-bot。**《x2d-pdaf-sim: An open PDAF autofocus decision-policy
simulation》。GitHub：<https://github.com/Konamill-bot/x2d-pdaf-sim>

这是关于 X2D 100C 4.2.0 PDAF 决策策略的相关仿真参考，可作为 AF-S 速度模型的
背景。仿真结果不是相机实测，也不被本项目当作 AF-C 已支持的证据。上游 README
标注项目使用 MIT 许可证。本项目没有复制其源码或生成结果。

### 原厂诊断通道参考

**WeiCheng97。**《Hasselblad X2D-series 5G unlock》。
GitHub：<https://github.com/WeiCheng97/Hasselblad-X2d-series-5g-unlock>

这是关于相机原厂诊断通道和本地设备通信观察的旁支参考，不是本项目 AF-S、AF-C、
人脸/眼部识别或对象识别结论的证据。上游仓库说明其代码使用 MIT 许可证，并有
自己的无线电法规免责声明；本地使用仍须遵守适用法律并取得设备授权。本项目不
复制其中的代码或设备数据。

### 引用与关系边界

这些参考资料用于记录研究来源，帮助读者理解研究路径。它们不表示上游作者为本
项目背书，不表示项目之间共享代码，也不表示上游结论已在本项目中独立确认。当前
研究结果仍受 [`RESEARCH_RESULTS.md`](../../RESEARCH_RESULTS.md) 中的证据等级和
限制约束。

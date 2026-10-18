# Hasselblad X-System CIM Firmware Research & Feature Extensions

## 欢迎交流 / Discussion and contributions

欢迎交流、分享研究发现和使用反馈。欢迎通过 [Issues](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/issues) 讨论问题与建议，也欢迎提交 [Pull Requests](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/pulls) 改进代码、文档和测试。

Discussion, research findings and feedback are welcome. Please use [Issues](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/issues) for questions and suggestions, and submit [Pull Requests](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/pulls) to improve code, documentation and tests.

---


An independent, non-official research project on Hasselblad X-System camera interoperability, user interfaces, autofocus behavior, feature extensions, and firmware formats.

**研究更新至 2026-10-16：** [X2D II 数字裁切离线候选](x2d2/digital-zoom/README.md) · [AFT／眼部共存与三档速度](x2d/research/4.2.0/AF-EYE-AND-SPEED-UPDATE.md) · [4／6／16 张实拍与电脑四亿 DNG](x2d/research/4.2.0/PIXEL-SHIFT-CAPTURE-RESULTS.md) · [JSR 蓝鸟腹部与文字的解析力三方对比](x2d/research/4.2.0/JSR-METAL-COMPARISON.md) · [Startup Studio](x2d/research/4.2.0/STARTUP-STUDIO-UPDATE.md) · [一代模型解密与独立 CPU 测试](x2d/research/4.2.0/MODEL-DECRYPTION-AND-CPU-RESULTS.md) · [完整成果表](RESEARCH_RESULTS.md)。新增 [PDAF／光谱只读工具](x2d/tools/firmware-analysis/focus-and-spectral/README.md)、[像素位移离线处理库](x2d/pixel-shift/README.md) 和 [TFLite 结构检查](x2d/tools/model-structure/README.md)。历史实机、离线检查及待验证内容分别标注，不提供设备部署后端。

**2026-10-16 归档补充：** [425 区域实验源码、快照契约与历史实机观察](x2d/CodeTests/pdaf-only-shadow/PDAF425.md) · [PDAF 实验记录模板、脱敏与离线回放](x2d/CodeTests/pdaf-only-shadow/PDAF425-RECORDING.md) · [自动亮度与 Windows 产品修正摘要](x2d/research/4.2.0/TOOLKIT-BRIGHTNESS-AND-WINDOWS.md)。425 候选只完成离线核心和历史原厂观察摘要，不是已安装的相位点升级；二代完整策略尚未移植。

This repository contains only source code, offline tools, tests, and sanitized research findings that contributors are authorized to publish. Vendor firmware, original shared libraries, models, DSP or kernel files, extracted or modified QML compilation units, device logs, and local build products are not distributed here.

**Research disclaimer:** read [DISCLAIMER.md](DISCLAIMER.md) before using any device-side material. This project is not affiliated with the referenced vendors, and all experiments are performed at the user's own risk and authorization.

## Contents

| Project | Public contents | Current status |
| --- | --- | --- |
| [X2D 100C](x2d/README.md) | Offline firmware and QML analysis, menu sources, autofocus research, object-recognition contracts, Doom/Shimeji desktop sources and shutter timing | Research candidates; no device deployment instructions |
| [X2D II](x2d2/README.md) | Version-specific model/PDAF comparisons and an offline crop-window planner | Geometry/controller/native/QML contracts only; no pixel crop, camera backend, signed package or second-generation hardware validation |

新增：[X2D 运行 Doom：快门开火、音效、滑动转向](x2d/doom/README.md) · [透明 Shimeji 宠物源码与桌面演示](x2d/shimeji-overlay/README.md) · [整机 UI 延迟诊断与三轮试验](x2d/research/4.2.0/UI-RESPONSIVENESS.md)。宠物临时实机交互得到确认；整机优化尚未确认改善。

See [RESEARCH_RESULTS.md](RESEARCH_RESULTS.md) for the complete status of the research results.

## Research references and their contribution

2026-10-14 新增：[FXGab69 的黑白帧与所有权离线源码](x2d/CodeTests/monochrome-frame-contracts/README.md)。来源作者的两笔提交归属保留，源码子集采用原项目许可；6 项离线测试通过，实际相机功能待验证。

The external projects below helped shape the research questions and analysis
methods. They are cited as provenance and acknowledgement, not as vendored
dependencies or proof of the results in this repository.

**Special thanks to [@derrickyau9](https://github.com/derrickyau9): for sacrificing an X1D II in his research, helping make today's firmware-unpacking methods and the flourishing research community possible. We are grateful for the cost he bore and the path his work opened for others.** See his [X1D II research](https://github.com/derrickyau9/Hasselblad_X1D_II_FirmwareDump).

- [`x2d-cim-notes`](https://github.com/Konamill-bot/x2d-cim-notes) was the direct inspiration for investigating whether the X2D 100C's in-camera firmware retained an AF-C capability or a disabled AF-C path. It helped separate the questions of code-path presence, UI gating, and actual camera behavior.
- [**@derrickyau9**](https://github.com/derrickyau9) implemented firmware extraction in his [Hasselblad X1D II research](https://github.com/derrickyau9/Hasselblad_X1D_II_FirmwareDump). We acknowledge that work as the source of the firmware-extraction research reference.
- [`x2d-pdaf-sim`](https://github.com/Konamill-bot/x2d-pdaf-sim) provided related PDAF decision-policy simulation context for the AF-S speed model; its simulation is not treated as hardware evidence.

The public menu candidate includes the source-level [`X2dNativeMenuLoader.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/X2dNativeMenuLoader.qml), the [`Bootstrap.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/Bootstrap.qml) attach logic, and the [`twelfth-entry SVG icon`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/assets/ic_main_menu_play.svg). The generated vendor QML unit and device installation package remain intentionally excluded.

See the [external research reference index](x2d/references/EXTERNAL-RESEARCH.md) for citation wording, license boundaries, and the distinction between inspiration and independently verified evidence.

## Reproduction

Run the safe offline suite with:

```sh
python3 scripts/reproduce_offline.py
```

The complete reproduction guide, including exact-version inputs for authorized hardware tests, is in [REPRODUCE.md](REPRODUCE.md).

## Evidence levels

- `Static analysis`: source code, firmware formats, symbols, or instructions inspected without device access.
- `Offline validation`: generators, simulators, or tests run on a computer without accessing a device.
- `Hardware validation`: restricted tests completed on a recorded model and firmware version.
- `User feedback`: observations confirmed by an operator and not necessarily independently measured.
- `Unverified`: not to be treated as implemented or deployable.

## Use boundaries

Research only devices, firmware, and environments that you own or are explicitly authorized to use. Follow applicable laws, contracts, warranty terms, security-disclosure rules, and third-party licenses. A research-purpose statement does not grant permission to access, modify, bypass technical measures, or redistribute third-party materials.

This repository does not provide one-click flashing packages and does not guarantee that any experiment applies to other firmware versions, lenses, or hardware batches. Start with offline tools and documentation.

## Development check

```sh
python3 scripts/validate_public_repo.py
```

The check rejects known binary or firmware formats, personal absolute paths, likely real device serial numbers, Python syntax errors, and broken repository-local Markdown links.

## Security and licensing

- Report security issues privately according to [SECURITY.md](SECURITY.md).
- Original project code is available under the [MIT License](LICENSE), except the [Shimeji overlay module](x2d/shimeji-overlay/README.md), which is GPL-3.0-or-later, and the [Doom module](x2d/doom/README.md), which is GPL-2.0-or-later. This license does not cover vendor or third-party material that contributors are not authorized to license.
- See [NOTICE.md](NOTICE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for source and third-party notices.
- Read the [Research Disclaimer](DISCLAIMER.md) for authorization, device-risk, warranty, privacy, and liability boundaries.
- GitHub citation metadata is provided in [`CITATION.cff`](CITATION.cff); external research provenance is listed in [X2D references](x2d/references/EXTERNAL-RESEARCH.md).

---

# 哈苏 X 系统 CIM 固件研究及功能扩展

这是一个面向哈苏 X 系统相机互操作性、用户界面、自动对焦行为、功能扩展与固件格式的非官方独立研究项目。

本仓库只收录贡献者有权公开的源码、离线工具、测试和经过脱敏的研究结论。厂商固件、原厂共享库、模型、DSP 或内核文件、从原厂程序提取或修改的 QML 编译单元、设备日志及本机构建产物均不随仓库分发。

**研究免责声明：** 使用任何实机相关材料前，请先阅读[研究免责声明](DISCLAIMER.md)。本项目与被提及的厂商没有关联，所有实验都必须基于用户自己的授权并自行承担风险。

## 当前内容

| 项目 | 公开内容 | 当前状态 |
| --- | --- | --- |
| [X2D 100C](x2d/README.md) | 对焦、AFT／眼部、三档速度、像素位移采集与离线处理、开机画面、模型结构、Doom／Shimeji 及离线固件工具 | 研究与候选；验证范围见成果表 |
| [X2D II](x2d2/README.md) | 1.3.16.2 模型／PDAF 静态对照与数字裁切窗口离线规划器 | 只有几何、控制器、C/QML 契约；无像素裁切、相机后端、签名包或本轮二代实机验收 |

完整状态见[研究成果总表](RESEARCH_RESULTS.md)。

## 研究参考资料及其帮助

2026-10-14 新增：[FXGab69 的黑白帧与所有权离线源码](x2d/CodeTests/monochrome-frame-contracts/README.md)。保留来源作者、原始提交对应记录及完整许可；6 项电脑端测试通过，实际相机功能待验证。

下面的外部项目帮助确定研究问题和分析方法。它们在此作为来源记录和致谢，
不是被 vendoring 进来的依赖，也不是本仓库结论的直接证据。

**特别感谢 [@derrickyau9](https://github.com/derrickyau9)：献祭一台 X1D II，换来了今天的解包方法与后续研究的繁荣。感谢他为这条研究道路付出的代价与作出的贡献。** [查看他的 X1D II 研究](https://github.com/derrickyau9/Hasselblad_X1D_II_FirmwareDump)。

- [`x2d-cim-notes`](https://github.com/Konamill-bot/x2d-cim-notes) 是调查 X2D 100C 机内固件是否保留 AF-C 能力或被关闭 AF-C 路径的直接启发来源。它帮助我们把“代码路径存在”“界面 gate 开放”和“实机行为成立”区分开。
- 感谢 [**@derrickyau9**](https://github.com/derrickyau9)：他在 [Hasselblad X1D II 研究](https://github.com/derrickyau9/Hasselblad_X1D_II_FirmwareDump)中实现了固件提取，为本项目的固件提取研究提供了来源参考。
- [`x2d-pdaf-sim`](https://github.com/Konamill-bot/x2d-pdaf-sim) 提供了 PDAF 决策策略仿真的相关背景，用于理解 AF-S 速度模型；其仿真不能替代实机证据。

公开的菜单候选现在包含[源码级 `X2dNativeMenuLoader.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/X2dNativeMenuLoader.qml)、[`Bootstrap.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/Bootstrap.qml) 接入逻辑，以及[第十二格 SVG 图标](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/assets/ic_main_menu_play.svg)。生成后的原厂 QML 编译单元和设备安装包仍有意不随仓库发布。

详细的引用措辞、许可证边界，以及“研究启发”与“独立验证证据”的区别，见[外部研究参考索引](x2d/references/EXTERNAL-RESEARCH.md)。

## 复现

运行安全离线套件：

```sh
python3 scripts/reproduce_offline.py
```

完整复现说明以及授权实机测试所需的精确版本输入见[复现指南](REPRODUCE.md)。

## 验证层级

- `静态分析`：只检查源码、固件格式、符号或指令，不访问设备。
- `离线验证`：在电脑上运行生成器、模拟器或测试，不访问设备。
- `实机验证`：在明确记录的机型和固件版本上完成受限测试。
- `用户反馈`：由设备操作者观察确认，未必有独立测量。
- `待验证`：不能视为已实现或可部署。

## 使用边界

仅在自己拥有或获得明确授权的设备、固件和环境中研究。请遵守适用法律、合同、保修、安全披露和第三方许可要求。研究用途声明不会自动授予访问、修改、规避技术措施或再分发第三方材料的权利。

本仓库不提供一键刷写包，也不保证任何实验适用于其他固件、镜头或硬件批次。默认从纯离线工具和文档开始。

## 开发检查

```sh
python3 scripts/validate_public_repo.py
```

该检查会拒绝已知二进制或固件格式、个人绝对路径、疑似真实设备序列号、Python 语法错误和失效的仓库内 Markdown 链接。

## 安全与许可证

- 安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。
- 项目原创代码使用 [MIT License](LICENSE)，[Shimeji](x2d/shimeji-overlay/README.md) 为 GPL-3.0-or-later，[Doom](x2d/doom/README.md) 为 GPL-2.0-or-later；该许可不覆盖贡献者无权许可的厂商或第三方材料。
- 来源与第三方声明见 [NOTICE.md](NOTICE.md) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- 关于授权、设备风险、保修、隐私和责任边界，请阅读[研究免责声明](DISCLAIMER.md)。
- GitHub 引用元数据见 [`CITATION.cff`](CITATION.cff)，外部研究来源见 [X2D 参考资料](x2d/references/EXTERNAL-RESEARCH.md)。

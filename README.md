# Hasselblad X-System CIM Firmware Research & Feature Extensions

## 一键工具包 · 下载 / One-click toolkit

**[下载 Windows / macOS 一键工具包 →](https://github.com/radium-wang/x2d-907-one-click-extension-toolkit/releases/latest)**

[![Download toolkit](https://img.shields.io/badge/Download-Windows%20%2F%20macOS-0969da?style=for-the-badge)](https://github.com/radium-wang/x2d-907-one-click-extension-toolkit/releases/latest)

安装、更新和恢复说明：[一键工具包项目主页 / Toolkit & instructions](https://github.com/radium-wang/x2d-907-one-click-extension-toolkit)。使用前请核对该项目支持的机型、固件版本与验证范围。

## 赞助开发 / Support development

**[PayPal 赞助 →](https://paypal.me/RadiumWang) · [支付宝收款码 →](https://github.com/radium-wang/x2d-907-one-click-extension-toolkit#support-development)**

[![Support via PayPal](https://img.shields.io/badge/Support-PayPal-0070ba?style=for-the-badge)](https://paypal.me/RadiumWang)

赞助完全自愿，用于支持持续研究、工具开发和维护；获取工具与使用功能不以付款为条件。 Donations are voluntary and support ongoing research, development and maintenance.

---


An independent, non-official research project on Hasselblad X-System camera interoperability, user interfaces, autofocus behavior, feature extensions, and firmware formats.

This repository contains only source code, offline tools, tests, and sanitized research findings that contributors are authorized to publish. Vendor firmware, original shared libraries, models, DSP or kernel files, extracted or modified QML compilation units, device logs, and local build products are not distributed here.

**Research disclaimer:** read [DISCLAIMER.md](DISCLAIMER.md) before using any device-side material. This project is not affiliated with the referenced vendors, and all experiments are performed at the user's own risk and authorization.

## Contents

| Project | Public contents | Current status |
| --- | --- | --- |
| [X2D 100C](x2d/README.md) | Menu extensions, AF-S speed research, AF-C, stock face/eye detection enablement, factory debug UI finding, object recognition, shutter animation, and offline firmware tools | Research and candidates; not a complete product |
| [X2D II](x2d2/README.md) | Offline regional research for 1.3.16.2 | Not re-validated on hardware |

See [RESEARCH_RESULTS.md](RESEARCH_RESULTS.md) for the complete status of the research results.

## Research references and their contribution

The external projects below helped shape the research questions and analysis
methods. They are cited as provenance and acknowledgement, not as vendored
dependencies or proof of the results in this repository.

- [`x2d-cim-notes`](https://github.com/Konamill-bot/x2d-cim-notes) was the direct inspiration for investigating whether the X2D 100C's in-camera firmware retained an AF-C capability or a disabled AF-C path. It helped separate the questions of code-path presence, UI gating, and actual camera behavior.
- [`hasselblad-cim-firmware-extractor`](https://github.com/YuHaoyua/hasselblad-cim-firmware-extractor) helped establish CIM container and extraction terminology for the offline firmware-format work.
- [`x2d-pdaf-sim`](https://github.com/Konamill-bot/x2d-pdaf-sim) provided related PDAF decision-policy simulation context for the AF-S speed model; its simulation is not treated as hardware evidence.
- [`hasselblad-x1d-reverse-engineering`](https://github.com/YuHaoyua/hasselblad-x1d-reverse-engineering) provided historical reverse-engineering and documentation context while remaining outside the X2D/X2D II implementation scope.
- [`Hasselblad-X2d-series-5g-unlock`](https://github.com/WeiCheng97/Hasselblad-X2d-series-5g-unlock) provided adjacent factory-diagnostic-channel context; it is not evidence for the AF, face/eye, or object-recognition results here.

The public menu candidate includes the source-level [`X2dNativeMenuLoader.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/X2dNativeMenuLoader.qml), the [`Bootstrap.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/Bootstrap.qml) attach logic, and the [`twelfth-entry SVG icon`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/assets/ic_main_menu_play.svg). The generated vendor QML unit and device installation package remain intentionally excluded.

See the [external research reference index](x2d/references/EXTERNAL-RESEARCH.md) for citation wording, license boundaries, and the distinction between inspiration and independently verified evidence.

## Reproduction

Run the safe offline suite with:

```sh
python3 scripts/reproduce_offline.py
```

The complete reproduction guide, including exact-version inputs for authorized hardware tests, is in [REPRODUCE.md](REPRODUCE.md).

The factory-debug result has an explicit [from-zero reproduction boundary](x2d/research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md): the public inspector begins after an authorized ADB endpoint exists; it does not publish the factory-USB ADB bootstrap or an installation payload.

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
- Original project code is available under the [MIT License](LICENSE). This license does not cover vendor or third-party material that contributors are not authorized to license.
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
| [X2D 100C](x2d/README.md) | 菜单扩展、AF-S 提速研究、AF-C、原厂人脸/眼部识别开启、原厂 Debug 界面发现、对象识别、快门动画与离线固件工具 | 研究与候选；并非完整产品 |
| [X2D II](x2d2/README.md) | 1.3.16.2 地区离线研究 | 未重新实机验证 |

完整状态见[研究成果总表](RESEARCH_RESULTS.md)。

## 研究参考资料及其帮助

下面的外部项目帮助确定研究问题和分析方法。它们在此作为来源记录和致谢，
不是被 vendoring 进来的依赖，也不是本仓库结论的直接证据。

- [`x2d-cim-notes`](https://github.com/Konamill-bot/x2d-cim-notes) 是调查 X2D 100C 机内固件是否保留 AF-C 能力或被关闭 AF-C 路径的直接启发来源。它帮助我们把“代码路径存在”“界面 gate 开放”和“实机行为成立”区分开。
- [`hasselblad-cim-firmware-extractor`](https://github.com/YuHaoyua/hasselblad-cim-firmware-extractor) 帮助建立离线固件格式研究中的 CIM 容器和解包术语。
- [`x2d-pdaf-sim`](https://github.com/Konamill-bot/x2d-pdaf-sim) 提供了 PDAF 决策策略仿真的相关背景，用于理解 AF-S 速度模型；其仿真不能替代实机证据。
- [`hasselblad-x1d-reverse-engineering`](https://github.com/YuHaoyua/hasselblad-x1d-reverse-engineering) 提供了历史逆向和文档方法背景，但 X1D 不属于当前 X2D/X2D II 实现范围。
- [`Hasselblad-X2d-series-5g-unlock`](https://github.com/WeiCheng97/Hasselblad-X2d-series-5g-unlock) 提供了旁支的原厂诊断通道背景，但不是本项目 AF、眼部识别或对象识别结论的证据。

公开的菜单候选现在包含[源码级 `X2dNativeMenuLoader.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/X2dNativeMenuLoader.qml)、[`Bootstrap.qml`](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/Bootstrap.qml) 接入逻辑，以及[第十二格 SVG 图标](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/assets/ic_main_menu_play.svg)。生成后的原厂 QML 编译单元和设备安装包仍有意不随仓库发布。

详细的引用措辞、许可证边界，以及“研究启发”与“独立验证证据”的区别，见[外部研究参考索引](x2d/references/EXTERNAL-RESEARCH.md)。

## 复现

运行安全离线套件：

```sh
python3 scripts/reproduce_offline.py
```

完整复现说明以及授权实机测试所需的精确版本输入见[复现指南](REPRODUCE.md)。

原厂工程界面的发现另有[从零复现边界说明](x2d/research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)：公开检查器从已经授权的 ADB 端点开始，不发布 factory USB 开启 ADB 的引导或安装载荷。

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
- 项目原创代码使用 [MIT License](LICENSE)；该许可不覆盖贡献者无权许可的厂商或第三方材料。
- 来源与第三方声明见 [NOTICE.md](NOTICE.md) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- 关于授权、设备风险、保修、隐私和责任边界，请阅读[研究免责声明](DISCLAIMER.md)。
- GitHub 引用元数据见 [`CITATION.cff`](CITATION.cff)，外部研究来源见 [X2D 参考资料](x2d/references/EXTERNAL-RESEARCH.md)。

# Hasselblad X-System CIM Firmware Research & Feature Extensions

## Support the research

[View support options](SUPPORT.md)

## Discussion and contributions

Discussion, research findings and feedback are welcome. Please use [Issues](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/issues) for questions and suggestions, and submit [Pull Requests](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/pulls) to improve code, documentation and tests.

For camera extensions, visit the [X2D/907 One-Click Extension Toolkit](https://github.com/Gothenburg-R-D-Team/x2d-907-one-click-extension-toolkit). Its experimental macOS and Windows app offers optional autofocus and eye-recognition features for the first-generation X2D 100C and 907X / CFV 100C on stock firmware 4.2.0. See the toolkit repository for compatibility, downloads, and restoration instructions.

## Project overview

An independent, non-official research project on Hasselblad X-System camera interoperability, user interfaces, autofocus behavior, feature extensions, and firmware formats.

This repository contains only source code, offline tools, tests, and sanitized research findings that contributors are authorized to publish. Vendor firmware, original shared libraries, models, DSP or kernel files, extracted or modified QML compilation units, device logs, and local build products are not distributed here.

**Research disclaimer:** read [DISCLAIMER.md](DISCLAIMER.md) before using any device-side material. This project is not affiliated with the referenced vendors, and all experiments are performed at the user's own risk and authorization.

## Research and progress

The table groups the research currently documented in this repository by topic. Each link gives the evidence and exact validation limits; [RESEARCH_RESULTS.md](RESEARCH_RESULTS.md) lists the individual findings.

| Camera | Research | Current progress and limits |
| --- | --- | --- |
| X2D II | [八向摇杆 / Eight-way joystick](x2d2/joystick-eight-way/README.md) | 1.3.18.1 native input synthesis, evdev/uinput adapter and offline tests; all four diagonals, hold and release confirmed in one 45-second camera test. No persistent installation or long-term validation. |
| X2D II | [LiDAR and autofocus](x2d2/research/1.3.16.2/LIDAR-PIPELINE.md) | ADS6401 depth and AF-S/AF-C decision paths mapped offline; no second-generation camera validation. |
| X2D II | [Startup resources and variants](x2d2/research/1.3.16.2/STARTUP-LOGO-VARIANTS.md) | Six hardware-stage identifiers and Logo resources inspected; cold-start selection remains unverified. |
| X2D II | [Display and low-gray mura](x2d2/research/1.3.16.2/DISPLAY-MURA.md) | Brightness mapping and RGB LUTs inspected; no panel-specific spatial correction validated. |
| X2D II | [IBIS and Earth rotation](x2d2/research/1.3.16.2/IBIS-GPS-EARTH-ROTATION.md) | Location fields and compensation calls identified; controller formula and fallback remain unknown. |
| X2D II | [AF icons and UI assets](x2d2/README.md) | AF-S/AF-C interface assets extracted for offline inspection; no device UI change. |
| X2D II | [Encrypted models and PDAF](x2d2/research/1.3.16.2/MODEL-AND-PDAF-STATUS.md) | 39 model files remain encrypted; PDAF comparison is static, with no second-generation inference or device test. |
| X2D 100C | [AF-C backend and menu](x2d/research/AFC-MENU-RUNTIME-RESULT.md) | Stock continuous-focus state reached on hardware; a menu gate alone does not establish focusing performance. |
| X2D 100C | [Twelfth menu entry](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/README.md) | Stock-style menu behavior was confirmed in a temporary device session; the public source is not a persistent installer. |
| X2D 100C | [AF-S Type1 scan candidate](x2d/CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md) | Exact-version offline generator verified two changed instructions; end-to-end focusing and camera safety remain untested. |
| X2D 100C | [AFT and eye recognition](x2d/research/4.2.0/AF-EYE-AND-SPEED-UPDATE.md) | Optional AFT and eye-state coexistence tested on a separate candidate; integrated behavior and optical benefit remain distinct. |
| X2D 100C | [Three focus-speed levels](x2d/research/4.2.0/AF-EYE-AND-SPEED-UPDATE.md) | Low, medium, and high selector has limited local and user validation; multipliers are not end-to-end speed gains. |
| X2D 100C | [Stock AF parameters and PDAF trial](x2d/research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md) | Read-only stock parameters recorded; a temporary 80→100 trial reduced hunting but caused false focus and was retired. |
| X2D 100C | [CDAF, Kalman, TAF, VDAF and BDAF](x2d/research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md) | Code paths and candidate contracts analyzed; no validated new camera autofocus algorithm. |
| X2D 100C | [AF simulation and frame filtering](x2d/research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md) | Seven simulation scenarios and a four-frame filter candidate checked offline; neither proves camera success rates. |
| X2D 100C | [AFT face regions and display](x2d/research/4.2.0/AFT-FACE-TRACKING-RESULTS.md) | ROI publication and main-box selection received limited RAM-device feedback; sustained tracking remains unverified. |
| X2D 100C | [425-area PDAF candidate](x2d/CodeTests/pdaf-only-shadow/PDAF425.md) | Sampling geometry, offline core, and historical stock observations recorded; no installed 425-point upgrade. |
| X2D 100C | [Second-generation focus strategy comparison](x2d/research/4.2.0/FOCUS-STRATEGY-PORT-BOUNDARIES.md) | Static comparison identified data and timing gaps; matching area counts would not complete a strategy port. |
| X2D 100C | [Spectral white balance](x2d/research/4.2.0/SPECTRAL-WHITE-BALANCE.md) | AS7341 and AWB weighting paths mapped statically; camera readings and image benefit unmeasured. |
| X2D 100C | [Pixel-shift capture](x2d/research/4.2.0/PIXEL-SHIFT-CAPTURE-RESULTS.md) | 4/6/16-frame RAW sequences captured; physical precision and full-image quality remain unquantified. |
| X2D 100C | [Computer-side DNG reconstruction](x2d/research/4.2.0/JSR-METAL-COMPARISON.md) | A 408.24-megapixel RGB16 DNG was built from four frames; strict pixel identity failed and optical gain is not proven. |
| X2D 100C | [Offline pixel-shift library](x2d/pixel-shift/README.md) | Public four/six-frame processing subset passes host tests on synthetic inputs; separate from JSR. |
| X2D 100C | [25MP low-noise and video](x2d/research/4.2.0/IMAGING-AND-VIDEO-UPDATE.md) | Software downsizing remains a candidate; no full-frame hardware binning or playable in-camera video demonstrated. |
| X2D 100C | [Startup Studio](x2d/research/4.2.0/STARTUP-STUDIO-UPDATE.md) | Mac installation and factory restoration tested on a standard X2D; Windows and other models need full camera validation. |
| X2D 100C | [Toolkit brightness and Windows history](x2d/research/4.2.0/TOOLKIT-BRIGHTNESS-AND-WINDOWS.md) | Archived feature behavior and desktop checks; physical display and native Windows results are not established here. |
| X2D 100C | [Startup Logo research](x2d/research/4.2.0/STARTUP-LOGO-REPLACEMENT.md) | Main-screen image extraction and temporary color display tested; shoulder-screen asset and persistent boot path remain unresolved. |
| X2D 100C | [Shutter animation](x2d/CodeTests/shutter-animation-preview/README.md) | Visual candidate and timing analysis available offline; no installed camera feature claimed. |
| X2D 100C | [Doom](x2d/doom/README.md) | Engine, shutter firing, sound, and swipe controls received limited first-generation feedback; public tree has no deployment backend. |
| X2D 100C | [Shimeji overlay](x2d/shimeji-overlay/README.md) | Transparent overlay had temporary device interaction; public module has desktop checks, not a firmware installer. |
| X2D 100C | [Whole-camera UI response](x2d/research/4.2.0/UI-RESPONSIVENESS.md) | Stock frame and touch timing measured; three trials did not confirm improvement and stock state was restored. |
| X2D 100C | [Temporary Wi-Fi page button](x2d/research/4.2.0/TEMPORARY_WIFI_BUTTON_TRIAL.md) | Temporary copy passed transfer checks but execution was denied; the button never appeared on the camera. |
| X2D 100C | [Object recognition](x2d/object-recognition/README.md) | Frame adapters and offline contracts investigated; no deployable live-view recognition port. |
| X2D 100C | [Encrypted models and CPU inference](x2d/research/4.2.0/MODEL-DECRYPTION-AND-CPU-RESULTS.md) | 30 first-generation containers decrypted and signatures checked; isolated NNF CPU synthetic-input test is not live recognition. |
| X2D 100C | [Monochrome frame candidate](x2d/CodeTests/monochrome-frame-contracts/README.md) | Attributed source subset passed six offline tests; frame-ownership issue reproduced, camera behavior unverified. |
| X2D 100C | [Lens and menu-state compatibility](x2d/research/4.2.0/LENS-AND-STATUS-COMPATIBILITY.md) | XCD 45/3.5 and menu lifecycle reviewed; user-reported root cause is not closed. |
| X2D 100C | [Power and USB startup diagnosis](x2d/research/4.2.0/USB-POWER-STARTUP-DIAGNOSIS.md) | Battery reinsertion, shoulder-screen H, and USB recovery paths documented; no validated fix. |
| X2D 100C | [Bluetooth wake behavior](x2d/research/4.2.0/WIRELESS-AND-RECOVERY-UPDATE.md) | One device woke from stock sleep via phone; waking from full power-off remains unimplemented. |
| X2D 100C | [exMCU boot and recovery](x2d/research/4.2.0/EXMCU-BOOT-AND-RECOVERY.md) | E2 USB boot and MCU SPI recovery paths mapped; rescue loader and eMMC write-back are absent. |
| X2D 100C | [CIM containers and updater](x2d/research/4.2.0/FIRMWARE-CONTAINERS-UPDATE.md) | Eight-payload stock repacking matched byte-for-byte; modified-package signing and full installation unproven. |
| X2D 100C | [Offline firmware tools](x2d/tools/README.md) | Read-only firmware, PDAF, spectral, and model-structure helpers are available; vendor inputs are not distributed. |
| X2D 100C | [Security disclosure](x2d/research/4.2.0/SECURITY-DISCLOSURE-STATUS.md) | Vendor receipt and public/private maintenance status recorded; report details and endorsement are not claimed. |


## Research references and their contribution

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

## 支持研究

[查看赞助方式](SUPPORT.md)

## 欢迎交流

欢迎交流、分享研究发现和使用反馈。欢迎通过 [Issues](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/issues) 讨论问题与建议，也欢迎提交 [Pull Requests](https://github.com/radium-wang/Hasselblad-X-System-CIM-Firmware-Research-Feature-Extensions/pulls) 改进代码、文档和测试。

想体验相机扩展功能？欢迎前往 [X2D/907 一键扩展功能工具包](https://github.com/Gothenburg-R-D-Team/x2d-907-one-click-extension-toolkit)：面向第一代 X2D 100C / 907X & CFV 100C（原厂固件 4.2.0）的实验性 macOS / Windows 桌面工具，提供连续对焦、追踪对焦、人眼识别等可选功能。适配范围、下载与恢复说明请以工具包仓库为准。

## 项目概述

这是一个面向哈苏 X 系统相机互操作性、用户界面、自动对焦行为、功能扩展与固件格式的非官方独立研究项目。

本仓库只收录贡献者有权公开的源码、离线工具、测试和经过脱敏的研究结论。厂商固件、原厂共享库、模型、DSP 或内核文件、从原厂程序提取或修改的 QML 编译单元、设备日志及本机构建产物均不随仓库分发。

**研究免责声明：** 使用任何实机相关材料前，请先阅读[研究免责声明](DISCLAIMER.md)。本项目与被提及的厂商没有关联，所有实验都必须基于用户自己的授权并自行承担风险。

## 现有研究与进展

下表按主题归并本仓库现有研究。各链接说明证据和具体验证边界；逐项结果见[研究成果总表](RESEARCH_RESULTS.md)。

| 机型 | 研究主题 | 当前进展与限制 |
| --- | --- | --- |
| X2D II | [八向摇杆实现](x2d2/joystick-eight-way/README.md) | 1.3.18.1 输入状态机、原生适配及离线测试；45秒实体测试确认四斜向、长按、松手正常。未做常驻安装或长期验收。 |
| X2D II | [LiDAR 测距与自动对焦](x2d2/research/1.3.16.2/LIDAR-PIPELINE.md) | 离线梳理 ADS6401 深度数据及 AF-S／AF-C 决策链；未做二代实机验收。 |
| X2D II | [启动资源与版本差异](x2d2/research/1.3.16.2/STARTUP-LOGO-VARIANTS.md) | 核对六个硬件阶段标识与 Logo 资源；冷启动选择链未验证。 |
| X2D II | [显示与低灰 mura](x2d2/research/1.3.16.2/DISPLAY-MURA.md) | 梳理亮度映射与 RGB LUT；尚无个体屏幕空间补偿验证。 |
| X2D II | [IBIS 与地球自转](x2d2/research/1.3.16.2/IBIS-GPS-EARTH-ROTATION.md) | 确认定位字段与补偿调用；控制器公式和无定位降级尚不清楚。 |
| X2D II | [对焦图标与界面资源](x2d2/README.md) | 提取 AF-S／AF-C 界面资源供离线查看；未改动实机界面。 |
| X2D II | [加密模型与 PDAF](x2d2/research/1.3.16.2/MODEL-AND-PDAF-STATUS.md) | 39 个模型文件仍未解密；PDAF 仅静态对照，无二代推理或实机测试。 |
| X2D 100C | [AF-C 后端与菜单](x2d/research/AFC-MENU-RUNTIME-RESULT.md) | 实机进入原厂连续对焦状态；仅开放菜单 gate 不等于对焦效果验收。 |
| X2D 100C | [第十二格菜单入口](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/README.md) | 临时实机确认原厂风格菜单交互；公开源码不是持久安装包。 |
| X2D 100C | [AF-S Type1 扫描候选](x2d/CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md) | 精确版本离线生成器验证两条指令变化；整体合焦与相机安全未实测。 |
| X2D 100C | [AFT 与眼部识别](x2d/research/4.2.0/AF-EYE-AND-SPEED-UPDATE.md) | 独立候选完成 AFT 与眼部状态共存实机反馈；整合行为与光学收益分别验收。 |
| X2D 100C | [三档对焦速度](x2d/research/4.2.0/AF-EYE-AND-SPEED-UPDATE.md) | 低／中／高选择器有本地及部分用户验收；倍率不代表整体合焦提速。 |
| X2D 100C | [原厂对焦参数与 PDAF 试验](x2d/research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md) | 只读核对原厂参数；80→100 临时试验减少拉风箱却频繁虚焦，已淘汰。 |
| X2D 100C | [CDAF、Kalman、TAF、VDAF 与 BDAF](x2d/research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md) | 已分析代码路径与候选契约；没有新算法实机有效的结论。 |
| X2D 100C | [对焦仿真与四帧滤波](x2d/research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md) | 七类仿真场景及四帧滤波候选完成离线检查；不代表相机合焦成功率。 |
| X2D 100C | [AFT 人脸区域与显示](x2d/research/4.2.0/AFT-FACE-TRACKING-RESULTS.md) | 区域发布与主框选择有受限 RAM 实机反馈；持续追焦仍待验收。 |
| X2D 100C | [425 区域 PDAF 候选](x2d/CodeTests/pdaf-only-shadow/PDAF425.md) | 已记录采样几何、离线核心及原厂历史观察；未安装 425 点升级。 |
| X2D 100C | [二代对焦策略对照](x2d/research/4.2.0/FOCUS-STRATEGY-PORT-BOUNDARIES.md) | 静态对照指出数据与时序适配缺口；区域数相同不足以完成策略移植。 |
| X2D 100C | [光谱白平衡](x2d/research/4.2.0/SPECTRAL-WHITE-BALANCE.md) | 静态梳理 AS7341 与 AWB 权重链；未测单机读数及成像收益。 |
| X2D 100C | [像素位移采集](x2d/research/4.2.0/PIXEL-SHIFT-CAPTURE-RESULTS.md) | 已实拍 4／6／16 张 RAW 序列；物理位移精度与整图质量未量化。 |
| X2D 100C | [电脑端 DNG 合成](x2d/research/4.2.0/JSR-METAL-COMPARISON.md) | 四帧生成 4.0824 亿像素 RGB16 DNG；严格逐像素一致性未通过，光学增益未证实。 |
| X2D 100C | [像素位移离线处理库](x2d/pixel-shift/README.md) | 公开四／六帧处理子集以合成输入通过主机测试；与 JSR 处理器不同。 |
| X2D 100C | [25MP 低噪与录像](x2d/research/4.2.0/IMAGING-AND-VIDEO-UPDATE.md) | 软件缩图仍是候选；未证实全幅硬件合并或可播放的机内视频。 |
| X2D 100C | [开机画面应用 Startup Studio](x2d/research/4.2.0/STARTUP-STUDIO-UPDATE.md) | 普通 X2D 已测 Mac 安装与原厂恢复；Windows 和其他机型尚需完整实机验收。 |
| X2D 100C | [工具包亮度与 Windows 历史](x2d/research/4.2.0/TOOLKIT-BRIGHTNESS-AND-WINDOWS.md) | 归档功能行为和桌面检查；本文不据此宣称实体屏幕或原生 Windows 验收。 |
| X2D 100C | [开机 Logo 研究](x2d/research/4.2.0/STARTUP-LOGO-REPLACEMENT.md) | 主屏图提取及彩色短时显示已测；肩屏资源和持久开机链未解决。 |
| X2D 100C | [快门动画](x2d/CodeTests/shutter-animation-preview/README.md) | 有离线视觉候选及时序分析；未宣称已安装实机功能。 |
| X2D 100C | [Doom](x2d/doom/README.md) | 引擎、快门开火、音效及滑动控制有一代受限反馈；公开树不含部署后端。 |
| X2D 100C | [Shimeji 透明宠物](x2d/shimeji-overlay/README.md) | 透明覆盖层曾有临时实机交互；公开模块提供桌面检查，不含固件安装器。 |
| X2D 100C | [整机界面响应](x2d/research/4.2.0/UI-RESPONSIVENESS.md) | 已测原厂帧率和触摸时序；三轮试验未确认改善，最终恢复原厂。 |
| X2D 100C | [Wi-Fi 页面临时按钮](x2d/research/4.2.0/TEMPORARY_WIFI_BUTTON_TRIAL.md) | 临时副本通过传输校验，但执行被拒绝；按钮未在相机显示。 |
| X2D 100C | [目标识别](x2d/object-recognition/README.md) | 研究帧适配与离线契约；没有可部署的实时取景识别移植。 |
| X2D 100C | [加密模型与 CPU 推理](x2d/research/4.2.0/MODEL-DECRYPTION-AND-CPU-RESULTS.md) | 30 个一代容器完成解密与签名核对；独立 NNF CPU 合成输入测试不等于实时识别。 |
| X2D 100C | [黑白帧候选](x2d/CodeTests/monochrome-frame-contracts/README.md) | 保留作者归属的源码子集通过六项离线测试；复现帧所有权问题，实机待验收。 |
| X2D 100C | [镜头与菜单状态兼容](x2d/research/4.2.0/LENS-AND-STATUS-COMPATIBILITY.md) | 已审查 XCD 45/3.5 与菜单生命周期；用户反馈根因尚未闭合。 |
| X2D 100C | [电源与 USB 启动诊断](x2d/research/4.2.0/USB-POWER-STARTUP-DIAGNOSIS.md) | 记录电池重装、肩屏 H 与 USB 恢复排查路径；没有已验证修复。 |
| X2D 100C | [蓝牙唤醒行为](x2d/research/4.2.0/WIRELESS-AND-RECOVERY-UPDATE.md) | 一次实机确认手机可唤醒原厂自然休眠；真正关机唤醒未实现。 |
| X2D 100C | [exMCU 启动与恢复](x2d/research/4.2.0/EXMCU-BOOT-AND-RECOVERY.md) | 梳理 E2 USB 启动与 MCU SPI 恢复路径；缺救援加载器与 eMMC 回写。 |
| X2D 100C | [CIM 容器与更新器](x2d/research/4.2.0/FIRMWARE-CONTAINERS-UPDATE.md) | 八载荷原内容重封与官方逐字节一致；修改包签名与完整安装未证实。 |
| X2D 100C | [固件离线工具](x2d/tools/README.md) | 提供只读固件、PDAF、光谱及模型结构工具；不分发原厂输入。 |
| X2D 100C | [安全披露](x2d/research/4.2.0/SECURITY-DISCLOSURE-STATUS.md) | 记录厂商回执及公开／私有维护状态；不公开报告细节，也不宣称认可。 |


## 研究参考资料及其帮助

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

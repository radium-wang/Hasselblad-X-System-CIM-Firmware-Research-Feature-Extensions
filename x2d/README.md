# X2D 100C Research

The X2D tree covers firmware 4.2.0 unless a document states otherwise.

- [GPR / GVID 非 CNN RAW 视频](CodeTests/gpr-gvid-raw-video/README.md)：固定外部 GPR 依赖的约 100 MP 离线编码、标定提取与桌面播放实验；不是机内录像解锁。

- [AF-S Type1 scan candidate](CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md): exact-version offline patch generator and benchmark rules; not device-tested.
- [Menu extension](CodeTests/temporary_af_speed_probe/original-menu-candidate/README.md): source QML, icon and offline checks for the twelfth menu entry.
- [AF-C research](CodeTests/x2d-afc-research/README.md): public summary and exact-version offline gate patcher.
- [Object recognition](object-recognition/README.md): compatibility audit, frame adapter and offline contract tests; not a deployable port.
- [Shutter animation](CodeTests/shutter-animation-preview/README.md): browser/QML visual candidate, read-only timing analysis and audio source.
- [Doom](doom/README.md)：第一代 4.2.0 的真实引擎、快门开火、音效与滑动；独立 GPL-2.0-or-later，保留引擎、界面及桌面检查；设备运行器未公开。
- [Shimeji 透明宠物](shimeji-overlay/README.md)：引擎适配、QML 点击穿透和桌面验证；临时实机用户确认，公开版不含安装链。
- [菜单响应诊断与三轮试验](research/4.2.0/UI-RESPONSIVENESS.md)：原厂 57–58 FPS 但拖动落后；未确认改善，已恢复原厂。
- [Firmware tools](tools/README.md): offline firmware and QML analysis helpers.
- [静态开机 Logo 位置调查](research/4.2.0/STARTUP-LOGO-LOCATION.md)：主屏原图已离线还原；肩屏资源路径已找到，图像数据仍待提取。
- [开机 Logo 替换实验](research/4.2.0/STARTUP-LOGO-REPLACEMENT.md)：主屏原厂灰度图与用户提供的 250×250 彩色图均已完成短时 RAM 显示和回退验证；肩屏待解析。
- [exMCU 启动与恢复边界](research/4.2.0/EXMCU-BOOT-AND-RECOVERY.md)：区分 MCU 备份、主系统 A/B 与 E2 USB 启动模式。
- [Research notes](research/): selected sanitized findings and validation limits.
- [External research references](references/EXTERNAL-RESEARCH.md): citation-only provenance, including the X2D CIM notes that inspired the AF-C investigation.

The public tree contains offline analysis, source UI and desktop checks. Device observation scripts and deployment tools are not included. PDAF record handling is limited to local anonymization and offline analysis of operator-provided text.

## 最新研究汇总（归档更新至 2026-10-16）

最新验收状态以[成果总表](../RESEARCH_RESULTS.md)及分主题报告为准，早期“尚未验证”文字保留其历史范围。

- [425 区域候选源码与同帧快照契约](CodeTests/pdaf-only-shadow/PDAF425.md)：补齐 2026-10-08 历史原厂观察和离线实现；不是可安装升级，未完成二代完整策略移植。
- [PDAF 实验记录方法](CodeTests/pdaf-only-shadow/PDAF425-RECORDING.md)：记录模板、本地文本脱敏与离线回放；不含设备采集或连接步骤。
- [自动亮度、Windows 界面与退出修正摘要](research/4.2.0/TOOLKIT-BRIGHTNESS-AND-WINDOWS.md)：独立工具包历史功能记录与验证边界，不收录产品操作后端。
- [AFT、眼部共存与三档速度](research/4.2.0/AF-EYE-AND-SPEED-UPDATE.md)
- [像素位移实拍、倒计时及 JSR 电脑合成](research/4.2.0/PIXEL-SHIFT-CAPTURE-RESULTS.md)；[独立离线 C 处理库](pixel-shift/README.md)
- [JSR 蓝鸟腹部、文字的解析力三方对比](research/4.2.0/JSR-METAL-COMPARISON.md)：同位置局部及剖面核验，Wine／Metal 可见解析细节相当，早期全图严格一致性失败保留
- [Startup Studio 应用与菜单生命周期](research/4.2.0/STARTUP-STUDIO-UPDATE.md)
- [一代模型解密、签名与独立 CPU 合成输入测试](research/4.2.0/MODEL-DECRYPTION-AND-CPU-RESULTS.md)；[TFLite 结构工具](tools/model-structure/README.md)
- [425 区域边界](research/4.2.0/PDAF-425-BOUNDARIES.md)、[采样几何](research/4.2.0/PDAF-SAMPLING-GEOMETRY.md)、[控制策略对照](research/4.2.0/FOCUS-STRATEGY-PORT-BOUNDARIES.md)
- [AS7341 光谱白平衡链路](research/4.2.0/SPECTRAL-WHITE-BALANCE.md)；[对焦／光谱离线工具](tools/firmware-analysis/focus-and-spectral/README.md)
- [FXGab69 黑白候选的本地审查](research/4.2.0/MONOCHROME-CANDIDATE-REVIEW.md)
- [FXGab69 黑白帧离线源码收录](CodeTests/monochrome-frame-contracts/README.md)：2026-10-14 收录 PR #9 的处理核心与所有权测试，保留作者及来源许可；6 项离线测试通过，实机待验收。
- [镜头与模式状态兼容审查](research/4.2.0/LENS-AND-STATUS-COMPATIBILITY.md)
- [电池重装与肩屏 H 的诊断边界](research/4.2.0/USB-POWER-STARTUP-DIAGNOSIS.md)
- [安全披露与公开维护状态](research/4.2.0/SECURITY-DISCLOSURE-STATUS.md)

- [原厂对焦参数与实验](research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md)
- [AFT 人脸区域与主框](research/4.2.0/AFT-FACE-TRACKING-RESULTS.md)
- [无线与恢复更新](research/4.2.0/WIRELESS-AND-RECOVERY-UPDATE.md)
- [固件与模型容器](research/4.2.0/FIRMWARE-CONTAINERS-UPDATE.md)
- [像素位移、低噪与视频](research/4.2.0/IMAGING-AND-VIDEO-UPDATE.md)

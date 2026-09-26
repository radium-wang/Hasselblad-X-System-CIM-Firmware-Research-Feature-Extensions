# Research Results

Updated: 2026-09-26.

## Reproducibility scope

The repository now includes [`scripts/reproduce_offline.py`](scripts/reproduce_offline.py) and the full [reproduction guide](REPRODUCE.md) for the safe offline evidence. Read the [Research Disclaimer](DISCLAIMER.md) before using any device-side material. It is a sanitized research release; camera-side reproduction still requires the exact authorized inputs described in that guide.

- Reproducible from the repository alone: static audits, offline compatibility checks, candidate generators, host-side tests, and the documented analysis of the included source and research records.
- Requires authorized exact-version inputs and hardware: menu runtime behavior, AF-S and AF-C experiments, stock face/eye detection behavior, and any camera-side validation. The required firmware trees, vendor libraries, compiled QML units, and device access are not distributed here.
- Intentionally omitted: vendor firmware and binaries, derived QML units, encrypted models, DSP or kernel files, device logs, local build outputs, keys, and installation or root/ADB tooling that could directly reproduce an unauthenticated system-write chain.
- Readers can audit and extend the research and reproduce its offline evidence. They cannot download this repository and recreate every device-side function or the exact camera state from the repository alone.

## X2D menu extension

- A candidate was implemented that preserves the stock menu, adds a twelfth entry named “耍起功能”, and uses an original SVG icon.
- During temporary hardware testing, the operator confirmed the stock-style paging, upper-left back action, master switch, and AF-C sub-switch in both directions.
- The default focus popup is AF-S/MF; after AF-C is enabled it becomes AF-S/AF-C/MF; after it is disabled the two-item list returns.
- A one-minute watchdog restores the stock GUI and then clears the temporary payload and debug state.
- A resident build, half-press return to live view, sleep/wake, first-render cost, and cross-reboot acceptance remain incomplete.

## X2D AF-S speed-up

- Two fixed-request Type2 direction-scan branches were located in `_exec_pdaf_afs_process` for version 4.2.0.
- The offline candidate changes only those two Type2 requests to Type1; the 1,872-byte function changes two instructions and two bytes.
- In the checked speed model, the request value changes from `0.25B` to `0.5B`; this does not mean that total focus time becomes twice as fast.
- Four candidate tests pass. The candidate has not been accepted on hardware, and there are no low-light, close-focus, overshoot, thermal, or power measurements.

## X2D AF-C

- The investigation was initially motivated by the external [`x2d-cim-notes`](x2d/references/EXTERNAL-RESEARCH.md) research notes. That repository is cited as inspiration and provenance, not as direct evidence or a copied implementation.
- The stock 4.2.0 backend was confirmed to contain a continuous-autofocus state machine.
- A hardware experiment observed a single-focus operation entering continuous-focus state and returning continuous success; releasing the control stopped it and returned to AF-S.
- Opening `CameraUI.canChangeAfc` alone does not extend the Control Screen. The stock model contains only AF-S/MF and needs three additional model objects plus popup layout changes.
- A temporary combined candidate passed menu-display and switch-flow checks. Long-term stability, power use, sleep, cross-reboot behavior, and a persistent production design remain incomplete.
- The X2D II fast-AF stack cannot be copied directly: the two generations use different sensors, ranging hardware, AF ABI, and tuning stack.

## X2D factory debug UI

- Static analysis identified `SystemProperties::isAdbLocked()` in the stock 4.2.0 GUI. It reads `sys.usb.config`; the presence of `adb` selects the unlocked maintenance branch at GUI startup.
- Restarting the unmodified stock GUI while that USB configuration is active exposes the factory maintenance surface, including `Debug Mode`, related developer entries, and the white OSD clock. `system.debug_mode` is a visible state value, not the unlock trigger.
- The public [`factory_debug_ui.py`](x2d/CodeTests/factory-debug-ui/factory_debug_ui.py) tool reads a fixed state surface, checks the exact stock GUI hash and process context, can explicitly restart the stock GUI through an already-authorized ADB endpoint, and verifies the production-locked recovery values.
- The detailed evidence record is [`FACTORY-DEBUG-UI-FINDINGS.md`](x2d/research/4.2.0/FACTORY-DEBUG-UI-FINDINGS.md).
- Factory-USB ADB enablement, arbitrary shell execution, `/system` remounting, file upload, process-memory writes, persistence, and payload installation remain intentionally unpublished. This finding is separate from AF-C, face/eye detection, and object recognition and does not prove a complete deployable feature.

## X2D face/eye detection enablement

- The first-generation X2D 4.2.0 stock runtime was confirmed to expose face/eye detection paths, including `FaceInfo`, `E_FaceDetection`, `setFaceDetectionMode`, and `setFaceRoiData`.
- These stock interfaces are the documented basis for enabling and using the camera's eye-detection function. This is separate from the second-generation Human/Pet/Vehicle object-recognition backend.
- The public evidence establishes the first-generation face/eye path and its ROI interface; it does not establish stable second-generation object recognition, eye-lock AF, or AF-C coupling.
- The eye-detection path should remain independent: if an experimental object backend fails, stock face/eye detection and AF-S/AF-C must remain available.

## X2D object recognition

- The X2D II 1.3.16.2 to X2D 4.2.0 model containers, dependencies, symbols, DSP/kernel components, frame structures, and communication interfaces were audited.
- A compatibility gate rejects packaging second-generation binaries directly as a first-generation candidate.
- A second-generation Pet model returned `-10` at the first-generation stock verification entry and did not reach inference; a first-generation stock model passed the comparison path.
- The frame-descriptor component passed host safety checks, an ARM64 build, and an in-camera synthetic-data self-test.
- An isolated no-initialization link diagnostic for the second-generation stock libraries passed on first-generation hardware, but no model, tracking, or AF function was called.
- An early CPU single-frame Vehicle detection took about 1.289 seconds and peaked at about 102 MB; the dynamic-box route was retired after stutter/flicker feedback.
- Thirty-seven offline contract tests pass; seven are skipped because no valid fixed vendor input was provided.
- Real frames, real-time recognition, stable tracking, AF ROI, and AF-C coupling remain incomplete.

## X2D shutter animation and sound

- A four-stage 400 ms shutter animation and browser preview were produced.
- Software logs provided complete show/hide and restore samples of 995 ms and 663 ms; these are not optical screen-blackout durations.
- The old direct-PCM approach interfered with stock notification sounds, so the work moved to the stock audio-client path; the operator confirmed that the revised one-shot preview was audible.
- Audio assets are not in the repository, and their redistribution license has not been confirmed.
- Cold boot, shutter-event coupling, and long-term coexistence with stock notification sounds remain to be accepted.

## X2D II

- The current material is regional offline research and checking scripts for 1.3.16.2.
- First- and second-generation models are kept strictly separate; addresses, images, and validation conclusions are not reused across generations.

## Materials not published

This public candidate does not contain vendor binaries, derived QML units, device logs, personal identifiers, local build outputs, key material, regional license-signing modules, or tools that can directly reproduce an unauthenticated root/ADB/system-write chain. Related conclusions may be described in the repository, but original materials and high-risk proof of concept work require separate authorization, licensing, and coordinated disclosure review.

---

# 研究成果总表

更新日期：2026-09-26。

## 可复现范围

仓库现在包含 [`scripts/reproduce_offline.py`](scripts/reproduce_offline.py) 和完整的[复现指南](REPRODUCE.md)，用于复现安全的离线证据。使用任何实机相关材料前，请先阅读[研究免责声明](DISCLAIMER.md)。它仍是经过脱敏的研究发布版；相机侧复现需要按指南准备精确且获得授权的输入。

- 仅凭仓库即可复现：静态审计、离线兼容性检查、候选生成器、电脑端测试，以及对仓库内源码和研究记录的分析。
- 菜单运行时行为、AF-S 与 AF-C 实验、原厂人脸/眼部识别行为以及所有相机侧验证，需要获得授权的对应版本输入和实机。所需固件树、原厂库、编译后的 QML 单元和设备访问权限没有随仓库分发。
- 有意不公开：厂商固件和二进制、派生 QML 单元、加密模型、DSP 或内核文件、设备日志、本机构建输出、密钥，以及可以直接复现未鉴权系统写入链路的安装器或 root/ADB 工具。
- 读者可以审计和扩展研究，也可以复现离线证据；但不能只下载这个仓库，就重建全部设备侧功能或恢复相机的完全相同状态。

## X2D 菜单修改

- 已实现保留原厂菜单、在第十二格加入“耍起功能”入口和自有 SVG 图标的候选。
- 临时实机测试中，用户确认原厂风格滚动页、左上角返回、总开关与 AF-C 子开关的正反向流程正常。
- 默认对焦弹窗为 AF-S/MF；启用 AF-C 后为 AF-S/AF-C/MF；关闭后恢复两项。
- 一分钟 watchdog 自动恢复原厂 GUI，随后临时载荷和调试状态完成清理。
- 开机常驻版、半按回取景、休眠/唤醒、首次绘制开销和跨重启仍待完整验收。

## X2D AF-S 提速

- 对 4.2.0 的 `_exec_pdaf_afs_process` 定位到两条固定请求 Type2 的方向扫描分支。
- 离线候选只把两处 Type2 改为 Type1；1872 字节函数仅改变两条指令、两个字节。
- 在已核对的速度模型中，请求值从 `0.25B` 变为 `0.5B`；这不等于总合焦时间提升 2 倍。
- 4 项候选测试通过；尚未上机，没有低照度、近摄、过冲、温升或功耗数据。

## X2D AF-C

- 本次调查最初受到外部 [`x2d-cim-notes`](x2d/references/EXTERNAL-RESEARCH.md) 研究笔记启发。该仓库在此作为灵感和来源记录引用，不是本项目的直接证据，也没有复制其实现。
- 证实 4.2.0 原厂后端已包含连续对焦状态机。
- 真机运行时实验观察到单次对焦进入连续对焦状态并返回连续成功，松开后停止并恢复 AF-S。
- 单独打开 `CameraUI.canChangeAfc` gate 不足以扩展 Control Screen；原厂模型只有 AF-S/MF，需额外的三项模型与弹窗布局。
- 临时组合候选完成菜单显示和开关流程验收；长期稳定性、功耗、休眠、跨重启及正式持久化方案未完成。
- X2D II 的快速 AF 栈不能直接复制：两代传感器、测距硬件、AF ABI 和调校栈不同。

## X2D 原厂调试界面

- 静态分析定位到 4.2.0 原厂 GUI 的 `SystemProperties::isAdbLocked()`。它读取 `sys.usb.config`；含有 `adb` 时，GUI 启动阶段进入未锁定的原厂维护分支。
- 在该 USB 配置下重新启动未修改的原厂 GUI，会出现原厂维护界面，包括 `Debug Mode`、相关开发项目和白色 OSD 时钟。`system.debug_mode` 是可见状态值，不是解锁触发器。
- 公开的 [`factory_debug_ui.py`](x2d/CodeTests/factory-debug-ui/factory_debug_ui.py) 读取固定状态面，检查原厂 GUI 精确哈希和进程上下文，可以通过已经授权的 ADB 端点显式重启原厂 GUI，并检查恢复到量产锁定所需的状态值。
- 详细证据记录见 [`FACTORY-DEBUG-UI-FINDINGS.md`](x2d/research/4.2.0/FACTORY-DEBUG-UI-FINDINGS.md)。
- factory USB 开启 ADB、任意 shell、`/system` 重挂、文件上传、进程内存写入、持久化和载荷安装仍有意不公开。该发现独立于 AF-C、人脸/眼部识别和对象识别，也不等于完整可部署功能。

## X2D 人脸/眼部识别开启

- 已确认第一代 X2D 4.2.0 原厂运行面保留人脸/眼部检测路径，包括 `FaceInfo`、`E_FaceDetection`、`setFaceDetectionMode` 和 `setFaceRoiData`。
- 这些原厂接口构成开启和使用相机眼部识别功能的公开研究依据；它与第二代 Human / Pet / Vehicle 对象识别后端是两条不同路线。
- 当前公开证据确认了第一代人脸/眼部路径及其 ROI 接口，但不等于第二代对象识别、眼部锁定对焦或 AF-C 联动已经稳定实现。
- 眼部识别路径应保持独立：实验性对象后端失败时，原厂人脸/眼部识别以及 AF-S/AF-C 仍应可用。

## X2D 对象识别

- 完成 X2D II 1.3.16.2 到 X2D 4.2.0 的模型容器、依赖、符号、DSP/内核、帧结构和通信接口审计。
- 审计门禁会拒绝把二代二进制直接包装成第一代候选。
- 二代 Pet 模型在一代原厂验证入口返回 `-10`，未进入推理；一代原厂模型对照成功。
- 帧描述符组件通过宿主安全检查、ARM64 构建和机内合成数据自检。
- 二代原厂库的无初始化隔离链接诊断在一代实机通过，但没有调用模型、追踪或 AF。
- 早期 CPU 单帧 Vehicle 检测约 1.289 秒、峰值约 102 MB；动态框路线因卡顿/闪烁反馈退役。
- 37 项离线契约测试通过，7 项因未提供合法的固定原厂输入而跳过。
- 真实帧、实时识别、稳定追踪、AF ROI 和 AF-C 联动均未完成。

## X2D 快门动画与声音

- 形成四阶段 400 ms 快门动画与浏览器预览。
- 软件日志得到过 995 ms 和 663 ms 的完整显示隐藏/恢复样本；它们不是屏幕光学黑屏时间。
- 旧直接 PCM 方案会干扰原厂提示音，后续改为原厂音频客户端链路；用户确认新版单次试听可听。
- 音频素材不在仓库中，且其再分发许可未确认。
- 冷启动、拍摄事件联动和原厂提示音长期共存仍待验收。

## X2D II

- 现有内容为 1.3.16.2 地区离线研究与检查脚本。
- 第一代与第二代机型严格分开，不复用地址、镜像或验证结论。

## 未公开材料

本公开候选不包含厂商二进制、派生 QML unit、设备日志、个人标识、构建输出、密钥材料、地区授权签发模块或可直接复现未鉴权 root/ADB/系统写入链路的工具。相关结论可以在仓库中说明，但原始材料和高风险 PoC 需要独立的权限、许可和协调披露审查。

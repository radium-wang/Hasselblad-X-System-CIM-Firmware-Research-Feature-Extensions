# Reproduce the Research

This guide is the entry point for reproducing the published research. It separates repository-only checks from camera-side experiments that require an authorized, exact-version input set.

## 1. Run the complete safe offline suite

Use Python 3.9 or newer from the repository root:

```sh
python3 -m pip install -r x2d/CodeTests/temporary_af_speed_probe/standalone_handoff/requirements.txt
python3 scripts/reproduce_offline.py
```

The runner executes the publication safety check, the AF-S candidate tests, the object-recognition offline contract tests, the shutter timing tests, and the factory-debug-UI state/guard tests. It never connects to a camera, writes firmware, installs a payload, or starts a device experiment.

To include tests that inspect user-supplied firmware extraction roots, provide all four read-only roots:

```sh
python3 scripts/reproduce_offline.py \
  --source-system-root /path/to/x2d2-system-root \
  --source-vendor-root /path/to/x2d2-vendor-root \
  --target-system-root /path/to/x2d-system-root \
  --target-vendor-root /path/to/x2d-vendor-root
```

The roots must come from firmware and devices that the operator is authorized to use. They are never copied into the repository.

## 2. Reproduce each research area

| Area | Entry point | What can be reproduced |
| --- | --- | --- |
| Menu extension | `x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/README.md` | QML source structure, SVG asset, desktop checks, and the documented temporary runtime result |
| AF-S speed candidate | `x2d/CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md` | Exact-version hash gate, Type2-to-Type1 candidate generation, byte-diff checks, and offline benchmark calculation |
| AF-C | `x2d/CodeTests/x2d-afc-research/README.md` | Exact-hash offline gate patching and the model/layout reasoning; a complete persistent feature is not supplied |
| Face/eye detection | `x2d/object-recognition/research/X2D2-TO-X2D-PORT.md` | First-generation face/eye interfaces and ROI contracts; the stock model and camera-side behavior must be supplied by the operator |
| Object recognition | `x2d/object-recognition/README.md` | Compatibility audit, frame adapter, model-container checks, and offline contract tests |
| Factory debug UI | `x2d/CodeTests/factory-debug-ui/README.md` | Stock GUI lock-state finding, fixed ADB state readback, and an explicitly confirmed stock-GUI restart |
| Shutter animation | `x2d/CodeTests/shutter-animation-preview/README.md` | Browser/QML preview, timing analysis, and audio-client experiment notes |

## 3. Camera-side reproduction

Camera-side results depend on the exact X2D 4.2.0 or X2D II 1.3.16.2 environment recorded by each experiment. Read the experiment README before running anything. The public repository intentionally does not contain vendor firmware, compiled QML units, encrypted models, DSP or kernel files, runtime writers, installers, or device logs. A reader can reproduce the procedure after supplying lawful inputs and explicit device authorization; the repository alone cannot recreate those proprietary inputs or the original camera state. The factory-debug-ui implementation assumes ADB is already authorized and does not include the factory USB command that enables ADB.

Do not treat an offline candidate, a menu that renders, or a successful link diagnostic as a complete deployed feature. The experiment documents state the required acceptance checks, recovery path, and remaining limits.

---

# 复现研究成果

本说明是复现入口。它把仅依赖仓库的检查，与必须使用获得授权的精确版本输入和实机的实验分开说明。

## 1. 运行完整的安全离线套件

在仓库根目录使用 Python 3.9 或更高版本：

```sh
python3 -m pip install -r x2d/CodeTests/temporary_af_speed_probe/standalone_handoff/requirements.txt
python3 scripts/reproduce_offline.py
```

该入口会依次运行公开发布安全检查、AF-S 候选测试、对象识别离线契约测试、快门时序测试以及原厂调试界面的状态/门禁测试。它不会连接相机、写入固件、安装载荷，也不会启动实机实验。

如果要加入读取使用者固件提取目录的测试，请一次性提供四个只读目录：

```sh
python3 scripts/reproduce_offline.py \
  --source-system-root /path/to/x2d2-system-root \
  --source-vendor-root /path/to/x2d2-vendor-root \
  --target-system-root /path/to/x2d-system-root \
  --target-vendor-root /path/to/x2d-vendor-root
```

这些目录必须来自操作者有权使用的固件和设备，且不会复制到仓库中。

## 2. 分主题复现

| 主题 | 入口 | 可以复现的内容 |
| --- | --- | --- |
| 菜单扩展 | `x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/README.md` | QML 源码结构、SVG 资源、电脑端检查和已记录的临时实机结果 |
| AF-S 提速候选 | `x2d/CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md` | 精确版本哈希门禁、Type2→Type1 候选生成、字节差异检查和离线基准计算 |
| AF-C | `x2d/CodeTests/x2d-afc-research/README.md` | 精确哈希离线 gate 修改和模型/布局分析；没有提供完整持久化功能 |
| 人脸/眼部识别 | `x2d/object-recognition/research/X2D2-TO-X2D-PORT.md` | 第一代人脸/眼部接口和 ROI 契约；原厂模型及相机侧行为需要操作者自行提供 |
| 对象识别 | `x2d/object-recognition/README.md` | 兼容性审计、帧适配、模型容器检查和离线契约测试 |
| 原厂调试界面 | `x2d/CodeTests/factory-debug-ui/README.md` | 原厂 GUI 锁定状态发现、固定 ADB 状态读回和需要明确确认的原厂 GUI 重启 |
| 快门动画 | `x2d/CodeTests/shutter-animation-preview/README.md` | 浏览器/QML 预览、时序分析和音频客户端实验记录 |

## 3. 实机复现

实机结果依赖各实验记录的精确环境：X2D 4.2.0 或 X2D II 1.3.16.2。运行任何内容前先阅读对应实验 README。公开仓库有意不包含厂商固件、编译后的 QML 单元、加密模型、DSP 或内核文件、运行时写入器、安装器和设备日志。原厂调试界面实现假设 ADB 已经授权，不包含通过 factory USB 开启 ADB 的命令。读者在提供合法输入并取得明确设备授权后，可以按步骤复现；但仓库本身不能重新生成这些原厂输入或原相机状态。

离线候选、能够显示的菜单或通过的链接诊断都不能直接视为完整部署功能。各实验文档列出了所需验收、恢复路径和剩余限制。

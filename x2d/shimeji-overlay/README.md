# X2D Shimeji 透明宠物覆盖层

适用研究环境：第一代 X2D 100C，固件 4.2.0 build24849，Android 9 / API 28、ARM64、Qt 6.4.1。这是应用层移植源码与桌面复现入口，不是固件升级包或相机安装器；X2D II 未验证。

## 已验证的行为

2026-10-06 的临时实机版本运行 libshijima 角色状态机，可走动、爬墙、拖拽与双击互动。透明覆盖层仅保留宠物和右上角 Exit，背景与角色透明像素让点击穿过到底层菜单。用户确认“背景透明，菜单可点，拖动更跟手”。这属于一次实机与用户反馈，不代表长期功耗、拍摄稳定性、冷启动或其他固件已验收。

引擎约 75 次/秒输出状态；QML 16 ms 轮询，并在拖动事件内直接更新角色视觉位置，松手等待引擎确认序号后交回状态机。约 1.5 ms 的状态读取经过时间是异步请求耗时，不是 GUI CPU 时间。引擎更新率、轮询率及静止画面的 frameSwapped 数量都不等于屏幕实际拖动 FPS。

发布版将私有路径改为显式参数，移除了自动抓取整个宿主窗口的截图，指标写出默认关闭，并在掩码尚未载入时不捕获宠物点击。本次仅在电脑重新构建和验证这些调整，没有重新加载相机。原厂界面的延迟调查和三轮未确认改善的试验见[整机报告](../research/4.2.0/UI-RESPONSIVENESS.md)。

## 文件与依赖

| 路径 | 职责 |
| --- | --- |
| [native/engine.cc](native/engine.cc) | libshijima 的有界单角色适配器、输入白名单、原子状态发布与自测 |
| [ui/qml/PetOverlay.qml](ui/qml/PetOverlay.qml) | 透明覆盖、alpha 点击掩码、直接拖动、Exit 请求；不退出宿主 GUI |
| [ui/qml/DesktopHarness.qml](ui/qml/DesktopHarness.qml) | 自有菜单替身，用于电脑演示；不是原厂菜单 |
| [tools/build_engine.py](tools/build_engine.py) | 显式输入、固定上游版本的本地构建；可选 ARM64 静态交叉编译 |
| [tools/alpha_masks.py](tools/alpha_masks.py) | 角色 PNG 的 alpha>=20 行区间掩码 |
| [tools/run_desktop.py](tools/run_desktop.py) | 电脑演示与子进程清理，只管理自己创建的窗口和引擎 |
| [CodeTests/overlay/check_overlay.py](CodeTests/overlay/check_overlay.py) | 自有合成图与状态的 Qt 6.4.1 离线检查 |

需要 C++14 编译器、Git、Python 3.9+；Qt 桌面演示需要 Python 3.9–3.11 与 PySide6 Essentials 6.4.1。交叉编译使用 Zig 0.13.0。以下依赖与素材不随本仓库分发：

- [pixelomer/libshijima](https://github.com/pixelomer/libshijima/tree/361f452f3e89cdfaf04624db1c7641e3db410da9)，提交 `361f452f3e89cdfaf04624db1c7641e3db410da9`，GPL-3.0-or-later；含 Duktape 2.7.0（MIT）。
- pugixml 子模块提交 `27b68329de32cf9c601ca8eb6c588fd639960c40`（MIT），须初始化子模块。
- 本轮使用 [Neuron 角色包](https://github.com/qingchenyouforcc/NeurolingsCE-Qt/tree/b76816fbe52c51d617a4b5e1aa16c0e026f9e02f/mascot_pack/Neuron)，来源提交 `b76816fbe52c51d617a4b5e1aa16c0e026f9e02f`。来源声明 CC-BY-NC-SA-4.0，署名 Paccha，配置 promote、dalekcraft。角色是单独授权的非商业素材，不属于本模块 GPL 或仓库 MIT；本仓库不包含它。可自行提供兼容的 `actions.xml`、`behaviors.xml` 与 `img/*.png`，自测的断言针对 Neuron。

本模块新增源码按 [GPL-3.0-or-later](LICENSE) 发布，根目录 MIT 不覆盖本模块。分发链接后的引擎须保留 libshijima、Duktape、pugixml 的版权和许可，提供对应源码；分发角色须另遵守其许可。来源与版本详见[第三方说明](../../THIRD_PARTY_NOTICES.md)。

## 电脑端复现

以下均从仓库根目录执行，只写本地生成物、不连接相机。上游与素材目录由使用者准备；构建脚本不会下载资源、复制素材或运行安装。

```sh
python3 x2d/shimeji-overlay/tools/build_engine.py \
  --upstream /path/to/libshijima \
  --output x2d/shimeji-overlay/outputs/shimeji-host
mkdir -p x2d/shimeji-overlay/outputs/selftest
x2d/shimeji-overlay/outputs/shimeji-host \
  /path/to/Neuron x2d/shimeji-overlay/outputs/selftest selftest
```

引擎自测执行 1500 个加速 tick，断言至少 10 帧素材、20 次帧切换，以及拖动、爬墙、互动状态。记录的 Neuron 输入通过：16 帧、51 次切换，三种行为均通过。本次公开版的本机引擎重建、自测与两秒桌面演示通过，演示结束后子进程和临时状态目录均清理。普通运行最多约十分钟；状态目录必须存在，旧 `engine.stop` 会立即终止普通运行。不要把自测输出频率当成实时性能。

可选桌面 UI 检查不需要上游引擎或角色包：

```sh
python3 -m pip install PySide6-Essentials==6.4.1
python3 x2d/shimeji-overlay/CodeTests/overlay/check_overlay.py
python3 x2d/shimeji-overlay/tools/run_desktop.py \
  --engine x2d/shimeji-overlay/outputs/shimeji-host --character /path/to/Neuron
```

演示创建自己独占的临时状态目录，窗口关闭、Exit、超时或引擎结束时清理子进程。输出日志在模块 `outputs/`，默认忽略。合成测试断言透明背景、镜像 alpha 点击穿透、同事件拖动、松手确认、Exit 后宿主仍存活；不测试原厂菜单或实际屏幕延迟。详见[检查说明](CodeTests/overlay/README.md)。

本次 ARM64 Linux musl 静态交叉编译通过，输出类型核对为 AArch64 ELF；公开版产物未在相机重新执行。可选 ARM64 构建只生成文件，不安装：

```sh
python3 x2d/shimeji-overlay/tools/build_engine.py \
  --upstream /path/to/libshijima --compiler /path/to/zig --arm64 \
  --output x2d/shimeji-overlay/outputs/shimeji-arm64
```

## QML 接入契约与退出恢复

授权的 Qt 宿主可将 PetOverlay 作为窗口 contentItem 上的透明 Item，宽高绑定宿主并置顶。必须提供 `dataRoot`、`controlRoot`（以 `/` 结尾的 file URL）及 `assetRoot`（角色 img 的 file URL，无尾 `/`），先由 alpha_masks 生成 `controlRoot/hit-masks.json`。Qt 环境必须允许局部文件 XHR 读写；桌面脚本仅为自身进程设置这两个开关。

引擎读取 `input`：`sequence x y dragging behavior dragLeft dragTop`；QML 读取原子替换的 `state.json`，以 `input` 序号判断松手确认。坐标使用 720×540 的逻辑画布，输出帧锚点负责图片定位，镜像掩码负责透明像素穿透。该通道只应用于单用户、独占、可信角色目录；角色 XML 的脚本并非沙箱隔离的任意第三方代码。

Exit 只写 `controlRoot/exit.request` 并发出 `exitRequested()`，停止覆盖层输入和显示；宿主需自行销毁覆盖层并通知它拥有的引擎退出。**不得在原厂相机进程内调用 Qt.quit()**。最初独立宠物页面这样退出导致原厂界面结束，屏幕停留在哈苏 Logo；当时通过独立恢复路径重新启动原厂 GUI，用户确认恢复。后续临时部署改为退出标记、独立监督者与十分钟超时。标记和恢复流程已验证，但修正后的物理 Exit 点击及完整十分钟超时未分别完成全部实机验收。

公开源码不提供原厂 QML 编译单元注入、任意内存写入、factory/root 引导或设备部署监督者。从普通 USB 连接到相机运行并不能仅靠此模块复现，接入边界见[原厂工程界面说明](../research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)。此前临时文件和 RAM 修改不是刷写固件、修改系统分区或自动开机部署。本次整理没有操作设备。

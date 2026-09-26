# X2D 4.2.0 对象框显示实验

**已撤下，禁止继续上机（2026-09-26）。** 用户报告追踪试验使预览大幅卡顿、约每秒闪烁，明确要求原厂二代模块移植而不是自写替代检测/追踪。`dynamic_probe.py --execute` 已禁用；源码仅保留复盘，不是可部署候选。

## 范围与状态

第一代 X2D 100C 4.2.0，锁定 `camera-gui` 哈希。本目录不是完整对象追踪或 AF-C 实现。

- 旧版实机及用户反馈：真实单帧 Pet 检测结果可显示在机身屏幕，但 SVG 是静态的；物体移动不会更新框，也不改变原厂 AF 点或大小。不能把该验证称为追踪。
- 首次动态候选：12 帧重复检测实机通过，用户确认框会更新，但明确反馈更新极慢；单帧推理约 1.44–2.07 秒，结果年龄约 1.95–3.56 秒（秒级捕获时间有取整误差）。这只证明重复检测，不是流畅追踪。
- 当前候选：原厂 `odin-output` 取合成屏幕；独立线程做 320×320 检测，主线程在 256×192 灰度图上做多尺度模板匹配，读取最新帧并丢弃旧帧，不等待检测。超过 600 ms 的结果隐藏；匹配不足或超过 5 秒未检测确认则失锁。尚非二代原厂 CNNTK、重识别或 AF-C。
- 样式依据：X2D II 1.3.16.2 `PrimaryObjectIndicator.qml`、`AfSymbol.qml`、`AfSymbolVisual.qml` 的四角括号和 `max(longestSide / 15, 20)` 几何规则。本候选使用中性黑白线，不声称颜色和所有状态完全复刻；没有真实 AF 结果时不显示绿色合焦框或置信度标签。
- 不使用 LiDAR；没有原厂二代模型、身份重识别、眼睛定位、运动预测或 AF 联动。相似目标、遮挡、快速移动和尺度变化仍可能造成失锁或误匹配，不能声称具有二代的稳定对象身份追踪。

## 文件与依赖

- `X2dObjectOverlay.qml`：动态框、数据验证、过期隐藏。不写 Camera 属性。
- `X2dObjectOverlayBootstrap.qml`、`overlay_preload.c`、`build_overlay.py`：隔离 GUI 引导。原厂可执行文件不替换，只修改测试 GUI 进程的一个缓存指针。
- `overlay_probe.py`：版本/哈希检查、临时安装、60 秒机内 GUI 恢复计时器、精确文件清理。
- `dynamic_probe.py`：显式 `--execute` 才访问相机；暂存模型、限时捕获及推理、取诊断记录、清理并恢复 USB。
- `test_dynamic_contract.cjs`：用 Node 执行实际 QML 中的数据验证函数；不等于完整 Qt/QML 渲染测试。
- `make_boxes_svg.py`：历史单帧结果转换工具，不再是动态显示输入。
- 依赖：NDK、OpenCV 3.4.5 头文件、第一代原厂库、Darknet 模型、adb、PyUSB、pyelftools。固件、模型、构建产物和个人画面不随仓库分发。

构建命令见 `build_overlay.py --help` 和相邻 [检测器说明](../native-cpu-detector/README.md)。离线验证：

```sh
node x2d/object-recognition/CodeTests/liveview-overlay/test_dynamic_contract.cjs
```

## 副作用与恢复

只有实机入口才临时启用 ADB，向 `/blackbox/.codex-x2d-object-overlay` 写入测试输入及画面；临时添加三个新 `/system` 文件，随后保持系统只读。测试 GUI 临时替代原厂 GUI 进程，可能中断取景；不修改原厂 GUI 文件、init、AF 或镜头驱动。捕获限时 48 秒且最多 200 帧、推理外部硬超时 50 秒，GUI 60 秒计时恢复；主机最后核验并删除精确测试文件、恢复生产 USB。正常重启不等于删除持久分区的临时文件。

## 二代证据与当前适配的区别

X2D II 1.3.16.2 `dji_ml` 的动态符号确认 `CreateDetectionSubGraph`、`CreateTrackingSubGraph`、`CreateReidSubGraph`、`TrackingSubGraph::ReceiveFrameEventTrigger`、`GraphFrameRateController::TimerEntry`；导入 `CNNTKSingleTrackerUpdate`、`CNNTKTemplateSelect` 和 DSP 函数。它有专门的帧触发追踪和调度链，不是本实验最初的串行截图→完整检测→画框循环。静态符号不能证明具体调度频率或二代各模块的耗时。

当前实现借鉴其检测与追踪分离的职责，不是复制二代 CNNTK 二进制或加密模型。原厂库兼容性缺口见模块的符号审计；没有通过替换 DSP、内核或原厂服务来消除错误。CPU 模板匹配精度和抗遮挡能力不能等同二代神经跟踪及 re-id。

断线后需重新连接检查计时恢复及文件残留；不能承诺硬件、固件异常均可自动恢复。不要直接运行旧版残留恢复脚本；核对本地生成脚本哈希后才调用。

## AF 联动的已确认接口与门禁

离线一代 `LiveviewViewModel.qml` → `AutoFocus.qml` 路径：`setFocusPoint(pt)` 先通过 `Constants.getClosestInboundFocusPoint` 按裁切模式及 AF 尺寸限制位置，再写 `Camera.focus_point`。`Camera.af_region` 是结果区域，不能假定可写。一代大小通过预设索引改变，与二代独立宽高/对象区域不是同一接口。

后续必须确认取景坐标、裁切/放大/旋转状态及数据时效，再在原厂允许移动 AF 点的空闲状态桥接并保存/恢复原位置、大小。当前约 2 秒单帧推理不能直接用于运动目标 AF 闭环；保持 AF 写入禁用。

## 失败验收及恢复记录

独立追踪试验读到 52 帧、43 帧输出框、7 次失锁；取帧间隔中位数 855 ms、P95 916 ms，追踪计算中位数 30 ms、P95 79 ms，最高 RSS 111044 KB。用户确认能够跟随但不紧，并报告严重预览卡顿和约每秒闪烁。不能把计算速度改善或框会动写成功能通过。频繁截图与症状时间间隔吻合，疑似干扰合成预览；尚无隔离实验确认唯一因果。

同类检测的整体框/局部框重复、以交集除较小面积的关联规则会接受嵌套小框，代码已离线收紧，但没有再上机验证，也不继续这条替代路线。

设备计时器确认恢复原厂 GUI、删除系统载荷；主机重复恢复命令报错，随后只读核验原厂 GUI 哈希及无实验预载、按哈希清理暂存文件，并再次核实 `/system` 只读、生产 USB、测试目录消失。自动恢复脚本本身不能宣称全流程无故障。

用户随后指出仍有时钟。读回 `system.debug_mode=false`、`system.debug_options=None`，但 `gui.osd_clock=Top`：时钟是独立残留开关，此前只核验 GUI/USB 的“完全恢复”表述不准确。已单独写 `E_OSDClock_Off` 并读回 Off，没有重启服务或重置其他设置。DebugMode 菜单入口存在不等于该属性开启。

用户继续指出扩展维护项仍在。最终采用已有 `restore_production_gui_runtime`：先验证 USB config/state 均不含 ADB，再清零 `hbl.sutest_gui`、`persist.hbl.testmode`，关闭 debug mode/options/clock，明确观察 GUI 停止且 PID 消失后，由 init 启动新原厂 GUI。新 PID 与旧 PID 不同，原厂可执行文件和 init 配置哈希匹配、菜单 AF-C gate 为零、时钟 Off、调试 False/None、测试属性均为零。此前先启动 GUI 再关闭 ADB 的恢复顺序会保留 GUI 启动时的解锁维护菜单状态；只删载荷或只关时钟不是完整界面恢复。恢复代码执行成功，维护菜单的最终外观仍须用户观察确认。

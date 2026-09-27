# X2D 100C 4.2.0 临时实机菜单测试

> **Archive notice / 历史记录提示：** This file records a completed,
> operator-authorized device experiment. It is not a self-contained public
> installation guide. Several commands below refer to private/generated
> runners and device payloads that are intentionally absent from this
> repository; a clean clone cannot run them. For the public, bounded factory
> debug-UI path, read [`FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md`](../../../research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)
> and [`factory-debug-ui/README.md`](../../factory-debug-ui/README.md).
>
> **归档提示：** 本文件记录的是一次已完成、由操作者明确授权的实机实验，
> 不是自包含的公开安装指南。下方部分命令引用了有意不随仓库发布的私有/生成
> 运行器和机内载荷；干净副本不能直接运行。公开且受限的原厂工程界面路径请先
> 阅读[复现边界说明](../../../research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)
> 和[原厂调试界面说明](../../factory-debug-ui/README.md)。

> 2026-09-25 复测已完成并完整恢复。临时 GUI 的三个缓存 QML 单元指针、AF-C gate、预载环境和 `/system` 只读状态通过实机回读；用户确认三项对焦弹窗、第十二格图标/名称、自建页面及三种退出方式。AF-C 选中后的后端连续对焦效果未测。测试后七个载荷和暂存目录已删除，ADB 已关闭，原厂 GUI 正常运行。
> 首次测试曾因旧版脚本把标记缺失误判为失败而触发 SIGTERM；本次修正避免了该误杀。

> **当前版本边界：** 现用候选为 **60 秒上限、8 个载荷、原厂风格可滚动页面、总开关加 AF-C 开关**。下面单独记录旧版五分钟/七载荷测试及新版一分钟/八载荷测试，不能混用其进程地址和观察结论。包内 `deviceValidated=false`、`afcRuntimeModelMutationValidated=false` 仍表示不具备完整产品级验收：AF-C 实际连续跟焦、休眠/唤醒、跨重启与独立 watchdog 失效场景均未验证。

## 2026-09-25 五分钟实机复测

适用对象仍为第一代 X2D 100C 官方 4.2.0，原厂 `camera-gui` SHA-256 为 `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`。启动前经工厂 USB 只读核对原厂 init GUI 正在运行、探针 PID 为空、`/system` 只读。临时加载后，进程内回读三份 QML 缓存指针和 `01 00 00 00` AF-C gate，预载环境正确；用户再次确认三项对焦弹窗、第十二格图标和名称、自建页面以及 `EXIT`、右滑、下滑均正常。AF-C 实际连续跟焦仍未测试。

五分钟到期后，设备端输出记录 `X2D_MENU_PAGE_WATCHDOG_TIMEOUT`，临时 GUI 退出，原厂 init GUI 自动以新 PID 运行；工厂 USB 回读原厂 GUI 哈希、原厂 gate 和无预载环境。本次验证了计时到期时主控 shell 正常存活的自动切回；**没有**模拟主控 shell 被强制终止，独立 watchdog 自行启动原厂的分支仍为离线设计。

随后 `full-restore` 已删除七个精确载荷和专用 `/blackbox` 暂存目录，但旧版脚本最后以 ADB `su` 域删除 GUI 域创建的两个 `/tmp` 标记时收到 `Permission denied`，因此命令返回错误。经工厂 USB 只读确认仅剩两个精确标记、内容为 `MENU_AND_AFC_POINTERS_READY` 与 0 字节，再由对应的 `hbl_camera_service` 域删除并回读不存在；之后关闭临时 ADB，冷启动原厂生产状态 GUI。最终逐一核对七个载荷、专用暂存目录、两个标记均不存在，原厂 GUI 正常运行，USB 无 ADB，`/system` 只读，gate 为 `00 00 00 00`。

本地脚本随后改为由工厂 USB 域清理这两个标记，并新增离线回归；五项单元测试及 `self-test` 通过。**这一修正版完整清理流程尚未再做实机复测**，不能把上述手动分段恢复当成其自动成功的证据。

## 2026-09-25 一分钟新页面实机复测

用户再次明确要求实机测试。启动前离线 `self-test` 核对八个精确载荷；工厂 USB 只读确认目标仍是第一代 X2D 100C、原厂 4.2.0 GUI SHA-256 `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`、init 原厂服务运行、无探针 PID、`/system` 只读。启动临时 GUI 后，进程内回读 MainScreen 16624 字节、**原厂两项** ControlScreen 71108 字节、FocusPopover 13552 字节的三份预载映射，AF-C capability gate 为 `01 00 00 00`，`/system` 仍只读；标记最终为 `MENU_AND_AFC_SWITCHABLE_READY`。

用户实机确认：默认对焦弹窗为 AF-S/MF 两项；第十二格进入原厂风格的可滑动二级页，左上角返回、总开关和“开启 AF-C”开关均显示正常；开启总开关后再开启 AF-C，弹窗变成 AF-S/AF-C/MF 三项；先回到 AF-S/MF、关闭 AF-C 后弹窗恢复两项，左上角返回正常。此为**用户视觉与交互反馈**，并结合进程内指针/gate 回读；本轮未直接读取 Qt 列表对象内部状态，也未测试 AF-C 后端连续跟焦。

60 秒后，设备端输出 `X2D_MENU_PAGE_WATCHDOG_TIMEOUT`、`X2D_MENU_PAGE_GUI_EXITED:1` 和新标记；未发送手动恢复请求前，工厂 USB 已读到测试 PID 消失、原厂 init GUI 自动以新 PID 运行、gate 为原厂值且无预载环境。新版 `full-restore` 本次一次成功：八个系统载荷、专用 `/blackbox` 暂存目录和两个 GUI 域 `/tmp` 标记均逐项回读不存在；临时 ADB 已关闭、原厂 GUI 以生产状态冷启动、`/system` 只读。原厂 `/system/bin/camera-gui` 与 init 文件始终未改写。

仅在此次上机完成后修正了工具终端“manual checks”第 1 行沿用旧版三项默认弹窗的文案；它不改变测试包、计时器或加载逻辑。独立 watchdog 在主控 shell 被强制终止后的自行恢复分支仍未实测。

## 安全边界

- 不修改 `/system/bin/camera-gui`。
- 不修改任何 init `.rc` 文件，不设置开机自动加载。
- 旧版实机测试新增七个精确哈希的 `/system` 载荷文件；当前待验证包为八个，均应在完整恢复时删除。
- 测试 GUI 是手动 `LD_PRELOAD` 启动的原厂进程；重启机身会恢复 init 启动的原厂 GUI。
- 2026-09-25 早期复测使用 900 秒上限；随后 300 秒（五分钟）版和当前 60 秒（一分钟）版均已分别在实机验证计时到期自动切回。计时从临时 GUI 启动后开始，不是从相机开机时开始。
- 安装和清理由机内 `nohup` 事务执行；若仅电脑端 Python 中断、机内 shell 仍正常运行，事务会尝试回滚并恢复 `/system` 只读。断电、机内进程被强制终止等情形不在此保证内，必须实测只读状态。
- `emergency-restore` 只使用 factory USB，不依赖 ADB；它先恢复界面，载荷稍后再由 `full-restore` 删除。

设备端 watchdog 在当前设定的计时上限到期或测试 GUI 提前退出后，核对原测试进程的 PID 启动时间，终止仍在运行的原测试进程，等待其退出，再请求启动 init 管理的原厂 GUI。即使主控 shell 意外终止，独立 watchdog 仍可尝试这一步；主控 shell 正常运行时也有自己的恢复 trap。若计时进程被强制终止、内核/整机停机、测试 GUI 无法退出或 init 无法启动原厂服务，不能承诺计时恢复成功，须按下文只读检查和恢复流程处理。**这不是开机自动加载配置，亦没有覆盖原厂 `camera-gui`。**

macOS 上不要运行旧的 Unicorn 仿真。当前系统中的 `libunicorn.2.dylib` 会在
`uc_mem_map()` 初始化期间触发 `SIGILL`，这发生在被测代码运行之前。实机工具
`x2d_menu_page_probe_usb.py` 不导入 Unicorn；离线仿真脚本在 macOS 默认安全跳过。

## 一、离线自检

从仓库根目录执行：

```sh
PY=../.venv-x2d-af-speed/bin/python
TOOL=x2d/CodeTests/x2d-afc-research/x2d_menu_page_probe_usb.py
ADB=$(command -v adb)

"$PY" -B "$TOOL" self-test
"$PY" -B x2d/CodeTests/x2d-afc-research/test_x2d_menu_page_probe_usb.py
```

必须看到 `self-test OK` 和离线回归测试 `OK`。自检不连接相机。

## 二、连接后先做只读检查

```sh
"$PY" -B "$TOOL" --timeout-ms 15000 factory-status
```

必须确认目标为 `eagle2_ec1706_native`、`camera-gui` SHA-256 为
`16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`，并且
`/system` 为只读。该命令不改文件、服务、属性或 USB 模式。

如果仅需追查 2026-09-25 退出码 1 的旧测试进程，可再运行只读日志筛选：

```sh
"$PY" -B "$TOOL" --timeout-ms 15000 factory-diagnostics --pid 1915
```

只筛选该 PID 的最近日志；日志环形缓冲区可能已覆盖当天记录。不要把没有匹配行解释为进程没有报错。

## 三、启动临时测试

```sh
"$PY" -B "$TOOL" --adb-path "$ADB" --timeout-ms 15000 enter
```

工具会临时启用 USB ADB、上传精确载荷、短暂把 `/system` 重挂为读写以新增载荷，随后立即恢复只读；然后停止 init 的原厂 GUI，并手动启动带 preload 的原厂 GUI。构造器、三个 QML 指针、AF-C gate、SELinux 域和 `/system` 只读状态全部回读成功后，工具才会要求人工观察界面。

`enter` 的第一阶段会先启动 ADB 解锁状态的**原厂** GUI，此时 AF-C 可能已经出现；不要在这个画面验收。只有终端输出 `X2D custom menu-page probe is running` 后，才进入下一节人工验收。首次实机测试在这一步之前失败，所见 AF-C 不能归因于新预载。

## 四、人工验收

当前一分钟候选的人工验收步骤如下；上述实机复测已完成菜单开关正反向流程，但仍未验证真实连续跟焦：

1. 临时 GUI 启动后先确认对焦弹窗仍为原厂 `AF-S / MF` 两项。
2. 第十二格仍显示烧瓶图标和“耍起功能”；进入后确认左上角原厂风格返回、可纵向滑动、第一行总开关与第二行“开启 AF-C”开关。
3. 总开关关闭时 AF-C 行不可启用；打开总开关后点击 AF-C，只有控制器回读成功才显示为开启，此时重新打开对焦弹窗应为 `AF-S / AF-C / MF`。
4. 先切回 AF-S/MF，再关闭 AF-C，弹窗应恢复两项；关闭总开关后 AF-C 行再度不可操作。左上角返回应回主菜单；纵向滑动只滚动内容，不再作为退出手势。
5. 一分钟到期后确认测试 GUI 自动退出，原厂 GUI 恢复；随后运行完整清理。不要在本轮评价实际连续跟焦或镜头速度。
6. 需要查看进程内状态时执行：

```sh
"$PY" -B "$TOOL" --adb-path "$ADB" --timeout-ms 5000 status
```

## 五、正常完整恢复

```sh
"$PY" -B "$TOOL" --adb-path "$ADB" --timeout-ms 15000 full-restore
```

该命令先恢复 init 管理的原厂 GUI，再按 SHA-256 删除当前包的八个新增系统文件和 `/blackbox` 暂存目录，通过工厂 USB 服务域删除两个专用 `/tmp` 标记，确认 `/system` 只读，最后移除临时 ADB 并冷启动生产状态原厂 GUI。如果 ADB 已因恢复原厂 GUI 而消失，修正版会先通过 factory USB 只读检查；已清理则完成生产状态恢复验证，仍有受控文件时才临时恢复 ADB 完成清理。本次一分钟复测已验证该完整清理流程一次成功；断电和传输失败分支仍未实测。

## 六、Python 或 ADB 意外中断时

如果电脑端 Python 退出、ADB 消失或主命令失去响应，但 factory USB 仍可用：

```sh
"$PY" -B "$TOOL" --timeout-ms 15000 emergency-restore
```

它只接受工具生成且 SHA-256 完全匹配的恢复脚本，核对测试 GUI 的
`X2D_NATIVE_MENU` 和 `LD_PRELOAD` 环境后才终止该 PID，然后启动原厂 GUI。载荷此时仍留在磁盘，但没有 init 配置引用它们，因此是惰性的；ADB 恢复后仍应执行 `full-restore`。

如果电脑完全不可用，可重启相机。因为本测试不修改 init 配置，重启会直接运行原厂 GUI；之后再运行 `full-restore` 清除惰性载荷。

## 2026-09-25 首次实机测试与修正状态

- 用户观察：第一次哈苏标志和时钟出现后，Focus Mode 弹窗曾显示 AF-C；随后再出现一次哈苏标志，AF-C 消失，第十二格也未显示。只能确认 AF-C 曾短暂可见，不能确认它来自本预载构造器或能稳定使用。
- 机内测试 GUI 输出为 `X2D_MENU_PAGE_GUI_EXITED:1`；后续只读 logcat 取到 PID 1915 的 `Captured signal 15, quit!`。旧版主机脚本在未读到 `/tmp` 标记时会执行 `restore-runtime`，其恢复脚本正会向该 PID 发送 SIGTERM，因此该退出码不能证明 GUI 自行崩溃。`QStandardPaths` 和 `QCommandLineParser` 警告本身也不足以判断构造器状态。
- 原脚本在测试 GUI 退出、机内已恢复原厂 GUI 后，电脑端仍会再次运行恢复脚本，解释了额外一次启动。恢复后 USB 可切回无 ADB，导致旧版 `full-restore` 报无授权 ADB；短超时还曾使只读哈希查询超时。
- 首次失败后已在本地修正重复启动、保留退出诊断，以及 `full-restore` 对无 ADB/已清理状态的处理。再次修正为：`/tmp` 构造器标记缺失时，先只读核对运行进程的三份 QML 缓存指针、单元魔数与大小、AF-C gate、预载映射及 SELinux 域；不能仅因标记缺失就发 SIGTERM。该分支先经离线模拟，随后在下述复测中通过实机验证。
- 通过 factory USB 和 ADB 的只读复核确认：原厂 GUI 哈希未变，init 管理的原厂 GUI 在运行，`/system` 只读，七个新增系统路径和 `/blackbox/.codex-x2d-menu-page` 均不存在；最后已恢复无 ADB 的生产 USB 状态。

## 2026-09-25 复测结果

- 复测前原厂 GUI SHA-256 为 `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`，`/system` 只读，无测试 PID。离线自检和三项回归测试通过。
- 临时 GUI PID 1912 稳定运行；进程内回读：MainScreen 扩展单元 16624 字节、ControlScreen AF-C 单元 75576 字节、FocusPopover 单元 13552 字节，三份指针均落在预载映射内、具有 `qv4cdata` 魔数；AF-C gate 为 `01 00 00 00`，进程环境包含预期的 `LD_PRELOAD` 与 `X2D_NATIVE_MENU=1`，`/system` 保持只读。`/tmp` 构造器标记仍未读到，原因待查，但独立进程内回读已通过。
- 用户实机确认：对焦模式弹窗显示 AF-S / AF-C / MF；第十二格显示正确烧瓶图标和“耍起功能”；点击进入标题“耍起功能”、正文 `X2D test program` 的自建页面；`EXIT`、明显右滑和明显下滑均可退出。未确认 AF-C 选择后的实际连续对焦性能、半按快门、休眠/唤醒或开机常驻加载。
- 完整恢复成功：机内恢复脚本停止临时 GUI，删除七个精确载荷和暂存目录，关闭临时 ADB；最后只读 `factory-status` 显示原厂 GUI PID 2862、原厂哈希不变、测试 PID 与标记为空、`/system` 只读。未修改原厂 `camera-gui` 或 init 文件。

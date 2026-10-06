> 历史阶段报告。2026-10-06 的备用槽启动、写回及自动换槽新增验收见[恢复更新](WIRELESS-AND-RECOVERY-UPDATE.md)；下文未验收状态只对应当时实验。

# X2D 100C 4.2.0：错误页隐藏入口与 GUI 替换恢复边界

## 适用范围与证据

仅针对第一代 X2D 100C 官方 4.2.0。离线输入为已提取的官方固件：`camera-gui` SHA-256 `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`、`camera-upgrade` SHA-256 `c120c80fdfc15b2778e2a3e0323b606895d7a309c2cfc3a517dadcdefb90ea38`。本次只读这些离线文件，没有在相机上触发升级、重启或修改分区。

以下 `camera-gui` 十六进制偏移可用 `strings -a -t x camera-gui` 复核；它们是二进制内嵌 QML 源文本位置，不是设备内存地址。

## 已证实的 UI 行为（静态分析）

- `0x18f3c0c` 的 `ErrorNonAck` 页包含隐藏应急按钮逻辑：计数器初值为 0，条件为 `showEmergencyButtons` 且计数达到 5；`0x18f4158` 的感叹号图标点击信号使计数器加一。
- 显示后提供保存日志、从存储介质更新、开关 Wi-Fi 和 `FW Update Retry`。其中 `0x18f47dd` 的“从存储介质更新”加载 `../upgrade/UpgradeCheck.qml`；`0x18f4c06` 的重试按钮调用 `viewModel.programNodes()`。没有找到此处直接选择“机内系统备份并覆盖当前系统”的 UI 调用。
- 入口属于 `ErrorNonAck`（不可确认错误）页，不等于任何固件升级错误都会进入此页。该页面、感叹号点击逻辑和更新对话框均内嵌在 `camera-gui` 本身。

## 升级与系统分区线索（静态分析）

- `camera-upgrade` 识别 `.cim` 升级文件，固件升级源由存储监视与升级列表提供。[哈苏官方 X2D FAQ](https://www.hasselblad.com/x-system/x2d-100c-faq/)所述普通升级也要求事先把固件文件放在内置 SSD 或 CFexpress 卡，而非自动调用机内隐藏备份。
- `/system/bin/program_nodes.sh` 处理 USB-PD、exMCU 引导程序、exMCU 应用和部分型号 CPLD 等节点；这与 `FW Update Retry` / `programNodes()` 名称及升级程序的节点更新链相符，但不能把它解释成恢复 `/system/bin/camera-gui`。
- 本地 OTA 包的 `updater-script` 把 system/vendor 等镜像写向 `/dev/block/mirror/*_2`，并验证写入内容；`/system/bin/ota.sh` 要求 `/cache/ota.zip` 并切到 recovery。`boot_control` 也包含两个 slot 的状态字段。这些说明设备有升级/双槽机制，**不证明**另一槽当前保存可用原厂 GUI，也不证明 GUI 启动失败会自动回滚，不能当作已验证的救援流程。
- `/system/etc/init/camera-gui.rc` 的正常及测试 UI 服务都调用同一 `/system/bin/camera-gui`。若直接替换此 ELF 后动态链接或 QML 初始化失败，依赖它绘制的 `ErrorNonAck` 页面不能作为恢复入口。
- `/system/etc/init/camera-test.rc` 与 `/system/etc/init/msg2dbus.rc` 显示工厂测试与 USB 消息服务为独立 init 服务。先前短时实机实验已在 GUI 停止后使用工厂 USB；但**未验证冷启动时 GUI 持续失败的情况下**该通道仍可达、可写回 `/system`。不能据此承诺可救援。
- 旧的[分槽刷写研究计划](../FLASHING-PLAN.md)提出保留一个原厂槽、只修改另一个槽。它仍是实验设计，不是已验证回滚；在读取实际槽位、两槽完整性及独立回滚能力之前不能套用。

## 结论与安全边界

“错误页感叹号点五次出现应急按钮”可由此版本固件证实；“相机自带备份自动覆盖现有系统固件”不能证实，现有 UI 证据反而指向从外部存储介质选择升级文件。五次点击只适用于 GUI 已经成功运行且显示相应错误页的场景，不适用于替换 GUI 后无法启动的最危险故障。

在确认独立于 GUI 的恢复路径（例如厂商确认的维修/恢复方案，或经单独验收的冷启动工厂 USB 恢复）之前，不应覆盖 `/system/bin/camera-gui`。可继续做离线 ELF/QML 验证和不改原厂 GUI 的运行时实验。

## 2026-09-25 实机只读 A/B 核查

用户重新连接 X2D 后，经工厂 USB 的固定只读命令核对，未启用 ADB、未写入 `unrd`、未切槽、未挂载备用分区、未重启或刷写：

| 项目 | 读到的值 | 解释边界 |
| --- | --- | --- |
| 当前启动槽 | `ro.boot.slot_suffix=1`；`slot_1.status_active=1` | 当前从槽 1 运行 |
| 槽 1 | `/dev/block/mmcblk0p16`；512 MiB；ext4 UUID `9a31bcf2-2460-5c2c-a250-fc53852b47c0`；`clean` | 与本地官方 4.2.0 镜像 UUID、`unrd` 新/零范围 SHA-1 记录及运行中原厂 GUI 哈希吻合 |
| 槽 2 | `/dev/block/mmcblk0p17`；512 MiB；ext4 UUID `f21421bb-6ace-5721-a007-45c19a9e9557`；`clean` | UUID 与槽 1 不同；见下方临时只读挂载结果 |
| 槽状态 | 两槽的 `status_bootable` 与 `status_successful` 均为 `1`；槽 2 `status_active=0` | 是启动元数据，不是本次实机启动槽 2 的测试结果；不能证明自动回退或槽 2 GUI 可用 |
| 槽 2 系统范围记录 | `slot_2.system_new_sha1=4905f691ed7e489672ea1ee2654698ddf219bbdd`，范围末端 `115275` | 与槽 1 / 官方 4.2.0 的 `722f958c...`、`116115` 不同；不能把槽 2 视为相同版本的原厂备份 |
| 最终状态 | `/system` 仍从 p16 只读挂载；原厂 GUI SHA-256 `16391452...12e0`，init 服务运行 | 本次核查没有改变相机系统状态 |

槽 2 因基本 ext4 标识和状态元数据存在，值得继续作为**候选**研究；但启动可用性、失败后切回能力、GUI 完全失败时工厂 USB 可达性均未验证。`boot.mode=none`。`/dev/block/by-name` 中存在 `normal`/`normal_2`、`system`/`system_2` 和 `cache`，没有以 `recovery` 命名的分区链接；这不排除其他形式的 recovery 映像。下一步只能先做更完整的只读证据收集与独立恢复设计，不能据此切槽或覆盖 GUI。

## 2026-09-25 经用户授权的槽 2 临时只读挂载

用户明确允许临时以 `ro,noload` 挂载未启用的槽 2，只读取 GUI 哈希及版本线索。经工厂 USB 校验相机型号和当前原厂 GUI 哈希后，将 `/dev/block/by-name/system_2` 挂载于 `/tmp/x2d-slot2-ro`，读取后以 shell `EXIT` trap 卸载并删除临时目录。没有切槽、重启、修改 `/system` 或写固件。

| 项目 | 结果 |
| --- | --- |
| 槽 2 `bin/camera-gui` SHA-256 | `38555a38469c2c03b00344de915c1a0a692ae7f09d95aef544d0c70ef521dc13` |
| 槽 2 `build.prop` 构建号 | `ro.build.version.incremental=17098` |
| 当前槽 1 构建号 | `ro.build.version.incremental=24849` |
| 当前槽 1 原厂 GUI SHA-256 | `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0` |
| 后续独立复核 | `/tmp/x2d-slot2-ro` 未挂载且目录不存在；当前启动槽仍为 `1`，`/system` 仍从 p16 只读挂载，槽 1 GUI 哈希未变 |

因此槽 2 **确实有一个不同构建号的 GUI 文件**，不是当前 4.2.0 同版本系统的逐文件备份。`17098` 的具体对外固件版本尚未由本次证据确认。文件可读取、启动元数据为 `bootable/successful`，仍不能证明槽 2 此刻可成功冷启动，也不能证明修改槽 1 GUI 导致无法启动时设备会自动回退或允许外部修复。直接覆盖运行槽 GUI 的恢复风险仍未消除。

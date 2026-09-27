# Factory Debug UI Reproduction Boundary / 原厂工程界面复现边界

## Short answer / 先说结论

The reported problem is real: a clean clone of this public repository cannot,
by itself, take an ordinary USB-connected X2D and enable the factory/debug
interface from zero. This is not a missing Python package or an omitted
one-line `adb` option. The public release intentionally starts **after** a
lawful, already-authorized ADB endpoint exists.

反馈属实：从一个干净的仓库副本和普通 USB 连接开始，不能只靠本仓库从零
开启相机的原厂工程/调试界面。这不是漏装 Python 依赖，也不是少了一个普通
的 `adb` 参数。公开版本有意从“已经合法授权、已经出现的 ADB 端点”开始。

## What the public repository can reproduce / 仓库可以复现什么

The following parts are public and bounded:

- static evidence for the stock X2D 100C 4.2.0 GUI lock decision;
- fixed, read-only ADB state inspection;
- an explicit restart of the **unmodified** stock GUI when the authorized ADB
  endpoint is already active; and
- offline unit tests and production-state recovery checks.

公开且受限的部分包括：

- 原厂 X2D 100C 4.2.0 GUI 锁定判断的静态证据；
- 固定字段的只读 ADB 状态检查；
- 在已授权 ADB 端点已经活动时，明确确认后重启**未修改的**原厂 GUI；
- 离线单元测试和恢复量产状态的检查。

For an already-authorized endpoint, the safe sequence is:

```sh
# Read-only host checks; replace the placeholder with the selector shown by adb.
adb devices -l
adb -s <authorized-device-id> get-state
adb -s <authorized-device-id> shell getprop ro.product.device
adb -s <authorized-device-id> shell getprop sys.usb.config

# Run from the repository root. The tool performs only fixed operations.
python3 -B x2d/CodeTests/factory-debug-ui/factory_debug_ui.py \
  --serial <authorized-device-id> inspect
```

`adb devices -l` must show the device as `device`, not `unauthorized` or
`offline`. The inspector then checks the exact model, stock GUI hash, process
context, USB properties, and fixed debug-state fields. Read
[`factory-debug-ui/README.md`](../../CodeTests/factory-debug-ui/README.md) before
using its explicitly confirmed `restart-gui` action, and run `restore-check`
before treating the camera as production-locked again.

对于已经授权的端点，可以执行上面的只读顺序。`adb devices -l` 必须显示
`device`，不能是 `unauthorized` 或 `offline`。检查器随后会核对精确机型、
原厂 GUI 哈希、进程上下文、USB 属性和固定调试状态。使用明确确认的
`restart-gui` 前先阅读[原厂调试界面说明](../../CodeTests/factory-debug-ui/README.md)，
恢复后再运行 `restore-check`，不要仅凭菜单外观判断已经回到量产锁定状态。

## The missing bootstrap is intentional / 缺少的启动引导是有意的

The public tree does **not** contain the factory-USB transport or command that
changes a normal connection into an ADB-authorized endpoint. It also does not
publish an arbitrary remote shell, `/system` remount and file-upload sequence,
process-memory writer, persistence mechanism, generated vendor QML units, or a
runtime payload installer. These steps can cross an authorization boundary and
can leave a camera unusable, so publishing them as a copy-and-paste recipe
would be unsafe and would contradict the repository's publication boundary.

公开目录**不包含**把普通连接变成已授权 ADB 端点的 factory USB 传输层或
命令，也不公开任意远程 shell、`/system` 重挂与文件上传组合、进程内存写入器、
持久化机制、生成后的厂商 QML 单元或运行时载荷安装器。这些步骤可能越过
授权边界并使相机无法使用；把它们写成复制粘贴即可执行的配方既不安全，也
不符合本仓库的发布边界。

The observed trigger is narrower than a generic “engineering-mode switch”:
the stock GUI decides its branch at startup when `sys.usb.config` contains
`adb`, and the unmodified GUI must be started again. The visible
`system.debug_mode` value is an observation, not a substitute for that
bootstrap. The public inspector cannot create the USB condition it checks.

实际发现也不是一个可以任意写入的“工程模式开关”：原厂 GUI 在启动时读取
`sys.usb.config`，其中含有 `adb` 时才进入对应分支，并且需要再次启动未修改
的原厂 GUI。可见的 `system.debug_mode` 只是状态观察值，不能替代 ADB 引导；
公开检查器也不会自行制造它正在检查的 USB 条件。

## Historical commands are archival / 历史命令仅用于记录

`x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/LIVE-DEVICE-TEST.md`
is an archival experiment log, not a complete public installation guide. Its
historical examples mention private or generated runners such as
`x2d_menu_page_probe_usb.py`, `test_x2d_menu_page_probe_usb.py`, and
`x2d_afc_preload_usb.py`; those files and their device-side payloads are not in
this repository. A command copied from that log is therefore expected to fail
with “file not found” in a clean clone. That failure is a publication boundary,
not evidence that `adb` is missing from the host.

`LIVE-DEVICE-TEST.md` 是历史实机实验记录，不是完整的公开安装指南。其中的
历史示例提到 `x2d_menu_page_probe_usb.py`、
`test_x2d_menu_page_probe_usb.py`、`x2d_afc_preload_usb.py` 等私有或生成的
运行器；这些文件及其机内载荷没有随本仓库发布。因此在干净副本中复制这些
命令而出现“找不到文件”是预期结果，表示触及了发布边界，不是主机少安装了
`adb`。

For a public, offline-only check, use:

```sh
python3 scripts/reproduce_offline.py
```

It never connects to a camera. For the bounded stock-GUI finding, use only the
`factory-debug-ui` inspector described above and supply your own authorized
endpoint and recovery plan.

公开的纯离线检查请使用：

```sh
python3 scripts/reproduce_offline.py
```

它不会连接相机。若要核对原厂 GUI 发现，只使用上面说明的
`factory-debug-ui` 检查器，并由操作者自行提供已授权端点和恢复方案。

## Troubleshooting / 常见现象

| Symptom | Meaning | Safe next step |
| --- | --- | --- |
| `no devices/emulators found` | No ADB endpoint is visible to the host | Stop; do not substitute an arbitrary shell command. |
| `unauthorized` | The endpoint exists but host authorization is incomplete | Complete authorization on hardware you are allowed to test, then re-run the read-only checks. |
| `offline` | The endpoint is not in a stable state | Disconnect/reconnect only within the device's documented, authorized workflow. |
| `sys.usb.config does not contain adb` | The GUI unlock condition is not present | The public inspector cannot enable it; do not claim the test was reproduced. |
| `unexpected device` or stock-hash mismatch | Wrong model/version or modified GUI | Stop and use the exact recorded 4.2.0 stock input. |
| historical runner “file not found” | The command belongs to an unpublished experiment package | Use the public offline suite or the bounded inspector instead. |

| 现象 | 含义 | 安全的下一步 |
| --- | --- | --- |
| `no devices/emulators found` | 主机看不到 ADB 端点 | 停止，不要换成任意远程 shell 命令。 |
| `unauthorized` | 端点存在，但主机授权尚未完成 | 只在获准设备上完成授权，再重新做只读检查。 |
| `offline` | 端点不稳定 | 仅按设备公开、获准的流程断开并重新连接。 |
| `sys.usb.config does not contain adb` | GUI 解锁条件不存在 | 公开检查器不能开启它，不应声称复现成功。 |
| `unexpected device` 或原厂哈希不匹配 | 机型/版本不符或 GUI 已被修改 | 停止，改用记录中的精确 4.2.0 原厂输入。 |
| 历史运行器提示“找不到文件” | 命令属于未公开的实验包 | 使用公开离线套件或受限检查器。 |

See the [research disclaimer](../../../DISCLAIMER.md), the [factory UI finding](FACTORY-DEBUG-UI-FINDINGS.md),
and the [reproduction guide](../../../REPRODUCE.md) for the authorization,
recovery, and evidence-level limits.

另请阅读[研究免责声明](../../../DISCLAIMER.md)、[原厂调试界面发现](FACTORY-DEBUG-UI-FINDINGS.md)
和[复现指南](../../../REPRODUCE.md)，了解授权、恢复和证据等级边界。

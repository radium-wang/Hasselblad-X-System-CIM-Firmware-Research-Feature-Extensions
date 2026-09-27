# X2D Factory Debug UI Finding

> **Reproduction boundary / 复现边界:** this public tool starts only after a
> lawful, already-authorized ADB endpoint exists. It does not turn an ordinary
> USB connection into ADB or publish the factory-USB bootstrap. See the
> [full boundary note](../../research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)
> before treating the commands below as a from-zero procedure.
>
> **公开工具的前置条件：** 必须先有合法且已经授权的 ADB 端点。本工具不会把
> 普通 USB 连接变成 ADB，也不公开 factory USB 引导命令。不要把下面的命令
> 误读成从零开启工程模式的完整流程；先阅读[复现边界说明](../../research/4.2.0/FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)。

## Finding

For the stock X2D 100C 4.2.0 GUI, the locked/unlocked decision is made during GUI startup. In the production branch, `SystemProperties::isAdbLocked()` reads `sys.usb.config` and returns unlocked when the current USB configuration contains `adb`. Restarting the stock `camera-gui` while that configuration is active exposes the factory maintenance surface, including the `Debug Mode` entry and related developer items. The `system.debug_mode` property is a visible state value, not the trigger that unlocks the GUI.

The effect is therefore a two-part condition:

1. An already-authorized USB ADB connection exists and the current `sys.usb.config` contains `adb`; `sys.usb.state` is read as a second observation of the active USB state.
2. The unmodified stock GUI is stopped and started again.

The stock GUI executable remains unchanged. This explains why the white OSD clock and maintenance entries appeared together during the original research session.

## Included implementation

`factory_debug_ui.py` is a bounded ADB inspector for the exact X2D 100C 4.2.0 target. It reads the device, USB configuration, GUI lifecycle, GUI hash, SELinux context, debug properties, OSD clock, and test-mode properties. It can also restart the unmodified GUI when the operator explicitly supplies `restart-gui --confirm-restart`.

The public tool does not enable ADB, open the factory USB shell, execute arbitrary shell text, remount `/system`, upload files, modify process memory, or install a payload. Those operations are deliberately outside this public read-and-verify implementation. The operator must already have an authorized ADB endpoint.

Inspect the state:

```sh
adb devices -l
python3 -B x2d/CodeTests/factory-debug-ui/factory_debug_ui.py \
  --serial <authorized-device-id> inspect
```

`adb devices -l` must show the authorized endpoint as `device`. If it reports
`unauthorized`, `offline`, or no device, stop there: this repository does not
provide an ADB-enablement or authorization-bypass step.

`adb devices -l` 必须将已授权端点显示为 `device`。如果显示 `unauthorized`、
`offline` 或完全没有设备，请在这里停止；本仓库不提供开启 ADB 或绕过授权的
步骤。

After confirming that live view may be interrupted briefly and that `sys.usb.config` already contains `adb`, restart the stock GUI:

```sh
python3 -B x2d/CodeTests/factory-debug-ui/factory_debug_ui.py \
  --serial <authorized-device-id> restart-gui --confirm-restart
```

The tool refuses a different model, a non-stock GUI hash, or a configuration without `adb`. It never accepts a free-form remote command.

Verify the production-locked state after returning the camera to its normal USB configuration:

```sh
python3 -B x2d/CodeTests/factory-debug-ui/factory_debug_ui.py \
  --serial <authorized-device-id> restore-check
```

The restore check expects no `adb` in either USB property, `debug_mode=false`, `debug_options=None`, `osd_clock=Off`, `hbl.sutest_gui=0`, and `persist.hbl.testmode=0`.

## Evidence and limits

The discovery is a stock GUI behavior, not an AF-C gate and not proof that every hidden maintenance item is safe or useful. It does not by itself enable AF-C, eye detection, object recognition, or persistent firmware changes. A reboot with the production USB configuration remains the final recovery boundary.

The historical [live-device log](../temporary_af_speed_probe/original-menu-candidate/LIVE-DEVICE-TEST.md)
contains references to private/generated runtime runners that are not part of
this public tool. Those examples are evidence notes, not copy-and-paste
installation commands.

---

# X2D 原厂调试界面发现

## 研究发现

对第一代 X2D 100C 4.2.0 原厂 GUI 的静态分析确认，锁定/未锁定状态在 GUI 启动时决定。量产分支中的 `SystemProperties::isAdbLocked()` 会读取 `sys.usb.config`；当本次 USB 配置包含 `adb` 时，原厂 GUI 会进入未锁定分支。保持该配置并重新启动原厂 `camera-gui` 后，会出现原厂维护界面，包括 `Debug Mode` 和相关开发项目。`system.debug_mode` 是可见状态值，不是解锁 GUI 的触发条件。

因此触发条件有两个部分：

1. 已经获得授权的 USB ADB 连接存在，并且当前 `sys.usb.config` 含有 `adb`；`sys.usb.state` 会作为活动 USB 状态的第二个观测值读取。
2. 停止后重新启动未修改的原厂 GUI。

原厂 GUI 可执行文件本身没有被修改。这解释了最初研究时白色 OSD 时钟与维护菜单同时出现的现象。

## 本次加入的实现

`factory_debug_ui.py` 是绑定第一代 X2D 100C 4.2.0 的受限 ADB 检查器。它读取机型、USB 配置、GUI 生命周期、GUI 哈希、SELinux 域、调试属性、OSD 时钟和测试模式属性。操作者显式指定 `restart-gui --confirm-restart` 后，它也可以重启未修改的原厂 GUI。

公开工具不会启用 ADB，不会打开 factory USB shell，不接受任意 shell 文本，不会重挂 `/system`、上传文件、改写进程内存或安装载荷。这些操作有意不放入公开的读回和验证实现中；操作者必须先拥有一个已授权的 ADB 入口。

读取当前状态：

```sh
adb devices -l
python3 -B x2d/CodeTests/factory-debug-ui/factory_debug_ui.py \
  --serial <authorized-device-id> inspect
```

确认可以短暂中断取景，且 `sys.usb.config` 已经包含 `adb` 后，再重启原厂 GUI：

```sh
python3 -B x2d/CodeTests/factory-debug-ui/factory_debug_ui.py \
  --serial <authorized-device-id> restart-gui --confirm-restart
```

工具会拒绝错误机型、非原厂 GUI 哈希或不含 `adb` 的配置，也不接受自由格式的远端命令。

将相机恢复到普通 USB 配置后，检查量产锁定状态：

```sh
python3 -B x2d/CodeTests/factory-debug-ui/factory_debug_ui.py \
  --serial <authorized-device-id> restore-check
```

恢复检查要求两个 USB 属性都不含 `adb`，并且 `debug_mode=false`、`debug_options=None`、`osd_clock=Off`、`hbl.sutest_gui=0`、`persist.hbl.testmode=0`。

## 证据与限制

这是原厂 GUI 行为发现，不是 AF-C gate，也不能证明每个隐藏维护项目都安全或有用。它本身不会开启 AF-C、眼部识别、对象识别或持久化固件修改。恢复到量产 USB 配置后正常重启仍是最终恢复边界。

历史[实机记录](../temporary_af_speed_probe/original-menu-candidate/LIVE-DEVICE-TEST.md)
中提到的部分运行器属于私有或生成的实验包，不在公开工具中；那些示例是证据
记录，不是可以复制粘贴的安装命令。

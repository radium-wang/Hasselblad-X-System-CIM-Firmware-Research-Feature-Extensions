# X2D 4.2.0 Factory Debug UI Finding

> **Read first / 请先阅读:** the [factory-debug reproduction boundary](FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)
> explains why a clean clone cannot bootstrap ADB or enable this interface from
> an ordinary USB connection. The public implementation begins with an already
> authorized endpoint.
>
> [原厂工程界面复现边界说明](FACTORY-DEBUG-REPRODUCTION-BOUNDARY.md)解释了为什么
> 干净副本不能从普通 USB 连接开始引导 ADB 或开启该界面；公开实现以已经授权的
> ADB 端点为起点。

## English

### Result

Static analysis of the unmodified X2D 100C 4.2.0 `camera-gui` identified the
lock decision in `SystemProperties::isAdbLocked()`. The production branch reads
`sys.usb.config`; when the active USB configuration contains the `adb` function,
the GUI takes its unlocked maintenance branch during startup.

Restarting the stock GUI while that condition is present exposes the factory
maintenance surface, including `Debug Mode`, related developer entries, and the
white OSD clock. The visible `system.debug_mode` value is not the unlock
trigger. The stock GUI executable remains unchanged.

This is a two-part runtime condition:

1. An already-authorized USB ADB endpoint is active and `sys.usb.config`
   contains `adb`.
2. The unmodified stock `camera-gui` process starts again.

The finding is independent of the AF-C gate, face/eye detection path, and
object-recognition backend. It does not prove that every maintenance item is
safe, useful, or suitable for production use.

### Public implementation

[`factory_debug_ui.py`](../../CodeTests/factory-debug-ui/factory_debug_ui.py)
implements the safe, bounded part of the result:

- reads a fixed set of properties, the GUI lifecycle state, the process SELinux
  context, and the exact stock GUI hash;
- refuses a different device identity or a modified GUI executable;
- can explicitly restart the stock GUI after the operator confirms the brief
  live-view interruption; and
- verifies the production-locked values after recovery.

The accompanying offline tests cover the target guard, the recovery values,
both USB property checks, and the explicit restart confirmation.

The public repository deliberately does not include the factory-USB ADB
enablement command, an arbitrary remote shell, `/system` remounting, file
upload, process-memory writes, persistence, or a payload installer. The tool
assumes that the operator already has a lawful, authorized ADB endpoint and
only performs the fixed readback and stock-GUI lifecycle operation described
above.

This means the finding is not reproducible from a clean clone alone. The
historical live-device log may mention private or generated runners; those
names are not public entry points and are not expected to exist in a clone.

### Recovery boundary

Before returning the camera to normal use, remove `adb` from both the active
USB configuration and USB state, restore `debug_mode=false`,
`debug_options=None`, `osd_clock=Off`, `hbl.sutest_gui=0`, and
`persist.hbl.testmode=0`, then restart the camera normally. Run the public
`restore-check` action before treating the device as production-locked.

### Evidence level and limits

The lock decision and the stock-GUI restart behavior are static-analysis and
restricted hardware findings on the recorded X2D 100C 4.2.0 environment. The
repository does not claim that this behavior is unchanged on another firmware
version, hardware batch, or camera family.

## 中文

### 结果

对未修改的第一代 X2D 100C 4.2.0 `camera-gui` 进行静态分析后，定位到
`SystemProperties::isAdbLocked()` 中的锁定判断。量产分支读取
`sys.usb.config`；当当前 USB 配置包含 `adb` 功能时，GUI 在启动阶段进入
未锁定的原厂维护分支。

在这个条件成立时重新启动原厂 GUI，会出现原厂维护界面，包括
`Debug Mode`、相关开发项目和白色 OSD 时钟。可见的
`system.debug_mode` 值不是解锁触发器；原厂 GUI 可执行文件本身没有修改。

这是两个条件共同组成的运行时现象：

1. 已经获得授权的 USB ADB 端点处于活动状态，并且 `sys.usb.config`
   包含 `adb`。
2. 未修改的原厂 `camera-gui` 进程再次启动。

该发现独立于 AF-C gate、人脸/眼部识别路径和对象识别后端。它不代表每个
维护项目都安全、有用或适合生产环境。

### 公开实现

[`factory_debug_ui.py`](../../CodeTests/factory-debug-ui/factory_debug_ui.py)
实现了这个结果中安全且受限的部分：

- 读取固定的属性、GUI 生命周期、进程 SELinux 上下文和原厂 GUI 精确哈希；
- 拒绝错误的设备身份或被修改的 GUI 可执行文件；
- 操作者明确确认可能短暂中断取景后，可以重启原厂 GUI；
- 恢复后检查量产锁定所需的状态值。

配套离线测试覆盖目标门禁、恢复值、两个 USB 属性检查和显式重启确认。

公开仓库有意不包含 factory USB 开启 ADB 的命令、任意远程 shell、
`/system` 重挂、文件上传、进程内存写入、持久化或载荷安装器。该工具假设
操作者已经拥有合法且获得授权的 ADB 端点，只执行上面说明的固定状态读回和
原厂 GUI 生命周期操作。

因此，该发现不能仅从干净副本复现。历史实机记录可能提到私有或生成的运行器；
这些名称不是公开入口，在副本中不存在是预期行为。

### 恢复边界

相机恢复正常使用前，应从活动 USB 配置和 USB 状态中移除 `adb`，恢复
`debug_mode=false`、`debug_options=None`、`osd_clock=Off`、
`hbl.sutest_gui=0` 和 `persist.hbl.testmode=0`，然后正常重启相机。只有在
运行公开的 `restore-check` 操作通过后，才应把设备视为量产锁定状态。

### 证据等级与限制

锁定判断和原厂 GUI 重启行为，是在记录的第一代 X2D 100C 4.2.0 环境上得到
的静态分析与受限实机发现。仓库不声称其他固件版本、硬件批次或相机系列
保持相同的行为。

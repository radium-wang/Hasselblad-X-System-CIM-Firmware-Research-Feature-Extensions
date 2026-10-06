> 后续指令核对及恢复范围见[无线与恢复更新](WIRELESS-AND-RECOVERY-UPDATE.md)，本页保留早期分析边界。

# X2D 100C 4.2.0 exMCU 启动与恢复边界

## 适用范围与证据等级

本文只分析第一代 X2D 100C 官方 4.2.0 固件，CIM SHA-256 为 `5ae67d16a24b00f9300e3e9c1323e7d149248ad36975e12c4fa8da633b438e03`。证据来自官方固件的离线脚本与二进制字符串；没有对相机执行升级、重启、USB 模式切换或恢复测试。官方输入：[4.2.0 CIM](https://cdn.hasselblad.com/firmware/X2D-100C-Firmware/4.2.0/X2D_100C_v4_2_0.cim)。原厂二进制未收录于仓库。

## exMCU 是什么

`exMCU_x2.cont` 是独立于主系统的 MCU 应用固件，不是 `/system/bin/camera-gui`。其内有 STM32L4 HAL 路径、Qt for MCUs 图形代码、肩屏图标逻辑资源名，以及 `PowerHdlr` 对主处理器（固件称 `E2`）供电、复位和启动模式的处理。肩屏开机 Logo 的高可信逻辑资源名 `qrc:/gfx/icons/pic_power-on_h.svg` 见[开机画面调查](STARTUP-LOGO-LOCATION.md)。`exMCUloader.cont` 则是该 MCU 的引导程序镜像，二者在升级脚本中分别传给 `ApplicationUpgrade` 和 `BootUpgrade`。

## “exMCU 也是 A/B”指的是什么

| 层次 | 离线可见机制 | 能确认的范围 |
| --- | --- | --- |
| 主系统 | `hbl-upgrade` 更新 OTA 后，使用 `slot_*` 和 `unrd` 元数据切换新旧系统槽。 | 这是主系统 A/B；不能直接套到 exMCU。 |
| exMCU 应用 | `exMCUloader.cont` 字符串区可见 MCU 内部 Flash 应用、外部 SPI Flash 的 `Upgrade image` 与 `Backup image`、镜像 CRC 校验，以及内部应用校验失败后的升级／备份镜像恢复分支。`exMCU_x2.cont` 有 `Application Upgrade`、`Application Backup` 和将内部应用复制到外部 Flash 的逻辑。 | **有应用备份和恢复设计**，但证据显示的是“内部执行镜像 + 外部升级／备份镜像”，尚无两个对称、可独立启动的 exMCU A/B 槽证据。也未实机验证自动恢复成功率。 |
| exMCU 引导程序 | 升级脚本会单独上传 `exMCUloader.cont`；应用里可见 `Bootloader Upgrade`／`Bootloader Backup` 和编程内部 MCU Flash 的错误路径。 | 不能据此保证引导程序自身受同等回退保护，更不能保证写坏后用户可自行恢复。 |

官方 `hbl-upgrade` 在节点升级失败时会把系统随附的原厂 exMCU 应用重新送入 `ApplicationUpgrade`；`hbl-post-upgrade` 在 exMCU 与主系统版本不符时会尝试一次原厂 exMCU、USB-PD 和引导程序重发。这些补救都依赖相应通信与升级链仍能运行，并不是“任意损坏都能自动救回”的证明。

## exMCU 与 fastboot

`exMCU_x2.cont` 的 `PowerHdlr` 字符串明确存在“强制 E2 进入 USB boot mode”和“强制 E2 进入 eMMC boot mode”的供电分支。因此，**exMCU 有影响主处理器启动来源的代码路径**。目前未追到谁触发该分支、它是否在量产机上可用，也没有确认 USB boot mode 枚举出的 USB 协议。

“USB boot mode”不等于已经证明“Android fastboot”。[Android 官方文档](https://source.android.com/docs/core/architecture/bootloader/fastbootd)将 fastboot 描述为需要引导程序或 userspace 实现的具体协议；仅改变启动来源并不能证明设备实现并开放此协议。更不能由此推出：exMCU 自身损坏时还能靠它切换 E2 启动模式，或 fastboot 可以修复 exMCU。实机前至少需要只读确认 USB 枚举、协议响应和可恢复边界。

## 对开机 Logo 修改的影响

肩屏 Logo 线索位于 `exMCU_x2.cont` 的编译资源中。改它意味着改 MCU 应用镜像，并可能触发校验、升级与恢复逻辑；该步骤的风险和主系统 GUI 文件修改不同。主屏 Logo 仍需单独定位。现阶段没有得到可安全刷写或可靠回退的结论，也没有制作修改版 exMCU 镜像。

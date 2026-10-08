# X2D 4.2.0 无线唤醒与恢复验证更新

更新：2026-10-06。仅针对已记录的第一代 X2D 100C 4.2.0 实验。恢复结果不覆盖所有硬件故障。

## 蓝牙

原厂自然休眠后保持蓝牙广播，Phocus Mobile 连接使机身自动亮屏；实机记录为 bt-wakeup 和 E_SuspendWakeupSource_Bluetooth(11)。定位到 SoC 唤醒输入 GPIO 86。验证一次休眠恢复不代表长期待机耗电、所有配对状态或拍摄恢复全部通过。

真正按键关机后的蓝牙开机仍未实现。二代路径涉及无线服务、状态机和 exMCU；第一代供电、板级连线和 MCU 恢复证据未闭合。148 项指定指令检查通过，不能当成关机唤醒实机结果。

## exMCU 与 E2 USB boot

继续核对的原厂 MCU 代码具有由特定启动标志触发 E2 USB 启动来源覆盖的路径，累计 80 处关键指令核对。主 bootloader 的原厂签名及 checksum 检查通过。USB boot 不自动等于 Android fastboot。

MCU loader 从 SPI 副本恢复的是 MCU 自身应用，不是 Linux system。E2 救援 loader、下载协议和 eMMC 写回仍未验证，没有独立底层救砖保证。参见[早期分层报告](EXMCU-BOOT-AND-RECOVERY.md)。

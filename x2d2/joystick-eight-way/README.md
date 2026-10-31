# X2D II 八向摇杆输入合成

适用对象：Hasselblad X2D II 100C，原厂固件 **1.3.18.1**。状态：原生实现已完成，离线检查及一次45秒实体摇杆验收通过；尚未验证长期运行、所有界面和其他固件。

原厂对焦框已有斜向移动能力，但实体摇杆的相邻方向以独立按键到达。此模块维护实际按住的四方向集合，输出一个原厂专用八向键，复用原厂 GUI 的重复和对焦框移动逻辑。单独开启 GUI 的斜向属性不足以完成这项输入转换。

## 实现与文件地图

| 路径 | 职责 |
| --- | --- |
| [native/j8_core.c](native/j8_core.c) / [头文件](native/j8_core.h) | 方向状态机、相反方向冲突、同帧合并、切换与释放 |
| [native/j8_runtime.c](native/j8_runtime.c) / [头文件](native/j8_runtime.h) | 有界事件循环、同步边界、错误/超时/停止处理 |
| [native/j8_linux.c](native/j8_linux.c) | 实际 evdev/uinput 适配、合成设备就绪核对、临时输入独占与统一清理 |
| [CodeTests/input-synthesis/](CodeTests/input-synthesis/README.md) | 状态机、运行时、真实适配代码的系统调用替身检查及92事件相对时间回放 |
| [tools/check_offline.py](tools/check_offline.py) | 不访问设备的独立宿主构建和检查入口 |
| [research/INPUT-PATH.md](research/INPUT-PATH.md) | 原厂 GUI、MCU 与输入表达缺口的版本限定证据 |
| [FunctionalTests/liveview-eight-way/](FunctionalTests/liveview-eight-way/README.md) | 既有实机和用户验收摘要 |
| [source-manifest.json](source-manifest.json) | 本次迁入源码及归一化回放输入的SHA-256 |

八个C源码/头文件均与此前实机测试所用的实现及宿主检查源码逐字节一致。目录调整通过编译器 include 路径解决；新的独立离线入口不依赖其他项目的构建脚本。原始固件、共享库、原始设备日志与编译产物没有随库提供。

## 状态与时序

- 同一输入帧内合并方向状态；跨帧按下等待4ms，容纳相邻触点先后到达。
- 方向改变先释放旧方向，再按新方向；松手立即停止旧方向，剩余单轴等待8ms，避免两个触点先后释放造成短暂反冲。
- 相反方向冲突输出中性；实体重复事件不再额外生成重复，由原厂GUI负责长按。
- 其他机身按键触发透传及退出合成，待实际按键全部释放后结束；读写失败、SYN_DROPPED、时钟倒退等停止处理。
- Linux适配先确认虚拟输入已被Weston打开、物理输入处于中性，再取得临时独占；退出时释放按键、销毁自有设备、解除独占并关闭描述符。

## 离线复现

从仓库根目录运行：

```sh
python3 x2d2/joystick-eight-way/tools/check_offline.py
```

依赖Python3和支持AddressSanitizer/UndefinedBehaviorSanitizer的C11编译器，默认使用clang，可用 `--cc` 或 `CC` 指定。检查不需要厂商固件、共享库或相机。实际Linux适配器被编译进替身测试，设备调用全部替换为本地假实现，不会打开真实输入设备。临时二进制在系统临时目录生成并自动清理；报告保存到忽略提交的 `outputs/offline-checks.json`。

设备适配源码依赖Linux输入ABI、libevdev、相机固件对应的libc及Android/ARM64工具链；这些依赖不随库提供。公开入口只执行宿主检查。完整设备部署/传输/配置恢复脚本及常驻安装入口未收录；不能把仓库源码视为直接安装包。

## 验证范围

离线检查覆盖16组四斜向按下/松手顺序及长按、正向/斜向切换、冲突、停止/异常清理、92条归一化实体事件，以及实际Linux适配器的16组资源接管/故障场景和完整截止退出。

2026-10-31，既有45秒相机测试处理276条实体事件、228次输出状态变化，正常截止；用户确认“四个斜向正常，长按和松手正常”。测试后原配置和对焦点恢复，自有临时资源清理通过。该结果详见[实机验收](FunctionalTests/liveview-eight-way/README.md)，本次归档没有重新连接相机。

尚未完成常驻安装、开机自动启用、所有菜单/回放/自定义档切换和长期运行验收；其他机身按键仅有离线覆盖，不能由本轮拍摄界面验收推广。

# X2D 帧描述符适配模块：独立进程实机自检

日期：2026-09-26。目标：第一代 X2D 4.2.0（`eagle2_ec1706_native`）。本轮用户明确要求“上机试试”；执行前已说明只验证适配模块，不测试真实画面、原厂模型、追踪或 AF。

## 结果与范围

**实机通过**：Android ARM64 进程加载本模块共享库，执行与宿主一致的合成数据检查，验证平面间距转换、字段输出、输出哨兵、短输入／短输出／空指针拒绝、平面越界／重叠拒绝、整数溢出相关边界以及错误时不修改输出。

关键输出：

```text
FRAME_DESCRIPTOR_SANDBOX_READY
FRAME_DESCRIPTOR_PASS_NO_CAMERA_FRAME_OR_AF
PROBE_EXIT=0
device_payload_cleanup_completed
remote_directory_cleanup=verified
```

没有调用二代原厂帧转换、识别、追踪、模型初始化或 AF 函数；没有获取实时画面，没有注册帧回调，没有改 `camera-service`、GUI 或镜头行为。本轮不是对象识别／追踪功能验收，也不能据此认定完整移植成功。

载荷指纹：

| 文件 | SHA-256 |
| --- | --- |
| 独立自检程序 `probe` | `aabc501d19d56ebc84c4c5f6f477780fc2f8d8475a908c03dc2aea1409303663` |
| `libx2d_frame_adapter.so` | `ce07a9c8ba95408a61719126dbe972243d7c6926b7a65fe816ea52d266d8f899` |

## 保护措施与恢复

- 先核对目标、原厂 GUI 哈希、服务运行状态、系统分区只读及原厂 USB 模式。
- 临时运行时 ADB；载荷位于独立的 `/blackbox/.codex-x2d-frame-descriptor-probe`，拒绝覆盖已有目录，上传后逐文件验哈希。
- 进程低优先级；CPU 上限 2 秒、地址空间 64 MiB、输出文件 16 KiB、禁止 core dump，进程 alarm 5 秒，外层 timeout 10 秒。
- seccomp 禁止 ioctl、联网、创建线程／子进程、exec、访问其他进程、发送相关信号、挂载、重启和新开文件。失败即退出；没有修改 SELinux。
- 结束后按清单删除本轮文件并删除空临时目录；没有递归清理其他目录。机内临时副本已移除，本地源码和构建包保留，可重新构建。
- USB config/state 均恢复为 `rndis,mass_storage,bulk,acm`；`adbd=stopped`；GUI 和 camera-service 均为 running，`/system` 仍只读。
- 恢复后再次经工厂通道确认临时目录不存在，GUI SHA-256 仍为 `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`。
- 用户反馈：**取景、菜单、镜头全部正常，没有新增调试显示**。

## 文件与复现边界

- 实现：[frame_descriptor_adapter.c](../native/frame_descriptor_adapter.c)。
- 合成契约：[test_frame_descriptor_native.c](../CodeTests/offline-contract/test_frame_descriptor_native.c)。
- 机内沙箱入口：[frame_adapter_device_probe.c](../CodeTests/offline-contract/frame_adapter_device_probe.c)；不会被 Python 离线测试发现器执行。
- 离线构建：[prepare_frame_descriptor_probe.py](../tools/prepare_frame_descriptor_probe.py)。依赖 Python 3.9+、pyelftools、NDK r27d 和精确版本一代 system 提取树。输出目录必须已存在且为空。
- 历史执行／清理曾复用 native-loader probe。该设备执行器不在公开仓库中；公开版只保留源码、离线构建与合同测试。

示例从仓库根目录运行，以下仅构建和离线检查，不执行上机：

```sh
python3 -B x2d/object-recognition/tools/prepare_frame_descriptor_probe.py \
  --target-system-root /path/to/x2d-system-root \
  --ndk /path/to/android-ndk-r27d --output /path/to/empty-output
# 设备执行器未公开；请只运行离线构建与测试。
```

再执行需要当次明确设备授权和原厂状态预检，不能把本记录当成后续无限次试验许可。尚缺真实帧所有权、附加元数据、原厂模型运行和 AF 输出接口适配。

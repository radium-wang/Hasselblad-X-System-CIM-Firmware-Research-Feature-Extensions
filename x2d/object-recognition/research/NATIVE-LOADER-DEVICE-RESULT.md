# X2D 原厂二代库链接诊断实机结果

日期：2026-09-26。目标 X2D 4.2.0／55V；二代来源 1.3.16.2。
用户明确授权实机测试与后续 AF 联动，并在机旁确认状态。本轮仅执行受限链接诊断，**未实现或测试 AF 联动**。

## 范围

使用 [native-loader-probe](../CodeTests/native-loader-probe/README.md) 工具：

- 65 个临时库副本，共 47,517,408 字节，上传清单中 69 个文件哈希全部核对。
- 二代 `libnn_framework.so` 使用前一轮 TLS 导入元数据适配；第一代 DSP 库保留。
- 全部私有库副本禁用 DT_INIT／初始化数组及析构入口；检查拒绝 IFUNC／IRELATIVE。未覆盖原厂库。
- 诊断进程 seccomp 限制成功；禁止 ioctl、网络 socket、clone、exec、ptrace 等；10 秒 alarm、5 秒 CPU、256 MiB 地址空间上限，外层 15 秒 timeout。
- 只进行 dlopen/dlsym，不调用解析出的原厂函数；未上传模型，未启动二代 dji_ml，未接帧、GUI 或 AF。

这些副本不是功能候选，不能在禁用初始化的状态下用于正常推理。

## 两次尝试

1. 从工厂服务 shell 启动，诊断程序执行被拒绝，退出记录 127。没有进入库加载，不能算兼容性失败。载荷清理完成；USB 恢复后的枚举比原脚本 4 秒等待更迟，随后只读确认恢复。未关闭安全策略或修改标签。
2. 改用此前独立程序测试使用的 ADB shell（`u:r:su:s0`），未改变 SELinux。相同载荷通过进程限制，并获得：

```text
LINK_ONLY_SANDBOX_READY
LOAD_OK libnn_framework.so
LOAD_OK libcnntk_cbb.so
SYMBOL_RESOLVED_NOT_CALLED __emutls_get_address
SYMBOL_RESOLVED_NOT_CALLED CNNTKInit
SYMBOL_RESOLVED_NOT_CALLED CNNTKSingleTrackerUpdate
LINK_ONLY_PASS_NO_ALGORITHM_OR_AF_EXECUTION
PROBE_EXIT=0
```

这是**实机 Android 链接器能够加载无初始化诊断副本**的证据，比离线符号集合检查多了一步；不证明正常初始化、线程局部存储函数执行、原厂模型推理、DSP 调度或 AF 合法调用。dlsym 成功也不等于逐项检查了每个 GOT 实际绑定地址。

## 清理与恢复（实机复核）

- 设备端 supervisor 删除库及诊断可执行文件，主机清理剩余日志／归属标记，确切临时目录 `/blackbox/.codex-x2d-native-linkprobe` 不存在。
- USB config/state 均恢复 `rndis,mass_storage,bulk,acm`；adbd stopped。
- camera-service / camera-gui 均 running，未由本次测试停止或重启。
- /system 保持 ro；GUI SHA-256 前后均为 `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`。
- 只读 AF 查询为 `E_FocusModes_Afs(1)`，focus_point 为 `327685000`；这不是本轮设置或触发对焦的结果。
- 用户确认取景、菜单、镜头均正常，没有新增时钟或调试显示。

恢复证据覆盖本次确切载荷和已核对服务／文件，不是整机所有分区逐字节原厂认证。

## 下一步与限制

仍需解决原厂初始化／模型路径、第一代原生帧描述与引用释放、连续目标 ID／坐标输出，以及 AF 失锁／越界／过期结果回退。没有真实目标结果，不能把手工改焦点或仅画框当作 AF 联动完成。

`run_once.py` 已改为使用正常 ADB 独立进程入口，并对 USB 恢复做有上限的枚举及 config/state 重试。它默认只验证本地清单；`--execute` 才接设备。测试没有提交或推送。

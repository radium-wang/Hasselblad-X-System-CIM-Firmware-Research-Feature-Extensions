# 原厂帧转换离线模拟的宿主崩溃与防复发

## 范围和证据

2026-09-26，离线验证 X2D II 1.3.16.2 帧转换入口时，宿主为 Apple Silicon、macOS 27.0、Python 3.9.6、Unicorn 2.1.4。用户提供的崩溃报告显示：

- `EXC_BAD_INSTRUCTION (SIGILL)`；异常指令字 `0xd53b0028`。
- 调用链为 `uc_mem_map → uc_init_engine → machine_initialize → init_cache_info + 88`。
- 对该指令字的静态反汇编为 `mrs x8, ctr_el0`，即读取宿主缓存类型寄存器。

**已确定的直接原因**是 Unicorn 原生库在初始化宿主缓存信息时触发非法指令异常，不是 Python 普通异常，也不是相机端崩溃。发生在首次内存映射阶段，尚未开始模拟原厂函数。本轮未连接或改写相机。

尚未确定这一系统构建为何拒绝该寄存器读取；不能据此推断所有 macOS 或所有 Unicorn 版本都会崩溃。未重复触发故障，也未修改系统安全设置、Python 安装或第三方动态库。

## 已实施的防复发措施

在 [emulate_original_frame_adapter.py](../tools/emulate_original_frame_adapter.py) 中：

- Apple Silicon macOS 在导入 Unicorn、创建引擎和内存映射之前被保守拒绝，没有强制绕过开关。尚无经本项目验证可放行的修复版本。
- 命令行正常返回状态 2 并解释原因，不依靠 `try/except` 捕获原生 `SIGILL`。
- `--descriptor-only` 仅转换合成帧描述符，不导入模拟器，不读取固件，不接设备；输出明确标记原厂函数未执行。

这是**阻断已知崩溃路径**，不是修复 Unicorn 本身，也不是通过了原厂机器码模拟。将来在其他宿主运行模拟仍需独立验证。

## 离线验证

从仓库根目录：

```sh
python3 -B x2d/object-recognition/tools/emulate_original_frame_adapter.py --descriptor-only
python3 -B -m unittest discover -s x2d/object-recognition/CodeTests/offline-contract -v
```

新增 5 项测试覆盖字段映射、无效平面拒绝、原生库导入前门禁、CLI 正常拒绝及纯数据模式不调用模拟器。总计 20 项：18 项通过，2 项因未提供固件输入跳过。实际 CLI 纯数据模式返回 0；模拟入口返回 2，无进程崩溃。

帧描述符只适用于已分析的转换入口子集；真实帧的缓冲区持有／释放、原厂转换输出和 AF 联动均未因此获得验证。

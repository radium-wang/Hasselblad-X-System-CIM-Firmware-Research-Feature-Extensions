# X2D 对象识别后端移植

最新离线结论：两代共 45 个模型／配套资源容器的格式字段与材料标识相同，存储载荷
SHA-256 均匹配。二代另一条软件签名校验路径会在验签失败时返回 -10，但该路径的
算法要求与本批模型不同，不能替代实际 TEE 路径或证明本次错误的具体含义。
新增只读比较工具，37 项离线测试通过；本轮未连接或修改相机。详见
[容器元数据与错误分支](research/ORIGINAL-NATIVE-ADAPTATION.md#容器元数据对照与--10-的相关原厂分支纯离线)。

后续重新连接实机：只复用二代原厂 `libfw_util_ca.so` 的变体已确认实际调用目标，
但 Pet 模型仍返回 -10；随后用全套一代库和一代原厂人脸模型做同接口对照，校验成功。
因此测试接口并非整体失效，二代模型接受条件仍待解决，尚未进入推理或 AF。
两轮均完成临时文件清理和 USB 等状态恢复，用户确认全部正常。33 项离线测试通过，
详见上述适配记录末节。

随后离线追踪了保留一代通信库时剩余的 BB JSON 通道导入：它属于二代图像存储的条件分支，第一代按通道名创建的接口不是同义替代；原生帧附加字段和所有权仍未闭合。见[原厂适配进展](research/ORIGINAL-NATIVE-ADAPTATION.md)。这没有改变“不可接真实帧或 AF”的上机门禁，本轮没有连接相机。

最新核对确认两代 DSH 接收帧在 `+0x70` 使用相同的内存句柄槽；X2D 原厂 HAL 对自建 4 KiB 缓冲区的跨进程导入、原持有者释放后的有效性已通过隔离实机测试。但两代原厂 ML 发送端复制的输入帧结构分别为 `0x218`／`0x330` 字节，发送区域为 `0x278`／`0x390` 字节；接收器的复制范围覆盖读点并不能证明字段语义相同。真实帧、异步消费、二代模型和 AF 仍未接入。25 项离线测试通过，见上述适配记录。

继续核对已建立节点到事件消息的 `+0x14` 封包映射，并证实原厂发送端会清零部分附加字段；但二代回调最后四字节读取超出该路径明确复制的数据范围，接收端尾部来源尚未证明，不能无条件零填充。现有 26 项离线测试全部通过；本轮未上机、未修改 AF。详见上述适配记录末节。

2026-09-26 最新状态：自写 CPU 检测／追踪路线保持退役。二代原厂库的**无初始化隔离链接诊断已在一代实机通过**；临时载荷清理、USB 恢复及原厂服务状态已复核，用户确认没有新增调试显示。本轮未调用模型、追踪或 AF 函数；完整移植未完成。详见[实机记录](research/NATIVE-LOADER-DEVICE-RESULT.md)和[原厂适配进展](research/ORIGINAL-NATIVE-ADAPTATION.md)。

## 目的与边界

本模块研究把 X2D II 100C 的原厂 Human / Pet / Vehicle 检测、目标追踪与结果接口适配到第一代 X2D 100C，目标排除 LiDAR 依赖。AF 联动尚未实现；不能把这里的框显示或目标追踪称为 AF-C 已可用。早期旁路实验仅作失败路线记录，不再作为实现目标。

当前已完成移植前的接口、模型、运行库、加速器和平台兼容性审计，并把“不允许直接搬二代二进制”的条件做成可重复执行的门禁。审计结果表明，二代固件不能作为第一代 4.2.0 的安全安装候选；本模块目前不是可部署功能包。

## 适用对象

- 来源：X2D II 100C 1.3.16.2，`eagle2_hb722`，Android 9 / API 28 / ARM64。
- 目标：第一代 X2D 100C 4.2.0，`eagle2_ec1706_native`，Android 9 / API 28 / ARM64。
- 输入必须是从对应官方固件离线提取的 `system` 和 `vendor` 根目录；固件与提取物未随仓库提供。

两代机型相同的 Android 版本和 CPU ABI 不代表 ML、DSP、内核模块或 `camera-service` ABI 相同。

## 文件地图

- [tools/audit_model_containers.py](tools/audit_model_containers.py)：只读核对两代模型容器的非秘密元数据、长度、载荷摘要及固定原厂错误分支；不解密、不验签、不接设备。

- [native/](native/README.md)：可编译的帧描述符接口适配组件；已通过宿主 ASan/UBSan 测试并构建 Android ARM64 共享库，尚未接真实帧、原厂模型或 AF。
- [tools/audit_original_frame_contract.py](tools/audit_original_frame_contract.py)：固定版本原厂帧池、通道编号、附加元数据和释放接口的只读指令核对；依赖 `capstone` 与 `pyelftools`，不运行固件。详见[帧适配进展](research/ORIGINAL-NATIVE-ADAPTATION.md)。
- [research/HOST-EMULATOR-SIGILL.md](research/HOST-EMULATOR-SIGILL.md)：Mac 上 Unicorn 初始化崩溃的定位与防复发门禁；原厂函数模拟尚未通过，纯描述符检查可继续。
- [tools/emulate_original_frame_adapter.py](tools/emulate_original_frame_adapter.py)：合成帧描述符适配／原厂转换入口模拟实验；`--descriptor-only` 不需要第三方包，也不访问设备。模拟路径另需 `pyelftools`、`unicorn` 和固定版本原厂 ELF，Apple Silicon macOS 当前禁用该路径。
- [research/X2D2-TO-X2D-PORT.md](research/X2D2-TO-X2D-PORT.md)：来源实现、接口、资源、约束、迁移分段与当前阻断项。
- [research/compatibility-audit-4.2.0-vs-1.3.16.2.json](research/compatibility-audit-4.2.0-vs-1.3.16.2.json)：本轮离线输入得到的确定性审计证据，不含本机绝对路径。
- [research/symbol-surface-4.2.0-vs-1.3.16.2.json](research/symbol-surface-4.2.0-vs-1.3.16.2.json)：二代 `dji_ml` 对一代原厂库的动态符号缺口和来源库清单。
- [tools/audit_port.py](tools/audit_port.py)：只读固件树并生成兼容性报告。
- [tools/audit_symbol_surface.py](tools/audit_symbol_surface.py)：只读 ELF 强引用符号检查。
- [tools/audit_native_bundle.py](tools/audit_native_bundle.py)：只读计算原厂用户态依赖组合、版本化强引用及哈希清单。31 库方案保留一代 DSP，但有 2 项版本化导入缺口；32 库对照可消除这些缺口，却引入 DSP 通信差异，均未批准上机，也未证明最小。

后续增加 `--retain-target-library` 可锁定一代底层库，缺口必须报告，不能为了凑齐符号自动换成二代库。固定保留一代 `libduml_frwk.so`、`libduml_hal.so`、`libdsp_frwk.so` 后得到 23 库离线组合；结合既有 TLS 适配还剩 1 个版本化导入缺口。**不是运行时兼容性或完整移植通过。** 详见[后续原厂接口分析](research/ORIGINAL-NATIVE-ADAPTATION.md)。

- [tools/adapt_original_tls.py](tools/adapt_original_tls.py)：生成两个固定版本原厂 ELF 的**离线元数据适配副本**；绑定至原厂 FastRTPS 的 TLS 导出，保留算法代码字节。可在保留一代 DSP 的静态混合检查中消除上述 2 项缺口；未通过机内加载／运行验证，不是安装工具。
- [research/ORIGINAL-NATIVE-ADAPTATION.md](research/ORIGINAL-NATIVE-ADAPTATION.md)：原厂检测／追踪入口、CNN/VCR ioctl 核对、DSP 通信差异及下一步适配边界。
- [CodeTests/offline-contract/](CodeTests/offline-contract/)：兼容性、符号及版本化导入的离线单元测试。
- [CodeTests/native-loader-probe/](CodeTests/native-loader-probe/README.md)：原厂库无初始化隔离链接诊断；默认离线，显式执行才接设备。不能用其禁用初始化的副本做功能测试。
- [CodeTests/native-cpu-detector/](CodeTests/native-cpu-detector/README.md)：第一代原生 OpenCV 的单帧检测、连续检测与独立 CPU 追踪实验，不是二代模型直接移植。
- [CodeTests/liveview-overlay/](CodeTests/liveview-overlay/README.md)：已退役的动态对象框实验；用户报告卡顿／闪烁，执行入口已禁用，未接 AF。

该结构属于 `x2d/object-recognition/`：机型为第一代 X2D，功能为对象识别后端，工具、研究与代码验证均只服务这一长期功能边界。它没有复用菜单、AF 速度或 AF-C 实验目录。

## 依赖与输入

- Python 3.9 或更新版本。
- `pyelftools`，用于解析 `dji_ml` 的 `DT_NEEDED` 依赖。
- 四个只读目录：二代 `system`、二代 `vendor`、一代 `system`、一代 `vendor` 提取根目录。

从仓库根目录运行：

```sh
python3 -B x2d/object-recognition/tools/audit_port.py \
  --source-system-root /path/to/x2d2-system-root \
  --source-vendor-root /path/to/x2d2-vendor-root \
  --target-system-root /path/to/x2d-system-root \
  --target-vendor-root /path/to/x2d-vendor-root \
  --output /tmp/x2d-object-recognition-audit.json \
  --require-ready
```

`--require-ready` 在存在阻断项时返回状态 2，适合放入后续候选构建门禁。省略该参数时仍会完整输出报告并返回状态 0。

追加符号检查（仍从仓库根目录运行）：

```sh
python3 -B x2d/object-recognition/tools/audit_symbol_surface.py \
  --source-system-root /path/to/x2d2-system-root \
  --target-system-root /path/to/x2d-system-root \
  --output /tmp/x2d-object-symbol-surface.json
```

该工具假定目标 `system/lib64` 中所有库都可见，忽略符号版本和动态链接器命名空间，故刻意高估可兼容性；仍缺失的强引用符号足以拒绝直接替换。

## 副作用与恢复

兼容性审计脚本只读取给定目录；`--output` 只写用户指定的 JSON。它不连接相机、不运行固件程序、不修改镜像、不生成安装包，也不重启服务。删除输出 JSON 即可恢复，固件输入不会变化。

`CodeTests` 中历史实机代码具有设备副作用，不能与纯离线审计混用。动态框执行入口已禁用，不应为继续移植而重新启用。新的原厂模块上机方案尚未通过门禁。

## 验证结果

静态 / 离线验证：

- 审计脚本在本轮一代 4.2.0 与二代 1.3.16.2 的提取树上运行成功。
- 提供固定固件输入时 15 项离线测试通过；包含原厂 ELF 适配的代码字节保持、版本表、依赖／LOAD 段及诊断初始化入口禁用检查。未提供输入时为 13 项通过、2 项跳过；均不连接相机。
- `--require-ready` 对本轮真实输入返回状态 2；这是预期的安全拒绝，不是工具故障。
- 二代 `dji_ml` 的 385 个强引用符号中，有 48 个在一代 `system/lib64` 的所有库里均不存在；一代原厂程序与二代原厂程序各自在对应机型库中均无此类缺口。两代加密模型的共同文件头不能证明载荷可跨机型加载。
- 原厂二代模块尚未在第一代机内完成识别、AF ROI、性能、功耗、温升或冷启动验证。
- 后续新增的一次**独立单帧实机**试验输出 Vehicle 目标框（1.289 秒，峰值约 102 MB），已确认候选清理、USB 原厂模式与取景正常；仍没有实时识别、AF ROI 驱动、持续性能、功耗、温升或冷启动验证。见[详细记录](research/X2D2-TO-X2D-PORT.md)。

## 状态与限制

状态：**原厂二代运行时仍待适配；CPU 替代路线因实机负面反馈撤下，未实现 AF 联动。**

第一代缺少二代 `camera-service` 的 `object_detection` / `arbitrary_tracking` 设置和对象回调契约；二代运行时还要求第一代没有的 7 个用户态库，并对一代现有同名库有 22 个强引用符号缺口。两代的三个视觉内核模块、三个 DSP 固件及 18 个共有 ML 依赖均为不同构建。加密模型虽有相同容器头，但载荷能否跨机型加载未经验证。直接复制二代 `camera-service`、`dji_ml`、模型或 DSP/内核文件不构成可接受的移植方案。

目前继续核对原厂二进制接口：CNN/VCR 的若干 ioctl 命令和实际结构复制大小存在一致性，提供了保留第一代驱动的研究依据；DSP 握手编号和版本化导入则需要具体适配。不同文件哈希本身不能证明一定不兼容，符号闭合也不能证明可运行。

若原厂模型或 DSP 执行格式最终不兼容，仍可能需要针对 EC1706 的官方模型转换链／可构建源码；当前尚不能判定。仓库不会生成可刷写包，也不会把审计通过写成对象识别可用。

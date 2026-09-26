# 原厂库隔离链接诊断

用途：X2D 4.2.0 上验证二代 1.3.16.2 库的动态绑定，不调用模型、追踪或 AF。
这是加载器诊断，不是算法移植成品。所有私有库副本的初始化／析构入口禁用，禁止 IFUNC / IRELATIVE；原厂输入不修改。第一代 DSP 库保留，但其测试副本同样不初始化。不能用这些副本进行功能测试。

`prepare.py` 在空输出目录准备依赖副本和 NDK ARM64 诊断程序，依赖 pyelftools、对应原厂固件、前一步的 bundle 审计 JSON 及 Android NDK r27d。它不接设备。`link_probe.c` 设置 10 秒 alarm、5 秒 CPU 和 256 MiB 地址空间限制；若资源限制或 seccomp 设置失败则退出。过滤 ioctl、socket、clone、exec、ptrace 等调用；它不是通用恶意程序沙箱。只调用 dlopen/dlsym，不执行找到的函数，不调用 dlclose，最终 _exit。

部署仅限用户授权后的临时目录；不得覆盖 /system、改变 camera-service/GUI/AF。上传前须确认机型、原厂哈希、目录不存在、空间和用户在机旁。必须校验 SHA256SUMS，设置独立 timeout，并核实动态绑定基库来源。结束清理确切所属文件，恢复 USB；清理不能匹配别的实验或用户文件。

离线生成示例（从仓库根运行；空输出目录需预先建立）：

```sh
python3 -B x2d/object-recognition/CodeTests/native-loader-probe/prepare.py \
  --source-system-root /path/to/x2d2-system-root \
  --target-system-root /path/to/x2d-system-root \
  --bundle-audit /path/to/retained-dsp-audit.json \
  --ndk /path/to/android-ndk-r27d \
  --output /path/to/empty-output
```

生成 ELF 和库默认不随仓库分发。机内结果需另外记录，链接成功不代表初始化、推理、取景接入、LiDAR 排除、追踪性能或 AF 联动成功。

`run_once.py --package /path/to/output` 默认仅验证本地清单。显式 `--execute` 才启用运行时 ADB、上传、通过 ADB shell 启动设备端 timeout／清理脚本，再恢复原厂 USB。它不改变 SELinux；若进程限制失败，诊断退出。只清理本轮已验证清单中的确切路径，不递归删除其他文件。若设备端清理未确认，不会贸然删除运行中的载荷，需先核实状态。

2026-09-26 实机链接诊断通过，载荷与 USB 清理恢复已复核，用户确认机身正常。详见[实机证据与限制](../../research/NATIVE-LOADER-DEVICE-RESULT.md)。正常模型初始化、实时识别和 AF 联动未测试。

## 原厂模型容器的独立验证

`model_container_probe.c` 与 `tools/prepare_model_container_probe.py` 是新增的
`--kind model-container` 试验，不使用上述禁用初始化的库副本。
它只调用 X2D 4.2.0 原厂 `dji_fw_verify_load2mem` 一次，输入锁定二代
1.3.16.2 原厂 Pet 模型；不改模型、不绕过校验、不调用安装接口。
该步骤**不是模型推理或模型运行时初始化**，成功仅证明原厂容器接受。

依赖原厂固件输入、NDK r27d、pyelftools；二进制、模型与原始日志不随仓库提供。
打包工具只离线构建，参数为 `--target-system-root`、`--source-vendor-root`、
`--ndk`、`--output`（预先存在的空目录）。上机入口默认仍是本地校验；
显式 `--kind model-container --execute` 才进行设备操作，需另有用户授权。

副作用：临时 ADB、独立私有目录、原厂 ION/安全服务调用。与链接诊断不同，
此进程允许 ioctl；不能称为硬件隔离沙箱。设 10 秒 alarm、12 秒外部 KILL
超时、5 秒 CPU、256 MiB 地址空间、禁 core、低优先级；不能保证中断内核阻塞。
输出容量为输入大小，尾部保护页与前部哨兵检查，返回数据只在 RAM 中并主动清零，
不导出内容、不接真实帧、GUI、LiDAR、AF 或 CNN/VCR。原厂内部分配由原厂接口释放；
不能声称其所有内部缓冲区也经过了本程序清零。

载荷包含仅本轮拥有的 `model.enc`、`probe`、清单和脚本。设备脚本退出时删除载荷，
主机核实后清理日志／目录、恢复 USB 并复查原厂服务。失败不自动重试、不换校验器
或降低验证要求。离线检查通过不代表本步骤已经上机成功。

### 独立进程复用二代原厂调用层

打包工具新增显式 `--loader donor-ca --source-system-root /path/to/x2d2-system-root`。
默认 `--loader stock` 保留一代原厂路径；这两种模式都不是功能安装包。
`donor-ca` 仅额外携带一份**字节未修改**的二代 `libfw_util_ca.so`，模型和其余
组件不变。独立进程首先以完整临时路径加载此库，再加载一代原厂 `libfw_util.so`。
没有向相机服务注入，没有设置 LD_PRELOAD、没有修改系统库、TEE 服务或驱动。

离线核对二代库没有加载初始化入口，固定哈希及 `fw_util_verify_load2ion` 入口
`0x1700`；一代调用库的实际重定位槽为 `+0x1ffe0`。机内程序只读自己进程的该槽，
必须指向临时二代库的已知入口，且 `TEEC_InvokeCommand` 来自一代系统 `libteec.so`，
否则在校验前退出。这里没有重写校验、识别或追踪算法。

两代日志行为也不同：二代调用层向 `/dev/kmsg` 输出诊断文字；程序不启用调试页面。
原有资源限制和自动清理不变，额外库也列入确切清理名单。旧清单因源码／构建器版本变化
会被拒绝，需重新离线生成。上机结果不能只看 dlsym 成功，必须有实际调用目标确认标记。

2026-09-26：ARM64 编译、目标导入检查、32 项离线测试和 dry-run 通过。尝试上机时
连接预检未发现工厂 USB，随后 ADB 和 USB 枚举也均无相机；没有启用 ADB、上传载荷或
调用模型校验。此变体仍为待实机，不能写成已修复上一轮错误。

重新连接后的实机补记：实际调用目标核对通过，但 Pet 模型仍返回 -10，未进入推理。
载荷清理和状态恢复已复核，用户确认机身正常。

### 一代原厂模型对照

打包工具增加 `--model stock-face --target-vendor-root /path/to/x2d-vendor-root`，
用固定哈希的一代 `faceEye.tflite.eng.enc` 替代默认 `--model donor-pet` 输入；
不允许任意模型或修改容器。上机前额外核对机身 `/vendor` 原文件哈希。该次对照使用
`--loader stock`，不携带二代库，保持相同限时和清理边界。

实机返回 0、输出长度 745,512 字节、调用约 18 ms，输出缓冲区清零，退出码 0。
只证明一代容器通过原厂接口，未运行人脸模型。载荷清理、USB 恢复等复核通过，
用户确认正常、无新增显示。33 项离线测试通过。证据和限制见
[适配记录](../../research/ORIGINAL-NATIVE-ADAPTATION.md#二代原厂调用层的最小复用方案与原厂模型对照)。

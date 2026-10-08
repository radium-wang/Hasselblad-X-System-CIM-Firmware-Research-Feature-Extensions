# X2D II 对象识别移植到第一代 X2D

## 适用范围与证据等级

整理日期：2026-09-25。

- 来源：X2D II 100C 1.3.16.2，产品 `eagle2_hb722`。
- 目标：第一代 X2D 100C 4.2.0，产品 `eagle2_ec1706_native`。
- 证据：官方固件提取物的静态分析，以及本模块审计脚本的离线验证。
- 未做：没有连接设备，没有运行二代程序，没有把文件写入第一代相机，没有识别准确率或 AF 联动实测。

本研究只处理对象识别后端。菜单、AF 速度和 AF-C 不在本次范围内。

## 来源实现

二代实现是四层耦合系统，不是单一模型文件：

1. `camera-gui` 提供设置和显示，但不是识别算法本体。本次不迁移这一层。
2. `camera-service` 暴露 `camera.object_detection` 与 `camera.arbitrary_tracking`，维护 `E_ObjectDetection`，把检测结果更新为 `ObjectInfo` 列表，并向 AF 引擎传送对象/任意追踪目标。
3. `/system/bin/dji_ml` 构建 detection、tracking、re-id、pose 等图；其导出符号包含 `CreateDetectionSubGraph`、`CreateTrackingSubGraph`、`CreateReidSubGraph` 与 YOLOv8 后处理类型。
4. `/vendor/model/ml/` 提供加密模型；对象检测主模型为 person、pet、car 三组，每组包含常规、`p90`、`n90` 版本，并配套 pose、re-id、search/template 模型。

来源 `camera-service` 的静态符号确认了 `setObjectDetection`、`onAfObjectDetectionCb`、`updateDetectedObjects`、`setArbitraryTracking` 及对应 D-Bus 属性。原厂自测脚本按 Human、Pet、Vehicle、Off 顺序设置属性，说明这四种模式是正式控制面的一部分，而不是仅供界面显示的字符串。

## 输入输出接口

### 输入

- 识别数据：实时取景帧，由 ML 图的帧管理与预处理链消费。
- 控制属性：`camera.object_detection`。
- 模式：`E_ObjectDetection_Off`、`E_ObjectDetection_Human`、`E_ObjectDetection_Pet`、`E_ObjectDetection_Vehicle`。
- 相关控制：`camera.arbitrary_tracking` 以及任意追踪目标矩形。

### 输出

- `QList<ObjectInfo>` 形式的检测对象，包含对象位置及标签相关信息。
- `DCAMCaptureEnginePrivate::onAfObjectDetectionCb` 接收的 AF 对象检测回调。
- 追踪目标更新和共享的 detected-objects 数据。

第一代 4.2.0 的公开运行面仍是人脸/眼部检测：它有 `FaceInfo`、`E_FaceDetection`、`setFaceDetectionMode`、`setFaceRoiData` 等路径，也包含 HumanBody、HumanHead、AnimalFace 等通用枚举字符串；但第一代 `camera-service` 不包含上述对象识别属性、四种模式、`ObjectInfo` 更新和 AF 对象检测回调。通用枚举字符串不能作为算法或控制链已经存在的证据。

## 模型与算法依赖

离线清单见 [compatibility-audit-4.2.0-vs-1.3.16.2.json](compatibility-audit-4.2.0-vs-1.3.16.2.json)。主要差异如下：

| 项目 | X2D II 1.3.16.2 | X2D 4.2.0 |
| --- | --- | --- |
| 机型变体 | `eagle2_hb722` | `eagle2_ec1706_native` |
| ABI / OS | ARM64, Android 9, API 28 | ARM64, Android 9, API 28 |
| ML 主程序 | 新版 `dji_ml`，含 detection / YOLOv8 / tracking / pose / re-id | 旧版 `dji_ml`，以 face/eye、FDC、template/search tracking 为主 |
| 模型格式 | 22 个 `json.eng.enc` 文件，约 53.9 MiB | 旧 `tflite.eng.enc` 与资产，共约 30.3 MiB |
| 对象类别 | Human / Pet / Vehicle / Off | 无对应后端属性契约 |
| 二代新增用户态依赖 | `libvision_cnn.so`、`libvision_vcr.so`、`libopencv_world.so`、`libpose3d_cbb.so`、`libfacex_cbb.so`、`libpoa_cbb.so`、`libkpt_tk_cbb.so` | 不存在 |

除此之外，二代 `dji_ml` 依赖且一代也有的 18 个用户态库全部为不同构建，包括 `libdsp_frwk.so`、`libnn_framework.so`、`libmot_cbb.so`、`libreid_cbb.so`、`libdynamic_roi_cbb.so` 和 `libcnntk_cbb.so`。因此只补齐 7 个缺失库仍不能证明 ABI 闭合。

两代模型都是加密文件。补充核对全部一代 23 个与二代 22 个 `.eng.enc` 文件：前 4 字节均为 `IM*H`，偏移 40–47 均为 `PRAKTBIE`。因此此前将 `.json` / `.tflite` 后缀差异写成“加密容器格式不同”过强；现在只能确认模型名称和封装载荷预期有差异，不能由共同文件头推断能在另一平台解密、加载或正确执行。

新增 ELF 强引用符号审计见 [symbol-surface-4.2.0-vs-1.3.16.2.json](symbol-surface-4.2.0-vs-1.3.16.2.json)。二代 `dji_ml` 有 385 个强引用动态符号；即使保守地假定第一代 `system/lib64` **所有** `.so` 都可见，仍有 48 个找不到。一代原厂 `dji_ml` 的 301 个强引用在一代库中全部找到；二代原厂的 385 个强引用也在二代库中全部找到。缺失的 48 个中，22 个只在二代的同名新版库中提供，包括 `libnn_framework.so`、`libcnntk_cbb.so`、`libmot_cbb.so` 等；另有 25 个只由一代缺少的库提供，1 个兼有这两类来源。故只补齐新增的 7 个库仍不能让二代 `dji_ml` 与第一代原厂库完成符号绑定。这一检查不考虑符号版本、C++ 对象布局及动态链接器命名空间；它是拒绝直接替换的充分证据，但绝不构成成功移植的充分测试。

## 运行资源与目标平台约束

### 已确定

- 二代对象模型目录为 56,522,496 字节；一代现有 ML 模型目录为 31,823,040 字节。
- 二代 `dji_ml` 约 4 MiB，并额外直接依赖 7 个一代缺失的用户态库，其中 `libopencv_world.so` 约 8.9 MiB。
- 两代 `vision_cnn.ko`、`vision_vcr.ko`、`vision_sgbm.ko` 三个内核模块哈希全部不同。
- 两代 `ss_dsp0.fw`、`ss_dsp1.fw`、`ss_dsp2.fw` 三个 DSP 固件哈希全部不同。
- 两代同为 ARM64 / Android 9，只解决 ELF 指令集与基础系统代际问题，不能消除 EC1706 与 HB722 的视觉加速器、DSP、服务接口和模型容器差异。

### 尚未知

- 第一代可供对象检测使用的连续内存、DSP/NPU 调度余量、热设计余量和实时帧预算。
- 二代加密模型是否能合法转换为 EC1706 可加载格式。
- 第一代 AF 引擎接受通用对象 ROI 的精确调用约束、坐标系、时序和失效行为。

这些未知项不能通过桌面 ELF 可加载或字符串存在来替代实测。

## 移植方案与执行状态

### 阶段 0：兼容性门禁 — 已执行

新增只读工具 `tools/audit_port.py`，它锁定并比较：

- 产品、设备、Android API 与 CPU ABI；
- `camera-service` 的四个模式和后端契约标记；
- `dji_ml` 的 ELF 依赖闭包；
- 模型清单、大小、哈希与文件名格式；加密封装头另行只读核对；
- 视觉内核模块和 DSP 固件哈希。
- 二代 `dji_ml` 的强引用符号能否由一代原厂 `system/lib64` 提供（额外的只读审计）。

本轮真实输入被门禁拒绝，`direct_binary_transplant_ready=false`。拒绝原因完整写入 JSON 证据。离线单元测试覆盖通过与拒绝两条分支。符号审计进一步确认二代主程序不能直接绑定第一代原厂运行库。

### 阶段 1：EC1706 原生检测后端 — 阻断

目标不是让一代加载 HB722 二进制，而是产生一个针对 EC1706 4.2.0 ABI 的后端：

- 模型必须由 EC1706 支持的工具链生成，并保留来源和许可；
- 后端必须链接一代自己的 ML/DSP 用户态库；
- 输出先停留在规范化对象列表，不立即写 AF ROI；
- 加载、模型解析或推理失败时必须 fail closed，不改变原厂人脸检测和 AF 行为。

当前缺少可构建源码和模型转换链，无法安全实现此阶段。把二代库、DSP 固件和内核模块整套覆盖到一代会同时改变相机核心运行栈，已超出可验证的“对象识别移植”。

### 阶段 2：第一代服务适配 — 等待阶段 1

在后端可独立离线加载后，再为第一代增加版本绑定的最小适配层：

- 输入：第一代实时取景帧描述符；
- 设置：Off / Human / Pet / Vehicle；
- 输出：类别、置信度、目标矩形、帧号；
- AF 桥：只在坐标、时序和失效回退验证后把选定目标转换为原厂 AF ROI。

不得直接替换整个二代 `camera-service`，也不得复用二代地址或对象布局。

### 阶段 3：验证 — 等待阶段 1/2

1. 桌面：模型加载失败、空帧、越界框、类别切换和超时回退。
2. 机内非 AF：只显示/记录规范化检测结果，测帧率、内存、温度和休眠恢复。
3. AF 联动：分别验证 AFS 与支持条件下的追踪；这一步不等于修改 AF-C 功能。
4. 冷启动与恢复：原厂后端在候选失败时仍能启动，停用候选后恢复原行为。

每一阶段都必须有独立退出条件，不能用“界面出现选项”替代算法和 AF 联动验收。

## 当前结论

静态分析与离线验证结论：二代对象识别的控制面、运行时、模型、DSP 固件和视觉内核模块共同构成平台绑定实现。当前已有材料足以否定直接二进制移植，但不足以生成第一代可运行后端。

截至 2026-09-25，本轮实际交付的是可重复、可审计、默认拒绝不兼容候选的移植门禁；当时对象识别尚未进入机内运行。随后第一代原生旁路试验见下节。

## 2026-09-26：第一代原生旁路路线（历史，已退役）

后续用户报告预览卡顿／闪烁，并明确要求保留二代原厂算法。以下旁路方案不再执行，也不是当前移植路线。最新原厂模块适配及其边界见 [ORIGINAL-NATIVE-ADAPTATION.md](ORIGINAL-NATIVE-ADAPTATION.md)；早期“必须取得源码才能继续”的判断不应阻止对现有原厂二进制进行具体接口兼容分析。

用户指出第一代后来增加了人脸识别。此事实与固件证据一致：第一代 `camera-service` 有 `FaceInfo`、`MLControl::handleResults`、`MLControl::setTrackingTarget` 和 `setFaceRoiData`；`dji_ml` 含 `vpfVotStartReqProc`、`vpfVotSetMainTargetReqProc`，并引用 `template.tflite` / `search.tflite`。这些证据支持“一代已有检测、目标 ID 追踪和 AF ROI 基础设施”，但**不证明**其固有模型会输出 Human / Pet / Vehicle 三类对象，也不证明二代 YOLOv8 模型可直接加载。

新的实现假设是保留第一代原厂 `dji_ml`、DSP、内核模块和 `camera-service`，用旁路 CPU 检测器提供三类目标框，再研究把稳定目标接入第一代追踪/ROI。第一代 `/system/lib64/libopencv_java3.so` 自报 OpenCV 3.4.5，并含 `cv::dnn::readNetFromDarknet`、`readNetFromCaffe`、`readNetFromONNX` 与 `Net::forward` 符号。这提供了不依赖二代视觉加速器的候选推理库，但尚未验证模型加载或推理速度。二代加密 YOLOv8 模型不能直接当作 OpenCV 输入；需要来源与许可明确、可由 OpenCV 3.4.5 解析的另一个检测模型。因此这是**功能等效重建候选**，不是逐字节复制二代算法。

同日实机只读预检：USB 枚举为预期工厂接口，固件版本读回 `v4.2.0`，产品为 `eagle2_ec1706_native`；一次 `/proc/meminfo` 读到总内存约 771 MiB、可用约 448 MiB；机内确有原厂 OpenCV 库及 template 模型。内存快照不能替代峰值 RSS、持续帧率或温升测试。这轮没有上传模型、启动候选程序、改动服务或写 AF 参数。

最快的上机门禁顺序：

1. 离线取得 ARM64 Android 9 工具链及许可明确的轻量检测模型，编译**独立进程**，不替换原厂文件。
2. 在设备临时目录做有独立超时的“加载模型 → 单张测试帧 → 输出类别/置信度/矩形 → 退出”试验；不读取实时取景、不调用 AF。无论成功或失败都核对原厂取景和服务仍正常。
3. 单帧通过后才研究实时帧获取、低频识别与原厂追踪器的目标 ID/坐标契约；先记录目标框，不驱动镜头。
4. 只有追踪、失锁和坐标门禁在机内证实后，才另行测试 AF ROI；候选停止或超时应恢复原厂脸/眼与中心/触点 AF。

上述工具链与单帧程序后来已构建并进行一次实机试验，结果见下。实时取景输入、连续追踪和 AF 联动仍未完成。

### 首次机内单帧结果（实机验证）

首版的单输出限制来自原厂 OpenCV 库与新 NDK 的 `std::vector` ABI 不同。已按 OpenCV 3.4.5 Darknet 导入器的 `yolo_%d` 命名规则修改候选，改为分别调用该配置的 `yolo_16` 与 `yolo_23` 输出层；新版本已本地编译，尚未实机运行，不能把前述单输出结果归给它。

# X2D II 对焦、对象识别与追踪移植到第一代 X2D

## 适用范围与证据等级

整理日期：2026-09-25。

- 来源：X2D II 100C 1.3.16.2，产品 `eagle2_hb722`。
- 目标：第一代 X2D 100C 4.2.0，产品 `eagle2_ec1706_native`。
- 证据：两版官方固件提取物的 ELF 符号、AArch64 直接调用、配置与服务接口静态分析；第一代原厂 AF-C 后端另有 2026-09-23 实机运行记录。
- 未做：没有进行两机同场计时，没有测试对象识别准确率、追踪稳定性或镜头机械极限。2026-09-25 后续已接入第一代机身，做了只读预检、不写 AF 代码的暂停/恢复演练、原厂 AF-S 初始计时及一次 55V 扫描速度候选的限时 RAM 试验；详见下文追加记录。

本文回答三个相互关联、但不能混成一个补丁的问题：更快的 AF-S、实际可用的 AF-C，以及 Human / Pet / Vehicle 对象识别与目标追踪。

2026-09-25 实机追加：55V 镜头原厂 AF-S 三次成功样本从服务状态机进入到成功结果为 388 ms、211 ms、205 ms。无代码写入的暂停/恢复演练通过；在该阶段候选尚未写入。这些样本不是 X2D II 对比，也不足以估计提速。第三次只读轨迹显示首帧目标位置 90、合焦前当前镜头位置 117，且过程中目标估计一度跳至 247。后续离线数据流复核又发现既有绝对位置路由候选可能发送**最近安全界而不是 PDAF 目标**，方向可能偏离预测峰值；该候选已隔离，禁止上机。详见[设备记录](../../CodeTests/temporary_af_speed_probe/pdaf-abs-route-candidate/DEVICE-RESULT-2026-09-25.md)。

2026-09-25 后续限时试验：另一个、与绝对位置路由无关的 55V `lens_ctrl_get_focus_speed` 扫描速度候选，在用户同意并现场监护下临时写入第一代机身 RAM 15 秒，设备报告候选激活，随后完整原函数哈希和服务运行状态通过恢复核验，独立 `status` 也确认 `ORIGINAL_VERIFIED`。用户一次半按报告合焦且无异常。原厂日志一组完整事件约 367 ms；试验后一组约 272 ms，但后者靠近恢复时刻、没有精确 ACTIVE／RESTORED 时间戳，**不能确认它发生在候选生效期间，也不能据此计算提速**。这次验证的是部署与回滚，不是性能或机械安全。详见 [macOS 试验记录](../../CodeTests/temporary_af_speed_probe/MACOS-AF-SPEED.md)。

增加精确设备端时间戳后，一次 15 秒复试证实操作者两次半按均发生在自动恢复之后；另经单独授权的一次 45 秒窗口取得一组真正落在候选生效期间、机身报告成功且无可见异常的 AF-S 事件，状态机约 247 ms。恢复原厂后的近处对照约 363 ms，测试前一次近处原厂对照约 326 ms；但候选样本最终镜头位置为 1100、恢复原厂后样本为 1691，起点分别约 112／114，行程严重不匹配。用户确认机身为手持或构图有变化。候选日志虽出现扫描命令，也有绝对位置收尾。因此**仍不能宣称候选带来 AF-S 提速**；需要固定 AF 点与目标平面、相同起止镜头位置和成对重复。三次限时试验均恢复原厂函数，第三次经独立 `status` 复核。详见同一[实机记录](../../CodeTests/temporary_af_speed_probe/MACOS-AF-SPEED.md)。

用户再次请求后，相机与 AF 框固定，以可复位的近卡／远景采集两组原厂对照：近处终点 1011／1012，合焦约 333／342 ms。再经用户确认进行一次 45 秒候选窗口：唯一 AF-S 成功事件及终点 1010 确认处于候选生效期间，合焦无可见异常且原函数恢复；但设备日志环形缓冲区冲掉了 `FindFocusStart`，故**无候选合焦耗时**。目标位置终于可比，时间数据却不完整，仍不能判断性能。后续需先建立有界设备端日志采集，再取得新的实机授权。

后来经单独授权完成一次固定目标的 45 秒扫描提速候选＋有界日志组合：唯一窗口内 AF-S 为 **296 ms**，恢复后的同目标原厂样本为 **351 ms**；另有原厂样本 333、342、472 ms。候选扫描命令数值 2595、恢复后同方向可见原厂数值 1297，但这只是一轮候选样本，不能证明重复性、镜头安全或 X2D II 算法已移植。完整记录见 [MACOS-AF-SPEED.md](../../CodeTests/temporary_af_speed_probe/MACOS-AF-SPEED.md)。该候选已自动恢复，并经独立状态查询确认 `ORIGINAL_VERIFIED`。

## 当前结论

1. **X2D II 的快速 AF-S 不是单纯把镜头扫描速度乘大。** 二代相位 AF-S 主函数不直接调用 `lens_ctrl_get_focus_speed` 或 `lens_cmd_push_focus_scan_cmd`，而是利用 PDAF 网格、目标位置对齐和直接绝对位置命令。更少扫描行程是代码支持的机制假说；实际缩短多少毫秒尚无两机同场计时。
2. **仓库现有 X2D 提速方法与二代机制只有局部关系。** `lens_ctrl_get_focus_speed` 倍率补丁和 Type2→Type1 候选都会加快第一代的方向扫描分支；二代也保留速度计算、动态限速和 `scan_speed_boost: 1.5`。但这些方法不能复制二代的目标估计、状态机、PDAF/ToF 输入和 AFC 控制器。
3. **第一代的基础 AF-C 不需要从二代移植。** X2D 4.2.0 原厂已有 `StateAfContinuousFocus` 和 `_exec_pdaf_afc_process`，且真机曾观察到 `SuccessCont` 和松开后的 `SessionStop`。当前重点应是质量验收和调参，而不是替换二代库。
4. **要达到 X2D II 级别的 AF-C/对象追踪，不能直接复制二进制。** 二代增加了约 40 KiB 的 `afc_ctrl_process`、smart ROI、PDAF mesh、ToF 融合、对象检测回调和新版 ML/DSP 栈；第一代缺少这些完整契约。
5. **最现实的路线是分层复现概念，但第一版绝对位置路由候选已被否决。** 它复用 X2D 原厂 `_push_filtered_abs_cmd`，不引入二代 ToF/LiDAR 代码，却错误地可能把安全界而非 PDAF 目标送入绝对位置命令；[离线候选](../../CodeTests/temporary_af_speed_probe/pdaf-abs-route-candidate/README.md)现已隔离，不能用于实机。对象识别仍须另建 EC1706 可运行的检测后端，最后才把稳定目标 ROI 接给 AF-C。

## 静态证据：两代 AF 主路径并不相同

本轮锁定的核心文件如下。哈希只适用于表中的固件版本。

| 文件 | X2D 4.2.0 SHA-256 | X2D II 1.3.16.2 SHA-256 |
| --- | --- | --- |
| `libaaa.so` | `feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7` | `7d6164eccc734de7087bb778ee72f17a0b3ccf6c0d1f20092c7ebe74a86574ba` |
| `librcam.so` | `72ebc8deebce4a29047c475e77ab4edbf2860abb1f572fea45260fe17ad0bda5` | `3dd5b37b3db18b3e6b54271e1501b4dd337e101c06cdd386a896b1547b662f66` |

二代 `af_imx861.json` 的 SHA-256 为 `e4f965ed8634c0e14d418d4f57131243d7ea197b8abea2a84d9ee0f934d2ed9e`。

### AF-S

| 符号 | X2D 4.2.0 | X2D II 1.3.16.2 | 关键差异 |
| --- | --- | --- | --- |
| `_exec_pdaf_afs_process` | `0x90128`，1872 B | `0x1863f8`，2052 B | 一代有两处 `get_focus_speed → focus_scan_cmd`；二代主函数没有这两类调用 |
| `get_pdaf_distance_to_peak` | 812 B | 2288 B | 二代距离/峰值分类明显扩展，大小本身不等于性能，但调用和数据处理更丰富 |
| `lens_ctrl_get_focus_speed` | `0xac380`，1068 B | `0x213d30`，2580 B | 二代加入 AF-C 触发、数码变焦、拍照尺寸、最小/最大速度与 `limit_speed_range` 等上下文 |
| `lens_ctrl_set_focus_abs_param` | `0xa8bb8`，228 B | `0x20e470`，776 B | 二代支持 fine-tune 条件下把绝对位置请求转为受控扫描；普通路径仍可直达目标位置 |

第一代 `_exec_pdaf_afs_process` 的两处方向扫描分支调用：

```text
get_pdaf_distance_to_peak
  → 选择 Type2 / Type5
  → lens_ctrl_get_focus_speed
  → lens_cmd_push_focus_scan_cmd
```

同一函数也有 `lens_cmd_push_focus_abs_cmd` 和 `_push_filtered_abs_cmd`，所以第一代本来就是“扫描 + 位置命令”的混合实现。

二代 `_exec_pdaf_afs_process` 则调用 `_get_pdaf_align_lens_position`、PDAF mesh peak/ROI 和标准差时间滤波，随后使用 `lens_cmd_push_focus_abs_cmd` 或 `_push_filtered_abs_cmd`；该函数内没有 `lens_ctrl_get_focus_speed` 和 `lens_cmd_push_focus_scan_cmd`。这说明二代 AF-S 的主要提速逻辑更接近：

```text
更密集/更低延迟的测量
  → 估计应到达的镜头位置
  → 一次绝对位置移动
  → 必要时再小范围确认
```

而不是：

```text
保持原来的搜索路程
  → 只把扫描速度乘大
```

二代位置发送链使用 12 字节 X2Lens 消息；已查路径仍未发现独立的速度字段。因此，二代的直达位置移动也不能用 `lens_ctrl_get_focus_speed` 倍率补丁来等价描述。

### PDAF Type2 与 Type3 的真实移植边界（2026-09-25 追加）

第一代 4.2.0 导出 `pdaf_type3_run`（`0x8c8e0`）及 `pdaf_type3_cfg_x2d`，并在 Type3 路径包含 `sizeof(af_pdaf_type3_libaaa_input_s)` 输入大小断言。二代 1.3.16.2 的 `af_imx861.json` 则明确配置 `pd_type: PDAF_ALG_TYPE_2`、`stat_cfg_type: af_pdaf_type2_load_cfg_s` 和 `pd_mode: PDAF_TYPE_MODE_DSP_V3`；其 `pdaf_type2_run` 位于 `0x16e4c8`。二代 AF-S `0x186438` 调用的局部位置助手在 `0x185f24` **直接调用 `get_pdaf_type2_align_lens_pos`**，而不是读取一代 Type3 对象。二代 `pdaf_type2_run` 还在 `0x16e5bc` 使用固定大小的上下文结果 `memcpy`。这些是版本锁定的 ELF/配置静态证据，表明直接复制二代 AF-S 函数或把多出的 AF 区域截掉，无法构成一代可用的输入/输出 ABI 适配；“425/294 个区域”也不是两份相同结构数组的长度差。

一代 `pdaf_type3_statistics` 在 `0x8efec` 检查输入头大小为 `0x7d0`、在 `0x8f008` 核对帧号，并在 `0x8f0c0` 复制从输入 `+0x10` 起的 `0x6ff` 字节到 Type3 上下文 `+0xae4`。`pdaf_type3_roi` 在 `0x8e2e4`–`0x8e33c` 将四个浮点 ROI 坐标按设备区域尺寸换算成上下文中的整数边界。这说明第一代确有可追查的几何与帧同步入口，但**不能**仅凭这些偏移宣布每个相位区域、置信度或焦点目标的完整语义已解出。后续只读采集必须先证明字段与原厂日志/终点一致，不能对相机内存做猜测性写入。

### 优先移植路径：复用一代 Type3 汇总结果，而非逐点重排二代网格

用户观察：遮挡 X2D II 的雷达后，对焦主观上仍快于第一代。此观察提高了“PDAF-only 决策链值得优先研究”的优先级，但遮挡不等于固件内 ToF 被禁用，也没有同镜头、同目标的两机计时，不能据此量化雷达贡献。

二代 `_exec_pdaf_afs_process`（`0x1863f8`）及本次追查的两个本地位置命令助手（`0x186c00`、`0x1874f0`）的直接 `BL` 中，没有 ToF/fusion、`lens_ctrl_get_focus_speed` 或 `lens_cmd_push_focus_scan_cmd`；可见 PDAF mesh、时间标准差滤波、镜头限位与绝对位置命令。这是**直接调用链**证据，不能排除更早的统计生产、共享上下文或其他状态机间接使用 ToF。它足以确定优先研究 PDAF-only AF-S 位置路径，而不是把“挡住雷达”当作完整禁用实验。

现在可将**X2D II 的位置优先策略**与其 Type2 传感器处理分开：保留一代原厂 Type3 对 294 区域和当前 ROI 的统计、标定与合成结果，只在一代的 AF-S 决策/镜头命令层研究“高可信时直达峰值，否则原厂扫描”。这绕开 425→294 个点的原始统计 ABI 转换；它是策略适配，不是复制二代 `libaaa.so`。已有 55V 真机只读样本表明第一代 Type3 的汇总结果随镜头运动更新；二代 `_exec_pdaf_afs_process` 通过 Type2 对齐位置助手取处理后的结果，而不是在 AF-S 主函数里逐点解码 425 个区域。

精确版本锁定的第一代 `_exec_pdaf_afs_process` 给出了可复用边界：

| 静态位置 | 已证实的数据/调用 | 对移植的意义 |
| --- | --- | --- |
| `0x90158`、`0x901a0`、`0x9078c` | 取 `pdaf_lib_handle`；读取 `+0x10` 有符号离焦量、`+0x0c` 置信度 | 可以沿用原厂 Type3 汇总结果，不需伪造二代 Type2 上下文 |
| `0x90288`–`0x9029c` | 在一个分支用当前镜头位置加离焦量形成预测峰值，写入 `[sp+0x68]` | 需核对符号、步数与帧新鲜度；日志首帧 `target_pos` 不能直接等同峰值 |
| `0x903d8`–`0x903e8` | 按结果类型跳表；类型 2 到 `0x90400`，类型 3 到 `0x90500` | 一代已经同时具备扫描与位置控制策略，不能靠整体换库才获得直达位置 |
| `0x90500`–`0x905d8` | 类型 3 路径经原厂镜头范围限位、状态更新后，用预测峰值提交 `lens_cmd_push_focus_abs_cmd` | 可作为研究位置优先的原厂命令模板；**不能**直接把类型 2 改写成 3，因为类型、状态和限位语义不同 |
| `0x90678/0x906a0`、`0x90840/0x90868` | 类型 2 等方向扫描路径选速并发 `lens_cmd_push_focus_scan_cmd` | 回退应继续这些原厂调用，不是“出错后删除代码” |

上表的跳表来自 `0x1a4a54` 的四个有符号偏移，解析目标依次为 `0x903ec/0x905e4/0x90400/0x90500`。旧“绝对位置路由”候选跳向 `0x906ec`，参数是最近安全界而非峰值，已经隔离；**不得**把这条旧候选当作上述新路线的起点。

最快有价值的实现顺序是：先做一个**默认透传的 AF-S 决策拦截层**，仅记录一代 Type3 汇总结果、原厂所选分支和命令；在离线轨迹上验证峰值、置信度和镜头终点的误差，并以镜头范围、帧号、结果类型及多帧一致性设置 fail-closed 门禁；再独立验证不改变镜头行为的加载/回滚；最后才考虑对合格样本用一代原厂绝对位置命令替代扫描。任何首次驱动测试必须与旧速度倍率补丁互斥，RAM-only、限时恢复、完整原函数哈希核验、机旁监护。现阶段尚无通过这些门禁的新候选，因此不会把下一次半按当作“二代算法上机”。

AF-C 和对象识别应排在这个 AF-S 路线之后：第一代已有 AF-C 后端，但二代的 `afc_ctrl_process` 包含 ToF 融合、smart ROI 和新跟踪上下文，不能用“禁用雷达”一项配置复制；对象识别还缺第一代可运行模型与服务契约。

剔除 ToF/LiDAR 后可以研究的，是二代**位置优先、mesh/ROI 汇总和严格失效回退的控制思路**，不是原样覆盖 `libaaa.so` 或二代 `af_imx861.json`。因此新增 [PDAF-only 影子候选](../../CodeTests/pdaf-only-shadow/README.md)：以显式的第一代区域几何及标定后位置估计做离线汇总，拒绝稀疏、陈旧、矛盾或越界输入，默认继续原厂 AF 路径。它无测距字段、无设备部署和镜头命令；第一代 Type3 区域坐标、置信度标尺、镜头位置换算仍未证实，不能把离线单元测试写成移植完成。真正运行时回退必须在镜头命令之前发生；事后删除候选并恢复原厂参数不能撤销一次错误运动。

[一次新增的原厂 Type3 只读实机采样](../../CodeTests/pdaf-only-shadow/DEVICE-RESULT-2026-09-25.md)在固定机位、55V、AF-S 取得远／近两次成功事件（328／438 ms）。远处首帧 `cur_pos=979, peak=90, target_pos=313, conf=178`，随后目标值显著变化并在经过峰值后翻转方向；近卡首帧 `cur_pos=110, peak=883, target_pos=689, conf=15`，后续目标也持续漂移。即便是第一代原厂 PDAF 输出，也不能仅凭一帧或一个置信度数值决定直达位置。此采样没有运行影子候选，不是 X2D II 算法移植或性能验证。

进一步对两版原厂 ELF 逐条核对：第一代 AF-S 主函数分别在 `0x90678/0x906a0` 和 `0x90840/0x90868` 成对直接调用选速与扫描命令；二代同一主函数没有这两种直接调用。二代一条直接位置路径先在 `0x186894` 保存计算出的位置，存在镜头马达信息时在 `0x1868c4` 通过 `limit_pos_range` 限位，随后在 `0x186968` 提交 `lens_cmd_push_focus_abs_cmd`。这支持“目标估计和位置命令链不同于单纯加快扫描”的静态机制判断；它不证明每次拍摄都走该路径，亦不能据此量化相机间的速度差。第一代旧路由候选反而在 `0x906ec` 传入最近安全界，不能把它等同于这条二代路径。

### 二代配置中真正启用与未启用的项

X2D II 1.3.16.2 `af_imx861.json` 静态显示：

- `skip_wait_for_ae: 1`，允许 AF 不等待 AE 稳定；
- 13 组状态允许在同一帧继续转换；
- `max_frame_for_jump: 1`、CDAF `frame_delay: 0`；
- PDAF `stats_frame_delay_vs_lens: 1`、`low_lattency_afc_enable: 1`；
- PDAF 使用 `PDAF_TYPE_MODE_DSP_V3`；
- `afc_interval_time_ms: 30`；
- 动态速度计算启用，且按帧率、镜头最小/最大速度和场景限速；
- AF 算法配置启用 ToF，AFC 控制器以 PDAF 为 master、ToF 为 slave/backup 做融合；
- `scan_speed_boost: 1.5` 在三组 PDAF 模式参数中存在。

同时必须排除两个容易误判的点：

- `afs_speed_route_planner_run` 代码确实存在，并由 `af_lib_run` 调用，但本版配置是 `rtp.enable: 0`；函数入口也先检查该开关。因此不能把当前二代快速 AF-S 直接归因于 route planner。
- `pdaf_afc_finetune` 代码确实存在，但本版配置是 `finetune.enable: 0`。它证明二代预留了更完整的微调机制，不证明默认拍摄时启用。

综合这些证据，二代速度优势可能来自多个层级：传感器/PDAF 测量、可选的 ToF 距离输入、目标位置估计、等待帧/状态机、镜头命令调度以及实际所用镜头。静态分析不能给各项分摊毫秒，也不能证明 ToF 在某次具体对焦中必然参与。厂商资料明确说明二代有 425 个 PDAF 区域并配合 LiDAR，而一代为 294 个 PDAF 区域；这两项硬件差异不能靠替换软件获得。[X2D II 官方产品页](https://www.hasselblad.com/x-system/x2d-ii-100c)、[发布资料](https://www.hasselblad.com/press/press-releases/2025/hasselblad-introduces-the-x2d-ii-100c-and-xcd-35-100e/)。

### 不带 LiDAR 的可迁移部分与边界

| 层级 | 二代观察 | 第一代可用路径 | 是否纳入当前候选 |
| --- | --- | --- | --- |
| PDAF 目标位置优先 | `_get_pdaf_align_lens_position`、PDAF mesh、绝对位置命令 | 需重新设计第一代 PDAF 目标的 ABI 与方向门禁；不能复制二代 PDAF Type2 数据布局 | 否；旧路由候选因安全界误作目标被隔离 |
| 扫描速度 | 仍有 `lens_ctrl_get_focus_speed`、动态限速与 `scan_speed_boost`，但二代 AF-S 主函数无直接扫描调用 | 第一代扫描分支可单独测试 Type1 或倍率候选 | 否，不叠加 |
| 等待帧/状态机 | `skip_wait_for_ae` 等配置 | 需要独立测量与验证曝光/失焦风险 | 否 |
| ToF/LiDAR 融合 | 配置启用 ToF；AFC 控制器含融合路径 | 第一代没有测距硬件，不能仅复制配置或函数 | **明确排除** |
| 对象检测/追踪 | 新对象接口、模型与 smart ROI | 须独立做第一代可运行检测器和 AF-C ROI 适配 | 否 |

厂家同时推出的 XCD 35-100E 被称为其对焦最快的 XCD 镜头，因此任何跨机身速度比较都必须使用同一镜头及固件，不能把镜头差异算作机身算法收益。[发布资料](https://www.hasselblad.com/press/press-releases/2025/hasselblad-introduces-the-x2d-ii-100c-and-xcd-35-100e/)。

### 与 GUI 预加载方案的关系

“菜单修改”任务实机验证的是原厂 `camera-gui` 进程内的 QML 内容替换，不是 AF 库替换。X2D 4.2.0 的静态 ELF 则显示 AF 库位于另一条链：`camera-service → libdcam_frwk.so → libduml_hal_cam.so → librcam.so → libaaa.so`。`pdaf_lib_run` 在 `0x921b4` 经 PLT 调用导出的 `_exec_pdaf_afs_process`，符号为 `STB_GLOBAL`/`STV_DEFAULT`，未见 `DT_SYMBOLIC`/`DF_SYMBOLIC`。这为“服务进程预加载拦截”提供了**静态可行性线索**，并不证明设备上可预加载、可安全替换或可回滚。加载边界可用[离线验证器](../../CodeTests/temporary_af_speed_probe/pdaf-abs-route-candidate/verify_loader_boundary.py)复核；当前没有 AF 拦截器，也没有设备上的加载试验。

## 与仓库现有两种提速方法的关系

### `lens_ctrl_get_focus_speed` ×3/×3/×2 补丁

该候选只改变 X2D 4.2.0 动态计算成功后的三类拍照扫描速度：Type0 ×3、Type1 ×3、Type2 ×2；之后仍经过原厂帧率修正和数值上限。它不改变：

- 绝对位置命令；
- 动态计算失败后的回退速度；
- Type3/4/5；
- PDAF 目标估计、等待帧、AF 状态机和追踪；
- 镜头机械极限或对焦协议。

因此它和 X2D II 的关系是“同属镜头运动速度层”，不是“移植了二代 AF 算法”。2026-09-25 的限时实机试验证明该候选可被短时激活并恢复，且取得一次候选窗口内成功合焦；但配对目标的最终镜头位置与行程明显不同，仍无可归因的端到端 AF-S 提速或马达实际速度证据。

### PDAF 扫描 Type2→Type1 候选

该候选只把第一代两条已定位方向扫描分支从理论 `B/4` 改为 `B/2`，离线可验证为请求值 2×。它比全局倍率更窄，但仍保留第一代的扫描式控制；二代主 AF-S 路径没有对应的两次速度调用。因此它适合验证“第一代是否过早慢扫”，不能被称为二代算法移植。

### 结论

如果“库中那个增强对焦速度的方法”指上述任一候选，答案是：**有局部关系，但不是 X2D II 更快的主要充分条件。** 它们最多改善第一代 AF-S 中确实走扫描分支的部分时间；如果瓶颈是测量等待、方向判断、目标位置误差或收尾确认，提高扫描速度不会按同样倍率缩短总合焦时间。

## AF-C：第一代已有可用内核，二代增加的是质量层

### 第一代现状

X2D 4.2.0 `camera-service` 和 `libaaa.so` 已包含：

- `StateAfContinuousFocus`；
- `MetadataControl::setContinuousFocus()`；
- `E_AutoFocusStatus_RunningCont` 与 `E_AutoFocusResult_SuccessCont`；
- `_exec_pdaf_afc_process`（1032 B）与 `afc_tracking_process`。

进一步核对直接调用：第一代 `_exec_pdaf_afc_process` 主要更新 `alg_set_afc_info`、时间滤波和运动信息，函数内**没有** `lens_ctrl_get_focus_speed`、`lens_cmd_push_focus_scan_cmd` 或 `lens_cmd_push_focus_abs_cmd`。第一代 `afc_manager_run → afc_process` 从算法读取有效性、分数与离焦量，设置 ROI，并在条件满足时调用 `hybrid_af_start`。因此上文 AF-S 扫描路由候选不能被当作 AF-C 控制器移植；即使它间接影响一次重新获取焦点，也不能据此声称持续追踪改善。

2026-09-23 真机运行记录观察到 `StateAfSingle → StateAfContinuousFocus`、`SuccessCont`，AF-D 松开后产生 `SessionStop` 并恢复 AF-S。这证明第一代后端不是空壳。它仍只证明一次受控会话，不能代替多镜头、近远运动、低照度、低反差、休眠和连续拍摄验收。

### 二代新增的 AFC 能力

二代 `_exec_pdaf_afc_process` 为 1708 B，对比一代新增或显著扩展：

- `_get_pdaf_align_lens_position`；
- mesh peak/ROI；
- `afc_ctrl_save_peak_info` 和 `afc_ctrl_get_status`；
- `is_af_tracking_available` 与 tracking mode；
- 人脸/强制无穷远/弱光/IMU 等场景标志；
- `pdaf_afc_finetune` 调用点；
- no-score 与置信度处理。

更关键的是，二代另有 `afc_ctrl_process`（`0x1f2560`，40588 B），而一代没有同名控制器。其直接调用覆盖 smart ROI、tracking availability、PDAF/ToF 融合、运动限制、场景/IMU、预测时间、镜头位置与失焦控制。这不是把一代几个阈值改大就能得到的功能。

二代 1.3.16.2 的 AFC 配置把算法选择设为 PDAF 和 ToF 同时启用（`afc_ctrl_alg_cfg=[1,0,0,1]`），`fusion_enable=1`，PDAF 为 master、ToF 为 slave/backup；`enable_tof_tracking=0` 仅说明独立 ToF tracking 开关关闭，**不等于** AFC 融合不用 ToF。若在第一代做无测距硬件的 AFC，必须重新设计 PDAF-only 控制器及无效测量回退，不能把这组二代配置原样复制。

因此：

- **基础、中心/触点 ROI 的 AF-C：可行性高。** 先完善第一代已有路径的 GUI、触发语义和质量验证。
- **二代级 smart ROI / 对象锁定 AF-C：直接移植可行性低。** 需要检测器、追踪器、ROI 生命周期和新 AFC 控制逻辑共同存在。
- **选择性重写控制概念：可行性中等但工作量大。** 应针对第一代 ABI 实现最小状态机，不能载入二代 `libaaa.so`。

## 对象识别与目标追踪

二代 `camera-service` 明确提供：

- `camera.object_detection` 与 Human / Pet / Vehicle / Off；
- `camera.arbitrary_tracking`；
- `CameraObjectImpl::updateDetectedObjects()`；
- `DCAMCaptureEnginePrivate::onAfObjectDetectionCb()`；
- `ObjectInfo` 列表到 AF smart ROI 的桥。

第一代同一服务有脸/眼检测和原生 AF-C，但没有这组通用对象属性、`ObjectInfo` 更新与 AF 对象回调。二代 `dji_ml`、加密 YOLOv8/pose/re-id/tracking 模型、7 个第一代缺失的用户态库、3 个视觉内核模块和 3 份 DSP 固件又都与第一代构建不同。完整离线门禁见 [对象识别移植研究](../../object-recognition/research/X2D2-TO-X2D-PORT.md)，结果为 `direct_binary_transplant_ready=false`。

这里要区分三个目标：

| 目标 | 第一代可复用部分 | 主要缺口 | 当前判断 |
| --- | --- | --- | --- |
| 人脸/眼睛优先 AF | 已有检测与 ROI 路径 | AFC 长时间稳定性与选择策略 | 最适合先做质量基线 |
| 用户框选单目标追踪 | 旧 ML 栈含 template/search/MOT 线索 | 服务契约、帧输入、丢失重捕和资源预算未闭合 | 可研究，不能宣称已有可用后端 |
| Human / Pet / Vehicle 自动识别追踪 | 可复用取景帧与部分 ROI 桥概念 | EC1706 模型、运行时、类别检测、tracker、服务接口全缺 | 必须重建，不能复制二代二进制 |

对象检测到 AF-C 的正确接入顺序应是：

```text
检测器只输出类别/置信度/矩形
  → tracker 维持 target id、速度与失锁状态
  → ROI 适配层做坐标和帧号校验
  → 第一代 AF-C 消费稳定 ROI
  → 超时、越界或低置信度立即退回原厂中心/触点 ROI
```

不能把逐帧抖动的检测框直接写进镜头控制，也不能用“界面显示识别框”代替追踪和 AF 联动验收。

## 建议的移植路线

### 阶段 A：建立可比较的第一代基线

1. 对同一镜头、同一光照和同一近远目标记录 AF-S 总时间、首次镜头命令帧、最后到位帧、命令类型和重试次数。
2. 分开统计走绝对位置、过滤后位置和方向扫描的样本；否则速度补丁效果会被路径比例混淆。
3. 对第一代原生 AF-C 测试匀速横移、纵深运动、短暂遮挡、低照度和低反差，记录 hunting、丢失、重捕与松开停止。

当前仓库有扫描速度补丁的代码回读、一次 AF-C 状态机成功记录，以及第一代 55V 的三次原厂 AF-S 成功状态机耗时；仍没有按镜头命令类型、PDAF 预测误差和失败率分层的完整基线。

### 阶段 B：验证第一代可回滚的局部优化

1. 先用当前镜头报告的 min/max/fast/slow 数据约束运行时速度覆盖，小步测试，不直接套用二代 `1.5`。
2. 单独比较原厂、Type2→Type1 和受限倍率三种方案；两种补丁不得叠加。
3. 只有扫描分支耗时显著下降且失败率不升，才考虑保留该方向。

### 阶段 C：复现“目标位置优先”，不移植二代库

1. 在第一代 PDAF 输出上只记录预测目标位置，不驱动镜头；与原厂最终合焦位置比较误差分布。
2. 按镜头、距离、光圈、光照和方向建立置信度门禁。
3. 仅在高置信度时使用一次绝对位置命令；任何异常立即退回原厂扫描路径。
4. 不先删除 AE 等待或确认帧。状态机压缩必须晚于位置预测验证。

旧的精确版本锁定[离线路由候选](../../CodeTests/temporary_af_speed_probe/pdaf-abs-route-candidate/README.md)虽能验证跳入原厂过滤绝对位置函数，但其参数是选中的安全界，而不是 PDAF 预测目标；在一组实际只读轨迹中存在背离预测峰值的方向风险，故已隔离。**必须先重做参数数据流与双向安全门禁**，再谈目标误差采样或实机性能验证。

### 阶段 D：对象后端、追踪、AF 联动依次解耦

1. 先完成 EC1706 可运行的检测后端，只输出规范化结果，不写 AF ROI。
2. 再加入 target id、遮挡保持、重捕和超时的 tracker。
3. 完成帧率、内存、温度与休眠恢复后，才接入第一代 AF-C ROI。
4. 对象后端故障时必须 fail closed，原厂 AF-S/AF-C 和脸/眼检测仍能独立工作。

## 可行性总表

| 项目 | 直接移植二代二进制 | 在第一代上选择性实现 | 当前状态 |
| --- | --- | --- | --- |
| 更快的 AF-S 扫描分支 | 不需要，也不安全 | 高；已有两个离线/临时候选 | 缺端到端计时 |
| 二代式目标位置优先 AF-S | 不可直接移植 | 中；需重做目标参数数据流并验证第一代 PDAF 预测误差 | 旧离线路由候选已因潜在反方向命令被隔离，未实机验证 |
| 基础 AF-C | 不需要 | 高；原厂路径已一次实机跑通 | 缺系统质量验收 |
| 二代低延迟/融合 AFC | 低 | 中低；需重写控制器并适配第一代输入 | 未实现 |
| 用户框选单目标追踪 | 低 | 中低；旧 ML 资产可能提供起点 | 接口与资源未闭合 |
| Human / Pet / Vehicle 识别追踪 | 已被门禁拒绝 | 低到中；取决于 EC1706 模型与工具链 | 阻断在检测后端 |

## 证据与复现入口

- 第一代 AF-S 调用链、镜头命令与二代位置命令参考：[独立交接说明](../../CodeTests/temporary_af_speed_probe/standalone_handoff/README.md)。
- 第一代 ×3/×3/×2 候选的精确作用范围：[AF 速度流程](../../CodeTests/temporary_af_speed_probe/verified-x3-fast-only/AF_SPEED_FLOW.md)。
- 第一代 Type2→Type1 两指令候选：[PDAF 扫描候选](../../CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md)。
- 第一代原厂绝对位置路径的两/四指令候选：[PDAF AF-S 绝对位置路由候选](../../CodeTests/temporary_af_speed_probe/pdaf-abs-route-candidate/README.md)。
- 第一代原生 AF-C 状态机、GUI 门控与真机运行记录：[AF-C 研究](../../CodeTests/x2d-afc-research/README.md)。
- 对象识别的服务、模型、依赖和 DSP 兼容性门禁：[对象识别移植研究](../../object-recognition/research/X2D2-TO-X2D-PORT.md)。

本轮二代函数调用核对使用与 `offline_elf.py` 相同的 pyelftools/Capstone 只读解析方法，先核对上列 SHA-256，再解析 ELF 符号、PLT 和 AArch64 `bl` 目标。官方固件、提取根目录和专有二进制未收录于仓库；因此本文保存可共享的地址、大小、调用关系和哈希，不声称仅凭仓库即可重新生成全部二代反汇编。

## 限制

- 函数大小、符号数量和配置值只能证明架构差异，不能直接换算毫秒提升。
- `rtp.enable: 0` 与 `finetune.enable: 0` 只约束 X2D II 1.3.16.2 的本次配置，不能外推其他版本。
- 第一代 AF-C 的一次真机成功不等于达到产品级可用；菜单可见、模式可选、状态机运行和持续追焦质量是四个不同验收层级。
- 本轮没有安装、刷写、重启服务、触发对焦或生成可部署 CIM。
- “菜单修改”任务已实机验证的是原厂 `camera-gui` 进程内加载扩展并替换 QML；整文件替换仍为离线原型，不能由此推定 AF 后端可用相同进程入口替换。

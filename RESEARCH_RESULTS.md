# 研究成果总表

2026-10-31 补充：[X2D II 八向摇杆实现](x2d2/joystick-eight-way/README.md)面向1.3.18.1，收录输入状态机、原生evdev/uinput适配、ASan/UBSan离线检查及归一化方向回放。既有45秒实体测试处理276条输入、228次状态变化，用户确认四斜向、长按和松手正常；退出恢复通过。未完成常驻安装、其他界面及长期验收。本次迁入未连接设备，原始日志与部署后端未公开。

更新：2026-10-16。覆盖本项目 X2D 100C 4.2.0 与 X2D II 1.3.16.2 对照研究。补齐 2026-10-07 成果表之后的进展；历史实验保留各自日期与验收范围。

2026-10-14 补充：[FXGab69 黑白帧离线源码](x2d/CodeTests/monochrome-frame-contracts/README.md)收录 PR #9 的处理核心与所有权测试，保留原作者提交归属和来源许可。子集 6 项离线测试全部通过；原完整稿 240 项执行、30 项跳过。实际相机功能未验收。

2026-10-16 归档补充：[425 区域候选源码、快照契约与历史观察](x2d/CodeTests/pdaf-only-shadow/PDAF425.md)，包括 972 × 42 取样格和当前窗口约 90 × 3 的原厂实机观察摘要；[实验记录方法](x2d/CodeTests/pdaf-only-shadow/PDAF425-RECORDING.md)提供不含设备采集步骤的记录模板、脱敏和离线回放。新增候选尚未在相机运行，不能称为 425 点升级或二代完整策略移植。另补[自动亮度及 Windows 历史功能摘要](x2d/research/4.2.0/TOOLKIT-BRIGHTNESS-AND-WINDOWS.md)，完整产品由独立工具包维护。

本次公开的是研究结论、离线源码及处理用户本地记录的脱敏／回放工具。厂商固件、原始设备日志、个人路径、模型明文、密钥未收录。Doom 模块仅保留引擎、界面及离线检查；设备部署后端未收录。文档整理期间未连接相机，表中实机结果来自此前特定设备实验；一次成功不推广为跨版本产品保证。

## 2026-10-14 至 10-16 二代固件研究

| 主题 | 新增结果 | 证据与限制 |
| --- | --- | --- |
| LiDAR 与对焦 | ADS6401 流过滤、深度解码、ToF 结果分档，以及 AF-S / AF-C 的候选评分与接纳路径 | 1.3.16.2 静态 / 离线分析；没有遮挡前后运行轨迹、权重实测或二代设备验收，见 [LiDAR 报告](x2d2/research/1.3.16.2/LIDAR-PIPELINE.md) 和 [AF-S 报告](x2d2/research/1.3.16.2/AFS-WITHOUT-LIDAR.md) |
| 启动资源与变体 | 核对 6 个硬件阶段标识、vendor Logo 位图和 GUI / MCU 资源；未确认特殊版启动选择链 | 只确认原厂资产和静态资源，早期加载器与实机冷启动链未恢复，见 [启动报告](x2d2/research/1.3.16.2/STARTUP-LOGO-VARIANTS.md) |
| 显示与低灰 mura | 后屏 / EVF 的亮度映射、取景 / 回放 RGB LUT、亮度锚点插值；现有 LUT 没有屏幕位置维度 | 可讨论全局低灰色偏的 LUT 标定，不能由现有表直接修复固定位置绿斑；没有个体面板测量或空间补偿接口，见 [显示报告](x2d2/research/1.3.16.2/DISPLAY-MURA.md) |
| IBIS 与地球自转 | Phocus 位置代理、camera-service 经纬度字段、IBIS 坐标补偿消息和虚表调用已核对 | 哈苏官方说明经纬度与罗盘用于地球自转补偿；控制器内部公式、4 小时过期处理和无定位降级尚未恢复，见 [IBIS 报告](x2d2/research/1.3.16.2/IBIS-GPS-EARTH-ROTATION.md) |
| 对焦图标 | 提取二代 GUI 的 AF-S / AF-C 控制界面、实时取景和灰显 SVG / PNG | 原始固件 GUI 未随库提供；资源和预览放在 `x2d2/outputs/focus-icons-20261015/` |

新增工具均为只读离线解析：`x2d2/tools/inspect_lidar.py`、`inspect_afs.py`、`inspect_startup_variants.py`、`inspect_display.py` 与 `inspect_ibis.py`。原厂输入、共享库、内核模块、加密模型、设备日志和本机路径不随仓库分发。

## 2026-10-08 至 10-13 新增成果

| 主题 | 新增结果 | 证据与限制 |
| --- | --- | --- |
| AFT 与眼部 | 可选安装、四宫格模式、保存及按实际模式暂停／恢复眼部 | 独立候选实机和用户反馈通过；整合软件与光学量化分开，见 [对焦更新](x2d/research/4.2.0/AF-EYE-AND-SPEED-UPDATE.md) |
| 三档速度 | 低／中／高原厂选择器，公开工具包 0.4.17 | 本地与部分用户验收；倍率不是整体合焦收益或镜头安全保证 |
| 像素位移 | 电子快门 4／6／16 张实际 RAW 序列，起拍等待、倒计时与音量 | 实拍文件结构及序列验收；十六张元数据异常保留，物理精度和整图质量未量化，见 [采集报告](x2d/research/4.2.0/PIXEL-SHIFT-CAPTURE-RESULTS.md) |
| 电脑合成 | 同组实际四帧 Wine／Metal 生成 408240000 像素 RGB16 DNG；补单张 AHD 基线与原片细节扫描 | 纯重建 163.55→17.37 分钟，记录耗时比约 9.41；可见精细度相当，严格逐像素一致性失败。缓存复用非冷启动基准，不是机内合成或四倍光学细节证明，见 [三方科研报告](x2d/research/4.2.0/JSR-METAL-COMPARISON.md) |
| 合成库公开子集 | 自有四／六帧原尺寸处理、渲染与固定 MIT 内核 | [源码模块](x2d/pixel-shift/README.md)使用合成输入做主机测试；与 JSR 是不同处理器 |
| Startup Studio | 独立 Mac 通用 App、Windows preview.2、首次备份和原厂恢复 | 普通 X2D Mac 流程实测；Windows 和相关机型完整相机验收待测，见 [应用报告](x2d/research/4.2.0/STARTUP-STUDIO-UPDATE.md) |
| 一代模型 | 本轮完整枚举 30 个容器解密及原厂签名验证通过 | 四个 TFLite、七个 JSON 结构核对；明文、密钥与厂商输入不提供，见 [模型报告](x2d/research/4.2.0/MODEL-DECRYPTION-AND-CPU-RESULTS.md) |
| 自有签名／CPU | 独立验签解包后，特定公开测试模型通过原厂 NNF CPU 合成零输入 | 无实时取景、AF、DSP 或原厂服务接入；原厂不信任开发公钥 |
| 二代模型 | 39 个文件，6,084 次候选完整校验无匹配 | 未解密，未取得二代设备或推理结果，见 [二代报告](x2d2/research/1.3.16.2/MODEL-AND-PDAF-STATUS.md) |
| PDAF 425 | 固定容量、采样几何和两代控制策略对照 | [静态报告与工具](x2d/research/4.2.0/PDAF-425-BOUNDARIES.md)，不是 425 有效区域升级 |
| 光谱白平衡 | AS7341 结构、AWB 实际调用与光谱权重链路 | [固定版本静态分析](x2d/research/4.2.0/SPECTRAL-WHITE-BALANCE.md)，单台读数和收益未测 |
| 黑白候选审查 | FXGab69 原候选完成主机检查与 ARM64 构建，复现帧所有权问题 | 作者署名保留，[审查结论](x2d/research/4.2.0/MONOCHROME-CANDIDATE-REVIEW.md)；未修改、合入或实机验证 |
| 兼容与状态 | XCD 45/3.5 模式／状态审查及换图后菜单生命周期冲突 | [镜头审查](x2d/research/4.2.0/LENS-AND-STATUS-COMPATIBILITY.md)，实际用户根因仍待闭合 |
| 电源启动 | 电池重装、肩屏 H 与 USB 恢复的排查链路 | [诊断边界](x2d/research/4.2.0/USB-POWER-STARTUP-DIAGNOSIS.md)；反馈 4.0.0 与分析 4.2.0 分开，无已验证修复 |
| 披露与项目维护 | 厂商回执、公开稳定／私有开发分离及隐私整理 | [流程状态](x2d/research/4.2.0/SECURITY-DISCLOSURE-STATUS.md)，不公开报告细节或认可／奖励承诺 |

本次没有收录其他贡献者的工具包重构与新调试框架。Startup Studio 独立源码按对应版本许可维护；黑白实现归原贡献者。原始照片、设备记录及第三方处理程序不随成果摘要公开。

## 既有研究结果（状态更新至 2026-10-12）

| 主题 | 新增结论 | 验证及限制 |
| --- | --- | --- |
| Doom | 真实引擎、全按快门开火、扬声器音效、左右滑动转向 | 此前第一代 4.2.0 用户确认；公开版离线重验，有声版恢复仍缺读回，不是持久安装包 |
| Shimeji 宠物 | libshijima + 透明覆盖、alpha 点击穿透、直接拖动、退出标记 | 临时实机用户确认；公开版桌面重验，非固件安装包；角色素材单独授权 |
| 整机 UI 响应 | 原厂滑动窗口 57–58 FPS，触摸报告间隔约 6.95 ms；三轮临时对照 | 未确认主观改善；同步拖动候选出现页面错误已撤回，最终恢复原厂 |
| 原厂 AF 参数 | 六个槽位，默认总掩码 0x03；55V／AF-S 读回一致 | 静态＋只读实机，不是额外算法已运行 |
| PDAF 80→100 | 临时提高 2 档峰值分数，约 180 秒恢复 | 实机减少拉风箱但频繁虚焦，已淘汰；80 不是百分比 |
| CDAF 最终确认 | 定位到位、结果和 Success 转换，原精修开关不保证新反差验收 | 判定器离线，未安装 |
| Kalman／TAF | AF KF 入口为空；存在 TAF 距离预测、主体框 Kalman | 无直接开启 AF-S 焦距 Kalman 的证据 |
| VDAF／BDAF | 定位输入消费和镜头命令，默认参数关闭／为零 | 生产端、标定及性能未闭合 |
| 仿真审查 | 复跑七类新增场景，发现目标突变和综合指标退化 | 默认种子模型结果，不是相机成功率 |
| AFT 人脸 | AFT=6，两层门控及原厂连续／TAF 桥接已试运行 | 原厂入口进入，镜头持续追踪未验收 |
| AFT 区域与显示 | 区域发布接入；采样观察 AF 返回框停滞；目标坐标优先主框改善 | RAM 实机反馈；合焦状态未强制、镜头效果待测 |
| 四帧滤波 | 最近四帧代替十帧中心平均的有界候选 | ARM 模拟通过，未安装 |
| Logo | 主屏原图提取、旋转与替换；250×250 彩色短时显示通过 | 恢复清理通过；不是下次开机自动替换，肩屏待解析 |
| 蓝牙 | 原厂自然休眠保持广播，手机触发亮屏 | 一次实机，真正关机蓝牙开机未实现 |
| exMCU | E2 USB boot 路径与 MCU 自身 SPI 恢复核对 | 80 处指令；救援 loader、协议、eMMC 写回缺失 |
| CIM | 八载荷原内容重封与官方逐字节一致 | 原样复现，不是修改包签名成功 |
| 临时更新器 | 量产态跳过公钥索引 0，单改路径不足 | 完整验签、启动与安装未验证 |
| CNN／模型 | 驱动及容器审计；新增独立 NNF CPU 合成输入结果 | 二代 Pet 未通过一代接口；无实时识别、AF/DSP 或可用余量测量 |
| .eng.enc | 一代完整 30 文件解密及签名验证；二代完整 39 文件未解密 | 模型、密钥和完整设备证据未公开；不等同原厂接受自有签名 |
| 像素位移 | 原厂 4／6／16 帧调用链及新增实拍序列 | 完整机内合成、物理位移精度与全流程质量未验收 |
| 25MP 低噪 | 软件缩小路线可研究，未找到目标全幅硬件四合一模式 | 尚无机内安装或质量结果 |
| 录像 | 视频组件存在，D-Bus 开始／停止入口直接报错 | 无可播放机内文件，“完成 95%”没有依据 |

## 分主题报告

- [JSR 蓝鸟腹部与文字的解析力三方对比](x2d/research/4.2.0/JSR-METAL-COMPARISON.md)

- [Doom 实现与证据](x2d/research/4.2.0/DOOM-FEASIBILITY.md)及[源码/复现](x2d/doom/README.md)
- [Shimeji 透明宠物模块](x2d/shimeji-overlay/README.md)
- [整机 UI 响应与三轮试验](x2d/research/4.2.0/UI-RESPONSIVENESS.md)

- [原厂对焦参数、淘汰实验和仿真](x2d/research/4.2.0/AF-NATIVE-PARAMETERS-AND-TRIALS.md)
- [AFT、人脸区域和显示](x2d/research/4.2.0/AFT-FACE-TRACKING-RESULTS.md)
- [无线唤醒及恢复](x2d/research/4.2.0/WIRELESS-AND-RECOVERY-UPDATE.md)
- [固件与模型容器](x2d/research/4.2.0/FIRMWARE-CONTAINERS-UPDATE.md)
- [像素位移、低噪与视频](x2d/research/4.2.0/IMAGING-AND-VIDEO-UPDATE.md)
- [主屏 Logo 定位](x2d/research/4.2.0/STARTUP-LOGO-LOCATION.md)与[替换验收](x2d/research/4.2.0/STARTUP-LOGO-REPLACEMENT.md)

## 既有成果及状态更新

原厂后端连续对焦状态机曾在实机进入连续状态、返回 SuccessCont，松开停止并回 AF-S；菜单 gate 单独开放不足以扩展两项原厂模型。菜单显示不能替代对焦效果验收。

早期 Type2→Type1 扫描候选改变请求速度模型，不等于总合焦时间翻倍；某些速度 RAM 样本已有受限结果，但低照度、近摄、过冲、长期热与功耗缺完整验收。绝对位置路由旧候选可能误用安全界，已隔离禁止上机。

原厂人脸／眼部路径及 ROI 接口与二代 Human／Pet／Vehicle 是不同路线。ROI 接口存在不能当成完整功能移植。

## 相关机型研究摘要

本次用户要求汇总相关机型：907X／CFV II 50C 1.5.2 已完成 CIM／OTA／分区解包、Qt5 QML 解析及 66 项 ARM32 离线核对；找到 AFC 和速度 buff 入口。100C 套件不能直接安装，未实机适配。其原厂输入、机型工具及部署代码不迁入本树，不复用 X2D 地址。

二代仍为 1.3.16.2 离线对照及接口研究，不把一代实验结果写成二代验收。理光及其他品牌研究不在本表范围。

## 复现与证据

运行 `python3 scripts/validate_public_repo.py` 检查公开树，`python3 scripts/reproduce_offline.py` 执行已有离线套件。最新报告中的私有实机实验、厂商输入及仿真运行原始日志并未全部打包，不能仅下载本仓库重建全部结果。详见 [REPRODUCE.md](REPRODUCE.md) 与 [DISCLAIMER.md](DISCLAIMER.md)。

新增 Markdown 默认忽略；仅通过 .gitignore 的逐文件放行和人工审核进入公开树。该规则不删除既有 Git 历史，也不替代内容审核。

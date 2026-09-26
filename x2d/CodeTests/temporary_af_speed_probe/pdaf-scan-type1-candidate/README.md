# X2D 4.2.0 PDAF 方向扫描 Type1 候选

## 目的与边界

本候选只优化第一代 X2D 100C 4.2.0 的 AF-S 相位方向扫描分支：两处原厂拍照路径固定请求 Type2，本候选改为 Type1。两处进入条件、方向计算、命令队列、直接目标位置路径、取消/停止逻辑和内部 recording 的 Type5 均保持不变。

本目录不修改菜单，不移植 AF-C，不接入对象识别，也不包含设备安装器。候选与同级现有 ×3/×3/×2 `lens_ctrl_get_focus_speed` 补丁是两个不同实验，**不得叠加**。

## 流程、瓶颈与指标

固定输入是官方第一代 X2D 4.2.0 `/lib64/libaaa.so`，SHA-256 `feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7`。

AF-S 相位主函数 `_exec_pdaf_afs_process` 的两处方向扫描路径分别在 `0x9065c` 和 `0x90824` 选择拍照 Type2，随后调用 `lens_ctrl_get_focus_speed` 并排队 `lens_cmd_push_focus_scan_cmd`。在已确认的原厂动态分档、`slow_scale=0.5` 模型中，Type2 为 `B/4`，Type1 为 `B/2`；因此本候选的离线可验证指标是：**两条已定位方向扫描分支的请求速度从 0.25B 提升到 0.5B，即 2.0×**。

该指标不是总对焦时间。相位流程中的直接目标位置命令不经过这两处选速，帧率调整、条件相位加速、镜头内部控制、曝光条件和收敛次数仍会影响实际 AF-S 延迟。

## 文件地图

- `build_candidate.py`：核对精确 ELF、函数、上下文和两条指令，生成原始/候选函数及清单。
- `evaluate_benchmark.py`：离线汇总成对实测 CSV，输出中位数、P95、成功率和过冲率。
- `test_candidate.py`：候选字节范围、失败关闭和指标计算的无设备测试。
- `outputs/`：本地生成物；由 `.gitignore` 排除。

## 依赖与离线复现

从本目录运行；依赖沿用 `../standalone_handoff/requirements.txt`。输入须由使用者合法取得并核对，仓库不附带原厂 ELF。

```sh
python3 -m pip install -r ../standalone_handoff/requirements.txt
python3 -B -m unittest test_candidate.py
python3 -B build_candidate.py /path/to/x2d-4.2.0-system-root/lib64/libaaa.so
```

生成器要求 `_exec_pdaf_afs_process` 原函数 SHA-256 为 `042cc441a57fa5004b53f1f69a260799b4bb53768b311cf7d357d382ccce096d`，候选函数 SHA-256 为 `824a398ddac6ad99be93240422b356cadad2ff036fee26bb867dad37cb0d701a`。1872 字节函数中只允许两条指令改变，实际只改变两个字节；任何版本、上下文或最终哈希不匹配都会拒绝输出。

## 实机基准口径

若后续获得明确的实机实验授权，应先保持机位、目标、照度、光圈、镜头版本、起始距离与电量一致，按 `stock` / `candidate` 交替顺序分别采集近到远、远到近至少 20 组成对样本。CSV 表头必须为：

```text
variant,direction,trial,duration_ms,success,overshoot
```

然后离线运行：

```sh
python3 -B evaluate_benchmark.py timings.csv --output outputs/benchmark-result.json
```

建议验收门槛为：中位合焦时间至少改善 10%，P95 不变差，成功率下降不超过 1 个百分点，过冲率不增加。脚本会计算这些门槛，但它不是机械或热安全认证。

## 验证结果、状态与限制

当前状态为**离线候选，未实机安装**。使用哈希匹配的原厂 ELF 已验证：函数 1872 字节；两处 `mov w9,#2` 均变为 `mov w9,#1`；配对的 `mov w8,#5` 与 `csel` 上下文不变；仅 2 条指令、2 个字节变化；候选哈希匹配。

尚未验证镜头实际速度、端到端合焦时间、低照度、近摄、取消、过冲、温升或功耗。由于直接目标位置路径未改，不能预先承诺 AF-S 总耗时提升 2 倍。目录内没有设备写入、启动项或持久化副作用；生成物只写入指定本地输出目录。

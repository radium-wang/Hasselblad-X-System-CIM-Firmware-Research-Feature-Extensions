# X2D 4.2.0 PDAF AF-S 绝对位置路由：已隔离的离线候选

**状态：因方向错误已隔离，禁止上机写入。** 后续静态数据流审计发现，本候选把原厂扫描分支跳到 `_push_filtered_abs_cmd` 时，传入的不是 PDAF 预测峰值或日志中的 `target_pos`，而是当前镜头位置左右安全界中更近的一端。原厂扫描门槛 `0x92ba8` 返回 1 的条件恰是“当前位置位于峰值与所选安全界之间”，所以该安全界在当前镜头位置相对峰值的**另一侧**。在已采集的原厂会话中，`cur_pos=174, peak=125, left=8, right=242`，所选边界为 242；若过滤器决定更新命令，镜头可能先从 174 朝 242 移动，方向与预测峰值 125 相反。过滤器也可能保留旧目标，因此这不是已观测的异常运动，而是足以阻止试装的静态错误。默认构建已改为拒绝输出，只有显式 `--allow-unsafe-offline-audit` 才能生成带 `NOT_FOR_DEVICE` 名称的离线审计字节。

## 要验证的假说

X2D II 1.3.16.2 的 `_exec_pdaf_afs_process` 在已核对的主函数中不直接调用方向扫描和扫描选速，却使用 PDAF 对齐位置与绝对位置命令。第一代 X2D 4.2.0 本来就有 `_push_filtered_abs_cmd`，因此最初假设可以只改变路由来试验“目标位置优先”。**上述数据流审计已否定“本候选会发送 PDAF 目标位置”这一前提。** 本文件保留候选及其字节级审计，供解释失败原因；它不是可测试的提速实现。

这只是离线静态候选。没有相机测试证明它更快、更准或安全；方向扫描可能承担峰值确认和防过冲作用。官方比较还受 PDAF 区域数量、ToF 测距、镜头型号/固件等影响，这个候选不复制这些条件。

2026-09-25 的[实机记录](DEVICE-RESULT-2026-09-25.md)已确认机型、固件、原厂库及进程内函数哈希；不写 AF 代码的暂停/恢复演练通过。55V 镜头原厂 AF-S 两次成功样本的服务状态机耗时分别为 388 ms、211 ms。候选仍未加载或写入，尚无候选侧 AF-S A/B 数据。

## 改动范围

输入锁定官方 X2D 100C 4.2.0 `libaaa.so` SHA-256 `feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7`，以及 `_exec_pdaf_afs_process` 1872 字节 SHA-256 `042cc441a57fa5004b53f1f69a260799b4bb53768b311cf7d357d382ccce096d`。任何不匹配均拒绝生成。

默认 `first` 变体仅改 `0x9065c`/`0x90660` 两条指令：`is_stand_recording_af_mode()==0` 时从第一条 in-range 扫描分支跳到原厂 `0x906ec`，调用原厂 `_push_filtered_abs_cmd`；非零时仍以 Type5 进入原厂方向扫描。`both` 变体还改 `0x90824`/`0x90828`，同理跳到原厂 `0x906d0`。第一条路径在 `0x903c8–0x903d0` 选择并保存最近的安全界到 `[sp+0x80]`，`0x906ec` 把它装入 `w2`，`0x906f4` 把当前位置装入 `w3`，`0x906fc` 调用过滤函数。它保留了第一代 PDAF 结果指针和原厂镜头命令链，但**没有**把预测峰值作为该次绝对位置命令的目标参数。过滤函数 `0x92ae0` 可能沿用旧缓存目标，也可能把 `w2` 写入缓存并发送；不能把这层过滤当成方向安全证明。

这里特别保证条件跳转发生在写入 `w21` 之前：`x21` 在绝对位置路径仍是 PDAF 结果指针。如果先写 `w21` 再跳转，就会破坏指针，不能作为候选。生成器对精确源哈希、指令、跳转目标及这段标志位/指针上下文做校验。

| 变体 | 改动指令 | 候选函数 SHA-256 | 用途 |
| --- | ---: | --- | --- |
| `first`（默认） | 2 | `1aa5c6ebd146615ffbceab167419cdd8009817dfa1d302df6fc00a3ff461b809` | 最小单分支假说 |
| `both` | 4 | `3158a757d998a4e86cd0cd6896fc35c62ed5cef528944029c5645ddccb24d933` | 后续双分支对照 |

## 离线复现

依赖见相邻 `../standalone_handoff/requirements.txt`。本目录不含原厂库。给定合法取得的原厂提取物后：

```sh
python3 -m pip install -r ../standalone_handoff/requirements.txt
X2D_LIBAAA_420=/path/to/x2d-4.2.0/lib64/libaaa.so python3 -B -m unittest test_candidate.py
X2D_LIBAAA_420=/path/to/x2d-4.2.0/lib64/libaaa.so X2D_SYSTEM_ROOT_420=/path/to/x2d-4.2.0 python3 -B -m unittest test_candidate.py
python3 -B audit_target_flow.py /path/to/x2d-4.2.0/lib64/libaaa.so
python3 -B build_candidate.py /path/to/x2d-4.2.0/lib64/libaaa.so --allow-unsafe-offline-audit --output /tmp/x2d-afs-first-candidate
python3 -B build_candidate.py /path/to/x2d-4.2.0/lib64/libaaa.so --variant both --allow-unsafe-offline-audit --output /tmp/x2d-afs-both-candidate
python3 -B build_candidate.py /path/to/x2d-4.2.0/lib64/libaaa.so --emit-full-library --allow-unsafe-offline-audit --output /tmp/x2d-afs-elf-audit
python3 -B verify_loader_boundary.py /path/to/x2d-4.2.0
```

默认不生成任何候选。显式允许**离线风险审计**后，输出原始函数块、带 `NOT_FOR_DEVICE` 名称的候选函数块和审计清单；再加 `--emit-full-library` 才会额外生成完整的 `libaaa.AF_ROUTE_NOT_FOR_DEVICE.so`。原库尺寸不变，仅选中指令的文件字节变化，结果再次解析为 AArch64 ELF；单分支映像 SHA-256 为 `7448becb9b9a1facaea7c69efba066840f4e6001c0a8783529984c298eb3b7ce`。原 ELF BuildID 不随此实验更新，不能用它识别候选。此映像只供离线重现危险数据流，**禁止加载或安装**；目录内没有安装器、设备传输或持久化启动配置。输出目录需为空。它不得与同级 Type2→Type1、×3/×3/×2 扫描提速候选叠加。

`audit_target_flow.py` 只读取精确哈希的原厂 ELF、校验关键指令并输出 JSON，不接设备也不生成补丁。它将当前镜头位置映射到栈偏移 `0x70`、预测峰值映射到 `0x68`、计算目标映射到 `0x6c`、最近安全界映射到 `0x80`；旧候选的两条绝对位置入口却都从 `0x80` 取目标参数。该映射是重新设计的起点，**不是**说把一条 `ldr` 改为 `0x6c` 就安全：仍需验证计算目标的来源、限位、置信度、旧命令缓存与原厂扫描回退。

## 下一道门槛

**当前这份候选的下一步不是实机加载，而是重新设计。** 新路由须证明发送的目标与 PDAF 预测峰值、镜头限位及运动方向一致，并用离线数据流测试覆盖左右两向、安全界选择、旧命令缓存和过滤器全部分支。之后才可重新讨论同机身/镜头/固件的原厂基线、失焦与过冲风险、加载点和回滚。现有暂停/恢复演练不解除本候选的方向风险；AF-C/对象识别也未因此移植。

2026-09-25 的无写入第三次原厂 AF-S 轨迹显示：一轮成功对焦约 205 ms，首帧 `target_pos=90`、合焦前 `cur_pos=117`，同一会话的目标估计还短暂跳至 247；扫描准备日志出现，但没有证据证明候选所改的**具体**分支在这轮被执行。用户本轮选择不做 RAM 写入，候选继续保持离线状态并因后续数据流审计隔离。

离线反汇编还表明 `0x90640` 调用的 `0x92ba8` 只有在当前镜头位置处于预测峰值与选中安全界之间时返回 1；返回 0 的原厂路径本来就会转到过滤绝对位置命令。默认候选仅改变返回 1 且为拍照模式时的方向扫描路径，并非首帧无条件直达。第三次日志的首次位置/峰值/安全界 `204/52/169` 不满足这一条件，后一帧 `174/125/242` 满足；日志本身不能证明后一帧进入候选所改的具体基本块。

此前“菜单修改”任务中成功的运行记录是原厂 GUI 进程内的 `LD_PRELOAD`/QML 内容替换；整份 `camera-gui` 可执行文件替换仍停留在离线原型。这能证明 GUI 层的某种替换入口，但不是 AF 后端已经能热替换。

本版固件的静态 ELF 加载链是 `camera-service → libdcam_frwk.so → libduml_hal_cam.so → librcam.so → libaaa.so`；`pdaf_lib_run` 在 `0x921b4` 经 `libaaa.so` 的 PLT `0x2f250` 调用导出的 `_exec_pdaf_afs_process`，其 `.rela.plt` 项指向 GOT `0x1de390`。该函数为 `STB_GLOBAL`、`STV_DEFAULT`，且库未设置 `DT_SYMBOLIC`/`DF_SYMBOLIC`。这些条件由 `verify_loader_boundary.py` 独立检查。它们提示预加载符号拦截**可能**有独立于 GUI 缓存替换的入口，但还需验证实际动态链接顺序、调用 ABI、服务启动环境、SELinux 和故障回退；当前生成器没有实现拦截器或对原函数内存打补丁，更未在设备上验证此路径。

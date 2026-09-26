> 迁移的历史研究记录：原文描述的是当时的实验，不代表本次重新验证。外部依赖及本轮验证范围见仓库根目录 MIGRATION_DEPENDENCIES.md。

# X2D 对焦研究：无需原仓库的独立交接资料

本资料面向没有原研究仓库的接手者。下面给出公开输入、精确哈希、分析入口、已完成补丁和未完成内容；附件代码只在电脑上处理文件、模拟指令，**不访问 USB、不下发相机命令**。

单文件版的附录包含全部配套源代码，可复制到同名文件后使用；ZIP 版已拆好文件。原厂固件体积较大，不包含在资料包中，需要从下列公开来源取得。Python 依赖、编译器也需要自行安装。

## 一、对象、目标和可信状态

对象：第一代 Hasselblad X2D 100C，官方 4.2.0，XCD 55V。

已有实验是机身运行内存中的拍照 Type0 ×3、Type1 ×3、Type2 ×2，保留原厂帧率调整并加数值限幅。曾完成实机写入和完整函数回读匹配，但没有测得实际下发最大速度，不能宣称马达速度或总合焦时间按倍率改变。

用户后来报告重启相机。此前临时补丁不能视为仍生效；最近 USB 查询未找到控制接口，未核验本次启动。接手者应重新核对自身设备，不能继承旧运行地址或日志状态。

新目标：相位算法保留焦点和离焦估计，由机身根据距离选择 Type0／1／2，向镜头发送方向与速度，研究替代直接目标位置移动。**新方案没有完成，也没有可直接安装的方向控制补丁。**

## 二、从零取得可分析输入

### 1. 官方机身固件

[X2D 100C 官方 4.2.0 CIM](https://cdn.hasselblad.com/firmware/X2D-100C-Firmware/4.2.0/X2D_100C_v4_2_0.cim)

- 文件名：`X2D_100C_v4_2_0.cim`
- 大小：`175245312` 字节。
- SHA-256：`5ae67d16a24b00f9300e3e9c1323e7d149248ad36975e12c4fa8da633b438e03`

### 2. CIM 离线解包

公开参考：[hasselblad-cim-firmware-extractor](https://github.com/YuHaoyua/hasselblad-cim-firmware-extractor)。本研究原先参考的固定修订为 `768664267cb44621c3c12595ee9cc538020b1b94`，其脚本地址为：

<https://raw.githubusercontent.com/YuHaoyua/hasselblad-cim-firmware-extractor/768664267cb44621c3c12595ee9cc538020b1b94/hasselblad_extract.py>

这是外部工具，不随包分发。其公开用法是安装 `pycryptodome` 后，在电脑上运行：

```text
python hasselblad_extract.py X2D_100C_v4_2_0.cim
```

解包结果中的 `ota.zip` 是本资料下一步输入，预期大小 `173183251`，SHA-256：
`03c7e1e508bf17246e0be3e0b39d821683845561571dea57c09fcf0a3c9d736b`。

这里仅解包，不执行原厂升级脚本，不向相机传 CIM。公开解包器的校验不能代替上述固定 SHA-256。

### 3. 提取两份对焦库

推荐独立 Python 环境。解压资料包后进入该目录：

```text
python -m pip install -r requirements.txt
python -B extract_ota.py /path/to/ota.zip --out input
```

脚本验证 OTA 哈希，在内存里重建原厂 system 文件系统，只提取两个 ELF 到新目录；不会挂载文件系统或执行固件。需要有足够内存处理数百 MB 镜像，建议预留约 2 GB 空闲内存。输出已存在时拒绝覆盖。

| 文件 | 预期 SHA-256 |
|---|---|
| `input/libaaa.so` | `feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7` |
| `input/librcam.so` | `72ebc8deebce4a29047c475e77ab4edbf2860abb1f572fea45260fe17ad0bda5` |

已有同哈希 ELF 时可跳过 CIM／OTA 提取。任何不同版本都不能直接套用下面地址和补丁。

### 4. 查看真实函数

```text
python -B offline_elf.py input/libaaa.so --symbol lens_ctrl_get_focus_speed
python -B offline_elf.py input/libaaa.so --symbol _exec_pdaf_afs_process
python -B offline_elf.py input/libaaa.so --symbol is_cur_pos_between_start_and_peak
python -B offline_elf.py input/libaaa.so --symbol get_speed_type_from_peak_distance
python -B offline_elf.py input/librcam.so --kind librcam.so --symbol _DjiLensDrv_HBMOUNT_aaa_focus_abs_move_motor
python -B offline_elf.py input/librcam.so --kind librcam.so --symbol _DjiLensDrv_HBMOUNT_aaa_focus_scan_move_motor
```

分析器解析 AArch64 ELF、`.gnu_debugdata` 符号、动态符号及 PLT 调用目标。也可将同一 ELF 导入 Ghidra／IDA 对照。本文地址是 ELF 虚拟地址，不是文件偏移或本次开机的进程绝对地址。

## 三、现有速度补丁到底改了什么

函数 `lens_ctrl_get_focus_speed`：`0xac380..0xac7ac`，1068 字节。

六类是速度请求类型，不是六个独立状态机，也不是必须按顺序执行。

| 类型 | 用途分类 | 原厂动态相对速度* | 既有候选 |
|---|---|---|---|
| Type0 | 拍照快档 | B | ×3 |
| Type1 | 拍照慢档 | B/2 | ×3 |
| Type2 | 拍照更慢档 | B/4 | ×2 |
| Type3／4／5 | 内部 recording 三档 | 对应 B、B/2、B/4 | 不改 |

*限动态计算成功且慢速系数为 0.5，未计帧率和条件加速；B 是当轮计算值。内部 recording 分类不证明相机开放录像。

改动在**动态计算成功后的分档结果**上，随后仍走原厂帧率调整，不是把镜头回传最大速度简单乘三。失败回退值不乘倍率。模式2、拍照三档最终输出额外限制到 `0..21844`，回退值也限幅。

原实验安装前曾检查三处原厂条件相位加速不超过 `1.5`，所核对的后续整数链因此不超过 `32766`。这里是数值边界，不是镜头机械极限，也不能代替另一台设备的现场参数检查。

代码位置：`0xac6c4` 的 4 字节分支，以及 `0xac724` 起 84 字节；使用了原厂动态成功路径的详细日志空间。候选汇编见 `fastscan.S`；精确原始／候选字节见 `candidate.json`。

- 原函数 SHA-256：`c8b5407c615b60c05078bc7ba9ada8cf53c905bac17faa59561f948feac0d430`
- 候选完整函数 SHA-256：`4eb555dc16ad54bdcfecd244b63bfea7ee691ce67b8274a1244644392ba15e13`

## 四、独立复现已有倍率补丁的离线结果

资料包含汇编和完整指令模拟程序。编译器选择支持 AArch64 的 Clang 或 Zig，例如在资料目录执行其中一条：

```text
clang --target=aarch64-linux-gnu -c fastscan.S -o fastscan.o
```

或使用原实验同系列工具 Zig 0.13.0：

```text
zig cc -g0 -target aarch64-linux-gnu -c fastscan.S -o fastscan.o
```

然后：

```text
python -B verify_candidate.py input/libaaa.so
```

该程序用 Unicorn 执行原厂／候选 AArch64 函数，对照倍率模型，覆盖 1402 组输入；外部 getter 被模拟。输出写在该脚本目录，包括 `offline-results.json`、`candidate.json` 和从合法输入生成的函数二进制。

该测试证明的是覆盖条件内的函数计算和恢复字节一致，不测试相位闭环、马达运动、USB、安装事务或镜头机械极限。任何新方向控制候选都需要独立测试，不能沿用这 1402 组 PASS 当作已经覆盖。

## 五、直接目标位置与方向扫描的真实链路

相位 AF-S 主函数 `_exec_pdaf_afs_process` 位于 `0x90128`，长度 1872 字节。

```text
相位结果、当前位置和参考区间
  ├─满足某些原厂条件→方向 + Type2速度→扫描命令
  └─其他结果／条件→目标位置或过滤后的目标位置→位置命令
                         ↓
                 后续帧测量、控制和收尾
```

### 方向分支

- `0x90638..0x906a4`：区间判断成立后计算扫描速度；不成立转位置控制。
- `0x906bc..0x906e0`：区间和额外状态判断，满足条件转第二处扫描分支。
- `0x9080c..0x90868`：第二处方向扫描。
- `0x9065c`、`0x90824`：拍照选 Type2，内部 recording 分类选 Type5。
- 相位方向转换成 `0x7fff`／`0x8000`，速度经 `lens_ctrl_get_focus_speed` 计算，然后交给 `lens_cmd_push_focus_scan_cmd`。

### 位置分支

- `0x905d8`：`lens_cmd_push_focus_abs_cmd`。
- `0x906e0`、`0x906fc`：`_push_filtered_abs_cmd`，过滤后排队位置命令。
- `is_cur_pos_between_start_and_peak`：`0x92ba8`，392 字节，严格比较当前位置与相应参考位置／峰值区间。强制返回真不是保持原算法行为。

### 实际下发

位置：`lens_cmd_push_focus_abs_cmd` → `lens_ctrl_set_focus_abs_param` → `af_wrap_lens_abs_move_motor` → 镜头驱动。

`librcam` 中 `_DjiLensDrv_HBMOUNT_aaa_focus_abs_move_motor` 在 `0xd4cf8`，普通路径发送 CD focus 子类型6与 16 位目标位置，没有独立速度字段。额外 settings 参数在该路径未作为速度使用。

扫描：`lens_cmd_push_focus_scan_cmd` → `lens_ctrl_set_focus_scan_param` → `af_wrap_lens_scan_move_motor` → `_DjiLensDrv_HBMOUNT_aaa_focus_scan_move_motor`（`0xd4e38`）。它根据方向产生带符号速度，发送子类型5；**不包含目标停止位置**。

方向与速度命令不等于加速度控制，不能把原位置值直接放进方向字段，更不能把目标位置乘倍率称为提速。

## 六、新方向控制方案的修改位置与研究步骤

修改候选层应位于**相位计算结果到机身镜头命令队列之间**。最底层统一替换位置命令会同时影响其他用途，不能作为当前最小方案。

### 小范围候选：保留位置控制，仅改变相位扫描的选速

保留两处扫描分支的全部原厂进入条件，将固定 Type2 改成依据已核对距离类别选择 Type0／1／2。位置分支不动。这能研究相位方向扫描的三档速度，但**不满足全程取消位置命令的目标**。

距离映射参考：`get_speed_type_from_peak_distance`（`0x36048`）将类别1／2映射为拍照 Type1／2，默认 Type0；它不是“任意位置差转类别”的函数。`cdaf_get_scan_speed_type`（`0x574e0`）还有清晰度、当前档位、帧计数等条件，接口未核对前不能直接借用。

### 完整候选：机身接管方向／速度闭环

机身仍需保留内部目标与当前误差，控制的不只是方向，还包括：

1. 相位结果枚举、置信度和方向正负的含义。
2. 位置单位、距离分类阈值、快慢档切换和滞回。
3. 接近目标时减速、越过目标后的处理和合焦收敛。
4. 相位失效、无新帧、取消、松开快门、行程边界时的停止。
5. 命令队列替换和积压，防止继续执行旧方向。
6. 原厂帧率、条件加速和新倍率是否重复叠加。

停止入口已知：`lens_cmd_push_focus_stop_cmd`（`0xad850`）、`lens_ctrl_stop_focus_motor`（`0xa8d70`）、`af_wrap_lens_stop_focus_motor`（`0xb0460`）。当前相位主函数没有直接调用这些入口；不能因此断言原厂不会停止，也不能直接声称新方案停止链已完整。

可交付的新成果应是明确的控制流、改动范围、原厂／候选对照、取消与边界用例、独立撤回方案。当前不存在已经验证的完整方向控制补丁字节。

## 七、镜头和二代比较的独立线索

[55V 官方参考固件 v1.9.11](https://cdn.hasselblad.com/firmware/XCD_Lenses_Firmware_-_XCD_2_5/55V/1.9.11/XCD55V_v1_9_11.cim)

CIM SHA-256：`c66151aaaaa729e76766e9c280f7b84a8d48080eebac53331ff1695f8cf06e2b`。

共享代码 HEX 的 SHA-256：`d1e71cf4ab3fc051a4b9ae5331ba3efe1cd6d4b7fecc8ad09a2595854ae76ce4`；HEX 解码后 SHA-256：`ea5fbae70c5c07a3efdc7127b4d858e0b1f57262dfb134b0f92694c1ca602aaf`。这是另一种处理器固件，不能用本包 AArch64 ELF 分析器直接读取。

参考链：子类型6处理 `0x2144c` → 回调 `0x1a0cc` → `0x19cd4` → 正常分支 `0x19b84` → `0x10e5c` 选速 → `0x10c98` 条件限速／运动参数 → `0x13438` 驱动分派。镜头内有显式速度、预设速度和距离选速／插值，后续还有加减速。另有状态分支未完全追完，当前实机镜头版本也未证实相同。

二代参考为 **X2D II 100C 1.3.16.2**，仅供另行取得同版本官方固件后比对，不是完成一代研究的前置依赖。

- 二代 `libaaa.so` SHA-256：`7d6164eccc734de7087bb778ee72f17a0b3ccf6c0d1f20092c7ebe74a86574ba`
- 二代 `librcam.so` SHA-256：`3dd5b37b3db18b3e6b54271e1501b4dd337e101c06cdd386a896b1547b662f66`
- 二代位置发送入口 `0x73938` → `0x6b570` → `0x6b6d0`，改用 12 字节 X2Lens 消息，已查路径仍未见显式速度字段。
- 二代 `lens_ctrl_set_focus_abs_param`（`0x20e470`）有 fine-tune 条件转扫描线索。

一代旧协议子类型6和二代内部枚举2不能按数字直接比较。二代总体对焦快，不足以证明下发速度更大；还需比较目标更新、等待、微调和镜头新协议含义。

## 八、相机端接入和临时修改：必须另外具备的条件

本包完整支持离线复现，**不是独立 USB 安装器**。仅有这些文件、插上相机，并不能自动取得进程内存读写通道；普通文件传输也不等于可执行命令。原实验使用过维护 USB 通道，但该通道的实现不在本包，不能假定对方已经具备。

相机端实验需要在对方合法获授权、已经核对过副作用的维护通道上另行实现以下事务；不能用猜地址或未核验的凭据补齐：

1. 读取型号、版本、当前镜头、目标服务进程和启动身份。
2. 根据本次映射和 ELF 的 PT_LOAD 计算运行地址；此 ELF 的首段虚拟地址为 `0x1000`，不是直接把映射起点当加载偏移。
3. 回读完整目标函数并比对原厂哈希；不同版本、未知字节、旧进程身份直接停止写入。
4. 保存本次原始字节和身份；建立中断／失败恢复过程，并核对代码缓存同步、线程当前位置及调用返回路径。
5. 临时写入后恢复服务运行，回读完整函数，检查没有线程被追踪或暂停。
6. 用户手动对焦，分别确认移动、合焦、取消和停止；故障时用本次匹配材料撤回。

上一版实际工具曾暂停服务后检查线程 PC 再写入，不是“不暂停热写”。新多入口控制补丁需要重新审核这种方式；原实验成功不能代替代码缓存或并发执行方面的完整论证。

如果后续仍经过原厂条件加速，`21844` 上限成立还依赖现场验证额外加速不超过 `1.5`。无法验证时，不能把本包离线参数当成当前设备事实。

全线程 `strace` 先前导致取景卡住、不能对焦，移除后恢复；这条测速方法已停用。不能为了测速度再次照搬。

修改范围应限定机身服务 RAM。拔 USB 不撤回；相关服务重启或完整关机重开使该类 RAM 补丁失效。它不证明错误补丁无风险，也不意味着适合在换镜头后继续使用。不得复用另一台相机或上一轮启动的地址。

最终报告应分开说明：静态推断、离线模拟、实机写入回读、用户观察与实测数据。特别是“函数哈希一致”不等于“方向闭环成功”，更不等于“物理速度提升三倍”。


## 九、本独立包的复现检查

此次重新运行了本包自己的脚本：OTA 提取成功且两份 ELF 哈希匹配；符号及反汇编查看成功；重新汇编后 1402 组原厂／候选指令对照全部通过，219 组输出改变，模拟恢复字节一致。测试使用 Python 3.11、Zig 0.13.0，依赖版本已固定在 requirements.txt。

测试输入是本机已有的、哈希匹配的原厂 OTA，没有在此次重新下载和运行公开 CIM 解包器，也没有在全新系统上重新安装依赖。外部下载与安装仍是接手者的准备步骤。

包内没有原厂整包、照片、设备身份、密钥材料、USB 传输实现或自动相机安装器。固件内容由接手者从官方来源取得。单文件附录与 ZIP 中源码一致；这份资料不需要访问原研究仓库。

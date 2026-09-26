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


# 附录：完整配套文件

下面每节代码保存为标题中的文件名，所有文件位于同一目录即可。

## requirements.txt

```text
pyelftools==0.32
capstone==5.0.6
unicorn==2.1.4
brotli==1.2.0
dissect.extfs==3.14
```

## offline_elf.py

```python
"""Standalone, read-only ELF inspection. No device access or repository imports."""
import argparse
import hashlib
import io
import lzma
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile

HASHES = {
    'libaaa.so': 'feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7',
    'librcam.so': '72ebc8deebce4a29047c475e77ab4edbf2860abb1f572fea45260fe17ad0bda5',
}

class Binary:
    def __init__(self, path, expected):
        self.data = Path(path).read_bytes()
        if hashlib.sha256(self.data).hexdigest() != expected:
            raise ValueError('Firmware hash mismatch')
        self.elf = ELFFile(io.BytesIO(self.data))
        if self.elf['e_machine'] != 'EM_AARCH64':
            raise ValueError('Expected AArch64')
        debugelf = self.elf
        if not debugelf.get_section_by_name('.symtab'):
            debug = self.elf.get_section_by_name('.gnu_debugdata')
            if debug:
                debugelf = ELFFile(io.BytesIO(lzma.decompress(debug.data())))
        sym = debugelf.get_section_by_name('.symtab')
        self.symbols = list(sym.iter_symbols()) if sym else []
        dyn = self.elf.get_section_by_name('.dynsym')
        if dyn:
            self.symbols.extend(dyn.iter_symbols())
        self.names = {s['st_value']: s.name for s in self.symbols if s['st_value']}
        rel = self.elf.get_section_by_name('.rela.plt')
        plt = self.elf.get_section_by_name('.plt')
        if rel and plt:
            dyn = self.elf.get_section(rel['sh_link'])
            for i, r in enumerate(rel.iter_relocations()):
                self.names[plt['sh_addr'] + 32 + i * 16] = dyn.get_symbol(r['r_info_sym']).name + '@plt'
        self.cs = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
        self.cs.detail = True

    def read(self, address, size):
        for seg in self.elf.iter_segments():
            if seg['p_type'] != 'PT_LOAD':
                continue
            start = seg['p_vaddr']
            if start <= address and address + size <= start + seg['p_filesz']:
                offset = seg['p_offset'] + address - start
                return self.data[offset:offset + size]
        raise ValueError('Requested range is not fully file-backed')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('elf')
    p.add_argument('--kind', choices=HASHES, default='libaaa.so')
    p.add_argument('--symbol', default='_exec_pdaf_afs_process')
    args = p.parse_args()
    b = Binary(args.elf, HASHES[args.kind])
    matches = {(s['st_value'], s['st_size']) for s in b.symbols if s.name == args.symbol and s['st_value'] and s['st_size']}
    if len(matches) != 1:
        raise ValueError('Expected exactly one defined function with size')
    start, size = matches.pop()
    print(f'{args.symbol} ELF VA={start:#x}, bytes={size}')
    for ins in b.cs.disasm(b.read(start, size), start):
        name = ''
        if ins.mnemonic in ('bl', 'b') and ins.op_str.startswith('#'):
            name = b.names.get(ins.operands[0].imm, '')
        print(f'{ins.address:08x}: {ins.mnemonic:8} {ins.op_str:36} {name}')

if __name__ == '__main__':
    main()
```

## extract_ota.py

```python
"""Extract two fixed analysis ELFs from official 4.2.0 ota.zip, never run firmware."""
import argparse
import hashlib
import io
import zipfile
from pathlib import Path
import brotli
from dissect.extfs import ExtFS
from offline_elf import HASHES

OTA_SHA = '03c7e1e508bf17246e0be3e0b39d821683845561571dea57c09fcf0a3c9d736b'

def ranges(text):
    nums = list(map(int, text.split(',')))
    if not nums or nums[0] != len(nums) - 1 or nums[0] % 2:
        raise ValueError('Invalid range list')
    result = list(zip(nums[1::2], nums[2::2]))
    if any(not 0 <= a < b <= 131072 for a, b in result):
        raise ValueError('Range outside fixed firmware bounds')
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('ota')
    p.add_argument('--out', default='input')
    args = p.parse_args()
    raw = Path(args.ota).read_bytes()
    if hashlib.sha256(raw).hexdigest() != OTA_SHA:
        raise ValueError('Expected official X2D 4.2.0 ota.zip')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        lines = z.read('system.transfer.list').decode('ascii').splitlines()
        if lines[0] != '4' or lines[2:4] != ['0', '0']:
            raise ValueError('Unsupported transfer format')
        commands = [line.split() for line in lines[4:] if line.strip()]
        if any(len(c) != 2 or c[0] not in ('new', 'zero', 'erase') for c in commands):
            raise ValueError('Unsupported transfer operation')
        commands = [(op, ranges(rs)) for op, rs in commands]
        payload = brotli.decompress(z.read('system.new.dat.br'))
    expected = sum((b-a)*4096 for op, rs in commands if op == 'new' for a, b in rs)
    if expected != len(payload):
        raise ValueError('Payload size mismatch')
    size = max(b for _, rs in commands for _, b in rs) * 4096
    image = io.BytesIO(bytes(size))
    pos = 0
    for op, rs in commands:
        for a, b in rs:
            length = (b-a)*4096
            image.seek(a*4096)
            if op == 'new':
                image.write(payload[pos:pos+length]); pos += length
            else:
                image.write(bytes(length))
    image.seek(0)
    fs = ExtFS(image)
    entries = {}
    for name, expected_hash in HASHES.items():
        data = fs.get('/lib64/' + name).open().read()
        if hashlib.sha256(data).hexdigest() != expected_hash:
            raise ValueError('Extracted ELF hash mismatch: ' + name)
        entries[name] = data
    out = Path(args.out)
    if any((out / name).exists() for name in entries):
        raise FileExistsError('Output exists; choose a fresh output directory')
    out.mkdir(parents=True, exist_ok=True)
    for name, data in entries.items():
        (out / name).write_bytes(data)
        print(name, len(data), HASHES[name])

if __name__ == '__main__':
    main()
```

## fastscan.S

```asm
// First-generation X2D official 4.2.0 libaaa.so ONLY.
// Keep original divisor selection; scale only successful dynamic results.
.text

.Ldispatch:
.org 0xdc
b .Lbounded
.org 0x13c
// Bypass only the successful-calculation verbose diagnostic block.
and w8,w21,#0xffff
cmp w8,#2
b.hi .Ldispatch+0xc4
fmov s0,#3.0
fmov s1,#2.0
fcsel s0,s1,s0,eq
fmul s10,s10,s0
b .Ldispatch+0xc4
.Lbounded:
fcvtzs w8,s0
and w9,w21,#0xffff
cmp w9,#2
b.hi .Ldispatch+0xe0
ldr w9,[x24,#4]
cmp w9,#2
b.ne .Ldispatch+0xe0
cmp w8,#0
csel w8,wzr,w8,lt
mov w9,#21844
cmp w8,w9
csel w8,w9,w8,hi
b .Ldispatch+0xe0
```

## verify_candidate.py

```python
"""Execute original and candidate AArch64 functions offline; never accesses USB."""
import hashlib
import io
import json
import random
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
from offline_elf import Binary

def system_elf(unused_path, expected):
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python verify_candidate.py path/to/libaaa.so')
    return Binary(sys.argv[1], expected)

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm64_const import *

SHA = 'feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7'
ENTRY, END = 0xac380, 0xac7ac
PARAM, LENS, TLS, OUT, STACK, HALT = (0x2000000,0x2001000,0x2002000,0x2003000,0x2100000,0x2004000)

def pack(fmt, value): return struct.pack('<'+fmt, value)
def fbits(v): return struct.unpack('<I',pack('f',v))[0]
def fvalue(v): return struct.unpack('<f',pack('I',v & 0xffffffff))[0]

class Runner:
    def __init__(self, binary, ranges=(), oracle=False):
        self.u=Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.u.mem_map(0x1000,0xb00000)
        for seg in binary.elf.iter_segments():
            if seg['p_type']=='PT_LOAD': self.u.mem_write(seg['p_vaddr'],seg.data())
        self.u.mem_map(PARAM,0x20000)
        self.u.mem_map(STACK,0x20000)
        for va, data in ranges: self.u.mem_write(va,data)
        self.u.reg_write(UC_ARM64_REG_TPIDR_EL0,TLS)
        self.u.reg_write(UC_ARM64_REG_SP,STACK+0x10000)
        self.u.mem_write(0xa2f2f0,pack('Q',LENS))
        self.u.mem_write(TLS+0x28,pack('Q',0x12345678))
        self.u.hook_add(UC_HOOK_CODE,self.hook)
        self.oracle=oracle
        self.context=self.u.context_save()
        self.reached=False

    def hook(self,u,a,n,unused):
        if a==HALT: u.emu_stop(); return
        if a==0xac724 and self.case['type'] & 0xffff in (0,1,2):
            self.reached=True
            if self.oracle:
                scale=2.0 if self.case['type'] & 0xffff==2 else 3.0
                u.reg_write(UC_ARM64_REG_S10,fbits(fvalue(u.reg_read(UC_ARM64_REG_S10))*scale))
        if self.oracle and a==0xac6c4 and self.case['type'] & 0xffff in (0,1,2) and self.case['mode']==2:
            u.reg_write(UC_ARM64_REG_S0,fbits(min(21844,max(0,fvalue(u.reg_read(UC_ARM64_REG_S0))))))
        if a in (0x2bf70,0xacaa4): raise AssertionError('stack/assert failure')
        if a>=0x30000: return
        out=u.reg_read(UC_ARM64_REG_X1)
        if a==0x2daa0:
            u.reg_write(UC_ARM64_REG_X0,PARAM)
        elif a in (0x2e3c0,0x2fb00,0x2f9c0,0x2f9d0):
            u.mem_write(out,pack('H',self.case['lens_speed']))
            u.reg_write(UC_ARM64_REG_W0,self.case.get('lens_error',0)&0xffffffff)
        elif a in (0x2d2d0,0x2e9e0):
            key='aperture' if a==0x2d2d0 else 'fps_limit_factor'
            u.mem_write(out,pack('f',self.case[key]))
            u.reg_write(UC_ARM64_REG_W0,self.case.get('aperture_error',0) if a==0x2d2d0 else 0)
        elif a==0x2f9b0:
            u.mem_write(out,pack('d',self.case['lens_factor']))
            u.reg_write(UC_ARM64_REG_W0,self.case.get('factor_error',0))
        elif a==0x2cc00:
            u.mem_write(out,pack('I',self.case['focal']))
            u.reg_write(UC_ARM64_REG_W0,0)
        elif a in (0x2bf00,0x2bf10,0x2bf20): u.reg_write(UC_ARM64_REG_W0,0)
        else: raise AssertionError('unmodelled call '+hex(a))
        u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR))

    def run(self,c):
        self.case=c; self.reached=False
        u=self.u;u.context_restore(self.context)
        u.mem_write(PARAM,bytes(0x100));u.mem_write(OUT,b'\x9c\x9c')
        for offset,fmt,value in [(4,'I',c['mode']),(8,'B',1),(12,'f',60),(16,'H',c['steps']),
                                  (32,'I',35),(36,'f',c['close_scale']),(40,'f',c['slow_scale'])]:
            u.mem_write(PARAM+offset,pack(fmt,value))
        u.mem_write(LENS+8,pack('H',c['maximum']))
        u.mem_write(LENS+0x6b,pack('B',c['fallback']))
        u.reg_write(UC_ARM64_REG_X0,0);u.reg_write(UC_ARM64_REG_W1,c['type'])
        u.reg_write(UC_ARM64_REG_X2,OUT);u.reg_write(UC_ARM64_REG_S0,fbits(c['fps']))
        u.reg_write(UC_ARM64_REG_LR,HALT)
        for r in range(19,29):u.reg_write(globals()['UC_ARM64_REG_X'+str(r)],0x300000+r)
        u.emu_start(ENTRY,HALT,count=4000)
        assert u.reg_read(UC_ARM64_REG_PC)==HALT
        assert u.reg_read(UC_ARM64_REG_SP)==STACK+0x10000
        for r in range(19,29): assert u.reg_read(globals()['UC_ARM64_REG_X'+str(r)])==0x300000+r
        return (u.reg_read(UC_ARM64_REG_W0),struct.unpack('<H',u.mem_read(OUT,2))[0])

def main():
    binary=system_elf('/lib64/libaaa.so',SHA)
    obj=ELFFile(io.BytesIO((HERE/'fastscan.o').read_bytes()))
    assert not any(s['sh_type']=='SHT_RELA' and s.num_relocations() for s in obj.iter_sections())
    text=obj.get_section_by_name('.text').data()
    assert len(text)==0x190
    ranges=[(0xac6c4,text[0xdc:0xe0]),(0xac724,text[0x13c:0x190])]
    expected_destinations={0xac6c4:0xac744,0xac72c:0xac6ac,0xac740:0xac6ac,
                           0xac750:0xac6c8,0xac75c:0xac6c8,0xac774:0xac6c8}
    disassembly=[]
    for addr,data in ranges:
        for i in binary.cs.disasm(data,addr):
            disassembly.append(f'{i.address:08x}: {i.mnemonic} {i.op_str}')
            if i.address in expected_destinations:assert i.operands[-1].imm==expected_destinations[i.address]
    original=Runner(binary); oracle=Runner(binary,oracle=True);candidate=Runner(binary,ranges)
    base=dict(type=0,mode=2,lens_speed=5200,aperture=2.5,fps_limit_factor=1,
              lens_factor=.01175,focal=55,steps=1100,close_scale=1,slow_scale=.5,
              maximum=10000,fps=60,fallback=0)
    cases=[]
    for t in range(8):
        for mode in (0,1,2):
            for fps in (15,30,38,60,98,120):
                for fb in (0,1): cases.append(dict(base,type=t,mode=mode,fps=fps,fallback=fb))
    for t in range(6):
        for change in ({'aperture':0},{'steps':0},{'lens_error':-1},{'aperture_error':1},
                       {'factor_error':1},{'lens_factor':0},{'focal':20,'close_scale':.7}):
            cases.append(dict(base,type=t,**change))
    rng=random.Random(5515)
    for n in range(1000):
        cases.append(dict(base,type=rng.choice([0,1,2,3,4,5,6,65536,65537,65538,65539]),
            mode=rng.choice([0,1,2]),fps=rng.choice([24,38,60,98]),steps=rng.randrange(1,2000),
            lens_factor=rng.uniform(.0001,.02),aperture=rng.choice([2.5,4,8,11]),
            slow_scale=rng.choice([.25,.5,.75,1]),focal=rng.choice([20,35,55]),
            close_scale=rng.choice([.6,.8,1]),lens_speed=rng.randrange(1,10001)))
    for t in range(3):
        for speed in (0,21844,21845,32767,65535):
            for fps in (15,60,120):
                cases.append(dict(base,type=t,lens_speed=speed,fallback=1,fps=fps))
        for factor in (.000001,.0001,.001):
            for fps in (15,60,120):
                cases.append(dict(base,type=t,lens_factor=factor,fps=fps))
    changed=0
    for idx,c in enumerate(cases):
        a=original.run(c);o=oracle.run(c);p=candidate.run(c)
        assert o==p,(idx,c,a,o,p)
        if c['type']&0xffff not in (0,1,2) or c['mode']!=2:
            assert a==p,(idx,'unexpected change',c,a,p)
        if a!=p:changed+=1
    restore=bytearray(binary.read(ENTRY,END-ENTRY))
    for a,d in ranges:restore[a-ENTRY:a-ENTRY+len(d)]=d
    (HERE/'function-candidate.bin').write_bytes(restore)
    (HERE/'function-original.bin').write_bytes(binary.read(ENTRY,END-ENTRY))
    for a,d in ranges:restore[a-ENTRY:a-ENTRY+len(d)]=binary.read(a,len(d))
    assert bytes(restore)==binary.read(ENTRY,END-ENTRY)
    specs=[]
    for a,d in ranges:
        specs.append(dict(va=a,length=len(d),original=binary.read(a,len(d)).hex(),candidate=d.hex()))
    spec=dict(model='X2D 100C first generation',firmware='4.2.0',lens='55V',multiplier=3.0,stillMultipliers={'0':3.0,'1':3.0,'2':2.0},
              preBoostCeiling=21844,maximumVerifiedBoost=1.5,
              libaaaSha256=SHA,entry=ENTRY,end=END,functionSha256=hashlib.sha256(binary.read(ENTRY,END-ENTRY)).hexdigest(),
              candidateSha256=hashlib.sha256((HERE/'function-candidate.bin').read_bytes()).hexdigest(),ranges=specs)
    (HERE/'candidate.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    model=[dict(type=t,original=original.run(dict(base,type=t))[1],candidate=candidate.run(dict(base,type=t))[1]) for t in range(6)]
    result=dict(status='PASS',machineCodeCases=len(cases),changedCases=changed,model=model,
                tested='Original AArch64 function plus original FPS adjustment executed; external getters mocked; oracle scales successful dynamic types 0/1/2 by 3/3/2; all three bounded after FPS adjustment.',
                restore='byte-identical',deviceModified=False,actualMaximum=None,disassembly=disassembly)
    (HERE/'offline-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='disassembly'},indent=2))

if __name__=='__main__':main()
```

## candidate.json

```json
{
  "model": "X2D 100C first generation",
  "firmware": "4.2.0",
  "lens": "55V",
  "multiplier": 3.0,
  "stillMultipliers": {
    "0": 3.0,
    "1": 3.0,
    "2": 2.0
  },
  "preBoostCeiling": 21844,
  "maximumVerifiedBoost": 1.5,
  "libaaaSha256": "feef8a8dc3a27395e47232c2b25a5da7a7ab335922fbb527e637c439e35bcec7",
  "entry": 705408,
  "end": 706476,
  "functionSha256": "c8b5407c615b60c05078bc7ba9ada8cf53c905bac17faa59561f948feac0d430",
  "candidateSha256": "4eb555dc16ad54bdcfecd244b63bfea7ee691ce67b8274a1244644392ba15e13",
  "ranges": [
    {
      "va": 706244,
      "length": 4,
      "original": "0800381e",
      "candidate": "20000014"
    },
    {
      "va": 706340,
      "length": 84,
      "original": "a0090090020600d000f00f9142c03791e1031e32f2fdfd9780fb0736a40600b0a50600d084201791a5903d91200a8052a61c8152e1031e32e2630091e3031932ebfdfd9720faff3442c1221ea30600f0e103679e",
      "candidate": "a83e00121f09007108fcff540010211e0110201e200c201e4a09201edbffff170800381ea93e00123f090071c8fbff54090740b93f09007161fbff541f010071e8b3881a89aa8a521f01096b2881881ad5ffff17"
    }
  ]
}
```

## offline-results.json

```json
{
  "status": "PASS",
  "machineCodeCases": 1402,
  "changedCases": 219,
  "model": [
    {
      "type": 0,
      "original": 5170,
      "candidate": 15510
    },
    {
      "type": 1,
      "original": 2585,
      "candidate": 7755
    },
    {
      "type": 2,
      "original": 1292,
      "candidate": 2585
    },
    {
      "type": 3,
      "original": 5170,
      "candidate": 5170
    },
    {
      "type": 4,
      "original": 2585,
      "candidate": 2585
    },
    {
      "type": 5,
      "original": 1292,
      "candidate": 1292
    }
  ],
  "tested": "Original AArch64 function plus original FPS adjustment executed; external getters mocked; oracle scales successful dynamic types 0/1/2 by 3/3/2; all three bounded after FPS adjustment.",
  "restore": "byte-identical",
  "deviceModified": false,
  "actualMaximum": null,
  "disassembly": [
    "000ac6c4: b #0xac744",
    "000ac724: and w8, w21, #0xffff",
    "000ac728: cmp w8, #2",
    "000ac72c: b.hi #0xac6ac",
    "000ac730: fmov s0, #3.00000000",
    "000ac734: fmov s1, #2.00000000",
    "000ac738: fcsel s0, s1, s0, eq",
    "000ac73c: fmul s10, s10, s0",
    "000ac740: b #0xac6ac",
    "000ac744: fcvtzs w8, s0",
    "000ac748: and w9, w21, #0xffff",
    "000ac74c: cmp w9, #2",
    "000ac750: b.hi #0xac6c8",
    "000ac754: ldr w9, [x24, #4]",
    "000ac758: cmp w9, #2",
    "000ac75c: b.ne #0xac6c8",
    "000ac760: cmp w8, #0",
    "000ac764: csel w8, wzr, w8, lt",
    "000ac768: mov w9, #0x5554",
    "000ac76c: cmp w8, w9",
    "000ac770: csel w8, w9, w8, hi",
    "000ac774: b #0xac6c8"
  ]
}
```

## MANIFEST.json

```json
{
  "README.md": "6819d8bbb13f63ea981481accfe86ccdc59e0e912b4eee7c141ea036db9ce3d4",
  "requirements.txt": "10f08a5e315fea31f58c431f35b94f648cd6a131aa1f7213700b0a9066b2340c",
  "offline_elf.py": "b674e73dabce62bd5ec93295dcecd634663c0560f55e50d657d149381f0884f1",
  "extract_ota.py": "79eda79008965395f3473499715b6d0e4791acbbadb6cd2555b030261a86412d",
  "fastscan.S": "6d1c278125a8ac97499ff59c0a3b0a5919b7eb8593f09cb38db1aa9e086bafb1",
  "verify_candidate.py": "71eaeb54c46d7587defc10b556d0f78ace14f83f30332c14ee516b0bec59c79b",
  "candidate.json": "70c1e2a0a3fb941802a17d48b9a24f505af758d2af3fbff9a1fddfac1d3f4552",
  "offline-results.json": "fcdebaf656c31aeb3841a5f11b392b97842733c4a0ac9c80fac52a5a6501bc08"
}
```

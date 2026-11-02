# GPR / GVID 非 CNN RAW 视频离线实验

## 目的与范围

通过固定版本的 `dcliftreaves/gpr` 依赖，将约 100 MP X2D Bayer RAW 编码成
GVID 序列，再原生解码、导出带标定的 GPR / DNG，并生成普通桌面播放器可用的
MP4。编码器、容器和有界采集 API 均由 GPR 提供；本目录只维护薄适配层。
整个流程不依赖 CNN、Torch、模型权重或学习型图像恢复。

适用研究机型为第一代 X2D 100C，固件研究背景为 4.2.0。本目录的验证级别是
**桌面离线实验**，没有连接相机、修改固件或证明机内录像可用。X2D II 的
传感器接口、内存与性能需要独立验证。

## 拍 50 张照片后，一条命令查看结果

面向第一代 **X2D 100C** 的电脑端复现入口是 `camera_trial.py`。把相机拍摄的
50 张 FFF / 3FR / 已校准 Bayer DNG 复制到一个本地目录，即可运行。无需先手写
RAW 清单或逐项执行编码、解码、显影命令；不连接或控制相机。

首次准备需要 Python 3.11+、CMake 3.20+、C/C++ 编译器、zlib，以及含 `libx264`
和 `prores_ks` 的 FFmpeg / ffprobe。完整矩阵需要 `setpts` 的 `strip_fps` 功能；
实测 FFmpeg 8.1.1。以下命令从本模块目录执行：

```sh
python3 -m venv outputs/venv
. outputs/venv/bin/activate
python -m pip install -r requirements-trial.txt
python camera_trial.py /path/to/50-photos --output outputs/quick
```

**不需要另外准备 DNG/GPR。** FFF / 3FR 默认使用 LibRaw 已有的 X2D 型号 D65
颜色矩阵，结合每张原文件的白平衡、黑白电平、方向和裁切，自动创建本地
`reference.dng` 与 `reference-provenance.json`。该 DNG 保存第一帧对齐后的原始
传感器样本，不从有损 GPR 解码生成。它是单光源型号配置，不是新做的单机标定，
也不声称复现 Phocus / HNCS、镜头修正或双光源颜色配置。

已有同机型有效 DNG/GPR 的用户仍可用 `--reference` 覆盖默认颜色配置；输入目录
中的合格 DNG 也可自动提供参考。GPR 不作为原始像素输入。当前入口只接受第一代
X2D 100C，不能把二代数据当作已经验证。首次运行自动下载固定版本的公开 GPR
源码并编译；不上传照片、影片或元数据。

默认自然排序选取前 50 张照片，生成 **3840×2160、12-bit 计数、Q3 GVID**，
逐帧原生解码、检查校验/PTS/标定，并输出 1080p H.264 查看电影和 4K ProRes HQ。
打开 `outputs/quick/report.html` 即可比较编码时间、实测码率、RAW PSNR，并点击
影片链接。默认查看曝光为 0 EV，可用 `--exposure-ev 1` 调整显影；不改变保存的 RAW。
浏览器可能不直接播放 MOV，报告中的 MP4 供直接查看，MOV 可用支持 ProRes 的播放器打开。

**已用 50 张实际 X2D FFF 验证快捷入口**：50 帧均完成原生解码及元数据/校验检查，
MP4 与 ProRes HQ 均由 FFmpeg 完整解码并核对帧数。该次 M5 测试平均编码约
2.73 ms，VC-5 载荷在名义 30 fps 下约 128.7 Mb/s，RAW 样本 PSNR 为 54.51 dB。
这些是该组照片的电脑测量，不是相机采集或持续录像性能。
汇总见 [trial_evidence.json](trial_evidence.json)。完整入口另以 2 张真实照片跑通
30 组 GVID 与 64 组 FFmpeg，全部解码/帧数检查通过；2 帧只用于流程验收，
不用于代表长片码率。软件 ProRes 快捷路径与原生 3FR 像素准备也分别验证通过。

自动参考模式另外以全新依赖下载/构建及 50 张实际 X2D FFF 跑通，未提供
`--reference`；两个查看影片均为 50 帧。单独转换的 X2D 3FR 与 FFF 均生成 DNG
及 GPR，DNG 每个样本与对齐后的原始传感器样本相同，GPR 原生解码与标定检查通过。

完整试验另用一个输出目录：

```sh
python camera_trial.py /path/to/50-photos --output outputs/full --all --plan
python camera_trial.py /path/to/50-photos --output outputs/full --all
```

`--plan` 仅显示输入数量和试验范围。`--all` 执行：

| 类别 | 范围 |
| --- | --- |
| GVID | 4K 12-bit / 30 fps；8192×3424 的 11-bit 计数 / 24 fps；3840×1296 RAW / 60 fps；完整对齐尺寸 14-bit / 6 fps、16-bit / 2.7 fps；每种 Q0–Q5 |
| ProRes | 1080p60、4K24、4K30、8192×3424 / 24；Proxy、LT、Standard、HQ、4444、4444 XQ |
| H.264 目标码率 | 1080p60：5/10/20/40 Mb/s；4K24/30：10/25/50/100；8K24：50/100/200/400 |

GVID 为质量预设驱动的可变码率，报告提供实际码率。ProRes 同样按 profile 选择；
H.264 分别报告目标和实际码率。macOS 若提供 VideoToolbox，会另测要求硬件的
ProRes 路径；快捷导出默认使用软件编码。完整矩阵中不支持的组合在报告中标出失败原因，不当作通过。其他系统使用软件路径。
普通 ProRes 是去马赛克后的视频，**不是 ProRes RAW**；工具记录后者的编码器/解码器
可用性，但没有将“安装了解码器”当作实际 RAW 文件解码成功。

快捷试验建议预留至少 20 GB；50 张完整试验建议至少 100 GB，复杂画面可能更多。
完整试验包含 30 组 GVID、至多 64 组 FFmpeg 组合，生成大体积无损像素 NUT 参考片，
并对影片完整解码、计算 PSNR / SSIM，耗时明显长于快捷试验。可先用 `--limit 2`
验证本机依赖，再用 50 张比较质量。编码计时与整段文件/显影时间分开记录；FFmpeg
时间包含输入与转换开销。RAW PSNR 与显影后 PSNR / SSIM 不能直接互相比数值。

相同命令可以继续已有输出中的已完成组合；输入哈希或选项改变时拒绝复用目录。
中途失败可留下不完整当前组合，需查看日志并保留或清理该组合后重试；已完成组合
有 `result.json`，报告随完成情况更新。私有输入清单保存原始路径和哈希，所有输出
均应留在本地。输入目录只读，输出必须位于输入目录之外。

缩小输入使用偶数原点裁切及分 Bayer 平面的 Lanczos 缩放，再量化计数。它们用于
计算负载与压缩比较，**不模拟真实传感器跳行/binning、读出或噪声**。播放时间戳是
合成的；拍 50 张照片可以验证编解码链，不能验证持续传感器采集或相机发热。

## 单独把相机文件转换成 DNG / GPR

使用上面的 Python 环境与编译依赖；不需要 FFmpeg 或预先存在的参考图。
可给单张、多张文件或本地目录。默认最多前 50 张，输出目录必须不存在：

```sh
python convert_stills.py /path/to/photo.3FR --output outputs/still
python convert_stills.py /path/to/photos --output outputs/stills --limit 50
```

默认保留完整对齐尺寸（通常为 11664×8744），不经过快捷试验的 4K 缩放。
每张生成 `frames/000000.dng` 与 `frames/000000.gpr`，依次编号：

- **DNG**：未去马赛克的 uint16 Bayer；仅按本模块约定裁去底部不对齐行。
  逐样本验证与准备后的源 RAW 完全相同，并核对类型化标定；不经过 VC-5。
- **GPR**：Q3 VC-5 有损压缩，颜色/黑白电平/白平衡/裁切与 DNG 相同。
  逐帧原生解码并验证载荷与标定。`--quality 0` 至 `--quality 5` 选择压缩预设；
  16-bit 输入不代表 16-bit 无损压缩。
- `conversion.json`：逐帧完成状态、颜色来源与验证结果。`prepared/` 与中间
  `encoded.gvid` 也留在本地；输出含私人照片信息，不应上传。

仅需要精确像素 DNG 时加 `--format dng`；仅需要 GPR 时加 `--format gpr`。
`--build /path/to/existing-build` 可复用本模块构建；`--reference` 是可选颜色
配置覆盖项。现有文件拒绝覆盖，失败目录保留供检查，重试请用新输出目录。
导出的原始样本 DNG 可作为后续显式 `--reference`，没有已有 GPR 的循环依赖。

默认通过 RawPy `rgb_xyz_matrix` 读取 LibRaw `cam_xyz`，按 XYZ→camera 的 DNG
`ColorMatrix1` 方向直接写入，**不转置或求逆**，光源为 D65。这里只使用已有
型号矩阵，不根据拍摄场景猜测矩阵。依据：
[LibRaw 的矩阵方向说明](https://www.libraw.org/node/2099)、
[RawPy 属性实现](https://github.com/letmaik/rawpy/blob/main/rawpy/_rawpy.pyx)、
[LibRaw 型号颜色表](https://github.com/LibRaw/LibRaw/blob/master/src/tables/colordata.cpp)。

## 已测结果

2026-11-01，Apple M5 Max、18 核 CPU、128 GiB 内存、macOS 26.7.1，Release
原生编码，Q3，11664×8744 RGGB、16-bit 输入。汇总见 [evidence.json](evidence.json)。

| 输入 | 帧数 | 平均编码时间 | 编码时间范围 | 峰值进程 RSS | VC-5 总载荷 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 不同场景的真实 X2D 照片 | 8 | 47.23 ms | 28.20–73.49 ms | 339.17 MiB | 149.46 MB |
| 连贯的真实 X2D 照片序列 | 77 | 49.98 ms | 36.08–63.75 ms | 306.25 MiB | 1296.09 MB |

两组所有帧均完成原生解码与支持范围内的类型化标定导出核对；77 帧具有不同的
压缩载荷。8 帧结果以完整 16-bit 范围为峰值计算的 Bayer 样本 PSNR 为
46.21–54.64 dB。PSNR 不包含曝光归一化，也不等于视觉质量或色彩准确度保证。

77 帧序列已经导出并由 FFmpeg 完整解码验证为 1280×960 H.264、24 fps、
3.208 秒的本地查看视频。该组是连贯照片序列，**不是已核实的间隔延时摄影或
连续传感器录像**；播放时间戳是合成的名义时间戳。查看视频使用 +1 EV 普通
显影补偿，不改变保存的 RAW。

编码计时排除 FFF 解码、源文件读取、DNG 导出和显影，不能当作持续采集帧率。
RSS 是进程驻留内存，不是 malloc 总容量、相机 DMA 预算或最坏场景上限。
同版本单帧全范围合成噪声在该电脑上约需 464 MiB RSS，说明照片结果不能直接
证明相机内存适配。原始照片、影片及逐图私有记录只留在操作者本地；公开汇总
不是随仓库分发的测试输入。

## 文件地图与依赖

- `CMakeLists.txt`：固定外部源码版本、构建目标与 CTest。
- `demo.cpp`：逐帧离线输入、单 RAW 缓冲区租借、GVID 写入及计时。
- `mapped_input.h/.cpp`：显式格式的已映射 Bayer 回调输入；复制有效行后立即归还源。
- `test_mapped_input.cpp`：阻塞写入时的有界背压、拒绝/重试与输入格式检查。
- `inspect_firmware.py`：固定哈希的第一代固件配置、HAL 与传感器模式离线核对。
- `firmware_evidence.json`：固件候选模式与对应尺寸的电脑测试汇总。
- `decode_frame.cpp`：调用依赖的原生 VC-5 解码 API。
- `camera_trial.py`：50 张照片的快捷 / 完整试验入口、自动参考 DNG 与本地 HTML 报告。
- `convert_stills.py`：直接把 X2D FFF / 3FR 转成精确样本 DNG 与有损 GPR。
- `trial_gvid.py` / `trial_ffmpeg.py`：批量原生往返与影片 profile / 码率验证。
- `requirements-trial.txt`：桌面照片试验的固定 Python 依赖。
- `test_color_profile.py`：颜色矩阵方向、D65 标签及无效配置拒绝检查。
- `prepare.py`：可选的 X2D FFF / 3FR / Bayer DNG 像素与标定准备。
- `extract.py`：验证完整 GVID，原生解码并核对 GPR / DNG 标定。
- `render.py`：LibRaw 常规显影、缩小和 FFmpeg H.264 查看导出。
- `test_offline.py`：可自行生成的小型合成输入与完整往返/错误路径检查。
- `evidence.json`：不含源照片信息的实测汇总。

原生构建要求 macOS / Linux、CMake 3.20+、C/C++11 编译器、线程库和 zlib。
合成检查与提取脚本只用 Python 3 标准库和 GPR 自带工具。
准备真实输入另需 `rawpy`、`numpy`、`tifffile`；查看导出另需 `rawpy`、
`Pillow` 和带 `libx264` 的 FFmpeg。实测 Python 依赖版本见汇总。
原始照片由操作者提供，不随仓库附带；默认颜色配置来自 LibRaw 型号表，
同机型外部颜色参考仅为可选覆盖项。

依赖固定为 `dcliftreaves/gpr` 提交
`0a194995f481d09f347e99252d41558de3d97c77`，下载归档 SHA-256：
`3f41df424d7b6ffca9e4c6a15c3fabae3e59e5b6290ddc98b74f4f74ab688ab4`。
默认 CMake 只下载已固定的公开源码，不上传用户数据。亦可显式提供对应版本的
本地检出：`-DGPR_SOURCE_DIR=/path/to/gpr`，此时由操作者保证版本一致。
GPR 保留其 Apache-2.0 / MIT 许可；本目录适配器按仓库 MIT 许可提供。

## 构建及可公开复现的合成检查

以下命令都从本模块目录执行：

```sh
cmake -S . -B outputs/build -DCMAKE_BUILD_TYPE=Release
cmake --build outputs/build -j 4
ctest --test-dir outputs/build --output-on-failure
```

安装照片试验的 Python 依赖后，可另运行颜色矩阵检查：

```sh
python test_color_profile.py --gpr-source outputs/build/_deps/gpr_dependency-src
```

默认下载模式下，后续 Python 命令的 `--gpr-source` 使用
`outputs/build/_deps/gpr_dependency-src`。若配置了本地依赖，则替换为对应路径。
合成检查会生成 3 个不同的 128×96 RGGB16 帧，验证原生解码、GPR/DNG 类型化
标定、PTS、CRC、END3，并检查拒绝覆盖、截断文件和错误 RAW 长度。测试只在
临时目录写文件，结束后清除；不会访问设备或照片库。

新增回调检查使用 273 字节的奇数行距，让交替行处于非对齐地址，并用非零数据
填充 padding。提交后、等待编码前立即覆盖源缓冲区，结果仍须与紧密排列输入
逐字节相同。另一个原生检查阻塞 writer，验证队列上限为 1、返回 `BUSY` 后
不消耗帧索引、可重试同一索引，以及拒绝未知格式、短缓冲区和越界计数。

## 准备真实输入

输入契约是紧密排列的 little-endian uint16 RGGB，每帧 JSON 包含 GPR
`raw_metadata` 类型化标定。原生适配器支持 12/14/16-bit 计数域，低位深样本
必须处于声明范围；本目录的真实输入准备器只输出 **16-bit 计数域**。DNG 输入
必须已经具有匹配的 16-bit 数值与黑白电平，不会自动重标定其他数值域。

`frames.tsv` 每行用实际制表符分隔：RAW 路径、JSON 路径、纳秒 PTS。
相对路径以清单目录为基准，PTS 必须严格递增。编码器把帧 JSON 作为不透明
字节保存；`extract.py` 在导出前检查标定与头部契约。

已有校准 DNG 可直接准备；X2D FFF / 3FR 默认自动补齐型号颜色矩阵：

```sh
python3 prepare.py input-a.FFF input-b.FFF \
  --gpr-source outputs/build/_deps/gpr_dependency-src --output outputs/prepared --fps 24
outputs/build/gvid_raw_demo 11664 8744 16 3 24 \
  outputs/prepared/frames.tsv outputs/clip.gvid
```

准备器不插值像素。从 11664×8750 底部裁去 6 行得到 11664×8744，损失约
0.069% 像素，保留 RGGB 原点并调整 ActiveArea / DefaultCropSize。输出宽高以
准备器报告为准。GPR 的 `stock_crop.aligned` 对不支持的裁切标定拒绝操作，
不会静默忽略非空 opcode 等信息。

FFF 的可见像素来自 LibRaw；逐张黑白电平、白平衡、方向与裁切来自 FFF，
静态颜色矩阵默认来自 LibRaw X2D D65 型号配置，也可由同机型外部参考覆盖。
**未重现厂家镜头/opcode 处理，
不声称与 Phocus 显影完全一致。** 输入 GPR 不能作为原始像素来源；参考 GPR
只提供颜色标定，不会再次压缩其有损像素。

## 原生提取与查看视频

```sh
python3 extract.py outputs/clip.gvid outputs/decoded \
  --decoder outputs/build/gvid_decode_frame \
  --gpr-source outputs/build/_deps/gpr_dependency-src
python3 render.py outputs/decoded outputs/review.mp4 --exposure-ev 1
ffprobe -v error -count_frames -select_streams v:0 \
  -show_entries stream=codec_name,width,height,nb_read_frames outputs/review.mp4
```

提取前完整检查 GVID v3、帧校验、标定与 END3，随后导出每帧 VC-5、原始压缩
载荷的 GPR、原生解码 RAW 与 DNG，逐项核对支持的类型化标定。
`extraction.json` 记录 PTS 和摘要；这些文件可能包含私有图像信息，应留在本地。

查看导出使用常规 LibRaw 去马赛克、源白平衡/颜色和缩小，不用 CNN。默认接受
名义恒定帧率 PTS；其他节奏必须显式给 `--fps` 重新解释查看速度。此选项和
`--exposure-ev` 都不改变 GVID 时间戳或 RAW 内容。MP4 只是缩小的查看副本，
完整 RAW 交付物仍为 GVID 及提取结果。

## 副作用、限制与后续接口

所有入口只读显式提供的输入并新建输出；照片与影片处理纯离线。首次构建可下载公开依赖。
底层入口拒绝覆盖；`camera_trial.py` 可按输入身份继续已有完成组合。失败可留下
不完整文件或部分提取目录，退出非零不能视为完成。每帧 flush 后才复用 RAW
缓冲区；当前策略便于验证生命周期，并不演示传感器流水线并行。
`fflush` / 关闭检查不提供 `fsync` 持久化保证。

VC-5 使用原有 12-bit log-domain 变换与有损质量预设；接收 16-bit 输入不等于
16-bit 无损编码。本实验没有机内部署、录制 UI、传感器 RAW 缓冲接口或热稳定
实测。未来接入首先需要确认 RAW 格式/步幅、缓冲所有权、采集节奏以及实际
可用内存；X2D II 需要单独审计。

可结合现有[第一代成像与视频研究](../../research/4.2.0/IMAGING-AND-VIDEO-UPDATE.md)
讨论后续接口。桌面测量只说明该编解码链能处理实际约 100 MP 帧，不能把
名义 24 fps 查看输出或 M5 编码性能直接外推成相机录像能力。

## 第一代固件的 RAW 视频候选：新增静态证据

从官方 X2D 100C 4.2.0 包只读提取配置与 ELF，交叉核对配置中的 RAW 输出、
编译 HAL 的模式指针及传感器驱动名称；不是只根据配置名推断。
复核输入的 SHA-256、16 条消费指令与结果见
[firmware_evidence.json](firmware_evidence.json)。原厂文件、完整配置和反汇编不公开。

| 候选 RAW 输出 | 名义速率 | 驱动模式 | 配置端口 | 当前验证级别 |
| --- | ---: | --- | --- | --- |
| 3840×2160 | 30 fps | 35，12-bit | BOUT0 | 配置 + 编译 HAL + 驱动表静态对应 |
| 8192×3428 | 24 fps | 33，11-bit | BOUT0 | 配置 + 编译 HAL + 驱动表静态对应 |
| 3840×1296 | 60 fps | 38，12-bit | BOUT0 | 对应 1080p YUV 模式，RAW 尺寸不同 |

第一代完整尺寸 14-bit 模式也在编译表中名义标为 6 fps。12K 名义 10 fps
候选的驱动名写 11-bit，而 HAL 位深字段为 12；不能静默当作同一含义。
RAW/传感器边界尺寸、最终 YUV 尺寸与 ADC 位深必须分别记录。

这些 `raw_dump` 流在模板中标记为 repeating + on-demand，声明存在不表示已经
激活。高层录像开始/停止仍有未实现路径。原来的 H.264/ProResRAW 模板另带较大
编码器预留，不应直接把整条模板当作低内存 GVID 实现。

只读复核命令（输入为自行准备的对应版本 system 根，输出放在输入树外）：

```sh
python3 inspect_firmware.py --system-root /path/to/x2d-system-root \\
  --output outputs/firmware-audit.json
```

该工具复用仓库现有 `pdaf-only-shadow/native_afs_parameters.py` 的标准库 ELF/APS2
读取器，不运行厂商代码。哈希不同即拒绝；没有自动解包、设备连接或模式切换。
X2D II 1.3.18.1 的配置/ELF 已另外本地检查，但本工具和上述地址只适用于第一代。
二代使用 IMX861 命名和不同流图，不能直接套用第一代模式或缓冲区 ABI。

## 已映射输入桥与候选尺寸测试

`gvid_submit_mapped` 是应用侧 C 契约，**不是对厂商 `cam_frame_buffer` 的 ABI 声明**。
只有调用方明确确认 `RGGB_U16_LE_COUNTS`、12/14/16-bit 计数域、尺寸与实际行距
后才接受。`RAW16_OPAQUE` 名称不足以证明线性排列、右对齐、Bayer 相位或光学
黑边布局。11-bit 传感器数据也不能直接假定为 GPR 的 12-bit 输入域；应先确认
映射计数与配套黑白电平。

调用方负责在回调有效期内完成 DMA 映射及 CPU 缓存同步。桥以零等待时间提交，
GPR 同步复制有效像素行和元数据后返回；此后源可立即解除映射/复用。它不保留
相机对象指针，不替调用方增减厂商引用计数。队列满返回 `BUSY`；调用方决定丢帧
或重试，成功帧索引须连续，PTS 保留实际间隔。停止采集回调后再 finish/destroy。
当前桥需复制一份 RAW；它是生命周期明确的候选，并非零复制或实机性能保证。

文件入口增加可选的第 8 个参数 `callback_stride_bytes`，用于离线回放已明确格式
的带 padding 输入，并在每次提交后模拟立刻覆盖源缓冲区：

```sh
outputs/build/gvid_raw_demo 3840 2160 12 3 24 \\
  outputs/mapped/frames.tsv outputs/mapped.gvid 7680
```

该回放仍逐帧 flush；真实生产者可在可用队列中继续提交，但不能在相机回调中
等待编码完成。元数据/标定的完整性要求与前文相同。

M5 上 Q3、各 8 张不同实际照片的左上裁切/量化输入，经过该复制桥实测：

| 输入尺寸 | 编码平均 / 最慢 | 读文件到 GVID 的短批次速率 | 峰值进程 RSS |
| --- | ---: | ---: | ---: |
| 3840×2160，12-bit 计数 | 3.53 / 5.62 ms | 84.58 fps | 62.84 MiB |
| 8192×3424，11-bit 计数放入 12-bit 容器 | 11.73 / 18.50 ms | 32.90 fps | 202.72 MiB |
| 11664×1248，12-bit 计数 | 6.12 / 9.63 ms | 61.77 fps | 108.78 MiB |

8192×3428 候选为了编码对齐再裁底部 4 行。测试输入只是计算负载样本，
**不模拟真实跳行/binning 的空间响应或噪声，不证明厂家模式的 RAW 格式**。
数据刚在本地生成，可能命中缓存；短批次速率不代表长时间存储、热稳定或相机
性能。4K / 8K 两组均原生解码并核对了支持的类型化标定，所有帧完成 END3 检查。

## ARM64 Android 9 编译检查

使用本地 Android NDK 28.2.13676358，API 28 / arm64-v8a，Release 构建
`gvid_raw_demo`、`gvid_decode_frame` 和 `gvid_mapped_input` 静态库通过。
生成 ARM64 ELF、解释器为 `/system/bin/linker64`；没有在相机或模拟器执行，
不能把交叉编译当成厂商 ABI、CPU 性能或硬件功能验收。使用自己的 NDK 路径：

```sh
cmake -S . -B outputs/android28 \\
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK_ROOT/build/cmake/android.toolchain.cmake" \\
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-28 \\
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build outputs/android28 --target gvid_raw_demo gvid_decode_frame -j 4
```

两个 ELF 所需的强外部符号名称，在第一代原厂 `libc/libm/libdl/libz` 导出中均可
找到；没有额外的 `libc++_shared.so` 依赖。此项仅核对符号名称，不代替符号版本、
加载器及运行时行为验证。

下一项实机前提是取得一帧匹配模式的 RAW、实际 plane/stride/时间戳描述与已核实
的生命周期/缓存契约，再将模式特定的标定传入本桥。当前代码没有自动绑定厂商
回调、切换传感器模式或提供设备部署步骤。

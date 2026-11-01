# GPR / GVID 非 CNN RAW 视频离线实验

## 目的与范围

通过固定版本的 `dcliftreaves/gpr` 依赖，将约 100 MP X2D Bayer RAW 编码成
GVID 序列，再原生解码、导出带标定的 GPR / DNG，并生成普通桌面播放器可用的
MP4。编码器、容器和有界采集 API 均由 GPR 提供；本目录只维护薄适配层。
整个流程不依赖 CNN、Torch、模型权重或学习型图像恢复。

适用研究机型为第一代 X2D 100C，固件研究背景为 4.2.0。本目录的验证级别是
**桌面离线实验**，没有连接相机、修改固件或证明机内录像可用。X2D II 的
传感器接口、内存与性能需要独立验证。

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
- `decode_frame.cpp`：调用依赖的原生 VC-5 解码 API。
- `prepare.py`：可选的 X2D FFF / Bayer DNG 像素与标定准备。
- `extract.py`：验证完整 GVID，原生解码并核对 GPR / DNG 标定。
- `render.py`：LibRaw 常规显影、缩小和 FFmpeg H.264 查看导出。
- `test_offline.py`：可自行生成的小型合成输入与完整往返/错误路径检查。
- `evidence.json`：不含源照片信息的实测汇总。

原生构建要求 macOS / Linux、CMake 3.20+、C/C++11 编译器、线程库和 zlib。
合成检查与提取脚本只用 Python 3 标准库和 GPR 自带工具。
准备真实输入另需 `rawpy`、`numpy`、`tifffile`；查看导出另需 `rawpy`、
`Pillow` 和带 `libx264` 的 FFmpeg。实测 Python 依赖版本见汇总。
原始照片及同机型颜色标定参考由操作者提供，不随仓库附带。

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
cmake --build outputs/build --target gvid_raw_demo gvid_decode_frame -j 4
ctest --test-dir outputs/build --output-on-failure
```

默认下载模式下，后续 Python 命令的 `--gpr-source` 使用
`outputs/build/_deps/gpr_dependency-src`。若配置了本地依赖，则替换为对应路径。
合成检查会生成 3 个不同的 128×96 RGGB16 帧，验证原生解码、GPR/DNG 类型化
标定、PTS、CRC、END3，并检查拒绝覆盖、截断文件和错误 RAW 长度。测试只在
临时目录写文件，结束后清除；不会访问设备或照片库。

## 准备真实输入

输入契约是紧密排列的 little-endian uint16 RGGB，每帧 JSON 包含 GPR
`raw_metadata` 类型化标定。原生适配器支持 12/14/16-bit 计数域，低位深样本
必须处于声明范围；本目录的真实输入准备器只输出 **16-bit 计数域**。DNG 输入
必须已经具有匹配的 16-bit 数值与黑白电平，不会自动重标定其他数值域。

`frames.tsv` 每行用实际制表符分隔：RAW 路径、JSON 路径、纳秒 PTS。
相对路径以清单目录为基准，PTS 必须严格递增。编码器把帧 JSON 作为不透明
字节保存；`extract.py` 在导出前检查标定与头部契约。

已有校准 DNG 可直接准备；X2D FFF 还需同机型参考 DNG/GPR 提供颜色矩阵：

```sh
python3 prepare.py input-a.FFF input-b.FFF --reference same-model-reference.dng \
  --gpr-source outputs/build/_deps/gpr_dependency-src --output outputs/prepared --fps 24
outputs/build/gvid_raw_demo 11664 8744 16 3 24 \
  outputs/prepared/frames.tsv outputs/clip.gvid
```

准备器不插值像素。从 11664×8750 底部裁去 6 行得到 11664×8744，损失约
0.069% 像素，保留 RGGB 原点并调整 ActiveArea / DefaultCropSize。输出宽高以
准备器报告为准。GPR 的 `stock_crop.aligned` 对不支持的裁切标定拒绝操作，
不会静默忽略非空 opcode 等信息。

FFF 的可见像素来自 LibRaw；逐张黑白电平、白平衡、方向与裁切来自 FFF，
静态颜色标定来自操作者提供的同机型参考。**未重现厂家镜头/opcode 处理，
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

所有入口纯离线，只读显式提供的输入并新建输出；输出拒绝覆盖。失败可留下
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

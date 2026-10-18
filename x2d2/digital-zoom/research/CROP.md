# X2D II 1.3.16.2 裁切接口边界

## 适用范围

对象为 X2D II 100C 原厂 1.3.16.2。下述名称来自该版本的静态字符串／符号研究贡献；原厂库与固件不随仓库提供。本轮新增验证只使用合成文件和纯几何，不连接相机。

## 当前结论

### 照片比例不是数字变焦（静态分析）

`HblmTypes::E_CropMode` 改变照片形状，保留完整宽或完整高。设置链名称包括 `CameraSettings::setCrop_mode_current(HblmTypes::E_CropMode, bool)`、`CameraObjectImpl` 对应入口、`MetadataControl::setCropMode`、`Cmd_SetCropMode` 与 `Worker::CropModeEvent`。这些名称证明照片比例链存在，不证明它接受任意矩形。

`Common::kCropBorderFRatio*` 表示全画面边缘内缩比例。已有静态记录如下；数值没有在本轮实机复测：

| 模式 | 水平内缩 | 垂直内缩 | 保留完整边 |
| --- | ---: | ---: | --- |
| 3:2 | 0 | 0.0555 | 宽 |
| 16:9 | 0 | 0.1250 | 宽 |
| 2:1 | 0 | 0.1667 | 宽 |
| 65:24 | 0 | 0.2538 | 宽 |
| 1:1 | 0.1318 | 0.0090 | 高（记录含小偏差，待复核） |

因此 16:9 的“1.0×”应是全宽的 16:9 基准；数字 2.0× 必须在该基准上再同时缩小两轴。旧候选错误地总以完整传感器对角线为分母，使 16:9、1:1 和 65:24 的最大数字倍数分别只有约 1.836×、1.697×、1.706×。当前 `crop_geometry.py` 已把每个照片比例的最大窗口独立定义为 1.0×，离线测试确认各比例都达到不低于 2.0×。

已记录的模式名称还包括 `E_CropMode_None`、`Ratio1to1`、`Ratio7to6`、`Ratio5to4`、`Ratio11to8p5`、`Ratio297to210`、`Ratio3to2`、`Ratio3to2Crop`、`Ratio16to9`、`Ratio2to1`、`Ratio65to24`、`All` 和 `Max`。`QSizeF Common::cropFactors(HblmTypes::E_CropMode)` 与 `Common::CropData` 仍属于固定比例证据。

### 机内放大查看不是拍摄裁切（静态分析）

`HblmTypes::E_ZoomLevel` 的 `Full`、`Half`、`Max`，以及 `ZoomFlick`、`ZoomOverlay`、`ZoomIndicator`，更符合查看／对焦放大链。没有证据表明它们改变保存照片。

### 任意矩形仍缺少可用后端（待验证）

`ImageMemory::toCroppedCopy(const QRect &)` 能对已经位于内存的缓冲区生成裁切副本。单一名称不能证明坐标属于传感器有效区、能驱动实时预览、会影响最终照片或能保持 RAW 管线。当前仓库没有把它实现成 `CropWindowSink`。

## 证据与复现

`find_crop_strings.py` 可扫描操作者合法取得的本地提取目录，包括共享库、静态库与对象文件。它以 64 KiB 块只读扫描 ASCII 字符串，跨块保留状态并跳过符号链接。命中只代表名称证据，不能自动提升为可调用 ABI 或可写接口。

纯几何与生命周期检查见 [`../CodeTests/offline-contract/`](../CodeTests/offline-contract/README.md)。测试证明窗口嵌套、CFA 对齐、请求不下取整以及 C/Python 一致性；不证明坐标空间或相机效果。

## 限制与下一步

下一项技术门槛是从 1.3.16.2 中确定同一任意矩形同时影响预览与保存照片的接口，记录参数单位、坐标原点、四项对齐、线程／生命周期和可逆性，再实现一个机型、版本限定的适配器。找到字符串、显示 QML 控件或通过桌面测试都不能替代这项证据。

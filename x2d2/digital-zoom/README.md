# X2D II 数字裁切（离线开发候选）

## 目的与边界

本模块计算 1.0×–2.0× 中心数字裁切窗口的机型隔离候选：当前照片比例先定义 1.0× 基准窗口，随后同时缩小宽、高，因此 16:9、1:1、3:2 与 65:24 都能得到相对于各自基准的真实 2.0× 规划值。算法、生命周期控制、通用 QML 组件及 C 核心已经进入离线测试；没有代码实际裁切像素或控制相机。

当前没有找到 X2D II 预览与拍摄共用的任意矩形接口，也没有厂商签名或普通更新器验收结果。源码不能直接放入 CFexpress，也不能通过 Phocus 变成可安装固件；本目录不包含安装器、系统文件替换或更新包生成器。裁切元数据按用户要求后置，GPS 是未来独立功能，不与本轮裁切后端混接。

## 适用对象与证据层级

- 机型：X2D II 100C；与第一代 `x2d/` 实现和地址严格分开。
- 固件研究基线：1.3.16.2，平台标识 `10.00.09.77`。
- 几何输入：[X2D II 100C 官方用户手册](https://cdn.hasselblad.com/manuals/X2D_II_100C_User_Manual/User_Manual/X2D_II_100C_User_Manual_v1.0_en.pdf)列出的 11656×8742、43.8×32.9 mm 规格，候选暂按 2 像素 CFA 相位对齐。
- 已验证：Python/C 几何一致性、控制器故障关闭、通用 QML 静态契约、只读字符串扫描和安装就绪门禁，均为电脑端离线验证。
- 未验证：上述公开像素是否等于内部 RAW／预览坐标、真实后端对齐要求、预览、保存文件、RAW、功耗、温度、重启保持、普通更新器安装和恢复。

## 文件地图

| 路径 | 职责 |
| --- | --- |
| `crop_geometry.py` | 以所选照片比例为 1.0× 基准，计算居中且对齐的窗口。 |
| `controller.py` | 区分选择、页面可见性和实际应用；未知后端一律拒绝宣称成功。 |
| `native/digital_zoom.c`、`.h` | 不依赖厂商库的 C99 几何核心，供以后合法适配器复用。 |
| `ui/qml/ZoomRail.qml` | 默认关闭的通用纵向缩放控件，只发出 `zoomRequested` 信号。 |
| `find_crop_strings.py` | 对操作者自备提取目录做有界、只读的 ASCII 名称扫描。 |
| `readiness-manifest.json` | 后端、签名、普通更新器与恢复门禁的当前状态。 |
| `tools/check_readiness.py` | 校验门禁；`--require-installable` 在条件未满足时失败。 |
| `research/CROP.md` | 原厂照片比例、放大查看与数字裁切的静态证据边界。 |
| `research/CFEXPRESS-PHOCUS-GATE.md` | 普通 CFexpress／Phocus 更新路径为何尚不能安装本候选。 |
| `CodeTests/offline-contract/` | 合成输入、C/Python 一致性和安全默认值检查。 |

## 后端契约

`CropWindowSink` 不是相机实现。实际适配器必须先声明精确的目标机型、固件版本、坐标空间、四项对齐、预览影响、保存照片影响和可逆性；任一门禁不匹配时 `ZoomSession` 只返回规划窗口，状态为 `backend-unavailable`，不会调用后端。进入 Review、Menu 或 Playback 会释放已应用窗口；返回 Shooting 才重新应用。应用异常会尝试释放并进入 `faulted`，关闭会幂等释放。

1.0× 使用原厂照片比例基准，控制器不会额外应用窗口。`FF eq.` 只是当前基准对角线缩到 35 mm 对角线时的等效停止点，不是新的照片比例。

## 依赖与副作用

- Python 3.9+；几何代码只使用标准库。
- C 一致性检查需要支持 C99 的主机 `cc`，只在临时目录生成动态库。
- QML 源码只导入 `QtQuick 2.12`；尚未绑定 X2D II 厂商模块。
- `find_crop_strings.py` 只读显式路径，不跟随符号链接，不解包固件，不访问设备。
- 所有默认检查都不连接相机、不写固件、不拍摄、不改变系统状态。

## 离线验证

从仓库根目录运行：

```sh
python3 -B -m unittest discover -s x2d2/digital-zoom/CodeTests/offline-contract -p 'test_*.py'
python3 -B x2d2/digital-zoom/tools/check_readiness.py
```

2026-10-16 本地结果：39 项检查通过；包含 5 种照片比例 × 6 个缩放请求的 C/Python 精确窗口对照。原生编译产物位于系统临时目录并在测试结束后删除。`check_readiness.py` 返回有效计划，同时明确显示 `NOT INSTALLABLE`；加上 `--require-installable` 会以非零状态拒绝继续。RAW 影响状态必须是布尔值，但按“元数据后置”的当前范围不作为可安装门禁。

## 状态、限制、恢复与输出

当前状态是“离线开发候选”，不是相机补丁。几何与生命周期错误已经可以在桌面端捕获，QML 只是可复用控件，真实 `CropWindowSink` 仍不存在。普通更新路径及阻塞项见[就绪门禁说明](research/CFEXPRESS-PHOCUS-GATE.md)。

本模块不会修改设备，所以没有需要执行的设备恢复步骤。仓库内不保留编译输出；以后若产生本地结果，应放在模块的 `outputs/`，默认不提交。只有识别并验证预览／拍摄后端、取得厂商授权签名、确认普通更新器接受、并完成冷启动恢复验证后，才可把 `installable` 状态改为真。

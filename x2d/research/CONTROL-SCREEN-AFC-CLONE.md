# X2D 4.2.0 Control Screen AF-C 临时克隆

## 结论

旧实验没有在主对焦菜单新增 AF-C，不是写入失败。原厂 X2D 4.2.0 的
`ControlScreenViewModel.focusModeModel` 只有：

1. `Autofocus` → `E_FocusModes_Afs`
2. `Manual Focus` → `E_FocusModes_Man`

`CameraUI.canChangeAfc` 控制的是 `LiveviewViewModel` 中已经存在的 AF-C 项；把它改为 true
无法给另一份模型创建新对象。X2D II 的对应 Control Screen 模型则明确有 AF-S、AF-C、MF
三个 `FocusModeListItem`，由此确定最小移植对象。

## 客户端 2026-09-24.11 的改动

[`build_x2d_controlscreen_afc_unit.py`](../tools/firmware-analysis/build_x2d_controlscreen_afc_unit.py)
只接受 SHA-256 为
`16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`
的 X2D 4.2.0 `camera-gui`，提取 `ControlScreenViewModel` 编译单元并生成独立克隆：

| 项目 | 原厂 | 临时克隆 |
|---|---:|---:|
| QML unit 大小 | 71108 | 75576 |
| strings | 650 | 651 |
| functions | 204 | 205 |
| objects | 13 | 14 |
| focus items | AF-S、MF | AF-S、AF-C、MF |

新增对象为：

```text
text      = Continuous Autofocus
icon      = image://svg/ic_controlscreen_focus_mode_AF-C
valid     = true
focusMode = E_FocusModes_Afc
```

克隆 SHA-256：
`546755c8c459e4a3d4cc1cf7d677bd521ae62bca9306e18f88bb17c811d00728`

原厂弹窗的 `PopoverFocusMode.qml` 另有一个独立常量
`readonly property int numItems: 2`。只新增模型对象会使第三项越过弹窗右边界，因此
2026-09-24.10 起还生成第二份精确 QML-unit 克隆，只将该常量改为 3；
2026-09-24.11 另加入不写相机的 `persistence-readiness` 审计：

| 项目 | 原厂 | 临时克隆 |
|---|---:|---:|
| unit 大小 | 13552 | 13552 |
| objects | 9 | 9 |
| `numItems` | 2 | 3 |

弹窗克隆 SHA-256：
`0958c3b8b3909228f2fec9e551f8a1fd7f867056810c47b982b1b21fbd830420`

临时 preload SHA-256：
`eec74136121485ee0931c467d197ae12ff1cfeb896800289f4d8d9ecfba95836`

preload 构造器在 QML cache 注册前同时：

1. 核对精确原厂 `ControlScreenViewModel` 指针、AOT 指针、unit 大小与对象数；
2. 核对嵌入克隆的大小、strings/functions/objects 数；
3. 核对原厂 `PopoverFocusMode` 的硬编码 2 项布局以及 3 项布局克隆；
4. 临时将两份 `CachedQmlUnit.qmlData` 分别指向模型克隆和布局克隆；
5. 将 `CameraUI.canChangeAfc` gate 设为 true；
6. 成功后写出 marker `X2D_AFC_PRELOAD_LAYOUT_OK`。

原厂 `/system/bin/camera-gui` 文件不被替换。克隆和指针只属于当前 GUI 进程。

## 运行

```sh
# Run from the repository root.
cd ./x2d/CodeTests/x2d-afc-research

shasum -a 256 x2d_afc_preload_usb.py libx2d_afc_gate.so \
  x2d_controlscreen_afc_unit.bin x2d_popover_focus_3items_unit.bin

python3 -B x2d_afc_preload_usb.py self-test

python3 -B x2d_afc_preload_usb.py \
  --adb-path /opt/homebrew/bin/adb \
  --serial YOUR_SERIAL \
  --timeout-ms 5000 \
  enter-factory-afc-runtime
```

预期终端必须同时出现：

```text
constructor marker: X2D_AFC_PRELOAD_LAYOUT_OK
process gate:       01 00 00 00
ControlScreen model: AF-S + AF-C + MF
Focus popover:      3-item layout
```

2026-09-24 的真机结果已经确认旧版模型克隆能显示并选择 AF-C，选择后机身会实际进入
连续对焦；同时也确认只改模型时第三项会越出弹窗右边界。新版布局克隆用于修正这个独立
的 2 项宽度计算，仍需在真机重新连接后核对三个条目是否等宽、全部位于弹窗内。

## 完整恢复

```sh
python3 -B x2d_afc_preload_usb.py \
  --adb-path /opt/homebrew/bin/adb \
  --serial YOUR_SERIAL \
  --timeout-ms 5000 \
  restore-factory-afc-runtime
```

客户端 2026-09-24.7 起恢复流程会等待 `sys.usb.config` 与 `sys.usb.state` 都实际移除
`adb` 后再重启 GUI，避免旧 USB 接口仍短暂存活时产生的竞态。恢复后应为精确原厂文件、
原厂 13-object unit、gate `00 00 00 00`、`/system` 只读、OSD Clock Off。相机重启也是
最终兜底恢复；该实验不设置开机自动启动。

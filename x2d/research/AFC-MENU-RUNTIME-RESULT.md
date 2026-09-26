# AF-C 菜单运行时写入复核

## 结论

运行时写入没有失败，但最初锁定的布尔量不属于用户打开的 Control Screen 菜单模型。
`/proc/<pid>/mem` 和启动前 preload 都确认 `CameraUI.canChangeAfc` 从
`00 00 00 00` 变为 `01 00 00 00`；菜单仍不变的决定性原因是 X2D 4.2.0 的
`ControlScreenViewModel.focusModeModel` 只有 AF-S 和 MF 两个对象，没有 AF-C 条目。

## 离线结构证据

- `CameraUI.qml` 的编译单元位于
  `_ZN21QmlCacheGeneratedCode29_app_qml_proxies_CameraUI_qml7qmlDataE`。
- `CameraUI.canChangeAfc` 的 Boolean 绑定在文件偏移 `0x018A2A64`，stock 值为
  `false`，补丁值为 `true`。
- `LiveviewViewModel.qml` 中已有 AF-C `FocusModeListItem`，其 `valid` 函数读取
  `CameraUI.canChangeAfc`；该 gate 对这套 Live View 模型有效。
- `ControlScreenViewModel.qml` 的 `focusModeModel` 只有 `Autofocus/AF-S` 与
  `Manual Focus/MF`，并未引用 `CameraUI.canChangeAfc`。
- X2D II 的对应模型有第三个 `Continuous Autofocus/AF-C` 对象，确认“新增对象”才是
  Control Screen 的正确移植粒度。
- 本地 QML 解析结果：stock 为 `value=false`，补丁副本为 `value=true`。

## 真机输出如何解释

`enable-afc-menu-runtime` 显示 `before: 00 00 00 00`、写入后
`after: 01 00 00 00`，证明进程内的一字节写入成功。

`enable-afc-menu-restart-runtime` 只能在新进程已经 `exec` 后才拿到 PID；即使随后
发送 `SIGSTOP`，QML 初始化可能已经开始。因此它不能保证“QML 启动前”完成写入。

`restore-afc-menu-restart-runtime` 先启动了一个全新的 stock `camera-gui`。这个进程
从未修改的系统文件加载，读到 `before: 00 00 00 00` 是预期结果；由于目标本来就是
stock 值，命令不会再写入任何字节。这不是对之前写入失败的证明。

## 修正后的临时方案

`2026-09-24.8` preload 内嵌一份从精确原厂单元生成并再次解析验证的克隆；在 QML cache
注册前只改 `CachedQmlUnit.qmlData` 指针。克隆由 13 个对象扩展为 14 个，焦点列表顺序为
AF-S、AF-C、MF；原厂 `/system/bin/camera-gui` 的内容和哈希不变。进程退出或相机重启后
指针与克隆一并消失，恢复命令还会删除精确哈希匹配的临时库并将 `/system` 重挂只读。

这仍是验证性运行时方案，不是可刷写固件。在没有完成 OTA/AVB 与断电回滚验证前，不把
它转成持久化 `/system/bin/camera-gui` 替换或自制 CIM。

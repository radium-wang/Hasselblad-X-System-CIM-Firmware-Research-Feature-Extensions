# X2D 100C 4.2.0：镜头对焦速度参数静态核对

## 结论

其他平台截图中的数值不能直接当作 X2D 的机身参数。X2D 4.2.0 的旧 AF 栈确实有对应的
“still/video、fast/slow”速度路径，但速度主要从当前连接的镜头控制数据中选择，
不是 `/etc/lens_config.json` 里的一个机身全局表。

因此本次没有把 `10000`、`20000` 或 X2D II 的配置写入相机，也没有制作可刷写的 CIM。

## 在 X2D `libaaa.so` 中找到的对应入口

文件：`work/firmware-analysis/x2d-system-root/lib64/libaaa.so`

导出符号包括：

| 入口 | 地址 | 作用 |
| --- | ---: | --- |
| `lens_ctrl_get_still_fast_scan_speed` | `0x00aaff0` | 静态拍摄高速扫描值 |
| `lens_ctrl_get_still_slow_scan_speed` | `0x00ab4d8` | 静态拍摄低速扫描值 |
| `lens_ctrl_get_video_fast_scan_speed` | `0x00abe98` | 视频高速扫描值 |
| `lens_ctrl_get_video_slow_scan_speed` | `0x00ab9c0` | 视频低速扫描值 |
| `lens_ctrl_get_focus_speed` | `0x00ac380` | 按速度类型选择最终值 |

`lens_ctrl_get_still_fast_scan_speed` 和 `lens_ctrl_get_still_slow_scan_speed` 都会先
调用 `af_get_lens_ctrl_param()`，按当前镜头的 lens id / per-frame 数据找到对应记录，
再读取记录中的 16 位速度字段。`lens_ctrl_get_focus_speed()` 根据速度类型在这些
still/video、fast/slow 入口之间选择，并在部分路径乘以镜头的比例因子。

同一库的日志字符串还明确包含：

```text
l_min_focus_speed
l_max_focus_speed
l_fast_scan_speed
lens video focus fast_speed=%d, slow_speed=%d
lens still focus fast_speed=%d, slow_speed=%d
```

这与截图中的“按镜头列出高速/低速目标值”概念相似，但数值来源和单位仍需从实际
镜头运行时数据确认。

## X2D 原生的临时覆盖入口

`af_debug_func` 的命令表中，命令 11 的调用序列是：

```text
参数 +4 -> af_set_debug_scan_speed_flag()
参数 +8 -> af_set_debug_scan_speed()
```

库内帮助文本为：

```text
debug scan speed: cmd_id(11), enable, speed
```

对应的调试命令格式是：

```text
rcam:af:debug:11:1:SPEED   # 临时启用
rcam:af:debug:11:0:0       # 关闭并恢复算法值
```

反汇编显示 setter 只是把值写入进程内的 AF debug 状态（速度字段偏移 `0x1c`，开关
偏移 `0x06`），没有看到可靠的上限校验。因此它适合做可回滚的运行时实验，不适合
把未经本机测量的跨平台数值写成永久机身参数。

## 与 X2D II 配置的区别

X2D II 的 `etc/aaa/af/af_imx861.json` 有 `AF_AFC_ENABLE`、
`still_fast_scan_speed_list`、`still_slow_scan_speed_list` 等新 ABI 配置。X2D 4.2.0
没有对应的外部 AF JSON 表，且两代机器的传感器、测距硬件和 AF ABI 不同；不能把
X2D II 的列表或 `scan_speed_boost` 直接复制到 X2D。

X2D 的 `/etc/lens_config.json` 只包含焦距、光圈、镜头名称等元数据，没有截图那样的
对焦扫描速度列表。

## 下一步（只读优先）

1. 安装待测试的 XCD 镜头，重启相机并进入实时取景。
2. 通过已授权的 USB ADB 或工厂 Wi-Fi 运行：

   ```bash
   python3 collect_x2d_af_wifi.py lens-diagnostics \
     --output x2d-lens-diagnostics.md
   ```

3. 报告中应取得 `l_min_focus_speed`、`l_max_focus_speed`、still/video 的 fast/slow
   值。只有拿到当前镜头的真实上限后，才考虑以小步长（约 5%）启用命令 11，并在每
   轮结束后立即发送关闭命令。

直接工厂 USB 目前只验证了参数 27/28（机身报告 `v4.2.0` 和运行标志），这条通道
本身尚未证明可以承载 RCam 命令 11；它不能代替 USB ADB 或 Wi-Fi 工厂 shell。

另外，`phocus` 的 `ReadParameter::getValue()` 和 `updateFocusModeChanged()` 已把
参数 ID `2` 对应到对焦模式，转换值为 `0=MF`、`1=AF-S`、`2=AF-C`、`3=AFT`。本地
USB 工具现在提供 `read-focus-mode`，仍然是单次只读请求；它不会写入 `2`，也不会
因此让菜单出现 AF-C。

## 直接工厂 USB 的受限对焦模式实验

静态核对 `phocus` 的 `WriteParameter::OnPhocusMessage()` 后，确认写入载荷是两字节小端
参数 ID 加上 `sCameraParameter` 文本标量；参数 2 的 AF-C 请求使用 `i2`，消息类型为
`0x03`。工具只开放 AF-C 写入和 AF-S 回滚，并在写入后用参数 2 的新序号读回：

```bash
python3 collect_x2d_af_usb.py set-afc-runtime
python3 collect_x2d_af_usb.py restore-afs-runtime
```

不测试 AFT，也没有开放其他写参数。这不是持久化机身参数修改。若读回不是
`E_FocusModes_Afc(2)`，应视为实验失败，不要重复发送；相机重启或执行
`restore-afs-runtime` 可恢复 AF-S。

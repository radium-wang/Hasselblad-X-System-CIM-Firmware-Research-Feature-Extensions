# Doom on Hasselblad X2D 100C

第一代 **X2D 100C、固件 4.2.0 / build 24849** 的临时 Doom 实验。此前实机用户确认：游戏画面可见、全按快门开火、扬声器有音效、左右滑动转向。静音版的 EXIT 返回及原厂恢复已读回；有声版退出后的音频关闭与完整恢复尚未读回验收。整理后的公开运行器仅完成离线验证，不能把旧版本实机反馈当作公开版本重新实测。

这是源码研究模块，使用 doomgeneric 的真实 Doom 引擎。游戏数据由使用者另行提供。没有背景音乐；经典 Doom 只支持左右转向，不支持上下自由视角。未验证 X2D II、其他固件、冷启动安装、长时间稳定性、功耗或相机显示 FPS。没有持久安装入口。详细证据见[研究报告](../research/4.2.0/DOOM-FEASIBILITY.md)。

## 操作

| 输入 | 行为 |
| --- | --- |
| 全按快门 | FIRE；按住持续开火，受游戏武器射速约束 |
| 半按快门 | 不开火 |
| 游戏画面左右滑动 | 转动视角；可与另一根手指的移动同时使用 |
| 屏幕箭头 | 前进、后退、左右转向；配合 STRAFE 横移 |
| FIRE / USE / RUN | 开火、使用、跑动 |
| ENTER / MENU | 确认、游戏菜单 |
| 右上角 EXIT | 请求结束，监护脚本恢复原厂 GUI 与 USB |

全按快门必须等页面获得焦点且读回 `forward_input_events == 3` 才生效。快速按下/松开通过计数器保留最短开火脉冲，系统按键自动重复不生成额外按下事件。退出或丢失焦点会释放输入，心跳丢失时引擎也会清除按键。

## 文件地图

| 目录 / 文件 | 职责 |
| --- | --- |
| `native/doomgeneric_x2d_file.c` | BMP 帧、文件输入桥、鼠标转向事件、计时和退出 |
| `native/doom_sound.c`、`audio_ring.h` | WAD DMX 音效、16 声道混音、48 kHz 双声道共享环 |
| `native/audio_bridge.c` | 对接原厂 `libaudioclient.so` 的扬声器流 |
| `ui/` | 游戏界面、相机按键接管、主菜单 Loader 装配 |
| `tools/build.py`、`build_audio.py` | 固定上游引擎与音频桥离线构建 |
| `tools/audit_platform.py`、`audit_shutter.py` | 固件哈希、符号、指令及按键路由离线检查 |
| `tools/build_loader.py`、`prepare_trial.py` | 本地生成菜单单元与短时实验包 |
| `tools/device_trial.py`、`trial_usb.py` | 默认只输出计划；显式 `--apply` 才访问相机 |
| `CodeTests/` | 真实桌面 Doom + Qt 测试、相机服务替身、PCM 消费器、合成 USB 测试 |

上游引擎、WAD、Qt、原厂固件和共享库均不随本仓库分发。源码不依赖私人仓库或个人目录。所有生成物放到仓库外的专用工作目录；不要提交载荷、固件或设备日志。

## 依赖与固定输入

- Python 3.9–3.11；Qt 测试使用 PySide6 Essentials / Qt **6.4.1**。macOS ARM 若该旧版本没有原生 wheel，可使用 Rosetta 的 x86_64 Python 3.11；本次 Qt 检查采用此环境。
- Git、Clang；ARM64 构建使用 [Zig 0.13.0](https://ziglang.org/download/0.13.0/)。构建器不会自动下载依赖。
- [ozkl/doomgeneric](https://github.com/ozkl/doomgeneric/tree/dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284)：提交 `dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284`，要求未修改工作树。
- 演示与测试采用 [Freedoom 0.13.0](https://github.com/freedoom/freedoom/releases/tag/v0.13.0) Phase 1 的 `freedoom1.wad`。SHA-256：`7323bcc168c5a45ff10749b339960e98314740a734c30d4b9f3337001f9e703d`。商业 Doom 的 WAD 不随源码提供。
- 音频桥与菜单包需要使用者有权使用的 X2D 4.2.0 system 提取目录。工具会校验原厂文件，不改输入。
- 只有实机步骤需要 Android `adb`、PyUSB 和系统 libusb。libusb 在 macOS / Linux 的安装方式及 USB 访问权限由使用者环境决定；Windows 传输未验证。

从仓库根目录执行，以下变量在同一 shell 会话保留。先建立专用工作目录：

```sh
MODULE=x2d/doom
DOOM_WORK=$(mktemp -d)
python3 -m venv "$DOOM_WORK/venv"
PY="$DOOM_WORK/venv/bin/python"
"$PY" -m pip install -r "$MODULE/requirements.txt"
"$PY" -m pip install -r "$MODULE/requirements-qt.txt"

git clone https://github.com/ozkl/doomgeneric.git "$DOOM_WORK/upstream"
git -C "$DOOM_WORK/upstream" checkout dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284
```

可从上面的 Freedoom 官方 release 自行获取素材，或使用下面的固定下载并校验压缩包和 WAD：

```sh
curl -fL https://github.com/freedoom/freedoom/releases/download/v0.13.0/freedoom-0.13.0.zip -o "$DOOM_WORK/freedoom.zip"
"$PY" - "$DOOM_WORK" <<'PY'
import hashlib, sys, zipfile
from pathlib import Path
work = Path(sys.argv[1])
assert hashlib.sha256((work/'freedoom.zip').read_bytes()).hexdigest() == '3f9b264f3e3ce503b4fb7f6bdcb1f419d93c7b546f4df3e874dd878db9688f59'
with zipfile.ZipFile(work/'freedoom.zip') as archive:
    wad = archive.read('freedoom-0.13.0/freedoom1.wad')
assert hashlib.sha256(wad).hexdigest() == '7323bcc168c5a45ff10749b339960e98314740a734c30d4b9f3337001f9e703d'
(work/'freedoom1.wad').write_bytes(wad)
PY
```

保留上游 ZIP 内的 `COPYING.txt` 和 `CREDITS`；若另行分发素材，保留其许可和署名。该旧引擎可能提示 Freedoom 兼容性警告，目前只验收 E1M1 的有限操作，没有全流程通关结论。

## 纯离线构建与测试

以下命令不连接相机，桌面音频消费器只捕获 PCM，不播放扬声器：

```sh
"$PY" -B -m unittest discover -s "$MODULE/CodeTests" -p test_trial_usb.py
"$PY" -B "$MODULE/tools/build.py" --upstream "$DOOM_WORK/upstream" --out "$DOOM_WORK/host"
clang -O2 "$MODULE/CodeTests/check_audio_sink.c" -o "$DOOM_WORK/audio-sink"
"$PY" -B "$MODULE/CodeTests/check_host.py" \
  --engine "$DOOM_WORK/host/doom-host" --wad "$DOOM_WORK/freedoom1.wad" \
  --audio-sink "$DOOM_WORK/audio-sink" --out "$DOOM_WORK/host-checks"
"$PY" -B "$MODULE/CodeTests/check_camera_page.py" --out "$DOOM_WORK/camera-mocks"
```

`check_host.py` 使用真实引擎和 Qt 事件，核对弹药减少、半按无效、快速快门、滑动改变玩家角度、双指并发、输入心跳及 EXIT；输出 `checks.json`、截图和 PCM。每次使用新的检查目录，避免旧输入/退出标记影响游戏。相机服务替身检查不证明实际相机完成了按键接管。

设置使用者自己的 Zig 和固件输入路径，再构建机内组件并生成本地包：

```sh
ZIG=/path/to/zig-0.13.0/zig
SYSTEM=/path/to/x2d-4.2.0-system-root
"$PY" -B "$MODULE/tools/audit_platform.py" --system "$SYSTEM" --out "$DOOM_WORK/platform.json"
"$PY" -B "$MODULE/tools/audit_shutter.py" --system "$SYSTEM" --out "$DOOM_WORK/shutter.json"
"$PY" -B "$MODULE/tools/build.py" --upstream "$DOOM_WORK/upstream" \
  --arm64 --zig "$ZIG" --out "$DOOM_WORK/arm64"
"$PY" -B "$MODULE/tools/build_audio.py" --system "$SYSTEM" --zig "$ZIG" --out "$DOOM_WORK/audio"
"$PY" -B "$MODULE/tools/prepare_trial.py" --system "$SYSTEM" \
  --engine "$DOOM_WORK/arm64/doom-x2d-arm64" --wad "$DOOM_WORK/freedoom1.wad" \
  --audio-bridge "$DOOM_WORK/audio/libdoom_audio.so" \
  --host-checks "$DOOM_WORK/host-checks/checks.json" --seconds 120 --out "$DOOM_WORK/payload"
"$PY" -B "$MODULE/tools/device_trial.py" launch \
  --payload "$DOOM_WORK/payload" --out "$DOOM_WORK/device"
```

最后一条默认只输出计划，`deviceAccess` 为 `false`。打包器检查桌面验收、当前源码和 WAD 哈希；ARM64 引擎为静态 musl，无动态解释器或可写可执行段。音频桥为独立 AArch64 共享库，仅链接使用者提供的精确原厂音频/系统库。打包器本地生成的菜单单元包含原厂字节，不能随开源源码再分发。

`audit_shutter.py` 默认仅静态校验。可选 `--emulate` 还需 Unicorn；本次 macOS ARM 环境的原生 Unicorn 初始化会 SIGILL，因此没有把该模拟列为通过项目。不要用 Python `-O` 跳过本模块的验收断言。

## 显式实机步骤与恢复

先阅读[仓库研究免责声明](../../DISCLAIMER.md)。只有对本人拥有或获授权的精确版本相机，且接受短时 GUI 重启与数据暂存时，才执行带 `--apply` 的命令。普通 USB 模式必须已经暴露接口 3，电脑只能连接一台匹配设备。运行器不会切换 USB configuration 或拆卸内核驱动来获取接口；无法 claim 时会停止。

先让相机回原厂取景界面、无拍摄进行，连接 USB 数据线并开机，`adb` 在 PATH 中。也可传入显式 `--adb /path/to/adb`。

```sh
"$PY" -B "$MODULE/tools/device_trial.py" launch --apply \
  --payload "$DOOM_WORK/payload" --out "$DOOM_WORK/device"
```

等待运行器报告 `readyForMenu`，再打开相机主菜单进入游戏。到期 30–180 秒（打包时配置，默认 120 秒）或点 EXIT 后，监护脚本请求恢复。计时从监护启动开始，包含准备时间，实际游玩会短于配置值。

状态与提前恢复使用同一个本地包：

```sh
"$PY" -B "$MODULE/tools/device_trial.py" status --apply \
  --payload "$DOOM_WORK/payload" --out "$DOOM_WORK/device"
"$PY" -B "$MODULE/tools/device_trial.py" restore --apply \
  --payload "$DOOM_WORK/payload" --out "$DOOM_WORK/device"
```

运行器首先核对机型/build、GUI/service/init 与音频库哈希、原厂 GUI、曝光空闲、路由为 0、USB 模式和空间。随后临时开启 ADB，将引擎和 WAD 放在 `/blackbox/.x2d-doom-trial-stage`，并挂载两个专用 RAM 文件系统。QML/BMP/输入/音频环走 RAM；启动原厂 GUI 后只替换该进程 RAM 内经哈希核对的 MainScreen 单元。扬声器桥使用原厂音频服务，流音量 80，不修改全局设备音量。

它会重启 GUI、临时改变 USB 功能、写入数据暂存目录和挂载 RAM；不写 `/system`、启动配置或固件分区，也不修改相机服务指令或 SELinux 策略。原厂 GUI 停止前检查监护、引擎和音频 PID 存活及退出标记。监护在独立服务域运行，退出、进程死亡或到期后释放路由、停止带本试验环境标记的进程、启动原厂 GUI、卸载 RAM、删除数据暂存并恢复原 USB。卸载失败会保留目录，不递归删除仍挂载的 RAM。`/tmp/x2d-doom-trial` 内可能保留本次日志，重启或下一次同所有者的空闲实验才清理。

恢复代码和准备门禁已经离线检查；有声版恢复尚缺实际关闭流、GUI/USB/路由/挂载清理的读回。应以 `restore` 输出与原厂界面确认结果；通信中断、进程竞态及异常断电的恢复不能视为保证。不要边拍摄边试验，也不要在版本校验失败后改掉哈希继续运行。输出设备日志仅留本地。

## 许可

本模块新增源码、界面、工具、测试和 README 使用 **GPL-2.0-or-later**，见 [LICENSE](LICENSE)。仓库根 MIT 不适用于此模块。没有将 doomgeneric 上游源码复制进仓库；构建产生的引擎包含其源码及原始版权声明，若自行分发构建结果，应按上游 GPL 提供对应源码与完整声明。

doomgeneric 来自 ozkl，核心源文件保留 Id Software、Simon Howard 等贡献者声明；Freedoom 0.13.0 的素材使用其三条款 BSD 许可，独立于引擎 GPL。Qt / PySide6 和原厂库也独立授权，没有随本源码分发。固定依赖和来源另见[第三方声明](../../THIRD_PARTY_NOTICES.md)。

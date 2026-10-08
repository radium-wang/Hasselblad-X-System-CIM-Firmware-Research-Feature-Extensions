# Doom on Hasselblad X2D 100C

第一代 **X2D 100C、固件 4.2.0 / build 24849** 的临时 Doom 实验。此前实机用户确认：游戏画面可见、全按快门开火、扬声器有音效、左右滑动转向。静音版的 EXIT 返回及原厂恢复已读回；有声版退出后的音频关闭与完整恢复尚未读回验收。公开源码仅完成离线验证，不能把旧版本实机反馈当作公开版本重新实测。

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
| 右上角 EXIT | 请求结束，释放界面输入 |

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
| `CodeTests/` | 真实桌面 Doom + Qt 测试、相机服务替身、PCM 消费器、合成 USB 测试 |

上游引擎、WAD、Qt、原厂固件和共享库均不随本仓库分发。源码不依赖私人仓库或个人目录。所有生成物放到仓库外的专用工作目录；不要提交载荷、固件或设备日志。

## 依赖与固定输入

- Python 3.9–3.11；Qt 测试使用 PySide6 Essentials / Qt **6.4.1**。macOS ARM 若该旧版本没有原生 wheel，可使用 Rosetta 的 x86_64 Python 3.11；本次 Qt 检查采用此环境。
- Git、Clang；ARM64 构建使用 [Zig 0.13.0](https://ziglang.org/download/0.13.0/)。构建器不会自动下载依赖。
- [ozkl/doomgeneric](https://github.com/ozkl/doomgeneric/tree/dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284)：提交 `dcb7a8dbc7a16ce3dda29382ac9aae9d77d21284`，要求未修改工作树。
- 演示与测试采用 [Freedoom 0.13.0](https://github.com/freedoom/freedoom/releases/tag/v0.13.0) Phase 1 的 `freedoom1.wad`。SHA-256：`7323bcc168c5a45ff10749b339960e98314740a734c30d4b9f3337001f9e703d`。商业 Doom 的 WAD 不随源码提供。
- 音频桥与菜单包需要使用者有权使用的 X2D 4.2.0 system 提取目录。工具会校验原厂文件，不改输入。

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
"$PY" -B "$MODULE/tools/build.py" --upstream "$DOOM_WORK/upstream" --out "$DOOM_WORK/host"
clang -O2 "$MODULE/CodeTests/check_audio_sink.c" -o "$DOOM_WORK/audio-sink"
"$PY" -B "$MODULE/CodeTests/check_host.py" \
  --engine "$DOOM_WORK/host/doom-host" --wad "$DOOM_WORK/freedoom1.wad" \
  --audio-sink "$DOOM_WORK/audio-sink" --out "$DOOM_WORK/host-checks"
"$PY" -B "$MODULE/CodeTests/check_camera_page.py" --out "$DOOM_WORK/camera-mocks"
```

检查真实引擎与 Qt 输入、弹药、快门、滑动、并发输入、心跳及 EXIT。相机服务替身只验证界面路由，不能证明真实设备完成按键接管。机内音频符号和固件平台检查使用使用者提供的只读固件输入；公开模块不包含设备传输、部署或恢复步骤。

## 许可

本模块新增源码、界面、工具、测试和 README 使用 **GPL-2.0-or-later**，见 [LICENSE](LICENSE)。仓库根 MIT 不适用于此模块。没有将 doomgeneric 上游源码复制进仓库；构建产生的引擎包含其源码及原始版权声明，若自行分发构建结果，应按上游 GPL 提供对应源码与完整声明。

doomgeneric 来自 ozkl，核心源文件保留 Id Software、Simon Howard 等贡献者声明；Freedoom 0.13.0 的素材使用其三条款 BSD 许可，独立于引擎 GPL。Qt / PySide6 和原厂库也独立授权，没有随本源码分发。固定依赖和来源另见[第三方声明](../../THIRD_PARTY_NOTICES.md)。

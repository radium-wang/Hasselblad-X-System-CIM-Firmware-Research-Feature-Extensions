# Reproduce the Offline Research / 离线研究复现

Read [DISCLAIMER.md](DISCLAIMER.md) first. The public tree supplies offline analysis, interface source and desktop tests. Camera configuration writers, device deployment/recovery commands and diagnostic-channel instructions are excluded. Historical device observations remain evidence summaries rather than executable procedures.

## Run repository-contained checks

Use Python 3.9 or later from the repository root:

```sh
python3 -m pip install -r x2d/CodeTests/temporary_af_speed_probe/standalone_handoff/requirements.txt
python3 -B scripts/reproduce_offline.py
```

The runner checks publication boundaries, the menu Loader source/icon, AF-S candidates, object-recognition contracts, shutter timing and synthetic UI traces. It does not connect to a camera. Optional Qt/native desktop checks are documented in the [Doom](x2d/doom/README.md) and [Shimeji](x2d/shimeji-overlay/README.md) modules.

For tests using operator-supplied firmware extraction roots, provide all four read-only directories:

```sh
python3 -B scripts/reproduce_offline.py \
  --source-system-root /path/to/x2d2-system-root \
  --source-vendor-root /path/to/x2d2-vendor-root \
  --target-system-root /path/to/x2d-system-root \
  --target-vendor-root /path/to/x2d-vendor-root
```

The directories are read-only inputs and are never copied into this repository. They must come from firmware the operator is authorized to use. Vendor firmware, libraries, models and generated compilation units are not distributed.

## Research entry points

| Area | Entry | Reproduction scope |
| --- | --- | --- |
| Menu | [source and tests](x2d/CodeTests/temporary_af_speed_probe/original-menu-candidate/README.md) | Source QML, SVG and desktop checks |
| AF-S | [candidate](x2d/CodeTests/temporary_af_speed_probe/pdaf-scan-type1-candidate/README.md) | Exact-version offline hash gates and byte-diff checks |
| AF-C | [research](x2d/CodeTests/x2d-afc-research/README.md) | Offline model/layout and gate analysis |
| Recognition | [contracts and audit](x2d/object-recognition/README.md) | Firmware compatibility and synthetic frame contracts |
| Doom | [module](x2d/doom/README.md) | Engine/audio builds and desktop input checks |
| Shimeji | [module](x2d/shimeji-overlay/README.md) | Native desktop engine, transparent QML and synthetic traces |
| Shutter | [preview](x2d/CodeTests/shutter-animation-preview/README.md) | Browser/QML preview and timing analysis |

## 中文说明

本公开树只提供离线分析、界面源码和桌面检查，不包含相机配置写入、设备部署／恢复命令或调试通道操作步骤。历史实机报告保留其机型、固件及验证限制，不能视作可执行的部署说明。

在仓库根目录运行上面的离线套件。默认不提供固件输入时，依赖外部输入的用例会跳过；需要时显式指定四个只读固件目录。Qt／原生桌面检查按对应模块说明执行，不自动下载依赖。

离线候选、能够显示的菜单或接口契约通过，不代表相机性能、稳定性或跨机型兼容性已通过验收。

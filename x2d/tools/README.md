> 迁移的历史研究记录：原文描述的是当时的实验，不代表本次重新验证。外部依赖及本轮验证范围见仓库根目录 MIGRATION_DEPENDENCIES.md。

# X2D 离线分析脚本位置

主屏开机图提取：[extract_main_startup_logo.py](firmware-analysis/extract_main_startup_logo.py)。从仓库根目录运行 `python3 x2d/tools/firmware-analysis/extract_main_startup_logo.py <原厂-eagle-backend.so> <本地输出目录>`；输入必须与 X2D 100C 4.2.0 固定哈希相符。脚本只读本地 ELF，输出标准版和 Earth Explorer 版原图 PNG，不生成刷机包或连接设备。原厂 ELF 与输出图均不随仓库提供。

主屏开机图离线替换：[replace_main_startup_logo.py](firmware-analysis/replace_main_startup_logo.py)。从仓库根目录运行 `python3 x2d/tools/firmware-analysis/replace_main_startup_logo.py <原厂-eagle-backend.so> <162x128目标PNG> <本地候选.so.NOT_FOR_DEVICE> --preview <预览PNG>`；若输入 RGB 含少量彩色像素，须显式加 `--convert-to-gray`。工具校验原厂 ELF 哈希，只改标准版 Logo 的 20,736 个索引字节范围，预览按原厂 17 级灰度表量化；不改引导程序、exMCU 或相机，也不生成签名升级包。输出只供离线分析。

页面研究脚本：inspect_gui_entry_4_2_0.py（外部输入或历史产物，未随迁移提供）。运行 `py -3.11 -B x2d/tools/inspect_gui_entry_4_2_0.py`，只读固定固件并向 stdout 输出 JSON，复核 QRC 页面、Wayland 启动和窗口分类/焦点指令；不启动 GUI 或连接设备。结果见 gui-entry-checks.json（外部输入或历史产物，未随迁移提供）。

当前脚本：inspect_counter_entry_4_2_0.py（外部输入或历史产物，未随迁移提供），复核官方 X2D 4.2.0 的镜头通道、文件传输及程序执行代码。运行 `py -3.11 -B x2d/tools/inspect_counter_entry_4_2_0.py`，只读本地固定固件，向 stdout 输出 JSON；不打开相机、不执行固件、不产生设备请求。结果见 counter-entry-checks.json（外部输入或历史产物，未随迁移提供）。

后续 X2D 专属分析脚本放在本目录，并明确绑定固件版本及输入哈希。本次未迁移共享 Python 工具：根目录 `tools/` 的脚本被既有客户端工作流、测试和其他分析脚本引用，部分固定从根目录 `.research-cache/` 读取并向 `research/` 输出。

共享工具与依赖详见 共享项索引（外部输入或历史产物，未随迁移提供）。本轮已保存的纯内存回读模拟位于 [CodeTests](../CodeTests/README.md)，不具备设备传输能力。不要为整理目录启动旧脚本中的下载、构建或硬件入口。

UI 轨迹摘要：[analyze_ui_trace.py](analyze_ui_trace.py)。只读显式保存的 getevent/proc/GPU/Weston 文本，输出聚合 JSON；USER_HZ 必须显式提供才计算单核百分比，不把帧率当延迟。见[测试说明](../CodeTests/ui-response/README.md)。

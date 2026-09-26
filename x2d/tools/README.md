> 迁移的历史研究记录：原文描述的是当时的实验，不代表本次重新验证。外部依赖及本轮验证范围见仓库根目录 MIGRATION_DEPENDENCIES.md。

# X2D 离线分析脚本位置

USB 页面脚本：[inspect_usb_ui_4_2_0.py](inspect_usb_ui_4_2_0.py)。运行 `py -3.11 -B x2d/tools/inspect_usb_ui_4_2_0.py`，复核 USB 测试消息到终端输入、原厂确认页/图片页、ABI 与显示基础；只读本地固件、向 stdout 输出 JSON，不构造设备请求。结果见 usb-ui-checks.json（外部输入或历史产物，未随迁移提供）。

页面研究脚本：inspect_gui_entry_4_2_0.py（外部输入或历史产物，未随迁移提供）。运行 `py -3.11 -B x2d/tools/inspect_gui_entry_4_2_0.py`，只读固定固件并向 stdout 输出 JSON，复核 QRC 页面、Wayland 启动和窗口分类/焦点指令；不启动 GUI 或连接设备。结果见 gui-entry-checks.json（外部输入或历史产物，未随迁移提供）。

当前脚本：inspect_counter_entry_4_2_0.py（外部输入或历史产物，未随迁移提供），复核官方 X2D 4.2.0 的镜头通道、文件传输及程序执行代码。运行 `py -3.11 -B x2d/tools/inspect_counter_entry_4_2_0.py`，只读本地固定固件，向 stdout 输出 JSON；不打开相机、不执行固件、不产生设备请求。结果见 counter-entry-checks.json（外部输入或历史产物，未随迁移提供）。

后续 X2D 专属分析脚本放在本目录，并明确绑定固件版本及输入哈希。本次未迁移共享 Python 工具：根目录 `tools/` 的脚本被既有客户端工作流、测试和其他分析脚本引用，部分固定从根目录 `.research-cache/` 读取并向 `research/` 输出。

共享工具与依赖详见 共享项索引（外部输入或历史产物，未随迁移提供）。本轮已保存的纯内存回读模拟位于 [CodeTests](../CodeTests/README.md)，不具备设备传输能力。不要为整理目录启动旧脚本中的下载、构建或硬件入口。

# 透明覆盖层离线检查

从仓库根目录执行 `python3 x2d/shimeji-overlay/CodeTests/overlay/check_overlay.py`。依赖 Python 3.9–3.11、PySide6 Essentials 6.4.1。脚本设 offscreen 和自身 QML 文件 XHR 开关，在临时目录生成不对称白色块与透明边缘 PNG、状态 JSON 和行区间掩码，结束后删除临时目录。

断言背景点击、透明边缘点击、镜像后透明像素点击均到达底层；拖动事件直接改变角色视觉坐标；松手保持该位置直到引擎序号确认；抓取自有覆盖层检查背景 alpha=0；Exit 发出标记并保留宿主窗口；退出后底层继续可点，且没有自动截图文件。

本次公开版检查通过。它使用模拟状态，不代表原厂相机窗口注入或真实触摸面板验收。原生引擎须另外构建并执行[模块自测](../../README.md)；完整桌面演示由 run_desktop 管理原生进程。

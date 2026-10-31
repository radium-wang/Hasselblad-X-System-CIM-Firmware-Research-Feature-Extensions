# X2D II 固件研究与功能实现

静态对照研究基线为1.3.16.2；八向摇杆模块适用于1.3.18.1，已完成一次45秒实体测试。各主题分别标注版本、证据和限制。

- [八向摇杆：实现、离线测试与实机验收](joystick-eight-way/README.md) — 四斜向、长按与松手已确认；未常驻安装。

- [模型解密状态与 PDAF 对照边界](research/1.3.16.2/MODEL-AND-PDAF-STATUS.md)
- [LiDAR 数据链与 AF-S / AF-C 对照](research/1.3.16.2/LIDAR-PIPELINE.md)
- [AF-S 与 LiDAR 遮挡路径](research/1.3.16.2/AFS-WITHOUT-LIDAR.md)
- [产品变体与启动资源](research/1.3.16.2/STARTUP-LOGO-VARIANTS.md)
- [显示链与低灰 mura](research/1.3.16.2/DISPLAY-MURA.md)
- [IBIS、经纬度与地球自转](research/1.3.16.2/IBIS-GPS-EARTH-ROTATION.md)

二代离线工具集中在 [`x2d2/tools/`](tools/)；分析产物集中在 [`x2d2/outputs/`](outputs/)，包括选定函数反汇编、JSON 审计、启动 Logo 预览和 AF-S / AF-C 图标资源。工具只读取用户自行准备且与哈希匹配的原厂输入，不加载固件、不连接设备、不提供安装或写入路径。

八向摇杆源码和专用测试归入独立的 [`joystick-eight-way/`](joystick-eight-way/README.md)；其公开检查入口只运行宿主替身，不访问设备。实际输入适配代码、依赖及既有验收边界在模块内说明。

机型与地址独立归档；一代模型解密、CPU 合成输入推理或采集试验不视为二代验收。原厂固件、配置、加密模型、安全组件与原始设备记录未随库提供。

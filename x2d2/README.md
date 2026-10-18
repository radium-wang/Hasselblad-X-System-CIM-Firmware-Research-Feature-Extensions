# X2D II 离线对照研究

固件基线：1.3.16.2。研究内容以静态分析、离线验证与数字裁切开发候选为主，没有本轮二代设备实测，也没有可安装的一代功能移植。

- [模型解密状态与 PDAF 对照边界](research/1.3.16.2/MODEL-AND-PDAF-STATUS.md)
- [LiDAR 数据链与 AF-S / AF-C 对照](research/1.3.16.2/LIDAR-PIPELINE.md)
- [AF-S 与 LiDAR 遮挡路径](research/1.3.16.2/AFS-WITHOUT-LIDAR.md)
- [产品变体与启动资源](research/1.3.16.2/STARTUP-LOGO-VARIANTS.md)
- [显示链与低灰 mura](research/1.3.16.2/DISPLAY-MURA.md)
- [IBIS、经纬度与地球自转](research/1.3.16.2/IBIS-GPS-EARTH-ROTATION.md)
- [数字裁切离线开发候选](digital-zoom/README.md)：照片比例基准几何、C 核心、通用 QML、故障关闭控制器与 CFexpress／Phocus 就绪门禁；没有相机后端或安装包。

二代离线工具集中在 [`x2d2/tools/`](tools/)；分析产物集中在 [`x2d2/outputs/`](outputs/)，包括选定函数反汇编、JSON 审计、启动 Logo 预览和 AF-S / AF-C 图标资源。工具只读取用户自行准备且与哈希匹配的原厂输入，不加载固件、不连接设备、不提供安装或写入路径。

机型与地址独立归档；一代模型解密、CPU 合成输入推理或采集试验不视为二代验收。原厂固件、配置、加密模型、安全组件与原始设备记录未随库提供。

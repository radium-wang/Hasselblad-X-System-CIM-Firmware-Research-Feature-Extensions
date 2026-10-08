# X2D 4.2.0：CPU 对象检测单帧旁路候选

**最新状态：停止上机。** 后续新增的连续检测和 `tracking_stream.hpp` CPU 模板追踪并非二代原厂算法；连续截图试验引发用户报告的预览卡顿、闪烁，已撤下并禁用动态实机入口。历史单帧结果不代表连续运行安全或满足原厂功能移植要求，详见 [屏幕实验复盘](../liveview-overlay/README.md)。以下单帧说明保留为历史范围，不是当前部署建议。

所属机型为第一代 X2D 100C，功能为对象识别后端。本目录是代码验证，不是相机运行时产品。它用机内已有的 OpenCV 3.4.5 DNN 库尝试识别单张图中的 Human / Pet / Vehicle，**不读取实时取景、不追踪、不驱动 AF、不修改 GUI 或原厂服务**。它使用公开兼容模型复现功能，不是把 X2D II 加密模型直接载入一代。

## 文件与依赖

- `native_cpu_smoke.cpp`：单帧推理程序，输出载入时间、总时间、峰值内存和最多 10 个候选框。
- `build.sh`：只在 Mac 本地交叉编译，不连接相机；`prepare_link_library.py` 仅制作临时链接副本，绝不改原厂库或将该副本上传相机。
- 依赖：Android NDK、Python `pyelftools`、OpenCV 3.4.5 官方头文件、X2D 4.2.0 固件提取的 `/system/lib64/libopencv_java3.so`、兼容的 Darknet cfg/weights 和测试图。外部工具、模型、原厂库及图片不随仓库分发。
- 类别映射：COCO 的 person→Human，car/bus/truck→Vehicle，cat/dog→Pet；不含所有宠物和车辆类别，也无二代的姿态/re-id 逻辑。

从仓库根目录运行构建脚本，并显式指定外部输入及输出路径：

```sh
sh x2d/object-recognition/CodeTests/native-cpu-detector/build.sh \
  /path/to/android-ndk-r27d \
  /path/to/opencv-3.4.5 \
  /path/to/x2d-system-root \
  /tmp/x2d-native-cpu-smoke
```

当前状态：已编译并完成一次首版单输出实机试验。公开样图中的车辆以 0.585 置信度输出，单帧总耗时 1289 ms、峰值 RSS 约 102 MB；候选退出、文件清理、USB 恢复及原厂界面均已核对。当前源码已更新为两个 YOLO 输出层，但这个新版**尚未上机**。实时取景、持续追踪与 AF 联动均未实现，不能宣称完整识别功能可用。详细证据与适用边界见 [移植研究](../../research/X2D2-TO-X2D-PORT.md)。

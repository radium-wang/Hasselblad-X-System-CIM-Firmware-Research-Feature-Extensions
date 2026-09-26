# 原厂帧输入适配组件

适用边界：第一代 X2D 4.2.0 → X2D II 1.3.16.2。这是接口胶水，不是识别、追踪或对焦算法实现，不是可安装功能包。

## 当前实现

`frame_descriptor_adapter.c/.h` 接收由调用方持有的一代 NV12 描述符与真实缓冲区大小，生成二代原厂**转换函数入口所用的描述符子集**。按已核对的 16→28 字节平面间距重排 stride、offset、rows，以及 plane_count/frame_id。

只允许偶数宽高、两平面、满足行数和边界的 NV12。检查乘法回绕、平面重叠和输出长度；失败不修改输出。模块不分配内存、不复制像素、不读设备、不运行线程、不接 AF、LiDAR 或 GUI。

调用方仍必须完成：

- 固件哈希与真实数据格式核对；函数本身不能从内存片段辨认固件版本。
- 在转换和后续原厂异步算法消费期间取得有效缓冲区租约。
- 一代附加信息到二代 `0x84` 入队记录尾部的语义映射。
- 原厂模型初始化、缓存同步、结果接口与 AF 联动。

输出 **不是完整 DSH 帧，不是 `0x84` 字节 `ml_image_info_t` 入队记录**，不能直接交给 `FrameManager::PushImage`。输出中仅供已分析转换器使用的未读取字段为零；不得把它用于其他未知入口。

## 构建与验证

依赖：宿主 C11 编译器；Android 交叉编译另需已同意许可的 NDK r27d。原厂固件不随模块提供。以下从仓库根目录运行，输出目录须已存在。

```sh
clang -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -fno-omit-frame-pointer \
  x2d/object-recognition/native/frame_descriptor_adapter.c \
  x2d/object-recognition/CodeTests/offline-contract/test_frame_descriptor_native.c \
  -o /path/to/build/test-frame
/path/to/build/test-frame

/path/to/ndk/toolchains/llvm/prebuilt/darwin-x86_64/bin/clang \
  --target=aarch64-linux-android28 -std=c11 -Wall -Wextra -Werror \
  -O2 -fPIC -shared -Wl,-z,defs -Wl,-z,relro,-z,now \
  x2d/object-recognition/native/frame_descriptor_adapter.c \
  -o /path/to/build/libx2d_frame_adapter.so
```

2026-09-26 离线结果：宿主合成数据测试通过，ASan/UBSan 未报告错误；ARM64/API 28 共享库构建通过，ELF 检查确认 AArch64，唯一业务导出为 `x2d_adapt_nv12_descriptor`。这不是原厂转换函数执行验证，更不是相机性能验证。生成物只在本地临时目录，没有上传或安装，无设备恢复操作。

后续经用户授权，已将独立沙箱自检程序和本库临时上传 X2D，机内合成数据测试通过并完整清理；仍未接真实帧或原厂算法。见[实机结果与恢复复核](../research/FRAME-DESCRIPTOR-DEVICE-RESULT.md)。

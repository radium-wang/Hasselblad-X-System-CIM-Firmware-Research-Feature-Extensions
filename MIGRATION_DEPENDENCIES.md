# External Inputs and Validation Boundary

This repository does not include official firmware, extracted system/vendor trees, vendor libraries, encrypted models, Qt binaries, device logs or generated native artifacts.

Offline tools require users to supply legally obtained inputs and must verify the exact hashes documented by each module. Optional dependencies include pyelftools, Capstone, PyUSB, Pillow, NumPy, SoundFile, dissect.extfs, brotli, pycryptodome, Qt/PySide and an ARM64-capable compiler. Install only the dependencies needed for the selected offline workflow.

Source presence does not imply device compatibility. Static analysis, offline validation, device verification and user feedback remain separate evidence levels.

## 2026-10-12 迁入范围

新收录对焦／白平衡四份只读检查脚本、脱敏主题报告、TFLite 结构检查和像素位移本地处理库。输入／输出都通过显式路径传递，固件与模型不随库提供；检查脚本的生成证据默认留在输入树外的新本地目录。

对焦／白平衡依赖 pyelftools 0.32 与 Capstone 5.0.6；模型结构依赖 tflite 2.18.0 与 flatbuffers 25.12.19。像素位移合成需要 POSIX C11 编译器，渲染另需 libjpeg API，开发版为 libjpeg-turbo 3.1.0。依赖未 vendoring。

新工具不包含相机部署后端。历史完整工具包检查、实拍及 JSR 处理的原始输入／日志没有全部公开，不能宣称只下载研究库就能重建这些结果。独立 Startup Studio 与工具包引用保留原许可，不按根 MIT 重新授权。

## 2026-10-16 PDAF 与本对话成果补充

`x2d/CodeTests/pdaf-only-shadow/` 补入 425 区域核心、相位行复制、被动同步观测适配器、ARM64 函数适配源码、构建与二代依赖审计，以及旧影子判定器。主机测试只用合成输入和临时目录；C11 编译器和地址／未定义行为检查运行库需由操作者提供。固件检查仍依赖 pyelftools 0.32、Capstone 5.0.6 和固定版本的一／二代自备输入；交叉构建另需 AArch64 clang / lld。

公开子集不依赖原先本地设备读取脚本，不收录其工厂／远程操作和传输后端。历史 972 × 42 模式观测只以脱敏摘要收录；原始日志、完整帧、原厂库、派生签名、编译产物与产品安装包不公开。自动亮度和 Windows 修正以独立工具包版本摘要归档，未将其产品实现或许可并入本库。

## 2026-11-01 二代 exMCU 研究归档

`x2d2/research/exmcu/` 收录肩屏架构、CRC/格式检查、摇杆输入与两版差异的脱敏研究摘要；`x2d2/tools/inspect_exmcu.py` 仅依赖 Python 3.9+ 标准库，读取显式提供的固定 1.3.18.1 原厂容器，检查 SHA-256、头部与 CRC，仅向标准输出写摘要。

原厂固件、字体、分析载体、完整反汇编、原始设备日志和部署/持久写入实现不随库提供。公开工具可重现原厂身份和 CRC 结论，不承担完整差异分类或原始 loader 仿真。研究地址只属于所列二代输入，不用于第一代或其他版本。

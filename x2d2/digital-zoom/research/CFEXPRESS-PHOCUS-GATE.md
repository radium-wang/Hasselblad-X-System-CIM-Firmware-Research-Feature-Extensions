# X2D II 普通 CFexpress／Phocus 安装门禁

## 适用范围

对象为 X2D II 100C、固件 1.3.16.2 和本模块数字裁切候选。本文只记录公开的正常更新路径与离线包结构结论，不提供系统替换、签名绕过、调试通道或设备传输步骤。

## 官方路径

X2D II 用户手册记录 Phocus Mobile 2 与可移动存储介质两类官方消费者更新渠道，两者的对象都是哈苏发布的完整固件。精确的原厂操作由手册维护，本文不复述设备传输或安装步骤。手册也没有把桌面 Phocus 描述为任意源码或第三方包安装器。

- [X2D II 100C User Manual v1.0](https://cdn.hasselblad.com/manuals/X2D_II_100C_User_Manual/User_Manual/X2D_II_100C_User_Manual_v1.0_en.pdf)（固件更新见第 64–65 页）
- [Hasselblad X System firmware](https://www.hasselblad.com/x-system/firmware/)
- [Phocus Mobile 2](https://www.hasselblad.com/phocus/phocus-mobile-2/)

## 当前静态证据

2026-10-16 对官方 1.3.16.2 文件做的离线检查记录：文件大小 364,814,336 字节，SHA-256 为 `9789d6a9843d388034bc12341ad9a97585c25cb98cf11a0da8b768399b4842f6`；外层带 `VHABCIM` 标头、平台 `10.00.09.77` 和 2026-07-30 构建日期。内层 OTA 是 Android whole-file SignApk／PKCS#7 签名包。仓库没有对应私钥，也没有厂商签名服务或 X2D II 固件扩展 SDK。

改变内层系统内容会使签名失效；只重建外层容器不能恢复厂商签名。因此“源码已完成”“能生成窗口”或“文件放进 CFexpress”均不等于普通更新器会接受。本结论是离线静态分析，没有在相机上提交修改包进行拒绝测试。

官方 1.3.16.2 [Release Notes](https://cdn.hasselblad.com/firmware/X2D_II_100C_Firmware/1.3.16.2/X2D_II_100C_Release_Notes_EN_20260803.pdf)明确写明更新后不支持降级。包内可观察到 A/B 式更新与失败回退逻辑，但那是厂商流程，不是已经验证的第三方冷启动恢复方案。

## 就绪条件

以下条件必须全部满足，才可把本候选称为可通过普通 CFexpress／Phocus 安装：

1. 明确 1.3.16.2 的任意矩形接口，并验证坐标、对齐、预览、保存照片和释放行为。
2. 存在版本限定的运行时适配器，并完成长时间、模式切换与异常恢复实机测试。
3. 由哈苏／授权方签名，或取得公开、授权且可审计的正常开发部署机制。
4. 普通更新器实际接受完整包，且安装后的版本、文件与行为可核验。
5. 冷启动失败恢复在同型号上独立验证；不能把静态 A/B 逻辑当成恢复保证。

`../readiness-manifest.json` 将这些状态保持为结构化门禁。默认校验只确认计划结构；`../tools/check_readiness.py --require-installable` 在任一门禁为假时返回失败。裁切元数据和 GPS 已列为后续项目，不阻塞当前几何研究，也不会被误报为已实现。

## 当前结论

本地已经可以继续开发和测试几何、控制器、QML 与未来适配器接口；目前不能诚实地产生普通更新器可安装的 `.cim`。最短的外部路径是由哈苏／授权服务提供签名或开发部署渠道。在此之前，任何“CFexpress 安装补丁”都会越过现有证据与恢复边界。

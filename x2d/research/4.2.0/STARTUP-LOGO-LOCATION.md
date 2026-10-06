# X2D 100C 4.2.0 静态开机 Logo 位置调查

## 目的与状态

目标是定位开机时的静态品牌 Logo 原始资源，供后续设计和可恢复的修改方案使用。**已从主屏显示后端还原标准版 Logo；肩屏找到高可信资源路径，尚未提取出其独立图像数据。** 用户提供的目标图已制成[主屏离线替换候选](STARTUP-LOGO-REPLACEMENT.md)，还没有完整双屏方案。本文结论来自官方固件的离线静态分析和用户对开机顺序的描述，没有连接或操作相机。

适用对象仅为第一代 X2D 100C 官方 4.2.0。官方 CIM SHA-256 为 `5ae67d16a24b00f9300e3e9c1323e7d149248ad36975e12c4fa8da633b438e03`；其中 `ota.zip` SHA-256 为 `03c7e1e508bf17246e0be3e0b39d821683845561571dea57c09fcf0a3c9d736b`，`/system/bin/camera-gui` SHA-256 为 `16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0`。

## 离线检查结果

| 对象 | 静态证据 | 结论边界 |
| --- | --- | --- |
| 官方 OTA 的 `system.new.dat.br` | 按原厂 `system.transfer.list` 还原为 ext4 镜像；逐层列出 1,069 个文件。未找到独立命名的 `logo`、`splash`、`bootanimation`、`startup` 文件，也未找到独立 PNG/JPEG/BMP/SVG 图片。 | 仅排除这些常见文件形式；不能排除无扩展名、自定义编码或运行时绘制。 |
| 官方 OTA 的 `vendor.new.dat.br` | 按原厂 `vendor.transfer.list` 还原为 ext4 镜像；列出 67 个文件，同样没有上述命名或独立图片。 | 不涵盖未包含在 OTA 中的机内存储区。 |
| 原厂 `camera-gui` | 解析 ELF 中的 Qt 资源树，共列出 785 个资源；`/icons/images/` 下为渐变、合规信息和测试图，未见品牌开机图。编译 QML 字符串中有 `E_SystemState_Boot`，但没有可直接对应的 Logo 图片路径或专门的 Logo QML。 | GUI 可处理 Boot 状态，不证明它负责绘制所见品牌 Logo。资源也可能以非常规格式或代码生成。 |
| 官方 `normal.img` | IMaH 签名和校验通过后，解出 `LRFS` initramfs；其中 `res/` 只有 `keys`，未见图像。 | 只覆盖这个 initramfs，不等于检查了机内全部启动分区。 |
| 官方 `bootarea.img` | 两个 IMaH 包可解出 `BLFA`、`BLLK`、`BDIF`；已解密模块未见 PNG/JPEG/BMP 签名。 | 不能排除私有图像格式、压缩数据或不随该官方包更新的资源。 |

这些结果说明：**不能直接通过替换 `/system` 里的普通图片文件来修改目标画面**。原图仍可能存于编译后的资源、未包含在官方 OTA 中的分区、设备专用配置或其他编码资源。

## 两块屏幕的新增线索

用户描述的顺序为：肩屏先出现 Logo，随后主屏出现**相同** Logo；两屏曾同时显示，之后肩屏切到数据，主屏切到相机画面。此为用户反馈，不是本轮独立录像测量。相同画面与重叠时间不能证明两块屏幕读取同一个文件。

- **肩屏：静态分析，高可信候选。** 官方 CIM 的 `exMCU_x2.cont`（SHA-256 `edc516db67242f583b6238397423c9d51d78044070f5b1608b47136a0b499b8c`）与系统镜像 `/etc/firmware/exMCU_x2.cont` 逐文件哈希相同。其内有 `qrc:/gfx/icons/pic_power-on_h.svg`，位于文件偏移约 `0xF05E0` 的只读字符串区。它紧邻 Qt for MCUs `Main` 的编译绑定信息；同一固件还包含 `GuiExec`、`Display power on`、`BasicScreen::image_source_bindingFunctor` 和多个 `ic_topdisplay_*` 图标路径。这把开机“H”图案的**逻辑资源名**定位到 exMCU 的肩屏 UI。当前文件里没有明文 SVG，也没有可直接提取的标准 PNG/JPEG/BMP；[Qt for MCUs 文档](https://doc.qt.io/QtForMCUs/qml-qtquick-image.html)说明图像默认在嵌入二进制前解压，因此原始 SVG 文件未必保留在固件中。尚未用资源引用或屏幕捕获证明 `pic_power-on_h.svg` 就是实际显示的全部画面。
- **主屏：离线还原，高可信。** 原厂 `camera-gui` 的资源列表没有同名 `pic_power-on_h.svg`。进一步从 `/system/lib64/weston/eagle-backend.so`（SHA-256 `a0ac02a51d87d08fa61fd0d1e79af15db248af4b5b32603b9483d09f9b7f6217`）找到 `blit_logo`：在尚无可绘制 UI surface 的分支中，它将图像居中复制到 framebuffer。标准版图像由 `.rodata` 中虚拟地址 `0x17AD78` 的 17 级灰度表和 `0x17AD89` 起的 162×128 索引字节构成；逐像素按代码中的查表方式还原后，是黑底白色 `H`。另有 570×426 的 Earth Explorer 专版数据，选择路径读取 `su_variant`。使用[离线提取工具](../../tools/firmware-analysis/extract_main_startup_logo.py)可重复生成 PNG；本地输出在 `x2d/outputs/startup-logo-4.2.0/`，不随仓库提交。此处已定位实际图像字节和绘制代码，但尚未以开机录像或设备帧缓冲对比验证量产机当次显示。
- **内核通用线索：未归因。** 官方 `normal.img` 解出的 Linux 内核还包含 `display_logo_start`、`display_logo_stop`、`display_find_logo`、`display_load_logo` 和 `splashboot=` 字符串；目前无需用这些通用符号解释已在 Weston 后端定位的 H 图，亦未证实其在本机冷启动时执行。
- **启动顺序：静态分析。** 官方 `normal.img` 的 `init.rc` 在 `early-init` 启动 `weston` 和 `camera-service`，在 `post-fs` 启动 `camera-gui`。这与主屏 Logo 可能先由较早阶段显示相容，但单靠服务顺序不能把主屏 Logo 归给内核、Weston 或 GUI 中的任何一个。

因此，若目标是两块屏幕一起修改，仍需分别处理 exMCU 肩屏资源和 Weston 主屏数据。两屏视觉上相同，固件中却不是同一份可直接替换的图片文件。

哈苏官方说明 Earth Explorer 限量版具有专属启动画面，证明 X2D 100C 产品线确有差异化启动显示；该说明没有给出资源路径或修改接口，不能据此推断普通版 4.2.0 的存储位置。来源：[官方 FAQ](https://www.hasselblad.com/x-system/x2d-100c-earth-explorer-limited-edition-faq/)。

## 复现材料与操作边界

- 官方输入：[X2D 100C 4.2.0 CIM](https://cdn.hasselblad.com/firmware/X2D-100C-Firmware/4.2.0/X2D_100C_v4_2_0.cim)。固件文件和提取出的原厂二进制仅在本机临时目录，不随仓库提供。
- CIM 解包依据：[固定修订的公开提取器](https://github.com/YuHaoyua/hasselblad-cim-firmware-extractor/blob/768664267cb44621c3c12595ee9cc538020b1b94/hasselblad_extract.py)，源码 SHA-256 为 `96461ea1baec8df4cf42925eedc2f79f673078d828c5348b9a4a47b8bd2886fd`；原包、OTA 和 GUI 分别按上文的 SHA-256 核对。
- `system`／`vendor` 镜像由仓库的 [`sdat2img.py`](../../tools/firmware-analysis/sdat2img.py)在电脑上还原；Qt 编译单元可用 [`qml_unit_search.py`](../../tools/firmware-analysis/qml_unit_search.py)只读检查。Qt 资源树由 ELF 内的 `qt_resource_struct`、`qt_resource_name`、`qt_resource_data` 静态解析。
- `normal.img`／`bootarea.img` 使用公开的 [`dji_imah_fwsig.py`](https://github.com/o-gs/dji-firmware-tools/blob/master/dji_imah_fwsig.py)只读解析；外部工具和解包文件没有纳入仓库。
- 原厂二进制保持原样；已另存主屏测试副本，未生成可刷包、连接设备或验证实机显示。

## 下一步定位所需证据

下一步应对 `exMCU_x2.cont` 的 Qt for MCUs 资源表做只读解析，确认 `pic_power-on_h.svg` 的像素数据范围及引用关系。完整开机录像能补充 Logo 首帧与 GUI 首帧的相对时序。随后如需机内证据，须针对具体只读项目单独授权；不得从当前线索推断一个可安全写入的分区。用户目标图已明确，完整双屏修改与恢复方案仍取决于肩屏绘制链路。

本地已保存研究文档、原图提取工具和主屏替换候选；未提交、推送、刷写或改变相机状态。

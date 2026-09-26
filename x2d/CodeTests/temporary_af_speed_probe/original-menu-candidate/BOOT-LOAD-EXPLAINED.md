# X2D 4.2.0 菜单扩展的开机加载原理与写盘边界

## 结论先行

开机常驻方案**会修改系统分区中的文件**，但不替换原厂 `/system/bin/camera-gui`。

它把独立 preload 库、QML 和 SVG 写入 `/system`，再修改 init 服务配置，使原厂 GUI 每次启动时加载扩展库。扩展库只在该次 `camera-gui` 进程内改写四个运行时字段：三个缓存 QML 单元指针和一个 AF-C gate。关掉进程后这些内存修改消失；之所以重启后还能再次出现，是 init 在下一次启动时又重新加载扩展库并重新完成挂接。

## 开机链路

```text
Linux / Android init
  -> 读取 /system/etc/init/camera-gui.rc
  -> 为 camera-gui 设置 X2D_NATIVE_MENU=1
  -> 为 camera-gui 设置 LD_PRELOAD=/system/lib64/libx2d_native_menu.so
  -> 启动原厂 /system/bin/camera-gui
  -> 动态链接器先加载 libx2d_native_menu.so
  -> preload constructor 校验机型、进程、固定 4.2.0 单元和缓存指针
  -> 通过 /proc/self/mem 原子挂接三份缓存 QML 单元并打开 AF-C gate
  -> 原厂 QML 引擎创建 MainScreen
  -> MainScreen 新增的 Loader 创建 X2dNativeMenuBootstrap.qml
  -> Bootstrap 接入第十二格、路由、返回、高亮和“耍起功能”常驻页
```

## 四处进程内修改

`native_menu_preload.c` 使用 `dl_iterate_phdr` 查找本次启动的 PIE 基址，因此不会保存或复用上一次启动的 ASLR 地址。固定偏移只适用于通过哈希和原始字节校验的第一代 X2D 4.2.0。

1. `MainScreen` 的 `CachedQmlUnit.qmlData` 指针：指向只追加一个 Loader 的副本。
2. `ControlScreenViewModel` 的缓存单元指针：指向 AF-S / AF-C / MF 三项模型副本。
3. `PopoverFocusMode` 的缓存单元指针：指向三项布局副本。
4. `CameraUI.canChangeAfc` gate：由 `0` 改为 `1`。

四处写入是一个事务。任何一步短写或回读不符，构造器会按相反顺序恢复已经触碰的字段；成功标记为 `MENU_AND_AFC_POINTERS_READY`。它不会自动把当前模式切到 AF-C，也不会直接驱动镜头。

## 主菜单第十二格

`PlayMenuModel.qml` 用 `DelegateModel` 包装原厂 `FavoriteModel`，不改原模型内容。只有同时满足以下条件才追加扩展项：

- 非稀疏主菜单；
- 原模型恰好 11 项；
- 没有与 `x2dPlayUi` 冲突的原厂名称。

第十二格显示“耍起功能”，图标指向 `/system/etc/X2dPlayIcon.svg`。`PlayMenuRoute.qml` 在原厂用未知名称查找子菜单之前消费该入口；其余 11 项继续原样调用原厂 `MainMenu.loadSubmenu()`。`ResidentPlayHost.qml` 保持同一个 `PlayPage` 实例，`EXIT`、Escape、菜单退出和原厂 `closeMenu` 只改变页面显隐并恢复焦点。

当前页面不执行 `/blackbox/script.sh`，也不启动第二个 `camera-gui --confirmtest`。这是有意的安全边界：先验证固定入口、图标和页面生命周期，再单独设计只接受固定标识与固定哈希的 launcher。

## 实际写入的系统文件

构建/安装事务会新增这些文件：

- `/system/lib64/libx2d_native_menu.so`
- `/system/etc/X2dNativeMenuBootstrap.qml`
- `/system/etc/X2dNativeMenuModel.qml`
- `/system/etc/X2dNativeMenuRoute.qml`
- `/system/etc/X2dNativeMenuHost.qml`
- `/system/etc/X2dPlayPage.qml`
- `/system/etc/X2dPlayIcon.svg`
- 其他由 `package.json` 精确列出的同版扩展文件

开机激活事务会修改：

- `/system/etc/init/camera-gui.rc`：只给原厂 `camera-gui` service 增加 `X2D_NATIVE_MENU` 和 `LD_PRELOAD` 两个环境变量。
- `/system/etc/init/x2d-preview-loader.rc`：撤下旧独立预览的 `post-fs` 自动启动触发，保留手动恢复能力，避免两个界面同时抢占。

原配置备份放到 `/system/etc/X2dBackup-*.before-x2d-native-menu`，刻意不放在 `/system/etc/init/`，因为 init 可能扫描非 `.rc` 后缀备份。安装和恢复都会先校验 SHA-256、拒绝符号链接、临时把 `/system` remount 为读写，写完 `sync` 后恢复只读。

## 不会修改的内容

- 不替换、不补丁原厂 `/system/bin/camera-gui` 文件。
- 不修改镜头、MCU、FPGA 或相机服务固件。
- 不写入 AF-C 后端算法。
- 不包含对象识别实现。
- 不把上一次进程的内存地址写入磁盘。

## 保护和恢复

- 精确 4.2.0 构建、缓存指针、单元字节和原始 gate 不匹配时拒绝挂接。
- `/blackbox/x2d-native-menu.disable` 可让 preload 启动后立即退出，不触碰 QML 指针。
- `/tmp/x2d-native-menu-attempt` 采用排他创建；同次开机第二次 GUI 启动跳过扩展，避免失败重启循环。
- `restore-boot.sh` 用精确备份恢复两份 init 配置。
- 替换正在映射的共享库前必须先停止已确认的 GUI；否则旧映射可能变成无目录链接，并导致 `/system` 无法及时恢复只读。

## 当前验证状态

历史“引闪”组合版曾通过一次冷启动挂接并回读 `MENU_AND_AFC_POINTERS_READY`；该证据不能直接继承给新的“耍起功能”页面和 SVG。2026-09-25 的“耍起功能”临时实机测试已通过三个缓存 QML 指针与 AF-C gate 的进程内回读，用户也确认三项对焦弹窗、第十二格图标/名称、页面进入及 `EXIT`/右滑/下滑退出；测试后已完整恢复原厂 GUI。`/tmp` 构造器标记仍缺失，原因待查；AF-C 后端连续对焦、半按、休眠/唤醒及开机常驻加载尚未验收。临时启动成功不能直接授权或证明持久开机配置安全。

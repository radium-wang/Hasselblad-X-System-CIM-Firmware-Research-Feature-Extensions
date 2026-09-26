# 第十二格 Loader 与图标

## 已补入的公开源码

- [`X2dNativeMenuLoader.qml`](X2dNativeMenuLoader.qml)：把
  [`Bootstrap.qml`](Bootstrap.qml) 作为原厂 `MainScreen` 的子项加载，并显式
  传入 `MainScreen` 与 `ControlDrawer` 引用。
- [`assets/ic_main_menu_play.svg`](assets/ic_main_menu_play.svg)：第十二格
  “耍起功能”的项目自有 SVG 图标。
- [`PlayMenuModel.qml`](PlayMenuModel.qml) 与 [`PlayMenuRoute.qml`](PlayMenuRoute.qml)：
  分别负责在原厂十一项之后追加第十二项，以及在原厂子菜单查表前消费该入口。

## 主机接入方式（源码级示意）

已经拥有合法、精确版本原厂 `MainScreen` 的离线主机，可以把 Loader 作为
`MainScreen` 的子项，并显式传入对象：

```qml
X2dNativeMenuLoader {
    anchors.fill: parent
    stockScreen: parent
    stockDrawer: parent.parent
    bootstrapSource: "file:///system/etc/X2dNativeMenuBootstrap.qml"
}
```

`bootstrapSource` 的设备路径只是加载位置示意；仓库没有提供生成后的原厂
QML 编译单元、preload 动态库、安装脚本或持久化启动配置。桌面检查默认从
仓库中的 `Bootstrap.qml` 加载，因此不会访问设备或写入系统分区。

## 图标路径

源码文件名是 `ic_main_menu_play.svg`。离线 sidecar 构建器会把它复制为
`X2dPlayIcon.svg`，与 `PlayMenuModel.qml` 中的运行时图标路径对应。图标是
本项目新增的素材，不是从厂商资源中提取的文件。

## 证据边界

该 Loader 补齐的是“原厂 MainScreen 如何创建 Bootstrap”的公开源码说明，
不是可直接刷入相机的完整版本。精确版本编译单元、原厂输入和设备授权仍需
由操作者自行准备；任何实机实验都必须先有独立备份和经过验证的恢复方案。

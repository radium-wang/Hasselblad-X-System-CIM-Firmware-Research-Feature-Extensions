> 迁移的历史研究记录：原文描述的是当时的实验，不代表本次重新验证。外部依赖及本轮验证范围见仓库根目录 MIGRATION_DEPENDENCIES.md。

# X2D II 100C 1.3.16.2 地区修改研究

2026-09-14。范围仅 Wi-Fi 地区修改及必要读取、回读。当前结果均为官方固件静态分析，尚未连接 X2D II。

## 输入与复现

官方文件：https://cdn.hasselblad.com/firmware/X2D_II_100C_Firmware/1.3.16.2/X2DII_100C_v1_3_16_2%281%29.cim

大小 364814336 字节。整包 SHA-256、六个外层条目校验与提取文件哈希见 `initial-evidence.json`。外层条目内容校验全部通过；SHA-256 为本次计算值，未取得官方独立 SHA-256 清单。离线脚本为 `../../tools/inspect_region.py`，从仓库根运行 `py -3.11 -B x2d2/tools/inspect_region.py`。输入与解包文件位于仓库 `.research-cache/x2d2`。

OTA 元数据为 eagle2_hb722，Android 9。已重建 system/vendor 文件系统并提取分析文件，没有运行机内程序或安装固件。

## 已核对

- `camera-system` 的 `ProdInfo::setWifiRegion(unsigned int)` 位于 ELF VA `0x138490`。通过 `0x42c403` 的 `Identity/WifiRegion` 字符串调用 `setConfigParam`（`0x136a60`），返回前比较缓存字段与请求值。
- `camera-test` 的 `ProdConfig::handleRequest` 位于 `0x5d110`，每次构造 `ProdInfo`。功能 1 调用 set，功能 2 调用 get；功能 3 初始化配置，不能用于本任务。
- `camera-test` 属性指针表 `0x1ee3a8` 的索引 13 仍为 `wifiRegion`；长度表 `0x193488` 对应值为 1 个 u32。读取指针时处理 ELF 相对重定位。
- `ProdConfig::get` 位于 `0x5d5f8`。回复正文先放状态，偏移 4 放属性索引，偏移 8 开始放转换后的数据。
- `camera-gui` 的 `DisplayConverter::setWiFiModeList` 位于 `0x170d978`。`0x170d9b8` 和 `0x170d9bc` 比较地区 2 与 8。两者走单选项分支，其余地区先添加额外选项再添加共有选项。尚待独立核对标签、枚举数值和网络服务国家映射。
- 二代存在 `ProdConfigLegacy` 和 `ProdConfig` 两条路径。字段索引一致不足以证明入口命令号和完整 USB 封装一致。

## 尚未完成

需要继续确认命令注册号、USB 收发封装/CRC、维护服务启动条件、CN/JP 枚举数值及网络国家映射、设置保存行为与读取新鲜度，然后实现限定地区字段的协议白名单和离线模拟。当前没有可声明已适配或可实机使用的二代修改客户端，也没有地区写入、回读或 5 GHz 实机验证。

本轮用户授权承接先前列明的本地下载、脚本、研究文档和离线验证路径，并限定只做改地区。不得扩展到其他设备设置、固件安装、调试接口或其他研究功能。

## 续轮核对：命令号、枚举和回执

以下补充取代上文对应待核对项，反汇编存于 `protocol-disassembly.json`。

- Qt 元数据独立解析确认 CN=6、JP=8、2gOnly=2。`camera-system` 元数据 `0x51b48c`、字符串表 `0x51f688`。
- WMS 国家映射函数 `0x313bc0` 使用表 `0x612248`，按地区值加一索引；处理 ELF 重定位后，6 对应 `kWmsCountryCodeCn`（`0x62fb70`），2 和 8 均对应 `kWmsCountryCodeJp`（`0x62fba0`）。这些 QString 在初始化前为空，不能把静态零数据误判成运行时空国家码；尚待跟踪字符串初始化及网络服务实际接受情况。
- `camera-test` 静态初始化 `0x3eee0` 在栈表偏移 `0x480` 写命令号 `0x31`，相应函数对象虚表为 `0x1ed678`；其调用槽 `+0x30` 经重定位指向 `0x530c8`，函数调用 `ProdConfig` 构造器 `0x5c970`。因此 49 确实是本代的地区属性维护入口，不是仅凭一代推测。
- `msg2dbus` 的 `UsbhostHandler::handleMessage`（`0x11f990`）接收 signal 10，从外层偏移 4 读长度、偏移 5 取内层数据，再发 `emitTestrx`。
- 真正测试回复出口是 `TestdRelayHandler::onTesttx`（`0x120fc8`）：signal 9，长度位于偏移 4，数据从偏移 5 开始，填充到 255 字节数据区。USB 目的节点为 8；TCP 目的节点为 9。普通 `UsbhostHandler::doTx` 的 signal 14 不适用于地区测试回复。
- `SUTest::sendResult`（`0x55e20`）回显前三个 u32，请求头之后的第 4 个 u32 存 CRC。CRC 覆盖 236 字节正文。`Crc16::calculate`（`0x52200`）的逐指令等价模型与 `binascii.crc_hqx(data,0)` 在 1004 个输入上完全一致，包括 1000 个固定种子的随机正文，见 `crc-checks.json`。这是离线模型验证，不是实机运行。
- `isTestMessageOk`（`0x59f30`）在该函数内只核对长度字段为 252、数据数组至少 252 字节；此函数并未校验 CRC。不能把其名称或一代描述当作已验证的 CRC 接收检查，是否在下一层校验仍需核对。

当前已建立命令号、属性号、功能号、枚举值和主要回执封装的一致性证据。仍未验证实际设备的固件、控制端点、维护服务运行状态、完整路由 origin、保存及跨启动效果；不据此直接运行一代客户端。

# Hasselblad X-System CIM Firmware Research & Feature Extensions

An independent, non-official research project on Hasselblad X-System camera interoperability, user interfaces, autofocus behavior, feature extensions, and firmware formats.

This repository contains only source code, offline tools, tests, and sanitized research findings that contributors are authorized to publish. Vendor firmware, original shared libraries, models, DSP or kernel files, extracted or modified QML compilation units, device logs, and local build products are not distributed here.

## Contents

| Project | Public contents | Current status |
| --- | --- | --- |
| [X2D 100C](x2d/README.md) | Menu extensions, AF-S speed research, AF-C, stock face/eye detection enablement, factory debug UI finding, object recognition, shutter animation, and offline firmware tools | Research and candidates; not a complete product |
| [X2D II](x2d2/README.md) | Offline regional research for 1.3.16.2 | Not re-validated on hardware |

See [RESEARCH_RESULTS.md](RESEARCH_RESULTS.md) for the complete status of the research results.

## Reproduction

Run the safe offline suite with:

```sh
python3 scripts/reproduce_offline.py
```

The complete reproduction guide, including exact-version inputs for authorized hardware tests, is in [REPRODUCE.md](REPRODUCE.md).

## Evidence levels

- `Static analysis`: source code, firmware formats, symbols, or instructions inspected without device access.
- `Offline validation`: generators, simulators, or tests run on a computer without accessing a device.
- `Hardware validation`: restricted tests completed on a recorded model and firmware version.
- `User feedback`: observations confirmed by an operator and not necessarily independently measured.
- `Unverified`: not to be treated as implemented or deployable.

## Use boundaries

Research only devices, firmware, and environments that you own or are explicitly authorized to use. Follow applicable laws, contracts, warranty terms, security-disclosure rules, and third-party licenses. A research-purpose statement does not grant permission to access, modify, bypass technical measures, or redistribute third-party materials.

This repository does not provide one-click flashing packages and does not guarantee that any experiment applies to other firmware versions, lenses, or hardware batches. Start with offline tools and documentation.

## Development check

```sh
python3 scripts/validate_public_repo.py
```

The check rejects known binary or firmware formats, personal absolute paths, likely real device serial numbers, Python syntax errors, and broken repository-local Markdown links.

## Security and licensing

- Report security issues privately according to [SECURITY.md](SECURITY.md).
- Original project code is available under the [MIT License](LICENSE). This license does not cover vendor or third-party material that contributors are not authorized to license.
- See [NOTICE.md](NOTICE.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for source and third-party notices.

---

# 哈苏 X 系统 CIM 固件研究及功能扩展

这是一个面向哈苏 X 系统相机互操作性、用户界面、自动对焦行为、功能扩展与固件格式的非官方独立研究项目。

本仓库只收录贡献者有权公开的源码、离线工具、测试和经过脱敏的研究结论。厂商固件、原厂共享库、模型、DSP 或内核文件、从原厂程序提取或修改的 QML 编译单元、设备日志及本机构建产物均不随仓库分发。

## 当前内容

| 项目 | 公开内容 | 当前状态 |
| --- | --- | --- |
| [X2D 100C](x2d/README.md) | 菜单扩展、AF-S 提速研究、AF-C、原厂人脸/眼部识别开启、原厂 Debug 界面发现、对象识别、快门动画与离线固件工具 | 研究与候选；并非完整产品 |
| [X2D II](x2d2/README.md) | 1.3.16.2 地区离线研究 | 未重新实机验证 |

完整状态见[研究成果总表](RESEARCH_RESULTS.md)。

## 复现

运行安全离线套件：

```sh
python3 scripts/reproduce_offline.py
```

完整复现说明以及授权实机测试所需的精确版本输入见[复现指南](REPRODUCE.md)。

## 验证层级

- `静态分析`：只检查源码、固件格式、符号或指令，不访问设备。
- `离线验证`：在电脑上运行生成器、模拟器或测试，不访问设备。
- `实机验证`：在明确记录的机型和固件版本上完成受限测试。
- `用户反馈`：由设备操作者观察确认，未必有独立测量。
- `待验证`：不能视为已实现或可部署。

## 使用边界

仅在自己拥有或获得明确授权的设备、固件和环境中研究。请遵守适用法律、合同、保修、安全披露和第三方许可要求。研究用途声明不会自动授予访问、修改、规避技术措施或再分发第三方材料的权利。

本仓库不提供一键刷写包，也不保证任何实验适用于其他固件、镜头或硬件批次。默认从纯离线工具和文档开始。

## 开发检查

```sh
python3 scripts/validate_public_repo.py
```

该检查会拒绝已知二进制或固件格式、个人绝对路径、疑似真实设备序列号、Python 语法错误和失效的仓库内 Markdown 链接。

## 安全与许可证

- 安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。
- 项目原创代码使用 [MIT License](LICENSE)；该许可不覆盖贡献者无权许可的厂商或第三方材料。
- 来源与第三方声明见 [NOTICE.md](NOTICE.md) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

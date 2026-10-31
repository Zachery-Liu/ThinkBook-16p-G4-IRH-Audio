# ThinkBook 16p G4 IRH 音频适配

[English](README.md) | **简体中文**

面向 Lenovo ThinkBook 16p G4 IRH（2023）的 macOS 音频适配，使用 Realtek ALC287 编解码器与两颗 Cirrus Logic CS35L41 智能功放。

本项目结合针对该板型的 CirrusAudioFixup 适配和 AppleALC 高音跟随实现，上下两组扬声器共享 48 kHz / 24-bit 双声道音频流。

## 参考硬件

| 组件 | 配置 |
| --- | --- |
| 笔记本 | ThinkBook 16p G4 IRH（2023），Intel Core i9-13900H |
| 参考系统 | macOS 15.8.1，x86_64 |
| 音频编解码器 | Realtek ALC287（`10EC0287`） |
| 功放板号 | `17AA38A9`（ACPI `_SUB`／原始 codec subsystem ID） |
| HDEF PCI 子系统 ID | `17AA384D` |
| 功放 | 两颗 CS35L41 B2：`0x40` 左声道，`0x41` 右声道 |
| I²C 控制器 | Intel I2C7（`8086:51D9`） |
| ACPI 设备 | `_SB.PC00.I2C7.SPKR`，`CSC3551` |
| 扬声器供电 | 外部升压，GPIO1 控制 VSPK |

参考机测试已确认底部低音出声，随后使用者反馈听到了上下两组扬声器；软件检查记录了高音通路与两颗低音功放同时启用。详细结果及待完成的硬件测试见[测试说明](docs/TESTING.md)。

## 实现内容

- **低音功放：** CirrusAudioFixup 负责板级发现、供电时序、OEM DSP 固件与左右调音，以及读取本机 EFI 校准数据。
- **播放时序：** `17AA38A9` 外部升压路径在上电和扬声器输出启用期间保留受保护寄存器访问窗口，随后关闭该窗口。
- **高音跟随：** AppleALC 保留原生 `Pin17 → DAC02` 双声道路由与 `Pin21 → DAC03` 耳机路由，通过串行化异步任务让 `Pin14 → DAC02` 跟随播放事件，稳定播放期间无需周期轮询。
- **诊断：** 有界 DSP 遥测记录运行状态、故障、衰减、输出功率和心跳信息。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| [`src/CirrusAudioFixup/`](src/CirrusAudioFixup/) | 适配后的功放驱动、继承的测试与诊断采集工具 |
| [`applealc/`](applealc/) | AppleALC 补丁、高音跟随实现与双声道路由资源 |
| [`tools/`](tools/) | 固件导入、依赖准备、构建与仓库检查工具 |
| [`tests/`](tests/) | 固件导入和高音跟随回归测试 |
| [`vendor/Lilu/`](vendor/Lilu/) | 构建头文件、插件入口与文件来源记录 |
| [`config/`](config/) | 依赖版本与固件清单 |
| [`reference/`](reference/) | 参考构建指纹与验证记录 |
| [`docs/`](docs/) | 硬件适配、构建、安装与技术文档 |

## 构建

构建需要 macOS、Apple Command Line Tools、Python 3、Git、固定版本的依赖、匹配的 OEM 固件及调音文件，以及本机有效校准数据。I²C provider 使用构建文档中指定的 VoodooI2C addressed-transfer 分支。

运行不依赖 OEM 固件的主机回归测试：

```bash
python3 tools/test.py
```

按[构建说明](docs/BUILD.md)准备依赖并导入 OEM 资源后，执行：

```bash
python3 tools/build_cirrus.py Debug
python3 tools/build_applealc.py Release
```

仓库提供源码和构建工具，不包含 OEM 固件、机器校准、完整 EFI 配置或预编译 kext。

## 文档

- [适配范围](docs/COMPATIBILITY.md)
- [构建说明](docs/BUILD.md)
- [安装与回退](docs/INSTALL.md)
- [技术记录](docs/TECHNICAL.md)
- [测试与结果](docs/TESTING.md)
- [贡献说明](CONTRIBUTING.md)

## 致谢

基于 [CirrusAudioFixup](https://github.com/hoaug-tran/CirrusAudioFixup)、[AppleALC](https://github.com/acidanthera/AppleALC)、[Lilu](https://github.com/acidanthera/Lilu)、[VoodooI2C addressed-transfer 分支](https://github.com/hoaug-tran/VoodooI2C)与 Linux ALSA／Cirrus 驱动资料实现。[Ayase-kira 的 ThinkBook G5 适配](https://github.com/Ayase-kira/ThinkBook-16p-G5-IRX-Audio)为共享路由的高音跟随方案提供了参考。

## 许可

本项目原创的工具、测试和文档采用 [BSD-3-Clause](licenses/Project-BSD-3-Clause.txt)。CirrusAudioFixup 及其适配保留上游[非商业软件分发许可](LICENSE)，AppleALC、Lilu 和其他第三方组件沿用各自许可。具体范围见[许可说明](LICENSING.md)与[第三方说明](THIRD_PARTY_NOTICES.md)。

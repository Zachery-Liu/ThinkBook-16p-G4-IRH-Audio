# ThinkBook 16p G4 IRH 音频适配

Lenovo ThinkBook 16p G4 IRH（2023，参考机 i9-13900H）、Realtek ALC287 与双 CS35L41 的实验性 macOS 音频移植源码。

**参考机已明确确认底部低音出声，随后反馈感觉上下两组均响；软件侧已确认高音及左右低音同时启用。仅一台机器验证，尚未逐只做独立声学测量，也未完成耳机切换、睡眠唤醒和长期稳定性测试。**

本仓库提供源码和复现方法，不提供整套 EFI、预编译安装包、OEM 固件本体或任何人的 UID／R0 校准值。源代码公开不等于任意硬件可直接安装。

## 适配范围

| 项目 | 参考配置 |
| --- | --- |
| 机器 | ThinkBook 16p G4 IRH，2023 |
| Codec | ALC287，`10EC0287` |
| 功放板号 | ACPI `_SUB`／原始 codec SSID `17AA38A9` |
| HDEF PCI SSID | `17AA384D`，不能代替功放板号 |
| 功放 | 两颗 CS35L41 B2；`0x40=LEFT`，`0x41=RIGHT` |
| 总线／ACPI | Intel I2C7 `8086:51D9`；`_SB.PC00.I2C7.SPKR`，`CSC3551` |
| 供电 | 外部升压、GPIO1 VSPK 开关 |
| 播放 | 48kHz、24bit、双声道 |

G5、其他板号、其他扬声器批次、其他 I²C 控制器均不在本机验证范围。驱动保留上游通用模块，但本仓库不据此宣称支持那些设备。

## 当前实现

- **CirrusAudioFixup**：精确板号及两端点发现、外部升压／VSPK、OEM 正常固件与左右调音、严格匹配本机硅片 UID 的 EFI 校准、受保护播放状态机与故障静音回退。
- **播放启用时序**：精确 `17AA38A9` 外部升压路径保留受保护寄存器窗口，待 PUP 和 `SPK_OUT_ENABLE` 完成后锁回；失败、取消及关闭时也处理锁回。本机随后恢复低音可听，未通过回退 A/B 实验证明这是唯一根因。
- **AppleALC**：保留单一双声道 `Pin17 → DAC02`、耳机 `Pin21 → DAC03`；以完成的音频状态事件触发异步工作项，让原有 `Pin14 → DAC02` 高音跟随。命令钩子内不等待、不额外执行 codec 事务；稳定播放后没有周期轮询。
- **播放遥测**：有界读取 DSP 状态、错误、衰减、输出功率与心跳，携带时间和路由身份。遥测不是原始 PCM 波形，也不能代替实听。

它是两组扬声器共享双声道信号，不是四个独立声道，也没有实现独立软件分频或证明达到 Windows 原厂响度／频响。

## 构建与使用

先读 [适配边界](docs/COMPATIBILITY.md)、[构建说明](docs/BUILD.md) 和 [试用与回退](docs/INSTALL.md)。需要自己的 OEM 固件和本机有效校准；不要伪造、清零或借用别人的校准。

```bash
python3 tools/test.py
```

这个命令运行不需要固件的主机回归，不访问真实音频硬件。真实固件解析／内核构建使用本地私有资源，具体步骤见构建文档。主机测试通过不代表实机出声或稳定。

## 仓库内容

- `src/CirrusAudioFixup/`：已适配的完整驱动源码、维护工具及测试夹具。
- `applealc/`：固定上游版本的补丁、高音跟随实现和原生双声道路由 XML。
- `tools/`：离线固件导入、源码准备、CLT 构建和公开内容检查。
- `vendor/Lilu/`：本次构建使用的少量 BSD 头文件及插件入口，含哈希溯源。
- `config/`：固件哈希、依赖提交和板级信息，均不含机器私有校准。
- `reference/working-build.json`：参考实机产物指纹与明确的验证边界，不是预编译发布包。

详细过程见 [技术记录](docs/TECHNICAL.md)，验证状态见 [测试说明](docs/TESTING.md)。

## 来源与许可

基于 [hoaug-tran/CirrusAudioFixup](https://github.com/hoaug-tran/CirrusAudioFixup)、[acidanthera/AppleALC](https://github.com/acidanthera/AppleALC)、[acidanthera/Lilu](https://github.com/acidanthera/Lilu)、[VoodooI2C addressed fork](https://github.com/hoaug-tran/VoodooI2C/tree/main) 和 Linux ALSA 驱动资料；[Ayase-kira 的 G5 移植](https://github.com/Ayase-kira/ThinkBook-16p-G5-IRX-Audio) 提供了高音跟随思路，不能套用其板号、左右顺序或校准。

**CirrusAudioFixup 上游采用非商业软件分发许可，禁止出售软件、收费 EFI 包及付费墙。** 本仓库保留该许可，不能把整个项目重新标为 MIT／BSD，也不宣称它属于 OSI 批准许可下的开源项目。AppleALC 补丁／跟随代码、Lilu 和其他第三方组件依各自许可；详见 [第三方说明](THIRD_PARTY_NOTICES.md) 与 `licenses/`。OEM 固件许可独立于源码许可。

反馈请只提供脱敏硬件标识、版本和症状；不要提交完整 EFI、三码、NVRAM、UID、校准记录或原始完整系统转储。见 [贡献说明](CONTRIBUTING.md)。

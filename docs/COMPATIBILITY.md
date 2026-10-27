# 适配边界

参考硬件是2023 ThinkBook 16p G4 IRH、ALC287、ACPI板号17AA38A9、两颗CS35L41 B2、Intel I2C7 51D9、CSC3551/SPKR及GPIO1外部VSPK拓扑。

驱动的本机发现路径检查从 `IOService:/AppleACPIPlatformExpert/PC00/AppleACPIPCI/I2C7@10,1/` 开始。这是已验证拓扑保护；其他命名空间不能通过改字符串就宣称等价。

HDEF PCI SSID 17AA384D不是功放板号。AppleALC可把codec subsystem运行时替换为106B0700；layout21内部显示为7是上游处理，不是错误覆盖。G5板号38F9、总线和左右地址次序不同，不能照搬。

本仓库不公开个人UID/R0，也不要求在JSON中手填别人的数据。驱动读取本机现有 `CirrusSmartAmpCalibrationData`，严格匹配非零硅片UID和有效记录；缺失、不匹配或故障时应保持输出受保护。不要注入伪造校准、关闭DSP保护或忽略PUP超时。

参考机macOS15.8.1 x86_64，仅一台机器试过；不保证其他系统、BIOS、扬声器批次、G4不同板号或G5兼容。没有Windows等效频响、最大声压、原厂分频点或专业测量结论。

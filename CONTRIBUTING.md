# 反馈与贡献

欢迎提供精确型号、板号、系统／驱动版本、症状及脱敏的第一故障。区分“日志／寄存器通过”和“实际听到声音”，区分真实测试与主机模拟。

不要上传完整EFI、三码、SystemUUID、完整NVRAM、硅片UID、R0／校准记录或原始完整IORegistry／系统转储。不要将OEM固件、生成FirmwareData.inc、deps、local、构建产物加入提交。

修改播放路径时，保留严格板号、UID校准、故障保护、取消与双端回退。高音改动不得随意写Pin17、DAC流、codec系数或改变增益；新增硬件需自己的证据和门控，不只替换板号字符串。

运行 `python3 tools/test.py`，并明确写出未验证的硬件行为。发布前运行 `python3 tools/check_public_tree.py`，使用Git提交或git archive导出，不直接压缩整个带私有依赖的工作目录。

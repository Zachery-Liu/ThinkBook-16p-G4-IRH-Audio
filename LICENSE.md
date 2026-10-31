# License

This repository contains components with separate licenses.

| Files / component | License |
| --- | --- |
| Original content in root-level `tools/`, `tests/`, `docs/`, `config/`, and `reference/`, plus `README.md`, `README.zh-CN.md`, and `CONTRIBUTING.md` | [BSD-3-Clause — Zachery Liu](licenses/Project-BSD-3-Clause.txt) |
| `src/CirrusAudioFixup/`, including adaptations of that driver | [CirrusAudioFixup License (Non-Commercial Software Distribution)](src/CirrusAudioFixup/LICENSE), also available as [CirrusAudioFixup-NonCommercial.txt](licenses/CirrusAudioFixup-NonCommercial.txt) |
| `applealc/` patches, follower implementation, and routing resource | BSD-3-Clause; retain the [AppleALC copyright and license](licenses/AppleALC-BSD-3-Clause.txt). Original additions by Zachery Liu also use [BSD-3-Clause](licenses/Project-BSD-3-Clause.txt) |
| `vendor/Lilu/` | [Lilu BSD-3-Clause](licenses/Lilu-BSD-3-Clause.txt), with separate licenses for bundled Capstone, LLVM, and HDE material |
| Other third-party material | Its original copyright notices and license terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

The project BSD-3-Clause grant covers original contributions in the paths above. It does not replace licenses on upstream or copied material. The CirrusAudioFixup license applies to that component and its derivative adaptations; its full text is preserved in the component directory and in `licenses/CirrusAudioFixup-NonCommercial.txt`.

BSD-3-Clause is an [OSI-approved open-source license](https://opensource.org/license/bsd-3-clause). CirrusAudioFixup's license restricts commercial software distribution, so the complete repository has mixed licensing rather than a single BSD-3-Clause or other OSI-approved license. Changing that component to a standard open-source license would require permission from its rights holders.

OEM firmware and tuning files are not included. Their licensing is separate from the source code. VoodooI2C and MacKernelSDK are separately obtained build/runtime dependencies with their own terms.

## 简体中文

本仓库采用分组件授权：原创的根目录工具、测试、文档、配置和参考记录，以及两份 README 与贡献说明，采用 BSD-3-Clause；AppleALC 相关实现沿用 BSD-3-Clause 并保留上游署名；CirrusAudioFixup 驱动及其衍生适配保留上游非商业软件分发许可。第三方文件沿用各自条款。

BSD-3-Clause 是 OSI 批准的开源许可证。由于 CirrusAudioFixup 的商业分发限制，整仓属于混合许可，不能统一改标为 BSD 或 MIT。若要为该驱动更换标准开源许可证，需要取得相关权利人的授权。

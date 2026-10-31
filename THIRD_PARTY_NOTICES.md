# 第三方与许可

本仓库原创工具、测试和文档采用 BSD-3-Clause，署名 Zachery Liu；文件范围及组件对应关系见 [LICENSE.md](LICENSE.md)，许可全文见 [licenses/Project-BSD-3-Clause.txt](licenses/Project-BSD-3-Clause.txt)。

- `src/CirrusAudioFixup`：基于hoaug-tran/CirrusAudioFixup，保留Tran Kinh Hoang原作者署名及非商业软件分发许可。该目录的 `LICENSE` 与 `licenses/CirrusAudioFixup-NonCommercial.txt` 保留原文；根目录 `LICENSE.md` 汇总各组件授权范围。
- `applealc`补丁／高音跟随及路由资源：基于acidanthera/AppleALC 1.9.9固定提交，按AppleALC的BSD-3-Clause保留来源及许可，见licenses/AppleALC-BSD-3-Clause.txt。
- `vendor/Lilu`：本地构建使用的Lilu Headers与Library/plugin_start.cpp，保留各文件版权及BSD-3-Clause许可。完整Lilu运行时不在仓库内。PROVENANCE.json记录实际文件哈希；原归档的提交未恢复，不虚构提交。
- Lilu所含Capstone与HDE头文件：保留原作者注释，并另附Capstone、LLVM及HDE原许可全文；这些组件不由Lilu的BSD-3-Clause或本仓库根许可替代。
- MacKernelSDK：作为用户另行取得的构建依赖，不在本仓库再分发；按上游和各头文件许可使用。
- VoodooI2C及其addressed fork：作为单独GPL-3.0依赖，不在本仓库再分发完整源码或二进制。准备工具只在用户取得的固定版本源Info.plist添加硬件ID，provider ABI说明保留上游链接。
- Linux ALSA/Cirrus驱动：寄存器、供电、固件、校准与播放时序参考。各参考源及其中原作者／SPDX声明不被本仓库根许可取代。
- G5参考移植：Ayase-kira/ThinkBook-16p-G5-IRX-Audio。借鉴其单一路由配合高音跟随思路；本实现改为事件驱动的异步序列化工作项，没有引入G5个人校准。

OEM DSP固件和调音未包含。licenses/Cirrus-firmware-license-reference.txt仅作为上游固件许可参考；它不代表任意OEM文件均被自动授权再分发。固件导入不会改变这些文件的独立许可。

仓库采用分组件许可：原创工具、测试和文档按 BSD-3-Clause 授权；CirrusAudioFixup 驱动及衍生适配沿用其非商业软件分发许可；其余组件保留各自原条款。

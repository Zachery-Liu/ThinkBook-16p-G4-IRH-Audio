# 构建

以下只准备源码和本地构建产物，不安装驱动、不改 EFI、不改 NVRAM。参考机仅有 Apple Command Line Tools，没有完整 Xcode。

## 1. 固定依赖

需要 macOS、Apple CLT、Python 3、Git。`vendor/Lilu` 冻结了实际使用的头文件和 `plugin_start.cpp`；来源目录版本标记为1.7.2，与参考机运行时记录的Lilu1.7.3不是同一个概念。原始归档提交未恢复，不冒充精确上游提交；文件哈希见 `vendor/Lilu/PROVENANCE.json`。

```bash
mkdir -p deps local
git clone https://github.com/acidanthera/MacKernelSDK.git deps/MacKernelSDK
git -C deps/MacKernelSDK checkout 7af1933c27aefcbdf4809ee44478829aad30f9c1
git clone https://github.com/acidanthera/AppleALC.git deps/AppleALC
git -C deps/AppleALC checkout ff01db21749271916d44605503499ceaa61d94b2
python3 tools/prepare_applealc.py
```

`prepare_applealc.py` 校验 HEAD 并应用补丁，复制原生 Pin17 路由。已修改或已准备的源码会拒绝重复套补丁，请使用干净的固定版本。

## 2. 本地导入自己的 OEM 资源

从你有权使用的匹配 OEM 驱动取得以下正常播放资源。哈希和大小见 `config/firmware-manifest.json`；不要使用 `_cal`／`_diag` 系数，也不要把同名但不同板号的资源强行导入。

| 用途 | 文件 |
| --- | --- |
| DSP 正常固件 | `halo_cspl_RAM_revB2_29.63.1.wmfw` |
| 左调音 | `17AA38A9_221222_V0_A0.bin` |
| 右调音 | `17AA38A9_221222_V0_A1.bin` |

```bash
python3 tools/embed_firmware.py \
  --wmfw local/halo_cspl_RAM_revB2_29.63.1.wmfw \
  --left local/17AA38A9_221222_V0_A0.bin \
  --right local/17AA38A9_221222_V0_A1.bin
```

生成的 `FirmwareData.inc` 被 Git 忽略。导入工具核对三项长度、哈希和格式后才原子写入；不会生成任何校准。没有有效本机 UID 校准，驱动仍应拒绝正常播放，不能用该工具绕过。

## 3. 测试和构建

```bash
python3 tools/test.py
python3 tools/build_cirrus.py Debug
python3 tools/build_applealc.py Release
```

产物分别为：

- `src/CirrusAudioFixup/build/CLT-Debug/CirrusAudioFixup.kext`
- `deps/AppleALC/build/Release/AppleALC.kext`

AppleALC 构建使用审查过的上游 ResourceConverter，不运行上游安装脚本；保留上游 PinConfigs personality，避免遗漏 `HDAConfigDefault`。两个 CLT 构建入口都使用 libkmod `_start/_stop`，另外链接真实模块入口；不要把 kmod_info 改回错误入口。

可用 `python3 tools/build_cirrus.py Debug --legacy-key-timing` 构建仅供受控对照的旧时序版本；它没有被本机当作成功版本验证，不要默认安装。Release Cirrus 也可构建，但参考机实际可听版本是 Debug Cirrus + Release AppleALC。

## 4. I²C provider 是单独的前置条件

必须具备兼容的40-byte `VoodooI2CTransferToAddress` ABI，不能把普通 stock VoodooI2C 当成可互换依赖。参考接口固定提交及布局见 `config/dependencies.json` 和驱动内 `docs/hardware/i2c_provider.md`。

如需从该 fork 源码准备本机匹配：

```bash
git clone https://github.com/hoaug-tran/VoodooI2C.git deps/VoodooI2C
git -C deps/VoodooI2C checkout 1a1ae9a26a74ec6b7e32a5d07f6a6ae9413bf298
python3 tools/prepare_voodooi2c.py deps/VoodooI2C
```

此工具只在源 Info.plist 的既有 CometLake personality 加入 `51D9` 并保留 `51E9`；不会编译、安装 provider 或验证总线时序。VoodooI2C 自身依赖／构建按其上游说明处理。本机的现有 provider 已工作且触控板曾验证正常，不能为音频随意替换。

编译依赖、OEM 文件、生成资源和构建产物均被忽略。公开发布只能使用 Git 提交或 `git archive` 导出的内容，不能直接把含 `local/`、`deps/` 的工作目录整体压缩上传。

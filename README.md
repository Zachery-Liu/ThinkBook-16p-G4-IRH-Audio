# ThinkBook 16p G4 IRH Audio

**English** | [简体中文](README.zh-CN.md)

macOS audio support for the Lenovo ThinkBook 16p G4 IRH (2023), combining the Realtek ALC287 codec with two Cirrus Logic CS35L41 smart amplifiers.

The port combines a board-specific CirrusAudioFixup adaptation with an AppleALC tweeter follower. The upper and lower speaker groups share a stereo stream at 48 kHz / 24-bit.

## Reference hardware

| Component | Configuration |
| --- | --- |
| Laptop | ThinkBook 16p G4 IRH (2023), Intel Core i9-13900H |
| Reference OS | macOS 15.8.1, x86_64 |
| Audio codec | Realtek ALC287 (`10EC0287`) |
| Amplifier board ID | `17AA38A9` (ACPI `_SUB` / original codec subsystem ID) |
| HDEF PCI subsystem ID | `17AA384D` |
| Amplifiers | Two CS35L41 B2 devices: `0x40` left, `0x41` right |
| I²C controller | Intel I2C7 (`8086:51D9`) |
| ACPI device | `_SB.PC00.I2C7.SPKR`, `CSC3551` |
| Speaker power | External boost with GPIO1 VSPK switching |

Reference-machine testing confirmed audible bass playback; the listener subsequently reported hearing both speaker groups. Software checks recorded the tweeter route and both bass amplifiers active. Detailed results and remaining hardware tests are listed in [Testing](docs/TESTING.md).

## Implementation

- **Bass amplifiers:** CirrusAudioFixup handles board discovery, power sequencing, OEM DSP firmware and left/right tuning, and calibration from the machine's EFI data.
- **Playback sequencing:** The `17AA38A9` external-boost path keeps protected registers accessible through power-up and speaker-output enable, then closes the register window.
- **Tweeter follower:** AppleALC keeps the native `Pin17 → DAC02` stereo route and `Pin21 → DAC03` headphone route. Serialized asynchronous work lets `Pin14 → DAC02` follow playback events, with no steady-state polling.
- **Diagnostics:** Bounded DSP telemetry captures status, faults, attenuation, output power, and heartbeat information.

## Repository layout

| Path | Contents |
| --- | --- |
| [`src/CirrusAudioFixup/`](src/CirrusAudioFixup/) | Adapted amplifier driver, inherited tests, and diagnostic collectors |
| [`applealc/`](applealc/) | AppleALC patch, tweeter follower, and stereo routing resource |
| [`tools/`](tools/) | Firmware import, dependency preparation, builds, and repository checks |
| [`tests/`](tests/) | Firmware-import and tweeter regression tests |
| [`vendor/Lilu/`](vendor/Lilu/) | Build headers, plugin entry point, and file provenance |
| [`config/`](config/) | Dependency revisions and firmware manifest |
| [`reference/`](reference/) | Reference build fingerprints and validation records |
| [`docs/`](docs/) | Hardware compatibility, build, installation, and technical notes |

## Building

Build requirements are macOS, Apple Command Line Tools, Python 3, Git, the pinned dependencies, matching OEM firmware and tuning files, and valid calibration data for the machine. The I²C provider uses the addressed-transfer VoodooI2C fork documented in the build guide.

Run the firmware-independent host regression suites with:

```bash
python3 tools/test.py
```

After preparing the dependencies and importing the OEM resources as described in [Building](docs/BUILD.md):

```bash
python3 tools/build_cirrus.py Debug
python3 tools/build_applealc.py Release
```

The repository contains source and build tools. OEM firmware, machine-specific calibration, complete EFI configurations, and prebuilt kexts are not included.

## Documentation

The detailed guides are currently in Simplified Chinese:

- [Hardware compatibility](docs/COMPATIBILITY.md)
- [Building](docs/BUILD.md)
- [Installation and rollback](docs/INSTALL.md)
- [Technical notes](docs/TECHNICAL.md)
- [Testing and results](docs/TESTING.md)
- [Contributing](CONTRIBUTING.md)

## Credits

Built on [CirrusAudioFixup](https://github.com/hoaug-tran/CirrusAudioFixup), [AppleALC](https://github.com/acidanthera/AppleALC), [Lilu](https://github.com/acidanthera/Lilu), the [VoodooI2C addressed-transfer fork](https://github.com/hoaug-tran/VoodooI2C), and Linux ALSA/Cirrus driver references. [Ayase-kira's ThinkBook G5 port](https://github.com/Ayase-kira/ThinkBook-16p-G5-IRX-Audio) informed the shared-route tweeter approach.

## License

Original project tooling, tests, and documentation use [BSD-3-Clause](licenses/Project-BSD-3-Clause.txt). CirrusAudioFixup and its adaptations retain the upstream [non-commercial software distribution license](LICENSE). AppleALC, Lilu, and other third-party components retain their respective licenses. See [License scope](LICENSING.md) and [Third-party notices](THIRD_PARTY_NOTICES.md).

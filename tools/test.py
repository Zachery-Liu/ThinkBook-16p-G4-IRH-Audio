#!/usr/bin/env python3
"""Public asset-free regressions. Never read NVRAM or real audio hardware."""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'src/CirrusAudioFixup'
suites=[
 C/'Tests/Drivers/check_key_lifetime.py',C/'Tests/Drivers/check_signal_telemetry.py',
 C/'Tests/Drivers/check_registers.py',C/'Tests/Transport/check_transport.py',
 C/'Tests/Drivers/check_cs35l41_power.py',C/'Tests/Drivers/check_calibration.py',
 C/'Tests/Drivers/check_tuning.py',C/'Tests/Platform/check_hda.py',
 C/'Tests/Platform/check_runtime.py',
 ROOT/'tests/test_tweeter_follower.py',ROOT/'tests/test_tweeter_runtime.py',
 ROOT/'tests/test_firmware_import.py']
for path in suites:
    print('Running '+str(path.relative_to(ROOT)),flush=True)
    subprocess.run([sys.executable,str(path)],cwd=ROOT,check=True)
print('PASS public asset-free regressions. Hardware behavior still requires on-device validation.')

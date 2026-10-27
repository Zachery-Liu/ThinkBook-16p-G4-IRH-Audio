"""Exercise public firmware import with synthetic data, never OEM payloads."""
from pathlib import Path
import hashlib,json,shutil,struct,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='thinkbook-import-') as d:
 t=Path(d)
 for p in ['tools','config','src/CirrusAudioFixup/Tools/Firmware']:(t/p).mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT/'tools/embed_firmware.py',t/'tools/embed_firmware.py')
 shutil.copy2(ROOT/'src/CirrusAudioFixup/Tools/Firmware/import_firmware.py',t/'src/CirrusAudioFixup/Tools/Firmware/import_firmware.py')
 data={'firmware':b'WMFW'+struct.pack('<IHBB',40,0,4,3)+bytes(28),
       'left':b'WMDR'+bytes(11)+b'\x01','right':b'WMDR'+bytes(11)+b'\x02'}
 manifest={'board':'17AA38A9','speaker_id':0}
 for n,b in data.items():
  (t/(n+'.dat')).write_bytes(b)
  manifest[n]={'filename':n+'.dat','size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 (t/'config/firmware-manifest.json').write_text(json.dumps(manifest))
 command=[sys.executable,str(t/'tools/embed_firmware.py'),'--wmfw',str(t/'firmware.dat'),'--left',str(t/'left.dat'),'--right',str(t/'right.dat')]
 subprocess.run(command,check=True,capture_output=True)
 target=t/'src/CirrusAudioFixup/CirrusAudioFixup/Devices/Amplifiers/CS35L41/Resources/Generated/FirmwareData.inc'
 before=target.read_bytes();assert b'0x17AA, 0x38A9, 0' in before
 assert b'cs35l41FirmwareCount = sizeof' in before
 assert subprocess.run(command,capture_output=True).returncode!=0
 (t/'right.dat').write_bytes(data['left'])
 assert subprocess.run(command+['--replace'],capture_output=True).returncode!=0
 assert target.read_bytes()==before
 (t/'right.dat').write_bytes(data['right'])
 subprocess.run(command+['--replace'],check=True,capture_output=True)
 assert target.read_bytes()==before
print('PASS firmware import: synthetic success, exact role/hash checks, atomic output, no blind overwrite, no calibration generation')

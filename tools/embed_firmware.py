#!/usr/bin/env python3
"""Embed only the reviewed OEM board firmware supplied by the local user."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('wmfw','left','right'):p.add_argument('--'+n,required=True,type=Path)
    p.add_argument('--replace',action='store_true',help='Replace an existing local generated catalog after verifying every payload')
    a=p.parse_args();manifest=json.loads((ROOT/'config/firmware-manifest.json').read_text())
    upstream=ROOT/'src/CirrusAudioFixup/Tools/Firmware/import_firmware.py'
    spec=importlib.util.spec_from_file_location('firmware_importer',upstream);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    payloads={}
    for arg,key in [('wmfw','firmware'),('left','left'),('right','right')]:
        data=getattr(a,arg).read_bytes();expected=manifest[key]
        if len(data)!=expected['size'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:
            raise SystemExit('Wrong board/firmware payload: '+arg)
        valid,message=mod.validate_wmfw(data) if arg=='wmfw' else mod.validate_bin(data)
        if not valid:raise SystemExit(message)
        payloads[arg]=data
    output=ROOT/'src/CirrusAudioFixup/CirrusAudioFixup/Devices/Amplifiers/CS35L41/Resources/Generated/FirmwareData.inc'
    if output.exists() and not a.replace:raise SystemExit('Local catalog already exists; use --replace deliberately')
    names={'wmfw':'thinkbook_17aa38a9_wmfw','left':'thinkbook_17aa38a9_left','right':'thinkbook_17aa38a9_right'}
    text='// Generated local OEM assets. DO NOT COMMIT OR DISTRIBUTE.\n'
    for key in names:text+=mod.format_c_array(names[key],payloads[key])+'\n'
    text+='const FirmwareResource cs35l41Firmware[] = {\n'
    text+='    {0x17AA, 0x38A9, 0, "'+manifest['firmware']['filename']+'", "'+manifest['left']['filename']+'", '
    text+='thinkbook_17aa38a9_wmfw, sizeof(thinkbook_17aa38a9_wmfw), thinkbook_17aa38a9_left, sizeof(thinkbook_17aa38a9_left), thinkbook_17aa38a9_right, sizeof(thinkbook_17aa38a9_right), false, nullptr, 0, nullptr, 0, nullptr, nullptr, false}\n};\n'
    text+='const size_t cs35l41FirmwareCount = sizeof(cs35l41Firmware)/sizeof(cs35l41Firmware[0]);\n'
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=str(output.parent),prefix='.firmware-')
    try:
        with os.fdopen(fd,'w') as f:f.write(text)
        os.replace(tmp,output)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('Generated ignored local catalog for 17AA38A9 / speaker 0. No calibration was generated or changed.')
if __name__=='__main__':main()

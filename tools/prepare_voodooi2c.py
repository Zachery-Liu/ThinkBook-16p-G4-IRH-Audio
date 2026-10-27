#!/usr/bin/env python3
"""Add the reviewed Intel I2C7 match without removing the touchpad match."""
from pathlib import Path
import argparse,json,plistlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args();source=a.source.resolve()
    ref=json.loads((ROOT/'config/dependencies.json').read_text())['VoodooI2C']['addressed_ABI_reference_commit']
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=ref:raise SystemExit('Wrong addressed-ABI source commit')
    path=source/'VoodooI2C/VoodooI2C/Info.plist';data=plistlib.loads(path.read_bytes())
    node=data['IOKitPersonalities']['VoodooI2CPCICometLakeController']
    tokens=node['IOPCIMatch'].split()
    for value in ['0x51e98086','0x51d98086']:
        if value.lower() not in [t.lower() for t in tokens]:tokens.append(value)
    node['IOPCIMatch']=' '.join(tokens)
    path.write_bytes(plistlib.dumps(data,sort_keys=False))
    print('Prepared PCI matches in source only. Build/provider ABI and touchpad must be checked separately.')
if __name__=='__main__':main()

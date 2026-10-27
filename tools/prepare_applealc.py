#!/usr/bin/env python3
"""Apply the exact-board follower to the fixed upstream source, offline."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'deps/AppleALC');a=p.parse_args();source=a.source.resolve()
    expected=json.loads((ROOT/'config/dependencies.json').read_text())['AppleALC']['commit']
    actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if actual!=expected:raise SystemExit('Wrong AppleALC base commit')
    patch=ROOT/'applealc/kern_alc-follow.patch'
    check=subprocess.run(['git','-C',str(source),'apply','--check',str(patch)],capture_output=True,text=True)
    if check.returncode:
        raise SystemExit('Source differs or is already prepared; use a clean fixed checkout. '+check.stderr)
    subprocess.run(['git','-C',str(source),'apply',str(patch)],check=True)
    for name in ['ThinkBookTweeterFollower.hpp','ThinkBookTweeterRuntime.hpp']:shutil.copy2(ROOT/'applealc'/name,source/'AppleALC'/name)
    shutil.copy2(ROOT/'applealc/resources/Platforms21.xml',source/'Resources/ALC287/Platforms21.xml')
    print('Prepared AppleALC source only; no EFI, NVRAM or services modified.')
if __name__=='__main__':main()

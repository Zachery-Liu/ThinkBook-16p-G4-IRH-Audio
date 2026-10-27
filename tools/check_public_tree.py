#!/usr/bin/env python3
"""Audit Git-tracked publication content, never private ignored build inputs."""
from pathlib import Path
import re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z']).decode().split('\0')
paths=[p for p in paths if p]
if not paths:raise SystemExit('No tracked files to audit; stage the intended public files first.')
errors=[]
for name in paths:
    path=Path(name);parts=path.parts
    if path.is_absolute() or '..' in parts or any(p in {'deps','local','build','dist','EFI','__pycache__'} for p in parts):errors.append(name+': private/build path')
    if path.suffix.lower() in {'.wmfw','.bin','.bincfg','.o','.exe','.log','.pyc'} or path.name=='FirmwareData.inc' or any(p.endswith(('.kext','.dSYM')) for p in parts):errors.append(name+': generated/private/binary asset')
    full=ROOT/path
    if full.is_symlink():errors.append(name+': unexpected symlink');continue
    data=full.read_bytes()
    if b'\0' in data:errors.append(name+': binary content')
    if re.search(rb'(?<!System)/(?:Users|Volumes)/(?!\$)[A-Za-z0-9_]',data):errors.append(name+': absolute personal filesystem path')
    if len(re.findall(rb'0x[0-9a-fA-F]{2}(?=\s*[,}])',data))>1000:errors.append(name+': possible embedded firmware array')
if errors:
    print('\n'.join(errors));raise SystemExit(1)
print('PASS public Git tree: '+str(len(paths))+' tracked source/document files; no firmware, EFI, private paths, build outputs or symlinks detected.')

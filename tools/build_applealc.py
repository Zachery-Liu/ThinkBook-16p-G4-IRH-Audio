from pathlib import Path
import hashlib,json,plistlib,subprocess,sys,zlib,copy,shutil
ROOT=Path(__file__).resolve().parents[1]
r=ROOT/'deps/AppleALC';SDK=ROOT/'deps/MacKernelSDK';LILU=ROOT/'vendor/Lilu'
if not (r/'AppleALC/ThinkBookTweeterRuntime.hpp').is_file():raise SystemExit('Prepare the fixed AppleALC source first')
if not (SDK/'Headers').is_dir():raise SystemExit('Missing deps/MacKernelSDK')
mode=sys.argv[1] if len(sys.argv)>1 else 'Release';assert mode in ('Release','Debug')
build=r/'build'/mode;build.mkdir(parents=True,exist_ok=True)
cc=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip();sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
# Reviewed upstream resource converter; invoke it directly, never upstream install scripts.
converter=r/'build/ResourceConverter'
if not converter.exists():subprocess.run([cc,'-std=c++17','-framework','Foundation','-framework','Cocoa',str(r/'ResourceConverter/main.mm'),'-o',str(converter)],check=True)
# Match upstream zlib.pl's newline/tab compaction, retaining all codecs/layouts.
for p in (r/'Resources').rglob('*.xml'):
 data=p.read_bytes().replace(b'\n',b'').replace(b'\t',b'')
 (Path(str(p)+'.zlib')).write_bytes(zlib.compress(data,9))
# Recreate the exact compact native route from public BSD-licensed XML.
xml=(ROOT/'applealc/resources/Platforms21.xml').read_bytes()
compressor=zlib.compressobj(6,zlib.DEFLATED,15,2,zlib.Z_DEFAULT_STRATEGY)
resource=compressor.compress(xml)+compressor.flush()
decode=lambda data:plistlib.loads(b'<plist version="1.0">'+data+b'</plist>')
active=decode(xml);source=decode((r/'Resources/ALC287/Platforms21.xml').read_bytes())
assert [x['NodeID'] for x in active['PathMaps'][0]['PathMap'][2][0][0]]==[0x17,2]
assert active==source,'Native route source differs from the reviewed profile'
assert len(resource)==312,'Unexpected native routing compression; review before building'
(r/'Resources/ALC287/Platforms21.xml.zlib').write_bytes(resource)
subprocess.run([str(converter),str(r/'Resources'),str(r/'AppleALC/kern_resources.cpp')],check=True)
flags=['-arch','x86_64','-std=c++17','-mkernel','-fapple-kext','-fno-exceptions','-fno-rtti','-fno-common','-fno-builtin','-nostdinc++','-g','-Os' if mode=='Release' else '-O0','-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DAPPLE','-DNeXT','-DPRODUCT_NAME=AppleALC','-DMODULE_VERSION=1.9.9','-DHAVE_ANALOG_AUDIO=1','-isysroot',sdk,'-mmacosx-version-min=11.0','-I'+str(SDK/'Headers'),'-I'+str(SDK/'Headers/bsd'),'-I'+str(LILU),'-I'+str(r/'AppleALC'),'-ffreestanding']
flags+=['-I'+str(p) for p in (r/'AppleALC').rglob('*') if p.is_dir()]
if mode=='Debug':flags+=['-DDEBUG=1']
sources=list((r/'AppleALC').rglob('*.cpp'))+[LILU/'Library/plugin_start.cpp']
objs=[]
for p in sources:
 obj=build/(p.name+'.o');print('Compile',p.name,flush=True)
 subprocess.run([cc,*flags,'-c',str(p),'-o',str(obj)],check=True);objs.append(str(obj))
km=build/'kmod.c';km.write_text('''#include <mach/mach_types.h>
#include <mach/kmod.h>
#include <string.h>
extern kern_return_t AppleALC_kern_start(kmod_info_t *, void *);
extern kern_return_t AppleALC_kern_stop(kmod_info_t *, void *);
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(as.vit9696.AppleALC, "1.9.9", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = AppleALC_kern_start;
__private_extern__ kmod_stop_func_t *_antimain = AppleALC_kern_stop;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
__attribute__((noinline,optnone)) void __bzero(void *p,size_t n){(void)memset(p,0,n);}
''')
obj=build/'kmod.o';subprocess.run([cc,*[f for f in flags if f!='-std=c++17'],'-x','c','-c',str(km),'-o',str(obj)],check=True);objs.append(str(obj))
binary=build/'AppleALC';subprocess.run([cc,'-arch','x86_64','-mkernel','-nostdlib','-isysroot',sdk,'-mmacosx-version-min=11.0','-Wl,-kext','-Wl,-undefined,dynamic_lookup',*objs,'-L'+str(SDK/'Library/x86_64'),'-lkmod','-lcc_kext','-o',str(binary)],check=True)
subprocess.run(['dsymutil',str(binary),'-o',str(binary)+'.dSYM'],check=True)
subprocess.run([sys.executable,str(ROOT/'src/CirrusAudioFixup/Tools/Build/verify_kext_vtables.py'),str(binary)],check=True)
subprocess.run(['lipo',str(binary),'-verify_arch','x86_64'],check=True)
(build/'build-provenance.json').write_text(json.dumps({'AppleALC_base_commit':'ff01db21749271916d44605503499ceaa61d94b2','source':'https://github.com/acidanthera/AppleALC','sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'mode':mode,'source_files':[str(p.relative_to(ROOT)) for p in sources],'known_audible_platforms21_sha256':hashlib.sha256(resource).hexdigest(),'cirrus_driver_unchanged':True},indent=2)+'\n')
print('BUILT',binary)

# Produce a complete bundle. The tested live Info.plist uses the upstream
# PinConfigs personality, so preserve that instead of omitting HDAConfigDefault.
info=plistlib.loads((r/'AppleALC/AppleALC-Info.plist').read_bytes())
values={'EXECUTABLE_NAME':'AppleALC','PRODUCT_BUNDLE_IDENTIFIER':'as.vit9696.AppleALC','PRODUCT_NAME':'AppleALC','PRODUCT_NAME:rfc1034identifier':'AppleALC','MODULE_VERSION':'1.9.9'}
def expand(item):
    if isinstance(item,str):
        for k,v in values.items():item=item.replace('$('+k+')',v)
        if '$(' in item:raise RuntimeError('Unresolved build placeholder: '+item)
        return item
    if isinstance(item,list):return [expand(x) for x in item]
    if isinstance(item,dict):return {k:expand(v) for k,v in item.items()}
    return item
info=expand(info)
pins=plistlib.loads((r/'Resources/PinConfigs.kext/Contents/Info.plist').read_bytes())
info['IOKitPersonalities'].update(pins['IOKitPersonalities'])
bundle=build/'AppleALC.kext/Contents';(bundle/'MacOS').mkdir(parents=True,exist_ok=True)
shutil.copy2(binary,bundle/'MacOS/AppleALC');(bundle/'Info.plist').write_bytes(plistlib.dumps(info,sort_keys=False))
print('BUNDLE',bundle.parent)

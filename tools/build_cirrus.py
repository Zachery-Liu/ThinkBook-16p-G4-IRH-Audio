from pathlib import Path
import subprocess, plistlib, sys
REPO=Path(__file__).resolve().parents[1]
root=REPO/'src/CirrusAudioFixup'
SDK=REPO/'deps/MacKernelSDK'
LILU=REPO/'vendor/Lilu'
if not (root/'CirrusAudioFixup/Devices/Amplifiers/CS35L41/Resources/Generated/FirmwareData.inc').is_file():
 raise SystemExit('Missing local OEM firmware: run tools/embed_firmware.py first')
if not (SDK/'Headers').is_dir():raise SystemExit('Missing deps/MacKernelSDK')
mode=sys.argv[1] if len(sys.argv)>1 else 'Debug'
assert mode in ['Debug','Release']
legacy='--legacy-key-timing' in sys.argv[2:]
dest=root/('build/CLT-'+mode+('-legacy-keys' if legacy else ''))
dest.mkdir(parents=True,exist_ok=True)
compiler=subprocess.check_output(['xcrun','--find','clang++'],text=True).strip()
sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
flags=['-arch','x86_64','-std=c++17','-mkernel','-fapple-kext','-fno-exceptions','-fno-rtti','-fno-common','-fno-builtin','-nostdinc++','-g','-O0','-DKERNEL','-DKERNEL_PRIVATE','-DDRIVER_PRIVATE','-DAPPLE','-DNeXT','-DDEBUG=1','-isysroot',sdk,'-mmacosx-version-min=11.0','-I'+str(SDK/'Headers'),'-I'+str(SDK/'Headers/bsd'),'-I'+str(LILU),'-I'+str(root/'CirrusAudioFixup')]
if mode=='Release':
 flags=[('-Os' if x=='-O0' else x) for x in flags if x!='-DDEBUG=1']
flags+=['-ffreestanding']
if legacy:flags+=['-DCIRRUS_LEGACY_KEY_TIMING=1']
flag_record=dest/'compiler-flags.txt'
flag_text='\n'.join(flags)
if not flag_record.exists() or flag_record.read_text()!=flag_text:
 for stale in dest.glob('*.o'):stale.unlink()
 flag_record.write_text(flag_text)
objects=[]
for source in sorted((root/'CirrusAudioFixup').rglob('*.cpp')):
 obj=dest/(str(source.relative_to(root)).replace('/','_')+'.o')
 if not obj.exists() or obj.stat().st_mtime<max(p.stat().st_mtime for p in (root/'CirrusAudioFixup').rglob('*') if p.is_file()):
  print('Compile',source.relative_to(root),flush=True)
  subprocess.run([compiler,*flags,'-c',str(source),'-o',str(obj)],check=True)
 objects.append(str(obj))
bundle=dest/'CirrusAudioFixup.kext/Contents';(bundle/'MacOS').mkdir(parents=True,exist_ok=True)
info=plistlib.loads((root/'CirrusAudioFixup/Info.plist').read_bytes());(bundle/'Info.plist').write_bytes(plistlib.dumps(info,sort_keys=False))
module=dest/'kmod.c'
module.write_text('''#include <mach/mach_types.h>
#include <mach/kmod.h>
extern kern_return_t CirrusAudioFixup_start(kmod_info_t *, void *);
extern kern_return_t CirrusAudioFixup_stop(kmod_info_t *, void *);
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(com.hoaugtr.CirrusAudioFixup, "1.1.1", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = CirrusAudioFixup_start;
__private_extern__ kmod_stop_func_t *_antimain = CirrusAudioFixup_stop;
__private_extern__ int _kext_apple_cc = __APPLE_CC__;
''')
if mode=='Release':
 # Recent CLT optimizers lower zero initialization to the userspace spelling
 # __bzero. Resolve it locally through the existing kernel memset import.
 with module.open('a') as f:
  f.write('''
#include <string.h>
__attribute__((noinline,optnone)) void __bzero(void *destination, size_t count) {
    (void)memset(destination, 0, count);
}
''')
obj=dest/'kmod.o'
subprocess.run([compiler,*[x for x in flags if x!='-std=c++17'],'-x','c','-c',str(module),'-o',str(obj)],check=True)
objects.append(str(obj))
binary=bundle/'MacOS/CirrusAudioFixup'
subprocess.run([compiler,'-arch','x86_64','-mkernel','-nostdlib','-isysroot',sdk,'-mmacosx-version-min=11.0','-Wl,-kext','-Wl,-undefined,dynamic_lookup',*objects,'-L'+str(SDK/'Library/x86_64'),'-lkmod','-lcc_kext','-o',str(binary)],check=True)
subprocess.run(['dsymutil',str(binary),'-o',str(bundle.parent)+'.dSYM'],check=True)
subprocess.run([sys.executable,str(root/'Tools/Build/verify_kext_vtables.py'),str(binary)],check=True)
subprocess.run(['lipo',str(binary),'-verify_arch','x86_64'],check=True)
print('BUILT',bundle.parent)

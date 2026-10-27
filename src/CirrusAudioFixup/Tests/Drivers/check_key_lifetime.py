"""Validate the reference external-boost key lifetime and failure cleanup.

This checks sequencing against the Linux reference, not analog audibility.
"""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
CPP=r'''
#include "Devices/Amplifiers/CS35L41/Playback.hpp"
#include <cassert>
#include <map>
#include <vector>
using namespace cirrus::devices::amplifiers::cs35l41;
struct Port:cirrus::core::RegisterIO {
 std::map<uint32_t,uint32_t> r;std::vector<std::pair<uint32_t,uint32_t>> log;
 unsigned calls=0,failAt=0,key=0;bool locked=true,pup=true,mail=true;
 bool step(){return ++calls!=failAt;}
 bool read(uint32_t a,uint32_t* v)override{if(!step())return false;*v=r[a];return true;}
 bool write(uint32_t a,uint32_t v)override{
  log.push_back({a,v});if(!step())return false;
  if(a==0x40){if(v==0x55)key=1;else if(v==0xaa&&key==1){locked=false;key=0;}else if(v==0xcc)key=2;else if(v==0x33&&key==2){locked=true;key=0;}}
  if(a==0x10010)r[a]&=~v;else r[a]=v;
  if(a==0x2014&&pup)r[0x10010]|=(v&1)?0x1000000:0x800000;
  if(a==0x13020&&mail)r[0x13004]=v==1?1:0;
  return true;
 }
 bool updateBits(uint32_t a,uint32_t m,uint32_t v)override{uint32_t old;return read(a,&old)&&write(a,(old&~m)|(v&m));}
 bool bulkRead(uint32_t,uint8_t*,size_t)override{return false;}
 bool bulkWrite(uint32_t,const uint8_t*,size_t)override{return false;}
 bool pollBit(uint32_t,uint32_t,uint32_t,uint32_t)override{return false;}
};
int main(){
 for(bool reference:{false,true})for(bool dsp:{false,true}){
  Port p;p.r[0x10098]=2;PlaybackTransition s;
  for(unsigned ms=0;ms<20&&s.phase!=PlaybackPhase::Prepared;++ms){
   assert(Playback::advance(p,s,ms,dsp,0x2b01,nullptr,kLegacyPowerConfiguration,reference)!=PlaybackProgress::Failed);
   if(reference&&(s.phase==PlaybackPhase::Pup||s.phase==PlaybackPhase::Output))assert(!p.locked&&s.testKeyOpen);
  }
  assert(s.phase==PlaybackPhase::Prepared&&p.locked&&!s.testKeyOpen);
  if(dsp){size_t enable=0,lastUnlock=0,lockAfter=0;
   for(size_t i=0;i<p.log.size();++i){auto [a,v]=p.log[i];if(a==0x40&&v==0xaa)lastUnlock=i;if(a==0x13020&&v==7){enable=i;if(reference)assert(lastUnlock<i);}if(enable&&a==0x40&&v==0x33)lockAfter=i;}
   assert(enable);if(reference)assert(lockAfter>enable);
  }
 }
 // Cancel while waiting for either PUP or the output command.
 for(auto phase:{PlaybackPhase::Pup,PlaybackPhase::Output}){
  Port p;PlaybackTransition s;s.phase=phase;s.testKeyOpen=true;p.locked=false;
  assert(Playback::closePreparation(p,s)&&p.locked&&!s.testKeyOpen);
 }
 // PUP and mailbox timeouts, unreadable acknowledgements and protection faults
 // all close the window before returning failure.
 for(unsigned kind=0;kind<5;++kind){
  Port p;PlaybackTransition s;s.phase=kind<2?PlaybackPhase::Pup:PlaybackPhase::Output;
  s.testKeyOpen=true;s.deadlineMs=0;p.locked=false;p.r[0x13004]=1;
  if(kind==1)p.r[0x10010]=0x80000000;
  if(kind==3)p.failAt=1;
  if(kind==4)p.r[0x13004]=0xffffff;
  assert(Playback::advance(p,s,100,true,0x2b01,nullptr,kLegacyPowerConfiguration,true)==PlaybackProgress::Failed);
  assert(p.locked&&!s.testKeyOpen);
 }
 // Inject each one-shot failure across the complete power/output path. Any
 // escaped open window is closed by the same cancellation used by the driver.
 Port good;good.r[0x10098]=2;PlaybackTransition g;
 for(unsigned n=0;n<20&&g.phase!=PlaybackPhase::Prepared;++n)Playback::advance(good,g,n,true,0x2b01,nullptr,kLegacyPowerConfiguration,true);
 const unsigned total=good.calls;
 for(unsigned fail=1;fail<=total;++fail){
  Port p;p.failAt=fail;p.r[0x10098]=2;PlaybackTransition s;
  for(unsigned n=0;n<200&&s.phase!=PlaybackPhase::Prepared&&s.phase!=PlaybackPhase::Failed;++n)Playback::advance(p,s,n,true,0x2b01,nullptr,kLegacyPowerConfiguration,true);
  assert(s.phase==PlaybackPhase::Failed);
  if(s.testKeyOpen)assert(Playback::closePreparation(p,s));
  assert(p.locked&&!s.testKeyOpen);
 }
 // One side can be prepared while its peer fails; cancel both before commit.
 Port l,r;l.r[0x10098]=r.r[0x10098]=2;r.pup=false;PlaybackTransition a,b;
 for(unsigned n=0;n<200&&b.phase!=PlaybackPhase::Failed;++n){if(a.phase!=PlaybackPhase::Prepared)Playback::advance(l,a,n,true,0x2b01,nullptr,kLegacyPowerConfiguration,true);Playback::advance(r,b,n,true,0x2b01,nullptr,kLegacyPowerConfiguration,true);}
 assert(b.phase==PlaybackPhase::Failed&&l.locked&&r.locked);
 assert(Playback::closePreparation(l,a)&&Playback::closePreparation(r,b));
}
'''
with tempfile.TemporaryDirectory(prefix='cirrus-keys-') as t:
 p=Path(t);(p/'test.cpp').write_text(CPP)
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(ROOT/'CirrusAudioFixup'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS reference key lifetime, legacy timing, cancellation, timeout/protection, transfer failure injection and stereo cancellation (ASan/UBSan)')

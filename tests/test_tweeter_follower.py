from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
CPP=r'''
#include "ThinkBookTweeterFollower.hpp"
#include <cassert>
#include <map>
#include <tuple>
#include <vector>
using F=ThinkBookTweeterFollower;
struct IO {
 std::map<std::tuple<unsigned,unsigned,unsigned>,unsigned> r;
 std::vector<std::pair<unsigned,unsigned>> writes;
 unsigned calls=0,failAt=0;bool same=true,stuckPower=false,changeBeforeUnmute=false;
 IO(){r[{0,0xf00,0}]=0x10ec0287;r[{2,0xa00,0}]=0x31;r[{2,0xf06,0}]=0x10;
 r[{0x17,0xf07,0}]=0x40;r[{0x17,0xf05,0}]=0;r[{2,0xf05,0}]=0;
 r[{0x14,0xf05,0}]=0x33;r[{0x14,0xb00,0xa000}]=r[{0x14,0xb00,0x8000}]=0x80;
 r[{0x14,0xf02,0}]=2;r[{0x14,0xf00,0xc}]=0x10000;r[{0x14,0xf0c,0}]=2;}
 bool unchanged(){return same;}
 bool get(unsigned n,unsigned v,unsigned a,unsigned& val){if(++calls==failAt)return false;val=r[{n,v,a}];return true;}
 bool set(unsigned v,unsigned a){
  assert((v==0x705&&(a==0||a==3))||(v==0x707&&(a==0||a==0x40))||
    (v==0x300&&(a==0xb000||a==0xa080||a==0x9080)));
  writes.push_back({v,a});if(++calls==failAt)return false;
  if(v==0x705&&!stuckPower)r[{0x14,0xf05,0}]=a|(a<<4);
  if(v==0x707)r[{0x14,0xf07,0}]=a;
  if(v==0x300){if(a==0xb000)r[{0x14,0xb00,0xa000}]=r[{0x14,0xb00,0x8000}]=0;
   if(a==0xa080)r[{0x14,0xb00,0xa000}]=0x80;if(a==0x9080)r[{0x14,0xb00,0x8000}]=0x80;}
  if(changeBeforeUnmute&&v==0x707&&a==0x40){r[{0x21,0xf09,0}]=0x80000000;}
  return true;
 }
 bool muted(){return r[{0x14,0xb00,0xa000}]==0x80&&r[{0x14,0xb00,0x8000}]==0x80;}
};
void finish(F& f,IO& io,unsigned start=0){for(unsigned t=start;t<=start+300;t+=10)if(f.step(io,t)==F::Progress::Done)return;assert(false);}
int main(){
 IO good;F g;finish(g,good);assert(g.owned&&!g.fault&&g.phase==F::Phase::Active);
 unsigned total=good.calls;
 assert(good.writes.size()==3&&good.writes[0]==std::make_pair(0x705U,0U)&&good.writes[1]==std::make_pair(0x707U,0x40U)&&good.writes[2]==std::make_pair(0x300U,0xb000U));
 // Unsupported format, channel offsets, headphones, wrong codec/connection,
 // power not actually D0 and disabled EAPD must never activate Pin14.
 for(unsigned k=0;k<10;++k){IO io;F f;
  if(k==0)io.r[{2,0xa00,0}]=0x33;if(k==1)io.r[{2,0xf06,0}]=0x12;
  if(k==2)io.r[{0x21,0xf09,0}]=0x80000000;if(k==3)io.r[{0x21,0xf07,0}]=0xc0;
  if(k==4)io.r[{0,0xf00,0}]=0x10ec0298;if(k==5)io.r[{0x14,0xf02,0}]=3;
  if(k==6)io.r[{0x17,0xf05,0}]=0x30;if(k==7)io.r[{0x14,0xf0c,0}]=0;
  if(k==8)io.r[{2,0xf06,0}]=0;if(k==9)io.r[{0x17,0xf07,0}]=0;
  finish(f,io);assert(io.writes.empty()&&!f.owned);
 }
 // Do not take ownership of another live path or an unknown gain/mute state.
 for(unsigned k=0;k<3;++k){IO io;F f;if(k==0)io.r[{0x14,0xf07,0}]=0x40;if(k==1)io.r[{0x14,0xf05,0}]=0;if(k==2)io.r[{0x14,0xb00,0xa000}]=0x81;finish(f,io);assert(io.writes.empty());}
 // Stop, headphone selection and sleep tear down only Pin14, without writes
 // to the DAC or Pin17. Reactivation is event-driven, not periodic polling.
 for(unsigned k=0;k<3;++k){IO io;F f;finish(f,io);
  if(k==0)io.r[{2,0xf06,0}]=0;if(k==1)io.r[{0x21,0xf09,0}]=0x80000000;if(k==2)io.r[{2,0xf05,0}]=0x33;
  finish(f,io,100);assert(!f.owned&&io.muted()&&io.r[std::make_tuple(0x14U,0xf07U,0U)]==0);
 }
 // All one-shot activation failures clean up without unmuting another route.
 for(unsigned k=1;k<=total;++k){IO io;F f;io.failAt=k;finish(f,io);assert(f.fault&&io.muted()&&!f.owned);}
 // Every restoration write failure is latched, even if later readback is safe.
 for(unsigned k=1;k<=4;++k){IO io;F f;finish(f,io);io.r[{2,0xf06,0}]=0;
  // The inactive-route snapshot performs 16 GETs before the four writes.
  io.failAt=io.calls+16+k;finish(f,io,100);assert(f.fault);}
 // Power transitions use actual+requested state. No sleep is executed in step.
 {IO io;F f;io.stuckPower=true;finish(f,io);assert(f.fault&&io.muted());}
 // Headphone event after power-up but immediately before unmute aborts safely.
 {IO io;F f;io.changeBeforeUnmute=true;finish(f,io);assert(io.muted()&&!f.owned);for(auto w:io.writes)assert(w!=std::make_pair(0x300U,0xb000U));}
 // Generation changes stop activation until the newest event is processed.
 {IO io;F f;io.same=false;assert(f.step(io,0)==F::Progress::Pending&&io.writes.empty());io.same=true;finish(f,io,10);assert(f.owned);}
 // An external modification of an owned path is restored and fault-latched.
 {IO io;F f;finish(f,io);io.r[{0x14,0xb00,0xa000}]=1;finish(f,io,200);assert(f.fault&&!f.owned&&io.muted());}
}
'''
with tempfile.TemporaryDirectory(prefix='thinkbook-tweeter-') as t:
 p=Path(t);(p/'test.cpp').write_text(CPP)
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(ROOT/'applealc'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS event-driven Pin14: guarded takeover, stereo activation, headphone/stop/sleep restore, transfer faults, generation races and write allowlist (ASan/UBSan)')

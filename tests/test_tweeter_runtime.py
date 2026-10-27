"""Compile the actual deferred runtime with fake kernel scheduling and codec IO."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
STUB=r'''
#pragma once
#include <cassert>
#include <cstdint>
#include <cstring>
#include <string>
#include <map>
#include <vector>
#include <tuple>
using IOReturn=int;constexpr int kIOReturnSuccess=0;
struct IOSimpleLock{bool held=false;};inline IOSimpleLock* heldGuard=nullptr;
inline IOSimpleLock* IOSimpleLockAlloc(){return new IOSimpleLock;}
inline void IOSimpleLockFree(IOSimpleLock* p){delete p;}
inline void IOSimpleLockLock(IOSimpleLock* p){assert(!p->held);p->held=true;heldGuard=p;}
inline void IOSimpleLockUnlock(IOSimpleLock* p){assert(p->held);p->held=false;heldGuard=nullptr;}
struct OSObject{unsigned refs=1;virtual ~OSObject()=default;void retain(){++refs;}void release(){assert(refs);if(!--refs)delete this;}};
struct OSString:OSObject{std::string value;OSString(const char* s):value(s){}bool isEqualTo(const char* s){return value==s;}};
struct OSNumber:OSObject{unsigned value;OSNumber(unsigned v):value(v){}unsigned unsigned32BitValue(){return value;}};
struct OSBoolean:OSObject{};inline OSBoolean trueValue;inline OSObject* kOSBooleanTrue=&trueValue;
struct OSDictionary:OSObject{};
struct OSIterator:OSObject{OSObject* item=nullptr;bool used=false;OSObject* getNextObject(){if(used)return nullptr;used=true;return item;}};
struct IOService:OSObject{
 std::map<std::string,OSObject*> props;std::map<std::string,std::string> published;
 virtual OSObject* getProperty(const char* s){return props[s];}
 void setProperty(const char* k,const char* v){published[k]=v;}
 void setProperty(const char* k,bool v){published[k]=v?"true":"false";}
 static OSDictionary* serviceMatching(const char*){return new OSDictionary;}
 static OSIterator* getMatchingServices(OSDictionary*);
};
inline IOService* board=nullptr;
inline OSIterator* IOService::getMatchingServices(OSDictionary*){auto* i=new OSIterator;i->item=board;return i;}
#define OSDynamicCast(T,p) dynamic_cast<T*>(p)
inline uint64_t nowMs=0;
inline uint64_t mach_absolute_time(){return nowMs*1000000;}
inline void absolutetime_to_nanoseconds(uint64_t t,uint64_t* n){*n=t;}
constexpr unsigned kMillisecondScale=1000000;
inline void clock_interval_to_deadline(unsigned n,unsigned,uint64_t* p){*p=(nowMs+n)*1000000;}
using thread_call_param_t=void*;using thread_call_func_t=void(*)(void*,void*);
struct Call{thread_call_func_t callback;bool pending=false;uint64_t deadline=0;unsigned options=0;};
using thread_call_t=Call*;constexpr unsigned THREAD_CALL_PRIORITY_USER=2,THREAD_CALL_OPTIONS_ONCE=1;
inline Call* thread_call_allocate_with_options(thread_call_func_t fn,void*,unsigned,unsigned options){auto* c=new Call;c->callback=fn;c->options=options;return c;}
inline bool thread_call_enter(Call* c){assert(c->options==THREAD_CALL_OPTIONS_ONCE);bool old=c->pending;c->pending=true;c->deadline=nowMs*1000000;return old;}
inline bool thread_call_enter_delayed(Call* c,uint64_t deadline){bool old=c->pending;c->pending=true;c->deadline=deadline;return old;}
inline bool thread_call_cancel_wait(Call* c){bool p=c->pending;c->pending=false;return p;}
inline bool thread_call_free(Call* c){assert(!c->pending);delete c;return true;}
struct AlcEnabler{uintptr_t orgIOHDACodecDevice_executeVerb=0;inline static AlcEnabler* instance=nullptr;static AlcEnabler* getShared(){return instance;}};
'''
CPP=r'''
#include "ThinkBookTweeterRuntime.hpp"
namespace R=ThinkBookTweeterRuntime;
struct Codec:IOService{
 std::map<std::tuple<unsigned,unsigned,unsigned>,unsigned> r;unsigned reads=0,writes=0;
 bool interruptOnce=false;
 Codec(){r[{0,0xf00,0}]=0x10ec0287;r[{1,0xf20,0}]=0x106b0700;r[{2,0xa00,0}]=0x31;r[{2,0xf06,0}]=0x10;
 r[{0x17,0xf07,0}]=0x40;r[{0x14,0xf05,0}]=0x33;r[{0x14,0xb00,0xa000}]=r[{0x14,0xb00,0x8000}]=0x80;r[{0x14,0xf02,0}]=2;}
};
IOReturn original(void* object,uint16_t n,uint16_t v,uint16_t a,unsigned* out,bool wait){
 assert(!heldGuard&&!wait);auto& c=*static_cast<Codec*>(object);if(v<0x100)v<<=8;
 if(v==0x705||v==0x707||v==0x300){assert(n==0x14);++c.writes;
  if(v==0x705)c.r[{n,0xf05,0}]=a|(a<<4);
  if(v==0x707)c.r[{n,0xf07,0}]=a;
  if(v==0x300){if(a==0xb000)c.r[{n,0xb00,0xa000}]=c.r[{n,0xb00,0x8000}]=0;if(a==0xa080)c.r[{n,0xb00,0xa000}]=0x80;if(a==0x9080)c.r[{n,0xb00,0x8000}]=0x80;}
  *out=0;return 0;
 }
 ++c.reads;*out=c.r[{n,v,a}];
 if(c.interruptOnce&&n==2&&v==0xa00){c.interruptOnce=false;R::notify(&c,0x21,0x707);}
 return 0;
}
void drain(){for(unsigned i=0;i<30&&R::work->pending;++i){auto* w=R::work;nowMs=w->deadline/1000000;w->pending=false;w->callback(nullptr,nullptr);}assert(!R::work->pending);}
int main(){
 AlcEnabler alc;alc.orgIOHDACodecDevice_executeVerb=reinterpret_cast<uintptr_t>(original);AlcEnabler::instance=&alc;
 Codec c;OSNumber vendor(0x10ec0287);c.props["IOHDACodecVendorID"]=&vendor;
 IOService b;board=&b;OSString discovery("THINKBOOK_16P_G4_17AA38A9_VERIFIED_I2C");OSNumber ssid(0x17aa38a9);
 b.props["Cirrus_I2C_Board_Discovery"]=&discovery;b.props["Cirrus_SSID_i2c0"]=b.props["Cirrus_SSID_i2c1"]=&ssid;b.props["Cirrus_Board_Authorized"]=kOSBooleanTrue;
 R::init();assert(R::work&&R::guard);
 // Diagnostic GETs never enqueue work, mutate a pin or call original extra.
 R::notify(&c,2,0xa00);assert(!R::work->pending&&!c.reads&&!c.writes);
 // Wrong HDMI identity never enters the worker.
 vendor.value=0x80862800;R::notify(&c,2,2);assert(!R::work->pending);vendor.value=0x10ec0287;
 // Exact-board authorization is mandatory and retained references balance.
 ssid.value=0x17aa38f9;R::notify(&c,2,2);assert(!c.reads&&!c.writes&&c.refs==2);drain();assert(!c.writes&&c.refs==1&&!R::owner);
 ssid.value=0x17aa38a9;
 // Twenty completed audio events coalesce to one work item, without codec IO
 // or waits inside the hook. A new event during the worker cannot enable from
 // its obsolete generation.
 for(unsigned i=0;i<20;++i)R::notify(&c,2,2);assert(!c.reads&&!c.writes&&c.refs==2);
 c.interruptOnce=true;drain();assert(R::follower.owned&&!R::follower.fault&&c.writes==3&&c.refs==2);
 assert(c.published["ThinkBookTweeterFollower"]=="ACTIVE_PIN14_VERIFIED");
 // Quiescent playback has no periodic callback remaining.
 assert(!R::work->pending);
 // The headphone route change schedules a bounded restore, preserving bass.
 c.r[{0x21,0xf09,0}]=0x80000000;R::notify(&c,0x21,0x707);drain();assert(!R::follower.owned&&c.writes==7);
 assert(c.r[std::make_tuple(0x14U,0xb00U,0xa000U)]==0x80);
 R::deinit();assert(c.refs==1&&!R::work);
 unsigned reads=c.reads,writes=c.writes;R::notify(&c,2,2);assert(c.reads==reads&&c.writes==writes);
 IOSimpleLockFree(R::guard);R::guard=nullptr;
}
'''
with tempfile.TemporaryDirectory(prefix='thinkbook-runtime-') as t:
 p=Path(t)
 for name in ('IOKit/IOLib.h','IOKit/IOService.h','kern/thread_call.h','libkern/c++/OSBoolean.h','libkern/c++/OSNumber.h','libkern/c++/OSString.h'):
  f=p/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('#include "fake.hpp"\n')
 (p/'fake.hpp').write_text(STUB);(p/'test.cpp').write_text(CPP)
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(p),'-I'+str(ROOT/'applealc'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS production deferred runtime: no extra codec IO or waits inside hook; exact-board gate, event coalescing, ONCE serialization, generation race, headphones, no idle polling and retained lifetimes (ASan/UBSan)')

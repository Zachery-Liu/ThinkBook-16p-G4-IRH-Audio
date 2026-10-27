#pragma once
#include "ThinkBookTweeterFollower.hpp"
#include <IOKit/IOLib.h>
#include <IOKit/IOService.h>
#include <kern/thread_call.h>
#include <libkern/c++/OSBoolean.h>
#include <libkern/c++/OSNumber.h>
#include <libkern/c++/OSString.h>

// This resident Lilu plugin coalesces HDA state events into one serialized
// work item. The audio hook never sleeps or runs extra codec transactions.
namespace ThinkBookTweeterRuntime {
using VerbCall=IOReturn(*)(void*,uint16_t,uint16_t,uint16_t,unsigned int*,bool);
static IOSimpleLock* guard=nullptr;
static thread_call_t work=nullptr;
static IOService* pending=nullptr;
static IOService* owner=nullptr;
static uint32_t generation=0;
static bool stopping=false;
static ThinkBookTweeterFollower follower;
inline uint64_t milliseconds() {
    uint64_t ns=0;absolutetime_to_nanoseconds(mach_absolute_time(),&ns);return ns/1000000;
}
static bool boardVerified() {
    auto* match=IOService::serviceMatching("CirrusAudioFixup");
    auto* iter=match?IOService::getMatchingServices(match):nullptr;
    if(match)match->release();
    if(!iter)return false;
    bool valid=false;
    while(auto* service=OSDynamicCast(IOService,iter->getNextObject())) {
        auto* discovery=OSDynamicCast(OSString,service->getProperty("Cirrus_I2C_Board_Discovery"));
        auto* left=OSDynamicCast(OSNumber,service->getProperty("Cirrus_SSID_i2c0"));
        auto* right=OSDynamicCast(OSNumber,service->getProperty("Cirrus_SSID_i2c1"));
        if(discovery&&discovery->isEqualTo("THINKBOOK_16P_G4_17AA38A9_VERIFIED_I2C")&&
            left&&right&&left->unsigned32BitValue()==0x17aa38a9&&right->unsigned32BitValue()==0x17aa38a9&&
            service->getProperty("Cirrus_Board_Authorized")==kOSBooleanTrue) {valid=true;break;}
    }
    iter->release();return valid;
}
struct IO {
    VerbCall call;IOService* codec;uint32_t token;
    bool unchanged() {
        IOSimpleLockLock(guard);bool same=!stopping&&generation==token;IOSimpleLockUnlock(guard);return same;
    }
    bool get(unsigned nid,unsigned verb,unsigned arg,unsigned& value) {
        return call(codec,nid,(verb&255)?verb:verb>>8,arg,&value,false)==kIOReturnSuccess;
    }
    bool set(unsigned verb,unsigned arg) {
        // Every extra write is confined to the known analog Pin14 switches.
        if(!((verb==0x705&&(arg==0||arg==3))||(verb==0x707&&(arg==0||arg==0x40))||
            (verb==0x300&&(arg==0xb000||arg==0xa080||arg==0x9080))))return false;
        unsigned ignored=0;
        return call(codec,0x14,(verb&255)?verb:verb>>8,arg,&ignored,false)==kIOReturnSuccess;
    }
};
static void run(thread_call_param_t,thread_call_param_t) {
    IOSimpleLockLock(guard);
    IOService* codec=pending;pending=nullptr;
    if(!codec&&owner){codec=owner;codec->retain();}
    uint32_t token=generation;bool stop=stopping;
    IOSimpleLockUnlock(guard);
    if(!codec)return;
    auto* alc=AlcEnabler::getShared();
    auto call=alc?reinterpret_cast<VerbCall>(alc->orgIOHDACodecDevice_executeVerb):nullptr;
    if(stop||!call){codec->release();return;}
    IO io{call,codec,token};
    if(!owner) {
        unsigned vendor=0,ssid=0;
        if(!boardVerified()) {codec->setProperty("ThinkBookTweeterFollower","WAITING_BOARD_IDENTITY");codec->release();return;}
        if(!io.get(0,0xf00,0,vendor)||vendor!=0x10ec0287||
            !io.get(1,0xf20,0,ssid)||(ssid!=0x17aa38a9&&ssid!=0x106b0700)) {
            codec->setProperty("ThinkBookTweeterFollower","CODEC_IDENTITY_REJECTED");codec->release();return;
        }
        IOSimpleLockLock(guard);owner=codec;owner->retain();IOSimpleLockUnlock(guard);
    }
    auto progress=follower.step(io,milliseconds());
    codec->setProperty("ThinkBookTweeterFollower",follower.verdict);
    codec->setProperty("ThinkBookTweeterFollowerVersion","G4-17AA38A9-event-v1");
    codec->setProperty("ThinkBookTweeterFollowerFault",follower.fault);
    codec->setProperty("ThinkBookTweeterFollowerOwned",follower.owned);
    IOSimpleLockLock(guard);bool again=!stopping&&generation!=token;stop=stopping;IOSimpleLockUnlock(guard);
    if(!stop) {
        if(again)thread_call_enter(work);
        else if(progress==ThinkBookTweeterFollower::Progress::Pending) {
            uint64_t deadline=0;clock_interval_to_deadline(10,kMillisecondScale,&deadline);
            thread_call_enter_delayed(work,deadline);
        }
    }
    codec->release();
}
static void init() {
    guard=IOSimpleLockAlloc();
    if(guard)work=thread_call_allocate_with_options(run,nullptr,THREAD_CALL_PRIORITY_USER,THREAD_CALL_OPTIONS_ONCE);
    if(!work&&guard){IOSimpleLockFree(guard);guard=nullptr;}
}
static void notify(void* device,uint16_t nid,uint16_t verb) {
    if(!guard||!work)return;
    const bool node=nid==1||nid==2||nid==0x14||nid==0x17||nid==0x21;
    const bool event=verb==0x705||verb==0x707||verb==0x706||verb==2||verb==3||verb==0x200||verb==0x300;
    if(!node||!event)return;
    auto* codec=static_cast<IOService*>(device);
    // Read existing identity properties only. Hardware identity is checked in
    // the worker before the first write; HDMI codec traffic is never followed.
    auto* vendor=OSDynamicCast(OSNumber,codec->getProperty("IOHDACodecVendorID"));
    if(!vendor||vendor->unsigned32BitValue()!=0x10ec0287)return;
    IOSimpleLockLock(guard);
    bool schedule=!stopping&&(!owner||owner==codec)&&(!pending||pending==codec);
    if(schedule){if(!pending){pending=codec;codec->retain();}++generation;}
    if(schedule)thread_call_enter(work);
    IOSimpleLockUnlock(guard);
}
static void deinit() {
    if(!guard)return;
    IOSimpleLockLock(guard);stopping=true;IOSimpleLockUnlock(guard);
    if(work){thread_call_cancel_wait(work);thread_call_free(work);work=nullptr;}
    // Normal use never hot-unloads this plugin. Quiesce owned Pin14 if the
    // framework calls deinit while its original executeVerb is still routed.
    auto* alc=AlcEnabler::getShared();
    if(owner&&follower.owned&&alc&&alc->orgIOHDACodecDevice_executeVerb) {
        IO io{reinterpret_cast<VerbCall>(alc->orgIOHDACodecDevice_executeVerb),owner,generation};
        follower.restore(io,milliseconds());
    }
    if(pending){pending->release();pending=nullptr;}
    if(owner){owner->release();owner=nullptr;}
    // Hook routing is resident for the life of the kernel; leave the guard
    // allocated so a late notify can observe stopping safely.
}
}

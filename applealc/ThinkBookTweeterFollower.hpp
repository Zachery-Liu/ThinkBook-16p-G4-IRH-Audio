// Pin14 follows the existing Pin17/DAC02 stereo route. No format, stream,
// codec-coefficient, EAPD or smart-amplifier writes are permitted here.
#pragma once
#include <stdint.h>
struct ThinkBookTweeterFollower {
    enum class Phase { Idle, PowerWait, Verify, Active, RestoreWait };
    enum class Progress { Done, Pending };
    Phase phase{Phase::Idle};
    bool owned{false}, fault{false};
    uint64_t deadline{0};
    const char* verdict{"IDLE"};
    struct Snapshot {
        unsigned id=0,fgPower=0,format=0,stream=0,p17=0,power17=0,powerDac=0,hpSense=0,hpPin=0;
        unsigned p14=0,power14=0,left=0,right=0,connection=0,pinCaps=0,eapd=0;
        bool active() const {
            return id==0x10ec0287 && !(fgPower&0x1ff) && format==0x31 && (stream>>4)!=0 && !(stream&15) && p17==0x40 &&
                !(power17&0x1ff) && !(powerDac&0x1ff) && !(hpSense&0x80000000U) && !(hpPin&0x40) && connection==2 &&
                (!(pinCaps&0x10000) || eapd==2);
        }
    };
    template<class IO> bool snapshot(IO& io, Snapshot& s) {
        return io.get(0,0xf00,0,s.id) && s.id==0x10ec0287 &&
            io.get(1,0xf05,0,s.fgPower) && io.get(2,0xa00,0,s.format) && io.get(2,0xf06,0,s.stream) &&
            io.get(0x17,0xf07,0,s.p17) && io.get(0x17,0xf05,0,s.power17) &&
            io.get(2,0xf05,0,s.powerDac) && io.get(0x21,0xf09,0,s.hpSense) && io.get(0x21,0xf07,0,s.hpPin) &&
            io.get(0x14,0xf07,0,s.p14) && io.get(0x14,0xf05,0,s.power14) &&
            io.get(0x14,0xb00,0xa000,s.left) && io.get(0x14,0xb00,0x8000,s.right) &&
            io.get(0x14,0xf02,0,s.connection) && io.get(0x14,0xf00,0xc,s.pinCaps) &&
            (!(s.pinCaps&0x10000) || io.get(0x14,0xf0c,0,s.eapd));
    }
    template<class IO> Progress restore(IO& io, uint64_t now) {
        // Attempt every mute/disable even after an earlier transfer fails.
        bool ok=io.set(0x300,0xa080);
        ok=io.set(0x300,0x9080)&&ok;
        ok=io.set(0x707,0)&&ok;
        ok=io.set(0x705,3)&&ok;
        if(!ok)fault=true;
        phase=Phase::RestoreWait;deadline=now+100;
        verdict=ok?"RESTORING":"RESTORE_WRITE_FAILED";
        return Progress::Pending;
    }
    template<class IO> Progress step(IO& io, uint64_t now) {
        Snapshot s;
        if(phase==Phase::RestoreWait) {
            unsigned p=0,power=0,l=0,r=0;
            bool read=io.get(0x14,0xf07,0,p)&&io.get(0x14,0xf05,0,power)&&
                io.get(0x14,0xb00,0xa000,l)&&io.get(0x14,0xb00,0x8000,r);
            if(read&&p==0&&(power&0x1ff)==0x33&&l==0x80&&r==0x80) {
                owned=false;phase=Phase::Idle;verdict=fault?"FAULT_DISABLED":"IDLE";return Progress::Done;
            }
            if(now<deadline)return Progress::Pending;
            fault=true;verdict="RESTORE_UNVERIFIED";return Progress::Done;
        }
        if(!snapshot(io,s)) {
            fault=true;verdict="READ_FAILED";
            return owned?restore(io,now):Progress::Done;
        }
        if(!s.active()) {
            if(owned)return restore(io,now);
            verdict=fault?"FAULT_DISABLED":"ROUTE_INACTIVE";return Progress::Done;
        }
        if(fault) { verdict="FAULT_DISABLED";return owned?restore(io,now):Progress::Done; }
        if(!owned) {
            // Do not take over an output managed by another route or helper.
            if(s.p14!=0||(s.power14&0x1ff)!=0x33||s.left!=0x80||s.right!=0x80) {
                verdict="PIN14_NOT_AVAILABLE";return Progress::Done;
            }
            if(!io.unchanged())return Progress::Pending;
            owned=true;phase=Phase::PowerWait;deadline=now+100;
            if(!io.set(0x705,0)){fault=true;return restore(io,now);}
            verdict="POWER_WAIT";return Progress::Pending;
        }
        if(phase==Phase::PowerWait) {
            if((s.power14&0x1ff)!=0) {
                if(now<deadline)return Progress::Pending;
                fault=true;return restore(io,now);
            }
            if(s.p14!=0||s.left!=0x80||s.right!=0x80){fault=true;return restore(io,now);}
            if(!io.unchanged())return Progress::Pending;
            if(!io.set(0x707,0x40)){fault=true;return restore(io,now);}
            // Repeat the routing checks immediately before unmute. A queued
            // headphone/stop event invalidates this activation generation.
            Snapshot latest;
            const bool readable=snapshot(io,latest);
            if(!readable)fault=true;
            if(!readable||!latest.active()||!io.unchanged())return restore(io,now);
            if(!io.set(0x300,0xb000)){fault=true;return restore(io,now);}
            phase=Phase::Verify;deadline=now+100;verdict="VERIFYING";return Progress::Pending;
        }
        if(s.p14==0x40&&!(s.power14&0x1ff)&&s.left==0&&s.right==0) {
            if(!io.unchanged())return Progress::Pending;
            phase=Phase::Active;verdict="ACTIVE_PIN14_VERIFIED";return Progress::Done;
        }
        if(phase==Phase::Verify&&now<deadline)return Progress::Pending;
        fault=true;return restore(io,now);
    }
};

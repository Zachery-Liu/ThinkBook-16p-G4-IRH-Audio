"""Exercise production telemetry's failure, pacing, lifecycle and JSON contract."""
from pathlib import Path
import json, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
CPP=r'''
#include "Devices/Amplifiers/CS35L41/SignalTelemetry.hpp"
#include <cassert>
#include <iostream>
#include <string>
using namespace cirrus::devices::amplifiers::cs35l41;
uint64_t now=0;
uint64_t clockMs(){return now;}
struct Port:cirrus::core::RegisterIO {
 unsigned reads=0,writes=0;uint32_t bad=0;uint64_t cost=0;
 int32_t lastError() const override{return -99;}
 bool read(uint32_t r,uint32_t* v)override{++reads;now+=cost;*v=0xabcdef;return r!=bad;}
 bool write(uint32_t,uint32_t)override{++writes;return false;}
 bool updateBits(uint32_t,uint32_t,uint32_t)override{++writes;return false;}
 bool bulkWrite(uint32_t,const uint8_t*,size_t)override{++writes;return false;}
 bool bulkRead(uint32_t,uint8_t*,size_t)override{assert(false);return false;}
 bool pollBit(uint32_t,uint32_t,uint32_t,uint32_t)override{assert(false);return false;}
};
int main(){
 SignalControl controls[2]{};strcpy(controls[0].name,"CSPL_ERRORNO");controls[0].address=0x2800010;
 strcpy(controls[1].name,"HALO_HEARTBEAT");controls[1].address=0x2800020;
 char text[SignalTelemetry::jsonCapacity];
 Port io;SignalTelemetry s;s.begin({4,1,0x31},0);
 assert(!s.advance(io,controls,2,0,clockMs)&&!io.reads);
 now=250;assert(!s.advance(io,controls,2,now,clockMs)&&io.reads==4);
 while(s.pending){now+=100;s.advance(io,controls,2,now,clockMs);}
 assert(s.complete&&s.completed==1&&s.cursor==SignalTelemetry::rawCount+2);
 assert(s.format(text,sizeof(text),controls,0x40,true));std::cout<<text<<"\n";
 auto before=io.reads;assert(!s.advance(io,controls,2,now,clockMs)&&io.reads==before);
 now=s.dueMs;while(s.completed<2){s.advance(io,controls,2,now,clockMs);now+=100;}
 before=io.reads;now+=5000;assert(!s.advance(io,controls,2,now,clockMs)&&io.reads==before);
 s.stop(now);s.begin({5,2,0x31},now);assert(s.epoch==2&&s.completed==0);
 io.bad=controls[0].address;now=s.dueMs;
 do{s.advance(io,controls,2,now,clockMs);now+=100;}while(s.pending);
 assert(!s.complete&&s.failures==1);assert(s.format(text,sizeof(text),controls,0x40,true));std::cout<<text<<"\n";
 // Slow reads: never start a second transfer after the slice budget expires.
 SignalTelemetry slow;slow.begin({6,1,0x31},now);now=slow.dueMs;io.cost=5;before=io.reads;
 assert(!slow.advance(io,controls,2,now,clockMs)&&io.reads==before+1);
 // Deadline expires before more I/O: absent entries remain null, unattempted.
 now=slow.startMs+2000;before=io.reads;
 assert(slow.advance(io,controls,2,now,clockMs)&&io.reads==before&&slow.timedOut&&!slow.complete);
 assert(slow.format(text,sizeof(text),controls,0x40,false));std::cout<<text<<"\n";
 SignalTelemetry cancel;cancel.begin({7,1,0x31},now);now=cancel.dueMs;io.cost=0;
 assert(!cancel.advance(io,controls,2,now,clockMs));cancel.stop(now);
 assert(cancel.aborted&&!cancel.complete&&!cancel.pending);
 before=io.reads;assert(!cancel.advance(io,controls,2,now,clockMs)&&io.reads==before);
 assert(!cancel.format(text,20,controls,0x40,true));
 strcpy(controls[0].name,"BAD\"NAME");assert(!s.format(text,sizeof(text),controls,0x40,true));
 assert(io.writes==0);
}
'''
with tempfile.TemporaryDirectory(prefix='cirrus-signal-') as t:
 p=Path(t);(p/'test.cpp').write_text(CPP)
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(ROOT/'CirrusAudioFixup'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 output=subprocess.check_output([str(p/'test')],text=True)
 samples=[json.loads(line) for line in output.splitlines()]
 assert samples[0]['complete'] and samples[0]['reads']['CSPL_ERRORNO']['valid']
 assert samples[1]['reads']['CSPL_ERRORNO']=={'value':None,'attempted':True,'valid':False,'error':-99}
 assert not samples[2]['reads']['SP_RATE_CTRL']['attempted'] and samples[2]['reads']['SP_RATE_CTRL']['value'] is None
 assert samples[2]['timed_out'] and not samples[2]['complete']
print('PASS bounded read-only signal telemetry: pacing, failure/null, timeout, cancellation, epochs, JSON, no writes (ASan/UBSan)')

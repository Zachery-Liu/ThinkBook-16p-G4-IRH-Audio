// Read-only, bounded telemetry. These are slow DSP/register observations,
// never PCM samples or proof of audibility. No telemetry operation writes HW.
#pragma once
#include "Core/RegisterIO.hpp"
#if defined(KERNEL) || defined(_KERNEL) || defined(__KERNEL__)
#include <IOKit/IOLib.h>
#else
#include <stdio.h>
#endif
#include <string.h>

namespace cirrus::devices::amplifiers::cs35l41 {
struct SignalControl { char name[64]{}; uint32_t address{0}; };
struct SignalIdentity {
    uint32_t generation{0}, tag{0}, format{0};
    bool operator==(const SignalIdentity& b) const { return generation == b.generation && tag == b.tag && format == b.format; }
};
class SignalTelemetry {
public:
    struct NamedRegister { const char* name; uint32_t address; };
    // Status registers are non-clearing diagnostic reads. Never read IRQ EINT
    // or protected/unknown registers merely to fill a diagnostic table.
    inline static constexpr NamedRegister raw[] = {
        {"PWR_CTRL1",0x2014}, {"PWR_CTRL2",0x2018}, {"AMP_OUT_MUTE",0x2024},
        {"PLL_CLK_CTRL",0x2c04}, {"GLOBAL_CLK_CTRL",0x2c0c},
        {"SP_ENABLES",0x4800}, {"SP_RATE_CTRL",0x4804}, {"SP_FORMAT",0x4808},
        {"SP_HIZ_CTRL",0x480c}, {"SP_TX_SLOT",0x4810}, {"SP_RX_SLOT",0x4820},
        {"SP_RX_WL",0x4840}, {"DAC_PCM1_SRC",0x4c00},
        {"DSP1_RX1_SRC",0x4c40}, {"DSP1_RX2_SRC",0x4c44},
        {"DSP1_RX5_SRC",0x4c50}, {"DSP1_RX6_SRC",0x4c54},
        {"AMP_DIG_VOL",0x6000}, {"AMP_GAIN",0x6c04}, {"GPIO1_CTRL",0x11008},
        {"IRQ_RAW1",0x10090}, {"IRQ_RAW3",0x10098}, {"MBOX2",0x13004},
        {"DSP_RX1_RATE",0x2b80080}, {"DSP_TX1_RATE",0x2b80280}, {"DSP_ARB_ERROR",0x2bc5a08}
    };
    static constexpr size_t rawCount = sizeof(raw)/sizeof(raw[0]), maxControls = 14, capacity = rawCount + maxControls;
    static constexpr size_t jsonCapacity = 6144;
    struct Reading { uint32_t value{0}; int32_t error{0}; bool attempted{false}, valid{false}; } readings[capacity]{};
    SignalIdentity identity{};
    uint64_t epoch{0}, sequence{0}, startMs{0}, endMs{0}, dueMs{0};
    size_t cursor{0}, controlCount{0};
    unsigned completed{0}, failures{0};
    bool session{false}, pending{false}, complete{false}, aborted{false}, timedOut{false};

    void begin(SignalIdentity id, uint64_t now) {
        identity = id; ++epoch; completed = 0; session = true;
        pending = complete = aborted = timedOut = false; dueMs = now + 250;
    }
    void stop(uint64_t now) {
        session = false;
        if (pending) { pending = false; aborted = true; complete = false; endMs = now; }
    }
    bool advance(core::RegisterIO& io, const SignalControl* controls, size_t count, uint64_t now, uint64_t (*clock)()) {
        if (!session || completed >= 2 || (!pending && now < dueMs)) return false;
        if (!pending) {
            for (auto& r : readings) r = {};
            controlCount = count < maxControls ? count : maxControls;
            ++sequence; startMs = now; cursor = failures = 0;
            complete = aborted = timedOut = false; pending = true;
        }
        auto time = [&]() { return clock ? clock() : now; };
        const uint64_t sliceStart = time();
        // Four reads per existing runtime callback, at most 4 ms between
        // starting transfers. An individual controller timeout is not preemptible.
        for (unsigned n = 0; n < 4 && cursor < rawCount + controlCount; ++n) {
            if (time() - startMs >= 2000) { timedOut = true; break; }
            if (n && time() - sliceStart >= 4) break;
            const size_t index = cursor++;
            const uint32_t address = index < rawCount ? raw[index].address : controls[index-rawCount].address;
            auto& r = readings[index]; r.attempted = true;
            r.valid = io.read(address, &r.value);
            if (!r.valid) { r.error = io.lastError(); ++failures; }
        }
        if (cursor < rawCount + controlCount && !timedOut) return false;
        pending = false; complete = !timedOut && !failures;
        endMs = time(); ++completed; dueMs = endMs + 1000;
        return true;
    }
    // JSON is published as one immutable IORegistry string per sweep. Only
    // fixed raw names and the driver-selected metadata allowlist are accepted.
    bool format(char* out, size_t size, const SignalControl* controls, uint32_t address, bool referenceKeys) const {
        size_t used = 0;
        auto append = [&](const char* fmt, auto... args) {
            if (used >= size) return false;
            int n = snprintf(out+used, size-used, fmt, args...);
            if (n < 0 || size_t(n) >= size-used) { used = size; return false; }
            used += size_t(n); return true;
        };
        if (!append("{\"version\":1,\"epoch\":%llu,\"sequence\":%llu,\"i2c_address\":%u,\"generation\":%u,\"tag\":%u,\"format\":%u,\"start_ms\":%llu,\"end_ms\":%llu,\"complete\":%s,\"aborted\":%s,\"timed_out\":%s,\"failed_reads\":%u,\"registered_controls\":%u,\"key_timing\":\"%s\",\"reads\":{",
            (unsigned long long)epoch,(unsigned long long)sequence,address,identity.generation,identity.tag,identity.format,
            (unsigned long long)startMs,(unsigned long long)endMs,complete?"true":"false",aborted?"true":"false",timedOut?"true":"false",
            failures,unsigned(controlCount),referenceKeys?"reference":"legacy")) return false;
        for (size_t i=0;i<rawCount+controlCount;++i) {
            const char* name = i<rawCount?raw[i].name:controls[i-rawCount].name;
            for (size_t j=0;name[j];++j) {
                char c=name[j]; if (!((c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_')) return false;
            }
            const auto& r=readings[i];
            if (!append("%s\"%s\":{\"value\":",i?",":"",name)) return false;
            if (r.valid) { if (!append("%u",r.value)) return false; }
            else if (!append("%s", "null")) return false;
            if (!append(",\"attempted\":%s,\"valid\":%s,\"error\":%d}",r.attempted?"true":"false",r.valid?"true":"false",r.error)) return false;
        }
        return append("%s", "}}");
    }
};
}

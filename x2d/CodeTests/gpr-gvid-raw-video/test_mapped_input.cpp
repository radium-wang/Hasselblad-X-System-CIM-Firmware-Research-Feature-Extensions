// SPDX-License-Identifier: MIT
#include "mapped_input.h"
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <vector>

struct Writer {
    std::mutex mutex;
    std::condition_variable changed;
    bool blocked = true, entered = false;
};
static int write_bytes(void *user, const uint8_t *, size_t) {
    Writer &writer = *static_cast<Writer *>(user);
    std::unique_lock<std::mutex> lock(writer.mutex);
    writer.entered = true;
    writer.changed.notify_all();
    return writer.changed.wait_for(lock, std::chrono::seconds(3),
                                  [&] { return !writer.blocked; }) ? 0 : -1;
}
static void require(bool value) {
    if (!value) throw std::runtime_error("mapped callback contract failed");
}
int main() {
    Writer writer;
    try {
        gpr_capture_config cfg = {};
        cfg.video = {128, 96, 24, 1, 3, 12, {'R','G','G','B'}};
        cfg.stride_bytes = 273;
        cfg.max_inflight = 1;
        cfg.workspace_bytes = 1024 * 1024;
        gpr_capture_callbacks callbacks = {write_bytes, nullptr, &writer};
        gpr_capture *created = nullptr;
        require(gpr_capture_create(&cfg, &callbacks, &created) == 0);
        std::unique_ptr<gpr_capture, decltype(&gpr_capture_destroy)> owner(created, gpr_capture_destroy);
        std::vector<uint8_t> raw(size_t(cfg.stride_bytes) * 96, 255);
        for (unsigned y = 0; y < 96; ++y)
            for (unsigned x = 0; x < 128; ++x) {
                raw[y * 273 + x * 2] = 0x23;
                raw[y * 273 + x * 2 + 1] = 1;
            }
        gvid_mapped_frame frame = {raw.data(), raw.size(), 128, 96, 273, 12,
                                  GVID_MAPPED_UNKNOWN, 0, 0, "{}", 2};
        require(gvid_submit_mapped(created, &cfg, &frame) == GPR_CAPTURE_INVALID);
        frame.layout = GVID_MAPPED_RGGB_U16_LE_COUNTS;
        frame.size_bytes = 95 * 273 + 256 - 1;
        require(gvid_submit_mapped(created, &cfg, &frame) == GPR_CAPTURE_INVALID);
        frame.size_bytes = raw.size();
        raw[1] = 16; // 4096 exceeds a 12-bit count domain.
        require(gvid_submit_mapped(created, &cfg, &frame) == GPR_CAPTURE_INVALID);
        raw[1] = 1;
        require(gvid_submit_mapped(created, &cfg, &frame) == GPR_CAPTURE_OK);
        {
            std::unique_lock<std::mutex> lock(writer.mutex);
            require(writer.changed.wait_for(lock, std::chrono::seconds(2), [&] { return writer.entered; }));
        }
        frame.index = 1;
        frame.timestamp_ns = 41666666;
        require(gvid_submit_mapped(created, &cfg, &frame) == GPR_CAPTURE_BUSY);
        {
            std::lock_guard<std::mutex> lock(writer.mutex);
            writer.blocked = false;
        }
        writer.changed.notify_all();
        require(gpr_capture_flush(created) == 0);
        // Rejection consumed no index; retry the same index and timestamp.
        require(gvid_submit_mapped(created, &cfg, &frame) == GPR_CAPTURE_OK);
        require(gpr_capture_finish(created) == 0);
        frame.index = 2;
        frame.timestamp_ns *= 2;
        require(gvid_submit_mapped(created, &cfg, &frame) == GPR_CAPTURE_CLOSED);
        gpr_capture_stats stats = {};
        require(gpr_capture_get_stats(created, &stats) == 0);
        require(stats.submitted == 2 && stats.written == 2 && stats.inflight_high_water == 1);
        std::puts("PASS: explicit layout, padded 12-bit rows, bounds/domain, bounded backpressure and retry");
        return 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "%s\n", error.what());
        return 1;
    }
}

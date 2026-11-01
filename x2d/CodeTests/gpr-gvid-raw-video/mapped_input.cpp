// SPDX-License-Identifier: MIT
#include "mapped_input.h"
#include <cstring>

int gvid_submit_mapped(gpr_capture *capture, const gpr_capture_config *cfg,
                       const gvid_mapped_frame *source) {
    if (!capture || !cfg || !source || !source->data ||
        source->layout != GVID_MAPPED_RGGB_U16_LE_COUNTS ||
        source->width != cfg->video.width || source->height != cfg->video.height ||
        source->stride_bytes != cfg->stride_bytes ||
        source->count_bits != cfg->video.sample_bits ||
        std::memcmp(cfg->video.cfa, "RGGB", 4) ||
        (source->count_bits != 12 && source->count_bits != 14 && source->count_bits != 16) ||
        source->width < 48 || source->height < 48 ||
        source->width > GPR_GVID_MAX_DIMENSION || source->height > GPR_GVID_MAX_DIMENSION ||
        uint64_t(source->width) * source->height > GPR_GVID_MAX_PIXELS ||
        source->stride_bytes < uint64_t(source->width) * 2 ||
        source->size_bytes < uint64_t(source->stride_bytes) * (source->height - 1) +
                             uint64_t(source->width) * 2)
        return GPR_CAPTURE_INVALID;
    const uint16_t endian = 1;
    if (*reinterpret_cast<const uint8_t *>(&endian) != 1) return GPR_CAPTURE_INVALID;

    // Byte loads also handle odd row pitch and unaligned mapped addresses.
    // Never include padding in the count-domain check.
    if (source->count_bits < 16) {
        const uint8_t *data = static_cast<const uint8_t *>(source->data);
        const uint32_t limit = 1u << source->count_bits;
        for (uint32_t y = 0; y < source->height; ++y) {
            const uint8_t *row = data + size_t(y) * source->stride_bytes;
            for (uint32_t x = 0; x < source->width; ++x)
                if ((uint32_t(row[2*x]) | (uint32_t(row[2*x+1]) << 8)) >= limit)
                    return GPR_CAPTURE_INVALID;
        }
    }
    gpr_capture_frame frame = {};
    frame.data = source->data;
    frame.size_bytes = source->size_bytes;
    frame.index = source->index;
    frame.timestamp_ns = source->timestamp_ns;
    frame.metadata = source->metadata;
    frame.metadata_size = source->metadata_size;
    // A null release callback selects GPR's copying, row-repacking path.
    return gpr_capture_submit(capture, &frame, 0);
}

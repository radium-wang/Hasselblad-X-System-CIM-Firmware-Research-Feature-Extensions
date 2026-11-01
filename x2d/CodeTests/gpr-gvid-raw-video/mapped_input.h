// SPDX-License-Identifier: MIT
#ifndef GVID_MAPPED_INPUT_H
#define GVID_MAPPED_INPUT_H
#include "gpr_capture.h"
#ifdef __cplusplus
extern "C" {
#endif

/* Normalized application contract, not a declaration of the vendor ABI.
 * The producer must map/synchronize its source and establish Bayer phase,
 * unpacking and count alignment before calling this function. RAW16_OPAQUE
 * alone does not establish any of those properties. */
enum gvid_mapped_layout {
    GVID_MAPPED_UNKNOWN = 0,
    GVID_MAPPED_RGGB_U16_LE_COUNTS = 1
};
typedef struct {
    const void *data;
    size_t size_bytes;
    uint32_t width, height, stride_bytes, count_bits;
    enum gvid_mapped_layout layout;
    uint64_t index, timestamp_ns;
    const void *metadata;
    size_t metadata_size;
} gvid_mapped_frame;

/* cfg must be the unchanged configuration used to create capture.
 * Nonblocking queue admission: BUSY means the caller may drop/retry the frame;
 * a rejected frame consumes no index. On success, RAW rows and metadata have
 * been copied, so the producer may immediately unmap/reuse the source. No
 * source pointer or callback is retained. Row copying itself is synchronous.
 * Call finish/destroy only after producer callbacks have stopped. */
int gvid_submit_mapped(gpr_capture *capture, const gpr_capture_config *cfg,
                       const gvid_mapped_frame *source);
#ifdef __cplusplus
}
#endif
#endif

#include "frame_descriptor_adapter.h"

static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static void put32(uint8_t *p, uint32_t n) {
    p[0] = (uint8_t)n; p[1] = (uint8_t)(n >> 8);
    p[2] = (uint8_t)(n >> 16); p[3] = (uint8_t)(n >> 24);
}

int x2d_adapt_nv12_descriptor(const uint8_t *first, size_t first_bytes,
                             uint64_t backing_bytes, uint8_t *out,
                             size_t out_bytes) {
    uint32_t width, height, stride[2], offset[2], rows[2];
    uint64_t end[2];
    uint8_t result[X2D_FRAME_DONOR_SUBSET] = {0};
    if (!first || !out || first_bytes < X2D_FRAME_OLD_MIN ||
        out_bytes < X2D_FRAME_DONOR_SUBSET || !backing_bytes ||
        backing_bytes > UINT32_MAX)
        return X2D_FRAME_ARGUMENT;
    width = get32(first + 0x38); height = get32(first + 0x3c);
    if (get32(first + 0x28) != 2 || get32(first + 0x80) != 2 ||
        !width || !height || (width & 1) || (height & 1))
        return X2D_FRAME_UNSUPPORTED;
    for (size_t i = 0; i < 2; ++i) {
        const uint8_t *plane = first + 0x40 + 16 * i;
        stride[i] = get32(plane); offset[i] = get32(plane + 4);
        rows[i] = get32(plane + 8);
        /* 64 位算术避免 32 位乘法回绕放行越界；最大乘积加偏移仍可容纳。 */
        end[i] = (uint64_t)offset[i] + (uint64_t)stride[i] * rows[i];
        if (stride[i] < width || rows[i] != (i == 0 ? height : height / 2) ||
            end[i] > backing_bytes)
            return X2D_FRAME_BOUNDS;
    }
    if ((uint64_t)offset[0] < end[1] && (uint64_t)offset[1] < end[0])
        return X2D_FRAME_BOUNDS;
    for (size_t i = 0; i < 0x40; ++i) result[i] = first[i];
    for (size_t i = 0; i < 2; ++i) {
        uint8_t *plane = result + 0x40 + 28 * i;
        put32(plane, stride[i]); put32(plane + 4, offset[i]);
        put32(plane + 12, rows[i]);
    }
    put32(result + 0xb0, 2); put32(result + 0xb4, get32(first + 0x84));
    for (size_t i = 0; i < sizeof(result); ++i) out[i] = result[i];
    return X2D_FRAME_OK;
}

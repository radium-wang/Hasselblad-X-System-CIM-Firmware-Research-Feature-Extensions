/* 合成数据测试，不加载任何原厂程序或访问设备。 */
#include "../../native/frame_descriptor_adapter.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void put(uint8_t *p, size_t at, uint32_t n) {
    for (size_t i = 0; i < 4; ++i) p[at+i] = (uint8_t)(n >> (i*8));
}
static uint32_t get(const uint8_t *p, size_t at) {
    return (uint32_t)p[at] | (uint32_t)p[at+1]<<8 |
           (uint32_t)p[at+2]<<16 | (uint32_t)p[at+3]<<24;
}
int main(void) {
    uint8_t old[0x88] = {0}, out[0xb8 + 16], reference[sizeof(out)];
    const uint32_t uv = 256 + 1344 * 720;
    const uint64_t capacity = uv + 1344 * 360;
    put(old, 0x28, 2); put(old, 0x38, 1280); put(old, 0x3c, 720);
    put(old, 0x40, 1344); put(old, 0x44, 256); put(old, 0x48, 720);
    put(old, 0x50, 1344); put(old, 0x54, uv); put(old, 0x58, 360);
    put(old, 0x80, 2); put(old, 0x84, 123);
    memset(out, 0xa5, sizeof(out));
    assert(x2d_adapt_nv12_descriptor(old, sizeof(old), capacity, out, sizeof(out)) == 0);
    assert(get(out, 0x5c) == 1344 && get(out, 0x60) == uv);
    assert(get(out, 0x68) == 360 && get(out, 0xb0) == 2 && get(out, 0xb4) == 123);
    assert(memcmp(out, old, 0x40) == 0);
    for (size_t i = 0xb8; i < sizeof(out); ++i) assert(out[i] == 0xa5);
    memcpy(reference, out, sizeof(out));
    assert(x2d_adapt_nv12_descriptor(old, 0x87, capacity, out, sizeof(out)) == X2D_FRAME_ARGUMENT);
    assert(x2d_adapt_nv12_descriptor(old, sizeof(old), capacity, out, 0xb7) == X2D_FRAME_ARGUMENT);
    assert(x2d_adapt_nv12_descriptor(NULL, sizeof(old), capacity, out, sizeof(out)) == X2D_FRAME_ARGUMENT);
    assert(x2d_adapt_nv12_descriptor(old, sizeof(old), capacity-1, out, sizeof(out)) == X2D_FRAME_BOUNDS);
    put(old, 0x54, 256);
    assert(x2d_adapt_nv12_descriptor(old, sizeof(old), capacity, out, sizeof(out)) == X2D_FRAME_BOUNDS);
    put(old, 0x54, uv); put(old, 0x40, UINT32_MAX);
    assert(x2d_adapt_nv12_descriptor(old, sizeof(old), capacity, out, sizeof(out)) == X2D_FRAME_BOUNDS);
    put(old, 0x40, 1344); put(old, 0x80, 5);
    assert(x2d_adapt_nv12_descriptor(old, sizeof(old), capacity, out, sizeof(out)) == X2D_FRAME_UNSUPPORTED);
    assert(memcmp(out, reference, sizeof(out)) == 0);
    puts("native descriptor contract PASS; no firmware execution or device access");
    return 0;
}

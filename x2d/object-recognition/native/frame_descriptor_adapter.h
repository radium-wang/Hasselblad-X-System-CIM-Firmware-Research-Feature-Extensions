#ifndef X2D_FRAME_DESCRIPTOR_ADAPTER_H
#define X2D_FRAME_DESCRIPTOR_ADAPTER_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* X2D 4.2.0 -> X2D II 1.3.16.2 原厂帧转换入口子集。
 * 不是完整 DSH frame，也不是 FrameManager 的 0x84 字节记录。
 * 调用方必须在整个调用期间持有有效输入；本模块不获取帧租约。
 * backing_bytes 必须来自真实缓冲区所有者，不能用 width*height 猜测。
 * out 必须与 first 指向的内存不重叠；错误时不修改 out。
 * 不接硬件、AF、模型、LiDAR，不申请内存或复制像素。
 */
enum {
    X2D_FRAME_OK = 0,
    X2D_FRAME_ARGUMENT = -1,
    X2D_FRAME_UNSUPPORTED = -2,
    X2D_FRAME_BOUNDS = -3,
    X2D_FRAME_OLD_MIN = 0x88,
    X2D_FRAME_DONOR_SUBSET = 0xb8
};

int x2d_adapt_nv12_descriptor(const uint8_t *first, size_t first_bytes,
                             uint64_t backing_bytes, uint8_t *out,
                             size_t out_bytes);
#ifdef __cplusplus
}
#endif
#endif

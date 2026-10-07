/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
/* GPL-2.0-or-later. Same lock-free ABI on the static engine and Android bridge. */
#ifndef X2D_DOOM_AUDIO_RING_H
#define X2D_DOOM_AUDIO_RING_H
#include <stdint.h>
#define X2D_AUDIO_MAGIC 0x58444135U
#define X2D_AUDIO_RATE 48000U
#define X2D_AUDIO_CAPACITY 16384U
struct x2d_audio_ring {
    uint32_t magic, rate, channels, capacity;
    uint64_t written, consumed, nonzero;
    uint32_t starts, closed, block_frames, failures;
    uint64_t reserved;
    int16_t samples[X2D_AUDIO_CAPACITY * 2];
};
_Static_assert(__builtin_offsetof(struct x2d_audio_ring, samples)==64,"ring ABI");
_Static_assert(__atomic_always_lock_free(8,0),"64-bit counters must be lock-free");
#endif

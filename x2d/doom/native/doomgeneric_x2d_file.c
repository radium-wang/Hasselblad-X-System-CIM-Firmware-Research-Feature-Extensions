/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
/* GPL-2.0-or-later. Offline platform experiment; no device transport or installer.
 * Plain C Doom core in a separate process, atomic BMP output for a QML Image.
 * The engine must run with cwd and IPC in its own temporary directory.
 */
#define _POSIX_C_SOURCE 200809L
#include "doomgeneric.h"
#include "doomkeys.h"
#include "doomstat.h"
#include "d_event.h"
#include "d_main.h"
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static char ipc[1024];
static uint64_t started;
static uint32_t frame, limit_frames = 350, limit_seconds = 10, mask;
static uint64_t last_input;
static unsigned long last_sequence;
static unsigned last_fire_count;
static long long last_look_total;
static unsigned look_events;
static uint32_t requested_mask;
static uint64_t fire_deadline;
static unsigned short queue[64];
static unsigned read_index, write_index;
static volatile sig_atomic_t stopping;
static const unsigned char keys[] = {KEY_UPARROW, KEY_DOWNARROW, KEY_LEFTARROW,
    KEY_RIGHTARROW, KEY_FIRE, KEY_USE, KEY_ENTER, KEY_ESCAPE, KEY_LALT, KEY_RSHIFT};

static uint64_t now_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) { perror("clock_gettime"); exit(2); }
    return (uint64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static void stop_signal(int n) { (void)n; stopping = 1; }
static void path(char *out, size_t size, const char *name) {
    if (snprintf(out, size, "%s/%s", ipc, name) >= (int)size) exit(2);
}
static void finish(void) {
    char name[1200]; path(name, sizeof name, "engine.done");
    FILE *f = fopen(name, "w"); if (f) { fprintf(f, "%u\n", frame); fclose(f); }
    printf("X2D_DOOM_OFFLINE_DONE frames=%u elapsed_ms=%llu\n", frame,
           (unsigned long long)(now_ms() - started));
    exit(0);
}
static void check_stop(void) {
    char name[1200]; path(name, sizeof name, "exit.request");
    if (stopping || access(name, F_OK) == 0 || now_ms() - started >= limit_seconds * 1000ULL
        || frame >= limit_frames) finish();
}
static unsigned bounded_env(const char *name, unsigned fallback, unsigned max) {
    const char *s = getenv(name); char *end; unsigned long n;
    if (!s) return fallback;
    errno = 0; n = strtoul(s, &end, 10);
    if (errno || !*s || *end || n < 1 || n > max) { fprintf(stderr, "Invalid %s\n", name); exit(2); }
    return (unsigned)n;
}
void DG_Init(void) {
    const char *root = getenv("X2D_DOOM_IPC");
    if (!root || root[0] != '/' || strlen(root) >= sizeof ipc) {
        fprintf(stderr, "X2D_DOOM_IPC must name an existing absolute temporary directory\n"); exit(2);
    }
    strcpy(ipc, root);
    limit_frames = bounded_env("X2D_DOOM_FRAMES", 350, 21000);
    limit_seconds = bounded_env("X2D_DOOM_SECONDS", 10, 600);
    signal(SIGINT, stop_signal); signal(SIGTERM, stop_signal);
    started = now_ms(); last_input = started;
    printf("X2D_DOOM_OFFLINE_READY %dx%d\n", DOOMGENERIC_RESX, DOOMGENERIC_RESY);
}
static void le16(unsigned char *p, unsigned n) { p[0] = n; p[1] = n >> 8; }
static void le32(unsigned char *p, uint32_t n) {
    p[0] = n; p[1] = n >> 8; p[2] = n >> 16; p[3] = n >> 24;
}
void DG_DrawFrame(void) {
    check_stop();
    unsigned char header[54] = {0};
    uint32_t bytes = DOOMGENERIC_RESX * DOOMGENERIC_RESY * 4;
    char tmp[1200], target[1200];
    header[0] = 'B'; header[1] = 'M'; le32(header + 2, 54 + bytes); le32(header + 10, 54);
    le32(header + 14, 40); le32(header + 18, DOOMGENERIC_RESX);
    le32(header + 22, -(int32_t)DOOMGENERIC_RESY); /* Top-down BGRX, BI_RGB. */
    le16(header + 26, 1); le16(header + 28, 32); le32(header + 34, bytes);
    path(tmp, sizeof tmp, "frame.bmp.tmp"); path(target, sizeof target, "frame.bmp");
    FILE *f = fopen(tmp, "wb"); if (!f) { perror("frame output"); exit(2); }
    int ok = fwrite(header, 1, 54, f) == 54 && fwrite(DG_ScreenBuffer, 1, bytes, f) == bytes;
    if (fclose(f) || !ok || rename(tmp, target)) { perror("publish frame"); exit(2); }
    ++frame;
    path(tmp, sizeof tmp, "state.json.tmp"); path(target, sizeof target, "state.json");
    f = fopen(tmp, "w"); if (!f) exit(2);
    fprintf(f, "{\"frame\":%u,\"width\":%d,\"height\":%d,\"elapsedMs\":%llu,\"inputMask\":%u,\"firePressCount\":%u,\"clipAmmo\":%d,\"lookTotal\":%lld,\"lookEvents\":%u,\"viewAngle\":%u}\n",
        frame, DOOMGENERIC_RESX, DOOMGENERIC_RESY, (unsigned long long)(now_ms() - started), mask,
        last_fire_count, players[consoleplayer].ammo[am_clip], last_look_total, look_events,
        players[consoleplayer].mo ? players[consoleplayer].mo->angle : 0);
    if (fclose(f) || rename(tmp, target)) exit(2);
}
void DG_SleepMs(uint32_t ms) {
    check_stop();
    struct timespec t = {ms / 1000, (long)(ms % 1000) * 1000000};
    while (nanosleep(&t, &t) && errno == EINTR) check_stop();
}
uint32_t DG_GetTicksMs(void) { check_stop(); return (uint32_t)(now_ms() - started); }
void DG_SetWindowTitle(const char *title) { (void)title; }

static void update_mask(uint32_t next) {
    for (unsigned i = 0; i < sizeof keys; ++i) {
        uint32_t bit = 1U << i;
        if ((mask ^ next) & bit) {
            unsigned slot = (write_index + 1) % 64;
            if (slot == read_index) { fprintf(stderr, "Input queue overflow\n"); exit(2); }
            queue[write_index] = keys[i] | ((next & bit) ? 0x100 : 0);
            write_index = slot;
        }
    }
    mask = next;
}
int DG_GetKey(int *pressed, unsigned char *key) {
    check_stop();
    if (read_index == write_index) {
        char name[1200]; unsigned long seq; unsigned next, fire_count; long long look; int extra;
        path(name, sizeof name, "input"); FILE *f = fopen(name, "r");
        if (f) {
            int count = fscanf(f, "%lu %u %u %lld %d", &seq, &next, &fire_count, &look, &extra); fclose(f);
            if (count == 5 && extra == 27182 && seq > last_sequence && next < (1U << sizeof keys)
                && look >= -1000000000LL && look <= 1000000000LL) {
                last_sequence = seq; last_input = now_ms(); requested_mask = next;
                if (fire_count > last_fire_count) {
                    last_fire_count = fire_count;
                    // Preserve an ordinary fast shutter tap even if its held snapshot was missed.
                    fire_deadline = now_ms() + 100;
                }
                long long delta = look - last_look_total;
                last_look_total = look;
                if (delta) {
                    if (delta > 2048) delta = 2048;
                    if (delta < -2048) delta = -2048;
                    event_t event = {ev_mouse, 0, (int)delta, 0, 0};
                    D_PostEvent(&event); ++look_events;
                }
            }
        }
        uint32_t effective = requested_mask;
        if (now_ms() < fire_deadline) effective |= 1U << 4;
        if (now_ms() - last_input > 750) effective = 0;
        update_mask(effective); /* Lost UI: release held controls on the next sample. */
    }
    if (read_index == write_index) return 0;
    unsigned short event = queue[read_index]; read_index = (read_index + 1) % 64;
    *pressed = !!(event & 0x100); *key = event & 255; return 1;
}

static int selftest(void) {
    DG_ScreenBuffer = calloc(DOOMGENERIC_RESX * DOOMGENERIC_RESY, sizeof(pixel_t));
    if (!DG_ScreenBuffer) return 2;
    DG_Init();
    for (int y = 0; y < DOOMGENERIC_RESY; ++y)
        for (int x = 0; x < DOOMGENERIC_RESX; ++x)
            DG_ScreenBuffer[y * DOOMGENERIC_RESX + x] =
                ((uint32_t)(x * 255 / DOOMGENERIC_RESX) << 16) |
                ((uint32_t)(y * 255 / DOOMGENERIC_RESY) << 8) | 0x55;
    DG_DrawFrame();
    update_mask((1U << 0) | (1U << 4));
    int pressed; unsigned char key;
    if (!DG_GetKey(&pressed, &key) || !pressed || key != KEY_UPARROW) return 3;
    if (!DG_GetKey(&pressed, &key) || !pressed || key != KEY_FIRE) return 3;
    update_mask(0);
    if (!DG_GetKey(&pressed, &key) || pressed || key != KEY_UPARROW) return 3;
    if (!DG_GetKey(&pressed, &key) || pressed || key != KEY_FIRE) return 3;
    printf("X2D_DOOM_PLATFORM_SELFTEST_PASS\n"); free(DG_ScreenBuffer); return 0;
}
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--platform-selftest")) return selftest();
    doomgeneric_Create(argc, argv);
    while (1) { check_stop(); doomgeneric_Tick(); }
}

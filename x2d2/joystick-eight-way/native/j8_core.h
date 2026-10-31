#ifndef J8_CORE_H
#define J8_CORE_H
#include <stdint.h>
enum { J8_UP=34, J8_RIGHT=49, J8_DOWN=48, J8_LEFT=47 };
/* Emission is one EV_KEY plus SYN_REPORT. Nonzero means abort and clean up. */
typedef int (*j8_emit)(void *, unsigned, int);
typedef struct {
    unsigned held, frame_held, active, pending;
    uint64_t due, last_time;
    unsigned failed, passthrough;
    j8_emit emit;
    void *context;
} j8_state;
void j8_init(j8_state *, j8_emit, void *);
int j8_direction_key(unsigned);
int j8_key(j8_state *, unsigned, int, uint64_t);
int j8_frame(j8_state *, uint64_t);
int j8_tick(j8_state *, uint64_t);
int j8_cancel(j8_state *, uint64_t);
/* Resend actually-held cardinal keys before entering permanent passthrough. */
int j8_disable(j8_state *, uint64_t);
#endif

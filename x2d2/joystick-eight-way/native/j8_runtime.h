#ifndef J8_RUNTIME_H
#define J8_RUNTIME_H
#include "j8_core.h"
typedef struct {unsigned short type,code;int value;} j8_event;
/* Platform callbacks return 0 on success, except next:1 event,0 timer,-1 error.
   Setup creates the virtual device, verifies compositor readiness and neutral
   physical keys, then grabs. Cleanup releases/destroys and always ungrabs. */
typedef struct {
    void *context;
    int (*setup)(void *);
    int (*next)(void *,j8_event *,uint64_t);
    int (*write)(void *,const j8_event *);
    uint64_t (*now)(void *);
    int (*stop)(void *);
    void (*cleanup)(void *);
} j8_platform;
typedef struct {unsigned events,changes;int reason,disabled;} j8_result;
enum {J8_DEADLINE=0,J8_STOP=1,J8_OTHER_BUTTON=2,J8_SETUP=-1,J8_READ=-2,
      J8_WRITE=-3,J8_DROPPED=-4,J8_FORMAT=-5,J8_CLOCK=-6};
int j8_run(j8_platform *,unsigned,j8_result *);
#endif

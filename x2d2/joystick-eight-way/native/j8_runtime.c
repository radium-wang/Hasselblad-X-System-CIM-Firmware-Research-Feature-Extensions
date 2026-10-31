#include "j8_runtime.h"
#include <string.h>
typedef struct {j8_platform *p;j8_result *r;} output;
static int emit(void *opaque,unsigned key,int value) {
    output *o=opaque;
    j8_event event={1,(unsigned short)key,value},syn={0,0,0};
    if (o->p->write(o->p->context,&event) || o->p->write(o->p->context,&syn)) return -1;
    o->r->changes++;return 0;
}
int j8_run(j8_platform *p,unsigned seconds,j8_result *r) {
    j8_state s;output out={p,r};uint64_t start,now,previous,deadline;
    int rc,ready=0;unsigned i; j8_event e;
    unsigned char down[768];
    memset(r,0,sizeof(*r));memset(down,0,sizeof(down));
    j8_init(&s,emit,&out);
    if (seconds<1 || seconds>60 || !p->setup || !p->next || !p->write || !p->now || !p->stop || !p->cleanup) {r->reason=J8_SETUP;return -1;}
    if (p->setup(p->context)) {r->reason=J8_SETUP;goto done;}
    ready=1;start=previous=p->now(p->context);deadline=start+seconds*1000u;
    for (;;) {
        now=p->now(p->context);
        if (now<previous) {r->reason=J8_CLOCK;break;}
        previous=now;
        if (now>=deadline) {r->reason=J8_DEADLINE;break;}
        if (p->stop(p->context)) {r->reason=J8_STOP;break;}
        rc=p->next(p->context,&e,(s.pending && s.due<deadline)?s.due:deadline);
        now=p->now(p->context);
        if (now<previous) {r->reason=J8_CLOCK;break;}
        if (rc<0) {r->reason=J8_READ;break;}
        if (!rc) {if (j8_tick(&s,now)) {r->reason=J8_WRITE;break;}continue;}
        r->events++;
        if (e.type==0 && e.code==3) {r->reason=J8_DROPPED;break;}
        if ((e.type!=0 && e.type!=1) || (e.type==0 && (e.code!=0 || e.value)) ||
            (e.type==1 && (e.code>=768 || e.value<0 || e.value>2))) {r->reason=J8_FORMAT;break;}
        if (e.type==1) {
            if (e.value!=2) down[e.code]=(unsigned char)e.value;
            if (j8_direction_key(e.code)) {
                if (j8_key(&s,e.code,e.value,now)) {r->reason=J8_WRITE;break;}
            } else {
                if (e.value==1 && !s.passthrough) {
                    if (j8_disable(&s,now)) {r->reason=J8_WRITE;break;}
                    r->disabled=1;
                }
                if (p->write(p->context,&e)) {r->reason=J8_WRITE;break;}
            }
        } else {
            if (j8_frame(&s,now) || p->write(p->context,&e)) {r->reason=J8_WRITE;break;}
            if (r->disabled) {
                for (i=0;i<768 && !down[i];i++) {}
                if (i==768) {r->reason=J8_OTHER_BUTTON;break;}
            }
        }
    }
    if (ready && !s.passthrough && !s.failed) (void)j8_cancel(&s,p->now(p->context));
done:
    p->cleanup(p->context);
    return r->reason<0?-1:0;
}

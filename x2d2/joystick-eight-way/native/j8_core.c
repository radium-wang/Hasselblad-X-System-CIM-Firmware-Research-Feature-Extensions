#include "j8_core.h"
#include <string.h>

static unsigned bit(unsigned key) {
    switch (key) {case J8_UP:return 1;case J8_RIGHT:return 2;
    case J8_DOWN:return 4;case J8_LEFT:return 8;default:return 0;}
}
int j8_direction_key(unsigned key) {return bit(key)!=0;}
/* Dedicated stock Linux key codes: T=up-left,H=up-right,R=down-left,P=down-right. */
static unsigned direction(unsigned mask) {
    static const unsigned map[16]={0,34,49,35,48,0,25,0,47,20,0,0,19,0,0,0};
    return map[mask&15];
}
static int clock_ok(j8_state *s,uint64_t now) {
    if (s->failed) return -1;
    if (now<s->last_time) {s->failed=1;return -1;}
    s->last_time=now;return 0;
}
static int send(j8_state *s,unsigned key,int value) {
    if (!key) return 0;
    if (!s->emit || s->emit(s->context,key,value)) {s->failed=1;return -1;}
    return 0;
}
void j8_init(j8_state *s,j8_emit emit,void *context) {
    memset(s,0,sizeof(*s));s->emit=emit;s->context=context;
}
int j8_key(j8_state *s,unsigned key,int value,uint64_t now) {
    unsigned b=bit(key);
    if (clock_ok(s,now) || !b || value<0 || value>2) return -1;
    if (s->passthrough) return send(s,key,value);
    /* Physical repeats do not create output repeats; the stock GUI owns repeat. */
    if (value==1) s->frame_held|=b;
    else if (value==0) s->frame_held&=~b;
    return 0;
}
int j8_tick(j8_state *s,uint64_t now) {
    unsigned key;
    if (clock_ok(s,now)) return -1;
    if (!s->pending || now<s->due) return 0;
    key=s->pending;s->pending=0;
    if (send(s,key,1)) return -1;
    s->active=key;return 0;
}
int j8_frame(j8_state *s,uint64_t now) {
    unsigned next, released;
    if (clock_ok(s,now)) return -1;
    if (s->passthrough) return 0;
    if (s->held==s->frame_held) return j8_tick(s,now);
    released=s->held&~s->frame_held;s->held=s->frame_held;
    next=direction(s->held);
    if (next==s->active && !s->pending) return 0;
    if (s->active) {
        if (send(s,s->active,0)) return -1;
        s->active=0;
    }
    s->pending=next;
    /* Coalesce near-simultaneous presses; release immediately stops old repeat.
       Delay a remaining cardinal 8ms so paired releases don't create a kick. */
    s->due=now+(released?8:4);
    return 0;
}
int j8_cancel(j8_state *s,uint64_t now) {
    unsigned active=s->active;
    if (clock_ok(s,now)) return -1;
    s->held=s->frame_held=s->pending=s->active=0;
    return send(s,active,0);
}
int j8_disable(j8_state *s,uint64_t now) {
    static const unsigned keys[4]={J8_UP,J8_RIGHT,J8_DOWN,J8_LEFT};
    unsigned i,mask=s->frame_held;
    if (clock_ok(s,now)) return -1;
    if (s->passthrough) return 0;
    if (j8_cancel(s,now)) return -1;
    s->passthrough=1;
    for (i=0;i<4;i++) if ((mask&(1u<<i)) && send(s,keys[i],1)) return -1;
    return 0;
}

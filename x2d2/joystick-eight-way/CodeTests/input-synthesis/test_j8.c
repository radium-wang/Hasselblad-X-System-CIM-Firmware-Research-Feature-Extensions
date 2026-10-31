#include "j8_runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef struct {uint64_t at;j8_event event;} timed;
typedef struct {
    uint64_t time,stop_at;timed input[512];unsigned count,index;
    j8_event output[4096];unsigned outputs,fail_write;
    int setup_fail,read_fail,cleanups,setup_calls,resources,held[768];
} fake;
static int core_emit(void *v,unsigned key,int value) {
    fake *f=v;assert(key<768);assert(value==0 || value==1 || value==2);
    if (value==1) assert(!f->held[key]);
    if (!value) assert(f->held[key]);
    if (value!=2) f->held[key]=value;
    f->output[f->outputs++]=(j8_event){1,(unsigned short)key,value};return 0;
}
static void key(j8_state *s,unsigned k,int value,uint64_t at) {
    assert(!j8_key(s,k,value,at));assert(!j8_frame(s,at));
}
static void neutral(fake *f) {unsigned i;for(i=0;i<768;i++) assert(!f->held[i]);}
static void diagonal_tests(void) {
    unsigned v,h,order,release_order,tests=0;
    for(v=0;v<2;v++)for(h=0;h<2;h++)for(order=0;order<2;order++)for(release_order=0;release_order<2;release_order++) {
        fake f={0};j8_state s;unsigned a=v?J8_DOWN:J8_UP,b=h?J8_LEFT:J8_RIGHT;
        unsigned expected=v?(h?19:25):(h?20:35),tmp;
        if(order) {tmp=a;a=b;b=tmp;}
        j8_init(&s,core_emit,&f);key(&s,a,1,0);key(&s,b,1,1);
        assert(!j8_tick(&s,5));assert(f.outputs==1 && f.output[0].code==expected && f.output[0].value==1);
        /* Long hold: raw repeats neither duplicate nor release synthesized key. */
        key(&s,a,2,100);key(&s,b,2,200);assert(!j8_tick(&s,5000));assert(f.outputs==1);
        if(release_order) {tmp=a;a=b;b=tmp;}
        key(&s,a,0,5001);assert(f.outputs==2 && !f.output[1].value);
        key(&s,b,0,5002);assert(!j8_tick(&s,5011));assert(f.outputs==2);neutral(&f);tests++;
    }
    printf("diagonal order/release/hold scenarios=%u\n",tests);
}
static void transitions(void) {
    fake f={0};j8_state s;
    j8_init(&s,core_emit,&f);
    key(&s,J8_UP,1,0);assert(!j8_tick(&s,4));assert(f.held[34]);
    key(&s,J8_RIGHT,1,10);assert(!f.held[34]);assert(!j8_tick(&s,14));assert(f.held[35]);
    key(&s,J8_UP,0,20);assert(!f.held[35]);assert(!j8_tick(&s,27));assert(!f.held[49]);
    assert(!j8_tick(&s,28));assert(f.held[49]);
    key(&s,J8_LEFT,1,30);assert(!f.held[49]);assert(!j8_tick(&s,40));neutral(&f);
    key(&s,J8_LEFT,0,41);assert(!j8_tick(&s,49));assert(f.held[49]);
    assert(!j8_cancel(&s,50));neutral(&f);
    assert(j8_tick(&s,49)<0); /* clock reversal cannot create more input */
    assert(j8_key(&s,49,1,55)<0);
    puts("cardinal/diagonal/conflict/cancel/clock scenarios passed");
}
static int setup(void *v) {fake *f=v;f->setup_calls++;f->resources=1;return f->setup_fail?-1:0;}
static int next(void *v,j8_event *e,uint64_t until) {
    fake *f=v;uint64_t limit=until<f->time+50?until:f->time+50;
    if(f->read_fail) return -1;
    if(f->index<f->count && f->input[f->index].at<=limit) {
        f->time=f->input[f->index].at;*e=f->input[f->index++].event;return 1;
    }
    f->time=limit;return 0;
}
static int write_event(void *v,const j8_event *e) {
    fake *f=v;
    if(f->fail_write && f->outputs+1==f->fail_write) return -1;
    assert(f->outputs<4096);f->output[f->outputs++]=*e;
    if(e->type==1 && e->value!=2)f->held[e->code]=e->value;
    return 0;
}
static uint64_t now(void *v) {return ((fake *)v)->time;}
static int stop(void *v) {fake *f=v;return f->stop_at && f->time>=f->stop_at;}
static void cleanup(void *v) {fake *f=v;f->resources=0;f->cleanups++;memset(f->held,0,sizeof(f->held));}
static j8_platform platform(fake *f) {return (j8_platform){f,setup,next,write_event,now,stop,cleanup};}
static void add(fake *f,uint64_t at,unsigned type,unsigned code,int value) {
    assert(f->count<512);f->input[f->count++]=(timed){at,{(unsigned short)type,(unsigned short)code,value}};
}
static void pair(fake *f,uint64_t at,unsigned code,int value) {add(f,at,1,code,value);add(f,at,0,0,0);}
static void lifecycle(void) {
    fake f={0};j8_platform p;j8_result r;unsigned i;int saw;
    pair(&f,10,34,1);pair(&f,11,49,1);p=platform(&f);
    assert(!j8_run(&p,1,&r));assert(r.reason==J8_DEADLINE);assert(f.cleanups==1&&!f.resources);neutral(&f);
    saw=0;for(i=0;i<f.outputs;i++) if(f.output[i].type==1&&f.output[i].code==35&&f.output[i].value==1)saw++;
    assert(saw==1);
    memset(&f,0,sizeof(f));f.setup_fail=1;p=platform(&f);assert(j8_run(&p,1,&r)<0);assert(f.cleanups==1&&!f.outputs&&!f.resources);
    memset(&f,0,sizeof(f));f.read_fail=1;p=platform(&f);assert(j8_run(&p,1,&r)<0&&r.reason==J8_READ);assert(f.cleanups==1);
    memset(&f,0,sizeof(f));pair(&f,10,34,1);f.fail_write=3;p=platform(&f);assert(j8_run(&p,1,&r)<0&&r.reason==J8_WRITE);assert(f.cleanups==1);neutral(&f);
    memset(&f,0,sizeof(f));pair(&f,10,34,1);add(&f,20,0,3,0);p=platform(&f);assert(j8_run(&p,1,&r)<0&&r.reason==J8_DROPPED);assert(f.cleanups==1);neutral(&f);
    memset(&f,0,sizeof(f));pair(&f,10,34,1);f.stop_at=30;p=platform(&f);assert(!j8_run(&p,1,&r)&&r.reason==J8_STOP);assert(f.cleanups==1);neutral(&f);
    memset(&f,0,sizeof(f));add(&f,10,1,34,7);p=platform(&f);assert(j8_run(&p,1,&r)<0&&r.reason==J8_FORMAT);assert(f.cleanups==1);
    memset(&f,0,sizeof(f));pair(&f,10,34,1);pair(&f,11,49,1);pair(&f,30,46,1);pair(&f,40,34,0);pair(&f,41,49,0);pair(&f,42,46,0);p=platform(&f);
    assert(!j8_run(&p,1,&r)&&r.reason==J8_OTHER_BUTTON&&r.disabled);
    saw=0;for(i=0;i<f.outputs;i++)if(f.output[i].type==1&&f.output[i].code==46)saw++;
    assert(saw==2);assert(f.cleanups==1);neutral(&f);
    puts("deadline/setup/read/write/drop/signal/format/other-button cleanup scenarios passed");
}
static void replay(const char *file) {
    fake f={0};j8_platform p; j8_result result;FILE *in=fopen(file,"rb");
    unsigned char b[24];int64_t sec,usec;uint64_t initial=0;unsigned i,diagonals=0;
    assert(in);
    while(fread(b,1,24,in)==24) {
        unsigned short type,code;int value;uint64_t at;
        memcpy(&sec,b,8);memcpy(&usec,b+8,8);memcpy(&type,b+16,2);memcpy(&code,b+18,2);memcpy(&value,b+20,4);
        at=(uint64_t)sec*1000+(uint64_t)usec/1000;if(!initial)initial=at;
        add(&f,at-initial,type,code,value);
    }
    assert(feof(in));fclose(in);p=platform(&f);assert(!j8_run(&p,45,&result));
    for(i=0;i<f.outputs;i++) {
        j8_event *e=&f.output[i];
        if(e->type==1&&e->value==1&&(e->code==35||e->code==25||e->code==19||e->code==20))diagonals++;
    }
    assert(diagonals>0);assert(f.cleanups==1&&!f.resources);neutral(&f);
    printf("real capture replay: input_events=%u synthesized_diagonal_presses=%u output_events=%u cleanup=1\n",result.events,diagonals,f.outputs);
}
int main(int argc,char **argv) {
    diagonal_tests();transitions();lifecycle();if(argc==2)replay(argv[1]);puts("ALL_OFFLINE_CHECKS_PASSED");return 0;
}

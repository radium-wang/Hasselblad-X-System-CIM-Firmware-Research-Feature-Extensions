/* Temporary, opt-in evdev/uinput adapter. No configuration or service writes. */
#include "j8_runtime.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#ifndef J8_PLATFORM_TEST
#include <linux/input.h>
#endif
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#ifdef J8_PLATFORM_TEST
#include "fake_linux_api.h"
#endif
struct libevdev;struct libevdev_uinput;
extern int libevdev_new_from_fd(int,struct libevdev **);
extern const char *libevdev_get_name(const struct libevdev *);
extern int libevdev_has_event_code(const struct libevdev *,unsigned,unsigned);
extern int libevdev_has_event_type(const struct libevdev *,unsigned);
extern int libevdev_enable_event_code(struct libevdev *,unsigned,unsigned,const void *);
extern void libevdev_set_name(struct libevdev *,const char *);
extern void libevdev_free(struct libevdev *);
extern int libevdev_uinput_create_from_device(const struct libevdev *,int,struct libevdev_uinput **);
extern const char *libevdev_uinput_get_devnode(const struct libevdev_uinput *);
extern int libevdev_uinput_write_event(const struct libevdev_uinput *,unsigned,unsigned,int);
extern void libevdev_uinput_destroy(struct libevdev_uinput *);

typedef struct {int source,uinput,grabbed,weston;struct libevdev *dev;
    struct libevdev_uinput *virtual;unsigned char down[KEY_CNT];} linux_state;
static volatile sig_atomic_t stopping;
static void signal_stop(int signo) {(void)signo;stopping=1;}
static uint64_t now_ms(void *unused) {
    struct timespec t;(void)unused;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) {stopping=1;return 0;}
    return (uint64_t)t.tv_sec*1000u+(uint64_t)t.tv_nsec/1000000u;
}
static int neutral(int fd) {
    unsigned char keys[(KEY_CNT+7)/8];unsigned i;
    memset(keys,0,sizeof(keys));
    if (ioctl(fd,EVIOCGKEY(sizeof(keys)),keys)<0) return 0;
    for (i=0;i<sizeof(keys);i++) if (keys[i]) return 0;
    return 1;
}
static int compositor_opened(int pid,const char *node) {
    char path[128],link[256];DIR *dir;struct dirent *entry;ssize_t n;int found=0;
    snprintf(path,sizeof(path),"/proc/%d/exe",pid);
    n=readlink(path,link,sizeof(link)-1);
    if (n<0) return 0;
    link[n]=0;
    if (strcmp(link,"/system/bin/weston")) return 0;
    snprintf(path,sizeof(path),"/proc/%d/fd",pid);dir=opendir(path);
    if (!dir) return 0;
    while ((entry=readdir(dir))!=NULL) {
        if (entry->d_name[0]=='.' || strlen(entry->d_name)>12) continue;
        snprintf(path,sizeof(path),"/proc/%d/fd/%s",pid,entry->d_name);
        n=readlink(path,link,sizeof(link)-1);
        if (n<0) continue;
        link[n]=0;
        if (!strcmp(link,node)) {found=1;break;}
    }
    closedir(dir);return found;
}
static int setup(void *opaque) {
    linux_state *s=opaque;uint64_t until;const char *name,*node;
    static const unsigned add[4]={KEY_H,KEY_P,KEY_R,KEY_T};unsigned i;
    s->source=open("/dev/input/event0",O_RDONLY|O_NONBLOCK|O_CLOEXEC);
    if (s->source<0 || libevdev_new_from_fd(s->source,&s->dev)<0) return -1;
    name=libevdev_get_name(s->dev);
    if (!name || strcmp(name,"exmcu_input")) return -1;
    if (!libevdev_has_event_code(s->dev,EV_KEY,J8_UP) ||
        !libevdev_has_event_code(s->dev,EV_KEY,J8_RIGHT) ||
        !libevdev_has_event_code(s->dev,EV_KEY,J8_DOWN) ||
        !libevdev_has_event_code(s->dev,EV_KEY,J8_LEFT) ||
        libevdev_has_event_type(s->dev,EV_ABS) || libevdev_has_event_type(s->dev,EV_REL) ||
        libevdev_has_event_type(s->dev,EV_REP) || !neutral(s->source)) return -1;
    for (i=0;i<4;i++) if (libevdev_enable_event_code(s->dev,EV_KEY,add[i],NULL)<0) return -1;
    libevdev_set_name(s->dev,"x2dii-joystick8-temporary");
    s->uinput=open("/dev/uinput",O_RDWR|O_NONBLOCK|O_CLOEXEC);
    if (s->uinput<0 || libevdev_uinput_create_from_device(s->dev,s->uinput,&s->virtual)<0) return -1;
    node=libevdev_uinput_get_devnode(s->virtual);
    if (!node || strncmp(node,"/dev/input/event",16)) return -1;
    until=now_ms(NULL)+3000;
    while (!compositor_opened(s->weston,node)) {
        if (stopping || now_ms(NULL)>=until) return -1;
        usleep(20000);
    }
    /* Kernel grab closes the drain/snapshot race: any nonneutral state aborts.
       Pre-grab queued events are drained only after grabbing, then rechecked. */
    if (ioctl(s->source,EVIOCGRAB,1)<0) return -1;
    s->grabbed=1;
    {
        struct input_event event;
        for (i=0;i<256;i++) {
            ssize_t n=read(s->source,&event,sizeof(event));
            if (n<0 && errno==EAGAIN) break;
            if (n!=sizeof(event)) return -1;
            if (event.type==EV_KEY) return -1; /* User was not neutral while arming. */
        }
        if (i==256 || !neutral(s->source)) return -1;
    }
    puts("J8_READY");fflush(stdout);return 0;
}
static int next(void *opaque,j8_event *event,uint64_t until) {
    linux_state *s=opaque;struct pollfd fd={s->source,POLLIN,0};struct input_event in;
    uint64_t now=now_ms(NULL);int wait=until>now?(int)(until-now):0;ssize_t n;int rc;
    if (wait>50) wait=50;
    rc=poll(&fd,1,wait);
    if (rc<0) return errno==EINTR?0:-1;
    if (!rc) return 0;
    if (fd.revents&(POLLERR|POLLHUP|POLLNVAL)) return -1;
    n=read(s->source,&in,sizeof(in));
    if (n<0 && (errno==EAGAIN || errno==EINTR)) return 0;
    if (n!=sizeof(in)) return -1;
    event->type=in.type;event->code=in.code;event->value=in.value;return 1;
}
static int write_event(void *opaque,const j8_event *event) {
    linux_state *s=opaque;
    if (!s->virtual || libevdev_uinput_write_event(s->virtual,event->type,event->code,event->value)<0) return -1;
    if (event->type==EV_KEY && event->code<KEY_CNT && event->value!=2)
        s->down[event->code]=(unsigned char)event->value;
    return 0;
}
static int stop(void *opaque) {(void)opaque;return stopping!=0;}
static void cleanup(void *opaque) {
    linux_state *s=opaque;unsigned i;
    if (s->virtual) {
        for (i=0;i<KEY_CNT;i++) if (s->down[i])
            (void)libevdev_uinput_write_event(s->virtual,EV_KEY,i,0);
        (void)libevdev_uinput_write_event(s->virtual,EV_SYN,SYN_REPORT,0);
        libevdev_uinput_destroy(s->virtual);s->virtual=NULL;
    }
    if (s->grabbed) {(void)ioctl(s->source,EVIOCGRAB,0);s->grabbed=0;}
    if (s->source>=0) {close(s->source);s->source=-1;}
    if (s->uinput>=0) {close(s->uinput);s->uinput=-1;}
    if (s->dev) {libevdev_free(s->dev);s->dev=NULL;}
}
int main(int argc,char **argv) {
    linux_state state; j8_platform p; j8_result result;long seconds,pid;char *end;
    struct sigaction action;int rc;
    if (argc!=4 || strcmp(argv[1],"--run-test")) {
        puts("offline by default; --run-test SECONDS WESTON_PID (1..60 seconds)");return argc==1?0:2;
    }
    seconds=strtol(argv[2],&end,10);if (*end || seconds<1 || seconds>60) return 2;
    pid=strtol(argv[3],&end,10);if (*end || pid<1 || pid>4194304) return 2;
    memset(&state,0,sizeof(state));state.source=state.uinput=-1;state.weston=(int)pid;
    memset(&action,0,sizeof(action));action.sa_handler=signal_stop;sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT,&action,NULL) || sigaction(SIGTERM,&action,NULL) || sigaction(SIGALRM,&action,NULL)) return 2;
    p=(j8_platform){&state,setup,next,write_event,now_ms,stop,cleanup};
    rc=j8_run(&p,(unsigned)seconds,&result);
    printf("J8_DONE reason=%d events=%u changes=%u disabled=%d resources_closed=%d\n",
           result.reason,result.events,result.changes,result.disabled,
           state.source<0 && state.uinput<0 && !state.virtual && !state.grabbed);
    return rc?1:0;
}

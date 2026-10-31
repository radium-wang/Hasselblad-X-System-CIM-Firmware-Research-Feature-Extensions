/* Exercise the actual Linux adapter with fake device/syscall boundaries. */
#define J8_PLATFORM_TEST
#define main j8_program_main
#include "j8_linux.c"
#undef main
#include <assert.h>
#include <stdarg.h>
struct libevdev {int value;};struct libevdev_uinput {int value;};
static struct {
    int fail,physical,ufd,virtual,grabbed,neutral_calls,dir_index,opened,drained,cleanup_writes;
    uint64_t clock;
} f;
static struct libevdev dev;
static struct libevdev_uinput virt;
static int fake_open(const char *name,int flags,...) {
    (void)flags;
    if (!strcmp(name,"/dev/input/event0")) {if(f.fail==1)return -1;f.physical=1;return 10;}
    assert(!strcmp(name,"/dev/uinput"));if(f.fail==7)return -1;f.ufd=1;return 11;
}
static int fake_close(int fd) {if(fd==10){f.physical=0;f.grabbed=0;}else {assert(fd==11);f.ufd=0;}return 0;}
int libevdev_new_from_fd(int fd,struct libevdev **p) {assert(fd==10);if(f.fail==2)return -1;*p=&dev;return 0;}
const char *libevdev_get_name(const struct libevdev *p) {(void)p;return f.fail==3?"wrong-device":"exmcu_input";}
int libevdev_has_event_code(const struct libevdev *p,unsigned type,unsigned key) {(void)p;(void)type;(void)key;return f.fail!=4;}
int libevdev_has_event_type(const struct libevdev *p,unsigned type) {(void)p;return f.fail==5&&type==EV_ABS;}
int libevdev_enable_event_code(struct libevdev *p,unsigned type,unsigned key,const void *v) {(void)p;(void)v;assert(type==EV_KEY);assert(key==35||key==25||key==19||key==20);return f.fail==6?-1:0;}
void libevdev_set_name(struct libevdev *p,const char *name) {(void)p;assert(!strcmp(name,"x2dii-joystick8-temporary"));}
void libevdev_free(struct libevdev *p) {assert(p==&dev);}
int libevdev_uinput_create_from_device(const struct libevdev *p,int fd,struct libevdev_uinput **out) {(void)p;assert(fd==11);if(f.fail==8)return -1;f.virtual=1;*out=&virt;return 0;}
const char *libevdev_uinput_get_devnode(const struct libevdev_uinput *p) {(void)p;return f.fail==9?NULL:"/dev/input/event8";}
int libevdev_uinput_write_event(const struct libevdev_uinput *p,unsigned type,unsigned code,int value) {(void)p;(void)code;assert(type==EV_SYN||type==EV_KEY);if(type==EV_KEY)assert(value==0);f.cleanup_writes++;return 0;}
void libevdev_uinput_destroy(struct libevdev_uinput *p) {assert(p==&virt);f.virtual=0;}
static int fake_ioctl(int fd,unsigned long request,...) {
    va_list ap;assert(fd==10);va_start(ap,request);
    if(request==EVIOCGRAB) {
        int grab=va_arg(ap,int);
        if(grab) {assert(f.opened&&f.virtual&&f.neutral_calls==1);if(f.fail==12){va_end(ap);return -1;}f.grabbed=1;}
        else {assert(!f.virtual);f.grabbed=0;}
    } else {
        unsigned char *keys=va_arg(ap,unsigned char *);assert(request==EVIOCGKEY(96));
        memset(keys,0,96);f.neutral_calls++;
        if(f.fail==10 || (f.fail==13&&f.neutral_calls==2)) keys[0]=1;
    }
    va_end(ap);return 0;
}
static ssize_t fake_read(int fd,void *buffer,size_t n) {
    assert(fd==10&&n==24);
    if(f.neutral_calls==1 && !f.drained) {
        if(f.fail==14)return 1;
        if(f.fail==15) {struct input_event *e=buffer;memset(e,0,24);e->type=EV_KEY;e->code=34;e->value=1;return 24;}
        f.drained=1;
    }
    errno=EAGAIN;return -1;
}
static int fake_clock_gettime(clockid_t id,struct timespec *t) {assert(id==CLOCK_MONOTONIC);t->tv_sec=(time_t)(f.clock/1000);t->tv_nsec=(long)(f.clock%1000)*1000000;return 0;}
static int fake_usleep(useconds_t t) {f.clock+=t/1000;return 0;}
static ssize_t fake_readlink(const char *name,char *out,size_t size) {
    const char *value=strstr(name,"/exe")?"/system/bin/weston":"/dev/input/event8";
    size_t n=strlen(value);assert(n<size);
    if(f.fail==11)return -1;
    memcpy(out,value,n);if(!strstr(name,"/exe"))f.opened=1;return (ssize_t)n;
}
static DIR *fake_opendir(const char *path) {(void)path;f.dir_index=0;return (DIR *)(uintptr_t)1;}
static struct dirent *fake_readdir(DIR *dir) {static struct dirent e;assert(dir==(DIR *)(uintptr_t)1);if(f.dir_index++)return NULL;memset(&e,0,sizeof(e));strcpy(e.d_name,"9");return &e;}
static int fake_closedir(DIR *dir) {assert(dir==(DIR *)(uintptr_t)1);return 0;}
static int fake_poll(struct pollfd *fds,nfds_t n,int wait) {assert(n==1&&fds->fd==10);f.clock+=(unsigned)wait;return 0;}
int main(void) {
    int fault;unsigned scenarios=0;
    for(fault=0;fault<=15;fault++) {
        linux_state s;int rc;
        memset(&f,0,sizeof(f));f.fail=fault;stopping=0;
        memset(&s,0,sizeof(s));s.source=s.uinput=-1;s.weston=123;
        rc=setup(&s);
        if(!fault) {assert(rc==0&&f.grabbed);s.down[35]=1;}
        else assert(rc<0);
        cleanup(&s);assert(!f.physical&&!f.ufd&&!f.virtual&&!f.grabbed);assert(!s.dev&&!s.virtual&&s.source<0&&s.uinput<0);
        scenarios++;
    }
    {
        char *argv[]={"bridge","--run-test","1","123"};
        memset(&f,0,sizeof(f));stopping=0;
        assert(j8_program_main(4,argv)==0);assert(!f.physical&&!f.ufd&&!f.virtual&&!f.grabbed);
    }
    printf("LINUX_ADAPTER_FAULT_SCENARIOS_PASSED=%u plus CLI deadline cleanup\n",scenarios);return 0;
}

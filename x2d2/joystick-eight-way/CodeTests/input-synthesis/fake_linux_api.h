#ifndef FAKE_LINUX_API_H
#define FAKE_LINUX_API_H
#include <stdint.h>
struct input_event {int64_t sec,usec;unsigned short type,code;int value;};
#define EV_SYN 0
#define EV_KEY 1
#define EV_REL 2
#define EV_ABS 3
#define EV_REP 20
#define SYN_REPORT 0
#define KEY_CNT 768
#define KEY_H 35
#define KEY_P 25
#define KEY_R 19
#define KEY_T 20
#define EVIOCGKEY(n) (0x1000ul+(0*(n)))
#define EVIOCGRAB 0x1001ul
static int fake_open(const char *,int,...);
static int fake_ioctl(int,unsigned long,...);
static ssize_t fake_read(int,void *,size_t);
static int fake_close(int);
static int fake_clock_gettime(clockid_t,struct timespec *);
static int fake_usleep(useconds_t);
static ssize_t fake_readlink(const char *,char *,size_t);
static DIR *fake_opendir(const char *);
static struct dirent *fake_readdir(DIR *);
static int fake_closedir(DIR *);
static int fake_poll(struct pollfd *,nfds_t,int);
#define open fake_open
#define ioctl fake_ioctl
#define read fake_read
#define close fake_close
#define clock_gettime fake_clock_gettime
#define usleep fake_usleep
#define readlink fake_readlink
#define opendir fake_opendir
#define readdir fake_readdir
#define closedir fake_closedir
#define poll fake_poll
#endif

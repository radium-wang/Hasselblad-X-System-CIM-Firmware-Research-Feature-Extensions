/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
/* GPL-2.0-or-later. X2D 4.2.0 stock libaudioclient ABI; dedicated sleep process.
 * Reads the engine's shared RAM ring, closes its stream on exit. No mixer writes.
 */
#include "audio_ring.h"
typedef unsigned long size_t;
extern int open(const char *,int,...),close(int),snprintf(char *,size_t,const char *,...),usleep(unsigned);
extern long write(int,const void *,size_t),lseek(int,long,int);
extern char *getenv(const char *);
extern int strcmp(const char *,const char *);
extern size_t strlen(const char *);
extern void *mmap(void *,size_t,int,int,int,long);
extern int munmap(void *,size_t),access(const char *,int);
extern void _exit(int);
extern void (*signal(int,void (*)(int)))(int);
struct stream_handle {unsigned id,bytes;void *buffer;};
struct audio_frame {void *buffer;unsigned bytes,valid;unsigned char reserved[56];};
_Static_assert(sizeof(struct stream_handle)==16,"stream ABI");
_Static_assert(sizeof(struct audio_frame)==72,"frame ABI");
extern int audio_client_get_dev_volume(const char *,unsigned *);
extern int audio_client_player_open_dev(const char *,const void *,int *);
extern int audio_client_player_close_dev(int);
extern int audio_client_player_open_stream(int,unsigned *,struct stream_handle *);
extern int audio_client_player_close_stream(int,struct stream_handle *);
extern int audio_client_player_write_frame(int,struct audio_frame *);
static volatile int stopping;
static void stopped(int n){(void)n;stopping=1;}
static void log_line(const char *s){write(1,s,strlen(s));write(1,"\n",1);}
static int run(void){
    const char *root=getenv("X2D_DOOM_IPC");char name[1200],exit_path[1200];
    if(!root || root[0]!='/')return 10;
    if(snprintf(name,sizeof name,"%s/audio-ring.bin",root)>=(int)sizeof name)return 10;
    if(snprintf(exit_path,sizeof exit_path,"%s/exit.request",root)>=(int)sizeof exit_path)return 10;
    int fd=-1;
    for(unsigned n=0;n<1600 && !stopping;++n){fd=open(name,2);if(fd>=0 && lseek(fd,0,2)==sizeof(struct x2d_audio_ring))break;if(fd>=0)close(fd);fd=-1;usleep(5000);}
    if(fd<0)return 11;
    struct x2d_audio_ring *r=mmap(0,sizeof *r,3,1,fd,0);close(fd);
    if(r==(void *)-1)return 12;
    if(__atomic_load_n(&r->magic,__ATOMIC_ACQUIRE)!=X2D_AUDIO_MAGIC || r->rate!=48000 || r->channels!=2 || r->capacity!=X2D_AUDIO_CAPACITY){munmap(r,sizeof *r);return 13;}
    unsigned volume[3]={0};int player=-1,error=0;
    struct stream_handle stream={0};unsigned config[11]={48000,16,2,0,2,0,80,0,0,0,0};
    if(audio_client_get_dev_volume("speaker",volume)<0 || audio_client_player_open_dev("speaker",0,&player)<0){munmap(r,sizeof *r);return 14;}
    if(audio_client_player_open_stream(player,config,&stream)<0){audio_client_player_close_dev(player);munmap(r,sizeof *r);return 15;}
    if(!stream.buffer || !stream.bytes || stream.bytes%4 || stream.bytes> X2D_AUDIO_CAPACITY*2)error=16;
    unsigned frames=stream.bytes/4;
    __atomic_store_n(&r->block_frames,frames,__ATOMIC_RELEASE);
    log_line(error?"X2D_DOOM_AUDIO_BAD_BUFFER":"X2D_DOOM_AUDIO_READY");
    uint64_t read=__atomic_load_n(&r->consumed,__ATOMIC_RELAXED),played=0,audible=0;
    unsigned idle=0;
    while(!error && !stopping && access(exit_path,0)!=0){
        uint64_t end=__atomic_load_n(&r->written,__ATOMIC_ACQUIRE);
        if(end<read || end-read>X2D_AUDIO_CAPACITY){error=17;break;}
        if(end-read<frames){
            if(__atomic_load_n(&r->closed,__ATOMIC_ACQUIRE))break;
            if(++idle>1200){error=18;break;}
            usleep(5000);continue;
        }
        idle=0;int16_t *out=stream.buffer;
        for(unsigned i=0;i<frames;++i){unsigned slot=((read+i)%X2D_AUDIO_CAPACITY)*2;out[i*2]=r->samples[slot];out[i*2+1]=r->samples[slot+1];audible+=out[i*2]!=0 || out[i*2+1]!=0;}
        struct audio_frame frame={0};frame.buffer=stream.buffer;frame.bytes=stream.bytes;frame.valid=stream.bytes;
        if(audio_client_player_write_frame(player,&frame)<0){error=19;break;}
        read+=frames;played+=frames;__atomic_store_n(&r->consumed,read,__ATOMIC_RELEASE);
        if(played%48000<frames){
            char text[160];snprintf(text,sizeof text,"X2D_DOOM_AUDIO_FRAMES %llu NONZERO %llu",(unsigned long long)played,(unsigned long long)audible);log_line(text);
        }
    }
    if(error)__atomic_add_fetch(&r->failures,1,__ATOMIC_RELAXED);
    if(audio_client_player_close_stream(player,&stream)<0)error=20;
    if(audio_client_player_close_dev(player)<0)error=21;
    munmap(r,sizeof *r);log_line(error?"X2D_DOOM_AUDIO_FAILED":"X2D_DOOM_AUDIO_CLOSED");return error;
}
__attribute__((constructor)) static void start(void){
    const char *enabled=getenv("X2D_DOOM_AUDIO_BRIDGE");if(!enabled || strcmp(enabled,"1"))return;
    signal(2,stopped);signal(15,stopped);signal(13,(void (*)(int))1);
    _exit(run());
}

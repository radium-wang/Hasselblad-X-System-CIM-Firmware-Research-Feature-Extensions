/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
/* GPL-2.0-or-later. DMX WAD sound mixer; 48 kHz stereo shared RAM, no PCM device. */
#define _POSIX_C_SOURCE 200809L
#include "i_sound.h"
#include "w_wad.h"
#include "z_zone.h"
#include "audio_ring.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

int use_libsamplerate;
float libsamplerate_scale = 1.0f;
static struct x2d_audio_ring *ring;
static int prefixed;
static unsigned cache_bytes;
struct sample { unsigned length, rate; unsigned char data[]; };
struct channel { struct sample *sample; uint64_t position; unsigned step; int vol, sep; };
static struct channel channels[16];
static unsigned le16(const unsigned char *p) { return p[0] | p[1]<<8; }
static unsigned le32(const unsigned char *p) { return le16(p) | le16(p+2)<<16; }
static void shutdown_audio(void) {
    if (ring) {
        __atomic_store_n(&ring->closed,1,__ATOMIC_RELEASE);
        munmap(ring,sizeof *ring);ring=NULL;
    }
}
static boolean init_audio(boolean prefix) {
    const char *root=getenv("X2D_DOOM_IPC");char name[1200];prefixed=prefix;
    if (!root || root[0]!='/' || snprintf(name,sizeof name,"%s/audio-ring.bin",root)>=(int)sizeof name) return false;
    int fd=open(name,O_RDWR|O_CREAT|O_TRUNC,0600);if(fd<0)return false;
    if(ftruncate(fd,sizeof *ring)){close(fd);return false;}
    ring=mmap(NULL,sizeof *ring,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);close(fd);
    if(ring==MAP_FAILED){ring=NULL;return false;}
    memset(ring,0,sizeof *ring);ring->rate=X2D_AUDIO_RATE;ring->channels=2;ring->capacity=X2D_AUDIO_CAPACITY;
    __atomic_store_n(&ring->magic,X2D_AUDIO_MAGIC,__ATOMIC_RELEASE);atexit(shutdown_audio);
    puts("X2D_DOOM_SFX_RING_READY 48000 stereo");return true;
}
static int lump_num(sfxinfo_t *sfx) {
    char name[16];snprintf(name,sizeof name,"%s%.8s",prefixed?"DS":"",sfx->name);
    return W_GetNumForName(name);
}
static struct sample *load_sample(sfxinfo_t *sfx) {
    if(sfx->driver_data)return sfx->driver_data;
    int lump=sfx->lumpnum;
    if(lump<0)lump=lump_num(sfx);
    int bytes=W_LumpLength(lump);if(bytes<40)return NULL;
    const unsigned char *raw=W_CacheLumpNum(lump,PU_STATIC);
    unsigned rate=le16(raw+2),length=le32(raw+4);
    if(le16(raw)!=3 || rate<4000 || rate>48000 || length<32 || length>(unsigned)bytes-8 || length>2097152 || cache_bytes+length>16777216){W_ReleaseLumpNum(lump);return NULL;}
    /* Vanilla DMX includes sixteen guard samples at each end. */
    struct sample *s=malloc(sizeof *s+length-32);
    if(s){s->length=length-32;s->rate=rate;memcpy(s->data,raw+24,s->length);cache_bytes+=s->length;sfx->driver_data=s;}
    W_ReleaseLumpNum(lump);return s;
}
static void params(int c,int vol,int sep) {
    if(c<0 || c>=16)return;
    channels[c].vol=vol<0?0:vol>127?127:vol;channels[c].sep=sep<0?0:sep>255?255:sep;
}
static int start_sound(sfxinfo_t *sfx,int c,int vol,int sep) {
    if(!ring || c<0 || c>=16)return -1;
    struct sample *s=load_sample(sfx);if(!s)return -1;
    channels[c]=(struct channel){s,0,(unsigned)(((uint64_t)s->rate<<16)/X2D_AUDIO_RATE),0,0};params(c,vol,sep);
    __atomic_add_fetch(&ring->starts,1,__ATOMIC_RELAXED);return c;
}
static void stop_sound(int c) {if(c>=0 && c<16)channels[c].sample=NULL;}
static boolean playing(int c) {return c>=0 && c<16 && channels[c].sample!=NULL;}
static void update_audio(void) {
    if(!ring)return;
    uint64_t read=__atomic_load_n(&ring->consumed,__ATOMIC_ACQUIRE),write=__atomic_load_n(&ring->written,__ATOMIC_RELAXED);
    if(read>write || write-read>X2D_AUDIO_CAPACITY){__atomic_add_fetch(&ring->failures,1,__ATOMIC_RELAXED);return;}
    unsigned block=__atomic_load_n(&ring->block_frames,__ATOMIC_ACQUIRE);
    unsigned ahead=block*2;if(ahead<2048)ahead=2048;if(ahead>X2D_AUDIO_CAPACITY/2)ahead=X2D_AUDIO_CAPACITY/2;
    uint64_t target=read+ahead;unsigned nonzero=0;
    for(;write<target;++write){
        int left=0,right=0;
        for(int c=0;c<16;++c){
            struct channel *ch=channels+c;struct sample *s=ch->sample;if(!s)continue;
            unsigned at=ch->position>>16,frac=ch->position&65535;
            if(at>=s->length){ch->sample=NULL;continue;}
            int a=(int)s->data[at]-128,b=at+1<s->length?(int)s->data[at+1]-128:a;
            int value=((a*(65536-(int)frac)+b*(int)frac)>>8);
            /* Preserve engine distance/volume/pan, modest output headroom. */
            left+=value*ch->vol*(255-ch->sep)/127/255/2;
            right+=value*ch->vol*ch->sep/127/255/2;
            ch->position+=ch->step;
        }
        if(left>24000)left=24000;if(left<-24000)left=-24000;
        if(right>24000)right=24000;if(right<-24000)right=-24000;
        unsigned slot=(write%X2D_AUDIO_CAPACITY)*2;
        ring->samples[slot]=(int16_t)left;ring->samples[slot+1]=(int16_t)right;
        nonzero+=left!=0 || right!=0;
    }
    __atomic_add_fetch(&ring->nonzero,nonzero,__ATOMIC_RELAXED);
    __atomic_store_n(&ring->written,write,__ATOMIC_RELEASE);
}
static snddevice_t devices[]={SNDDEVICE_SB};
sound_module_t DG_sound_module={devices,1,init_audio,shutdown_audio,lump_num,update_audio,params,start_sound,stop_sound,playing,NULL};
/* Music is explicitly disabled in this effects-only trial, all hooks remain safe. */
static boolean no_init(void){return false;}static void no_op(void){}
static void no_volume(int v){(void)v;}static void *no_register(void *p,int n){(void)p;(void)n;return NULL;}
static void no_unregister(void *p){(void)p;}static void no_play(void *p,boolean loop){(void)p;(void)loop;}
music_module_t DG_music_module={devices,1,no_init,no_op,no_volume,no_op,no_op,no_register,no_unregister,no_play,no_op,no_init,no_op};

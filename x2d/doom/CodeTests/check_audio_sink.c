/* SPDX-License-Identifier: GPL-2.0-or-later
Copyright (c) 2026 Radium Wang */
/* GPL-2.0-or-later. Host-only real-time ring consumer; captures PCM without speakers. */
#define _DEFAULT_SOURCE
#include "../native/audio_ring.h"
#include <stdio.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
int main(int argc,char **argv){
 if(argc!=3)return 2;int fd=-1;
 for(unsigned n=0;n<1600;++n){fd=open(argv[1],O_RDWR);if(fd>=0 && lseek(fd,0,SEEK_END)==sizeof(struct x2d_audio_ring))break;if(fd>=0)close(fd);fd=-1;usleep(5000);}
 if(fd<0)return 3;
 struct x2d_audio_ring *r=mmap(NULL,sizeof *r,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);close(fd);if(r==MAP_FAILED)return 4;
 for(unsigned n=0;n<200 && __atomic_load_n(&r->magic,__ATOMIC_ACQUIRE)!=X2D_AUDIO_MAGIC;++n)usleep(5000);
 if(r->magic!=X2D_AUDIO_MAGIC)return 5;
 FILE *f=fopen(argv[2],"wb");if(!f)return 6;
 __atomic_store_n(&r->block_frames,1024,__ATOMIC_RELEASE);
 uint64_t read=0,nonzero=0;unsigned idle=0;
 while(1){
  uint64_t end=__atomic_load_n(&r->written,__ATOMIC_ACQUIRE);
  if(end<read || end-read>X2D_AUDIO_CAPACITY)return 7;
  if(end-read<1024){if(__atomic_load_n(&r->closed,__ATOMIC_ACQUIRE))break;if(++idle>1200)return 8;usleep(5000);continue;}
  idle=0;int16_t samples[2048];
  for(unsigned i=0;i<1024;++i){unsigned at=((read+i)%X2D_AUDIO_CAPACITY)*2;samples[i*2]=r->samples[at];samples[i*2+1]=r->samples[at+1];nonzero+=samples[i*2]!=0||samples[i*2+1]!=0;}
  if(fwrite(samples,sizeof samples,1,f)!=1)return 9;
  read+=1024;__atomic_store_n(&r->consumed,read,__ATOMIC_RELEASE);usleep(21333);
 }
 fclose(f);printf("{\"frames\":%llu,\"nonzeroFrames\":%llu,\"soundStarts\":%u,\"failures\":%u}\n",(unsigned long long)read,(unsigned long long)nonzero,r->starts,r->failures);
 munmap(r,sizeof *r);return nonzero?0:10;
}

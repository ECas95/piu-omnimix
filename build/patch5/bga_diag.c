// Diagnostic only (BGA Dark research, keyboard test layer): /SETTINGS/PIU/bga.log. Logs each new (caller, size) of video
// texture uploads and texture binds + draws, and every change of the game globals where player options may live, sampled
// 5 times a second. Counters that change constantly are muted after 8 changes.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/stat.h>
static int fd=-1;static struct timespec t0;
static void logf_(const char*f,unsigned a,unsigned b,unsigned c,unsigned d){char s[160];struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
    int n=snprintf(s,sizeof s,"%ld ",(long)((t.tv_sec-t0.tv_sec)*1000+(t.tv_nsec-t0.tv_nsec)/1000000));n+=snprintf(s+n,sizeof s-n,f,a,b,c,d);if(fd>=0)write(fd,s,n);}
#define SEEN 512
static unsigned seen[SEEN];
static int first(unsigned k){unsigned h=(k*2654435761u)%SEEN;for(int i=0;i<SEEN;i++){unsigned j=(h+i)%SEEN;if(seen[j]==k)return 0;if(!seen[j]){seen[j]=k;return 1;}}return 0;}
void glTexSubImage2D(unsigned tg,int lv,int x,int y,int w,int h,unsigned f,unsigned ty,const void*p){
    static void(*real)(unsigned,int,int,int,int,int,unsigned,unsigned,const void*);if(!real)real=dlsym(RTLD_NEXT,"glTexSubImage2D");
    unsigned c=(unsigned)__builtin_return_address(0);
    if(w>=256&&first(c^(w*65536u+h)))logf_("TEXSUB caller=%x w=%d h=%d fmt=%x\n",c,w,h,f);
    real(tg,lv,x,y,w,h,f,ty,p);}
// second probe: the USB profile / player structs, the rest of the menu block and the per-player gameplay structs (0xab5da00)
static struct{unsigned lo,hi;}R[]={{0xac02640,0xac2d6a0},{0xab12800,0xab20000},{0xe35ce00,0xe35ce40}};
static unsigned *prev[3];static unsigned char *noisy[3];
static void*watch(void*a){(void)a;sleep(3);
    for(int r=0;r<3;r++){unsigned z=R[r].hi-R[r].lo;prev[r]=malloc(z);noisy[r]=calloc(1,z/4);memcpy(prev[r],(void*)R[r].lo,z);}
    for(;;){usleep(100000);for(int r=0;r<3;r++){unsigned n=(R[r].hi-R[r].lo)/4;volatile unsigned*m=(unsigned*)R[r].lo;
        for(unsigned i=0;i<n;i++){unsigned v=m[i];if(v!=prev[r][i]){if(noisy[r][i]<12){noisy[r][i]++;logf_("MEM %x %x -> %x (%u)\n",R[r].lo+i*4,prev[r][i],v,noisy[r][i]);}prev[r][i]=v;}}}}
    return 0;}
__attribute__((constructor)) static void init(void){clock_gettime(CLOCK_MONOTONIC,&t0);mkdir("/SETTINGS/PIU",0777);fd=open("/SETTINGS/PIU/bga.log",O_WRONLY|O_CREAT|O_TRUNC|O_SYNC,0666);pthread_t t;pthread_create(&t,0,watch,0);}

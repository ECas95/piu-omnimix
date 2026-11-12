// Basic Mode list as the ORIGINAL filter, enumerator and comparator build it (real qsort). argv[3] = "hooks" installs our module's hooks, "stock" runs the bare engine.
#define main previous_native_test_main
#include "test_channels.c"
#undef main
int main(int argc,char **argv)
{
    assert(argc==4);load_engine(argv[1]);jump_to(0x8052630,qsort);
    if(!strcmp(argv[3],"hooks"))install_prime2_channel();
    FILE *f=fopen(argv[2],"rb");assert(f);uint32_t header[11];assert(fread(header,1,44,f)==44);
    int ns=header[0],nc=header[1];uint32_t *songs=calloc(ns,36),*charts=calloc(nc,36),*orig=calloc(nc,36);
    assert(fread(songs+9,36,ns-1,f)==(size_t)ns-1);fseek(f,36,SEEK_CUR);
    assert(fread(orig+9,36,nc-1,f)==(size_t)nc-1);fclose(f);
    *(void **)0xac2d6b0=songs;*(int *)0xac2d6a8=ns;*(void **)0xac2d6b4=charts;*(int *)0xac2d6ac=nc;
    *(void **)0xac2d6a0=calloc(nc,8);*(void **)0xac2d6a4=calloc(nc,4);
    unsigned char screen[0x1000]={0};uint32_t *menu[96]={0};
    if(!strcmp(argv[3],"hooks")){for(int i=0;i<67;i++)menu[i]=table+i*5;*(void **)(screen+0x344)=menu;*(void **)(screen+0x348)=menu+67;*(void **)(screen+0x34c)=menu+96;*(int *)(screen+0x88)=67;}
    for(int channel=0;channel<0x2f;channel++){
        if(channel==6||channel==7||channel==9||channel==10||channel==11||channel==46)continue;
        memcpy(charts,orig,nc*36);
        *(uint8_t *)0xe35ce14=0;*(int *)0xe35ce0c=2;*(int *)0xe35ce04=1;
        ((int __attribute__((regparm(3)))(*)(void*,int,int))FILTER_SONGS)(screen,channel,0);
        int n=*(int *)0xac2d6c4;uint32_t *runs=*(uint32_t **)0xac2d6a0,*sel=*(uint32_t **)0xac2d6a4;
        printf("CHANNEL %02x songs=%d\n",channel,n);
        for(int i=0;i<n;i++){
            unsigned st=runs[i*2+1]&65535,cnt=runs[i*2+1]>>16;
            uint32_t *song=songs+runs[i*2]*9;
            printf("%d id=%08X parent=%08X",i+1,song[0],song[4]<(unsigned)ns?songs[song[4]*9]:0);
            for(unsigned j=0;j<cnt;j++){uint32_t *c=charts+sel[st+j]*9;printf(" %08X:%08X:%x",songs[(c[0]>>16)*9],songs[(c[0]&65535)*9],c[2]&0xfffff);}
            puts("");
        }
    }
    return 0;
}

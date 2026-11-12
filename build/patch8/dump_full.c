// Full Mode list per channel with our hooks and the game's REAL qsort + comparator. argv[3] = value of the sort-mode byte 0xe35ce1c.
#define main previous_native_test_main
#include "test_channels.c"
#undef main
int main(int argc,char **argv)
{
    assert(argc==4);load_engine(argv[1]);jump_to(0x8052630,qsort);install_prime2_channel();
    FILE *f=fopen(argv[2],"rb");assert(f);uint32_t header[11];assert(fread(header,1,44,f)==44);
    int ns=header[0],nc=header[1];uint32_t *songs=calloc(ns,36),*charts=calloc(nc,36),*orig=calloc(nc,36);
    assert(fread(songs+9,36,ns-1,f)==(size_t)ns-1);fseek(f,36,SEEK_CUR);
    assert(fread(orig+9,36,nc-1,f)==(size_t)nc-1);fclose(f);
    *(void **)0xac2d6b0=songs;*(int *)0xac2d6a8=ns;*(void **)0xac2d6b4=charts;*(int *)0xac2d6ac=nc;
    *(void **)0xac2d6a0=calloc(nc,8);*(void **)0xac2d6a4=calloc(nc,4);
    unsigned char screen[0x1000]={0};uint32_t *menu[96]={0};
    for(int i=0;i<67;i++)menu[i]=table+i*5;
    *(void **)(screen+0x344)=menu;*(void **)(screen+0x348)=menu+67;*(void **)(screen+0x34c)=menu+96;*(int *)(screen+0x88)=67;
    *(uint8_t *)0xe35ce1c=(uint8_t)atoi(argv[3]);
    for(int channel=0;channel<=LAST_ID;channel++){
        if(channel==6||channel==7||channel==9||channel==10||channel==11||channel==46)continue;   // not filterable, as test_channels.c
        memcpy(charts,orig,nc*36);
        *(uint8_t *)0xe35ce14=1;*(int *)0xe35ce0c=2;*(int *)0xe35ce04=1;
        ((filter_fn)FILTER_SONGS)(screen,channel,0);
        int n=*(int *)0xac2d6c4;uint32_t *runs=*(uint32_t **)0xac2d6a0;
        printf("CHANNEL %02x songs=%d\n",channel,n);
        for(int i=0;i<n;i++)printf("%08X\n",songs[runs[i*2]*9]);
    }
    return 0;
}

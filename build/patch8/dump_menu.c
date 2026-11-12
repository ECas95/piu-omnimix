// Full Mode channel menu as the original builder plus our hook leave it: channel ids in screen order.
#define main previous_native_test_main
#include "test_channels.c"
#undef main
int main(int argc,char **argv)
{
    assert(argc==3);load_engine(argv[1]);install_prime2_channel();
    FILE *f=fopen(argv[2],"rb");assert(f);uint32_t header[11];assert(fread(header,1,44,f)==44);
    int ns=header[0],nc=header[1];uint32_t *songs=calloc(ns,36),*charts=calloc(nc,36);
    assert(fread(songs+9,36,ns-1,f)==(size_t)ns-1);fseek(f,36,SEEK_CUR);
    assert(fread(charts+9,36,nc-1,f)==(size_t)nc-1);fclose(f);
    *(void **)0xac2d6b0=songs;*(int *)0xac2d6a8=ns;*(void **)0xac2d6b4=charts;*(int *)0xac2d6ac=nc;
    *(void **)0xac2d6a0=calloc(nc,8);*(void **)0xac2d6a4=calloc(nc,4);
    unsigned char screen[0x1000]={0};uint32_t *menu[96]={0};
    *(void **)(screen+0x344)=menu;*(void **)(screen+0x348)=menu;*(void **)(screen+0x34c)=menu+96;
    *(uint8_t *)0xe35ce14=1;*(int *)0xe35ce04=1;*(int *)0xab7de54=4;
    ((build_fn)BUILD_MENU)(screen);
    uint32_t **end=*(uint32_t ***)(screen+0x348);
    for(uint32_t **m=*(uint32_t ***)(screen+0x344);m<end;m++)printf("%02x %u\n",(*m)[0],(*m)[2]);
    return 0;
}

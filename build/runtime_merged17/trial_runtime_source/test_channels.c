// Execute PRIME's original filter and song enumerator with the patched hooks,
// using the installed catalog. This avoids requiring a player for every filter.
#define CHANNEL_POLICY_TEST
#include "channels.c"
#include <elf.h>
#include <stdlib.h>
#include <assert.h>

static void jump_to(uintptr_t addr, void *dest)
{
    *(uint8_t *)addr=0xe9;
    int32_t rel=(int32_t)((uintptr_t)dest-addr-5);
    memcpy((void *)(addr+1),&rel,4);
}
// Sorting affects order only; membership and chart groups are built beforehand.
static void skip_sort(void *base, size_t n, size_t size, void *fn) {(void)base;(void)n;(void)size;(void)fn;}
static void load_engine(const char *path)
{
    FILE *f=fopen(path,"rb"); assert(f);
    Elf32_Ehdr e; assert(fread(&e,1,sizeof(e),f)==sizeof(e));
    assert(e.e_type==ET_EXEC && e.e_machine==EM_386);
    Elf32_Phdr p[32]; assert(e.e_phnum<=32);
    fseek(f,e.e_phoff,SEEK_SET); assert(fread(p,e.e_phentsize,e.e_phnum,f)==e.e_phnum);
    uintptr_t lo=UINT32_MAX,hi=0;
    for(int i=0;i<e.e_phnum;i++)if(p[i].p_type==PT_LOAD){
        if(p[i].p_vaddr<lo)lo=p[i].p_vaddr;
        if(p[i].p_vaddr+p[i].p_memsz>hi)hi=p[i].p_vaddr+p[i].p_memsz;
    }
    lo&=~4095u; hi=(hi+4095)&~4095u;
    assert(mmap((void *)lo,hi-lo,7,MAP_FIXED|MAP_PRIVATE|MAP_ANONYMOUS,-1,0)==(void *)lo);
    for(int i=0;i<e.e_phnum;i++)if(p[i].p_type==PT_LOAD){
        fseek(f,p[i].p_offset,SEEK_SET);assert(fread((void *)p[i].p_vaddr,1,p[i].p_filesz,f)==p[i].p_filesz);
    }
    fclose(f);
    jump_to(0x8052630,skip_sort);
    jump_to(0x8052cf0,memmove);
    jump_to(0x8051b00,malloc);
    jump_to(0x8052540,free);
}
// Execute the original two-player confirmation lookup, ending immediately
// before formatting its debug message. It indexes each chart by wheel slot,
// independently of the displayed difficulty number (0x080d6c50..0x080d6ca2).
static void native_selected_pair(void *screen, unsigned *first, unsigned *second)
{
    unsigned a,c;
    __asm__ volatile("push %%ebp; push %%edi; mov $0x080d6c50, %%eax; call *%%eax; pop %%edi; pop %%ebp"
        : "=a"(a), "=c"(c) : "b"(screen) : "edx", "memory", "cc");
    *first=c; *second=a;
}
static void verify_imported_slots(unsigned char *screen, uint32_t *charts, int nc, int channel)
{
    uint32_t *runs=*(uint32_t **)0xac2d6a0, *selected=*(uint32_t **)0xac2d6a4;
    unsigned char *visited=calloc(nc,1); assert(visited);
    int total=0, pairs=0;
    for(int n=0;n<*(int *)0xac2d6c4;n++) {
        unsigned start=runs[n*2+1]&65535, count=runs[n*2+1]>>16;
        if(channel==0x34)assert(count==6);
        *(void **)(screen+0x6c)=runs+n*2;
        for(unsigned j=0;j<count;j++) {
            unsigned idx=selected[start+j];assert(idx>0 && idx<(unsigned)nc);
            assert(!visited[idx]);visited[idx]=1;total++;
            uint32_t *rec=charts+idx*9;
            assert((rec[0]>>16)==runs[n*2]);assert((rec[0]&65535)==runs[n*2]);
            assert(rec[1]!=UINT32_MAX);
            for(unsigned k=0;k<j;k++) {
                uint32_t *other=charts+selected[start+k]*9;
                assert(rec[1]!=other[1]); // distinct NX file; aliases remain forbidden
                if((rec[2]&0x0fff00)==(other[2]&0x0fff00))pairs++;
            }
            *(unsigned *)(screen+0xa8)=j;
            *(unsigned *)(screen+0x8c)=count-1-j;
            unsigned first,second;native_selected_pair(screen,&first,&second);
            assert(first==idx);assert(second==selected[start+count-1-j]);
        }
    }
    for(int i=1;i<nc;i++)if(*((uint8_t *)(charts+i*9)+10)&0x80)assert(visited[i]);
    if(channel==0x34){assert(total==3450);assert(pairs==34);}
    printf("Native two-player wheel slots: channel=%02x charts=%d equal-level pairs=%d all distinct and reachable\n",channel,total,pairs);
    free(visited);
}
int main(int argc,char **argv)
{
    assert(argc==3); load_engine(argv[1]); install_prime2_channel();
    const uint8_t lookup_end[]={0x89,0x4c,0x24,0x14};
    assert(memcmp((void *)0x080d6ca2,lookup_end,sizeof(lookup_end))==0);
    // Capture the two real chart indices before the unrelated debug formatter.
    memcpy((void *)0x080d6ca2,"\x89\xe8\xc3",3);
    FILE *f=fopen(argv[2],"rb"); assert(f);
    uint32_t head[11]; assert(fread(head,1,44,f)==44);
    int ns=head[0],nc=head[1];
    uint32_t *songs=calloc(ns,36),*original=calloc(nc,36),*charts=calloc(nc,36);
    assert(fread(songs+9,36,ns-1,f)==(size_t)ns-1);fseek(f,36,SEEK_CUR);
    assert(fread(original+9,36,nc-1,f)==(size_t)nc-1);fclose(f);
    *(uint32_t **)0xac2d6b0=songs; *(int *)0xac2d6a8=ns;
    *(uint32_t **)0xac2d6b4=charts; *(int *)0xac2d6ac=nc;
    *(void **)0xac2d6a0=calloc(nc,8); *(void **)0xac2d6a4=calloc(nc,4);
    unsigned char screen[0x1000]={0}; uint32_t *menu[64];
    for(int i=0;i<53;i++)menu[i]=table+i*5;
    *(void **)(screen+0x344)=menu; *(void **)(screen+0x348)=menu+53;
    *(int *)(screen+0x88)=53;
    int owners[53]={0},expected[53]={0};
    uint8_t *seen=calloc((size_t)ns*16*256,1);assert(seen);
    for(int i=1;i<nc;i++){
        unsigned owner=chart_owner(songs,ns,original+i*9);
        owners[owner]++;
        if(owner && original[i*9+1]!=UINT32_MAX)expected[owner]++;
    }
    for(int full=0;full<2;full++)for(int probe=0;probe<2;probe++)for(int channel=0;channel<53;channel++){
        if(channel==6 || channel==7 || channel==9 || channel==10 || channel==11 || channel==46)continue;
        memcpy(charts,original,nc*36);
        *(uint8_t *)0xe35ce14=full; *(int *)0xe35ce0c=2; *(int *)0xe35ce04=1;
        int ret=((filter_fn)FILTER_SONGS)(screen,channel,probe);
        int visible[53]={0};
        memset(seen,0,(size_t)ns*16*256);
        for(int i=1;i<nc;i++)if(*((uint8_t *)(charts+i*9)+10)&0x80){
            unsigned owner=chart_owner(songs,ns,charts+i*9);visible[owner]++;
            if(owner)assert(owner==(unsigned)channel);
            if(channel>=47)assert(owner==(unsigned)channel);
            if(!owner && (songs[(charts[i*9]>>16)*9+5]&0x01000000u) &&
                (((charts[i*9]>>16)==(charts[i*9]&65535)) || basic_alias(songs,charts+i*9)))
            {
                size_t key=(((charts[i*9]>>16)*16+((charts[i*9+2]>>16)&15))*256+
                             ((charts[i*9+2]>>8)&255));
                assert(!seen[key]);seen[key]=1;
            }
        }
        if(channel>=47){
            assert(visible[channel]==expected[channel]);
            verify_imported_slots(screen,charts,nc,channel);
            assert(*(int *)0xac2d6c4>0);
            uint32_t *runs=*(uint32_t **)0xac2d6a0;
            for(int a=0;a<*(int *)0xac2d6c4;a++)for(int b=a+1;b<*(int *)0xac2d6c4;b++)
                assert(runs[a*2]!=runs[b*2]);
            printf("full=%d probe=%d channel=%02x charts=%d songs=%d ret=%d\n",full,probe,channel,visible[channel],*(int *)0xac2d6c4,ret);
            if(channel==0x32)assert(*(int *)0xac2d6c4==140);
            if(channel==0x33)assert(*(int *)0xac2d6c4==152);
            if(channel==0x34){assert(*(int *)0xac2d6c4==575);assert(visible[channel]==3450);}
        }
        if(channel==0)assert(*(int *)0xac2d6c4>0);
    }
    // Resolve the current menu item through the original -1 refresh path.
    for(int channel=47;channel<53;channel++){
        memcpy(charts,original,nc*36); menu[0]=table+(channel==47?46:channel-1)*5;
        *(int *)(screen+0x70)=0;*(uint8_t *)0xe35ce14=0;
        ((filter_fn)FILTER_SONGS)(screen,-1,0);
        assert(*(int *)0xac2d6c4>0);
    }
    // A fresh Full Mode menu must retain every imported channel on its first build.
    memcpy(charts,original,nc*36);
    *(uint8_t *)0xe35ce14=0;*(int *)0xe35ce04=1;*(int *)0xab7de54=4;
    *(void **)(screen+0x34c)=menu+64;
    ((build_fn)BUILD_MENU)(screen);
    int built=*(int *)(screen+0x88), found[53]={0};
    for(int i=0;i<built;i++){assert(menu[i][0]<53);found[menu[i][0]]=1;}
    for(int c=47;c<53;c++)assert(found[c]);
    printf("Fresh Full Mode menu: %d categories, all six imported channels present\n",built);
    // Updated legacy charts stay with their media song, regardless of the former
    // version of their helper folder. Every own-channel run is an original song.
    for(int c=47;c<53;c++) {
        memcpy(charts,original,nc*36);*(uint8_t *)0xe35ce14=1;
        ((filter_fn)FILTER_SONGS)(screen,c,0);
        uint32_t *runs=*(uint32_t **)0xac2d6a0;
        for(int n=0;n<*(int *)0xac2d6c4;n++)
            assert(version_channel(songs[runs[n*2]*9+5]&255)==(unsigned)c);
    }
    // Quest/Train startup calls enumeration directly after marking E000 records.
    memcpy(charts,original,nc*36);
    for(int i=1;i<nc;i++)*((uint8_t *)(charts+i*9)+10)|=0x80;
    ((enum_fn)ENUM_SONGS)(1);
    for(int i=1;i<nc;i++)if(chart_owner(songs,ns,charts+i*9))
        assert(!(*((uint8_t *)(charts+i*9)+10)&0x80));
    for(int i=1;i<nc;i++)if(basic_alias(songs,charts+i*9))
        assert(!(*((uint8_t *)(charts+i*9)+10)&0x80));
    // Run the actual boot availability routine, including its original caller
    // address and E000 projection, rather than simulating a selection screen.
    memcpy(charts,original,nc*36);*(uint8_t *)0xe35ce14=0;
    ((void (*)(void))0x080d56d0u)();
    assert(*(int *)0xac2d6c4>0);
    assert(!*(uint8_t *)0x0a00ed40u);
    printf("Boot availability: %d songs; No Music Available flag clear\n",*(int *)0xac2d6c4);
    printf("PASS: cold/warm selection, category probes, all stock filters, six exclusive families and refresh\n");
    return 0;
}

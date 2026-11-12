#define NOTESKIN_TEST
#include "noteskin.c"
#include <elf.h>
#include <assert.h>
static void load(const char *path) {
 FILE *f=fopen(path,"rb"); assert(f); Elf32_Ehdr e; assert(fread(&e,1,sizeof(e),f)==sizeof(e));
 Elf32_Phdr p[32]; assert(e.e_phnum<=32); fseek(f,e.e_phoff,0); assert(fread(p,e.e_phentsize,e.e_phnum,f)==e.e_phnum);
 uintptr_t lo=UINT32_MAX,hi=0;
 for(int i=0;i<e.e_phnum;i++)if(p[i].p_type==PT_LOAD){if(p[i].p_vaddr<lo)lo=p[i].p_vaddr;if(p[i].p_vaddr+p[i].p_memsz>hi)hi=p[i].p_vaddr+p[i].p_memsz;}
 lo&=~4095u;hi=(hi+4095)&~4095u;assert(mmap((void *)lo,hi-lo,7,MAP_FIXED|MAP_PRIVATE|MAP_ANONYMOUS,-1,0)==(void *)lo);
 for(int i=0;i<e.e_phnum;i++)if(p[i].p_type==PT_LOAD){fseek(f,p[i].p_offset,0);assert(fread((void *)p[i].p_vaddr,1,p[i].p_filesz,f)==p[i].p_filesz);}
 fclose(f);
}
typedef int (__attribute__((regparm(2))) *skin_fn)(int,int);
int main(int argc,char **argv) {
 assert(argc==2);load(argv[1]);install_noteskin();assert(original_description);
 assert(*(uintptr_t *)0x8090d98==(uintptr_t)mods+TOTAL_MODS*24+4);
 for(unsigned i=0;i<sizeof(mod_bound_sites)/sizeof(*mod_bound_sites);i++)assert(*(uint8_t *)mod_bound_sites[i]==85);
 assert(categories[9]==20 && categories[10]==53 && categories[22]==82);
 for(int i=0;i<3;i++)assert(*(uint8_t *)skin_bounds[i]==47);
 for(int i=0;i<6;i++)assert(*(uint8_t *)random_checks[i]==46);
 skin_fn apply=(skin_fn)0x8088a80,active=(skin_fn)0x8088b70;
 int ids[]={50,84,85,86},banks[]={31,32,45,46};
 for(int player=0;player<2;player++) {
  for(int j=0;j<4;j++){apply(player,ids[j]);assert(*(int *)(0xab5da00+player*0x21230+0x203dc)==banks[j]);assert(active(player,ids[j])==1);}
  assert(active(player,-1)==0);apply(player,86);assert(*(int *)(0xab5da00+player*0x21230+0x203dc)==0);
  unsigned char ctx[128]={0},bga[0x1bc]={0};uint32_t slots[100];int cats[]={3};uint32_t *entries[4];
  for(int j=0;j<100;j++){slots[j]=0xfeed0000+j;*(void **)(bga+20+j*4)=slots+j;}
  for(int j=0;j<4;j++)entries[j]=(uint32_t *)(mods+(50+j)*24);
  *(int *)(ctx+4)=player;*(void **)(ctx+12)=cats;*(void **)(ctx+16)=cats+1;*(void **)(ctx+0x74)=bga;
  uint32_t ***v=(uint32_t ***)(0xab10d80+player*96+36);v[0]=entries;v[1]=entries+4;
  ((uint32_t *)(mods+83*24))[3]=0xaabb0011;((uint32_t *)(mods+84*24))[3]=0xaabb0022;
  uintptr_t expected[]={0xfeed0036,0xfeed0058,0xaabb0011,0xaabb0022};
  for(int j=0;j<4;j++){*(int *)(ctx+0x2c)=j;assert((uintptr_t)((description_fn)0x8062010)(ctx)==expected[j]);}
 }
 puts("PASS native engine: both players, selection/toggle, descriptions, reserved chart banks and category bounds");return 0;
}

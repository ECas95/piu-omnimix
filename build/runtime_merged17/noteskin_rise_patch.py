"""v370: PUMP IT UP RISE 1 noteskin (skin bank 47) in the selectable noteskin menu (noteskin.c). User 2026-10-26: RISE 2-5 removed."""
REPLACE=[
 ('#define SELECT_COUNT 47','#define SELECT_COUNT 48'),
 ('#define TOTAL_MODS 85','#define TOTAL_MODS 87'),
 ('#define CHART_SKIN_MAX 46  // 33..44 remain native chart banks; 45/46 are selectable.',
  '#define CHART_SKIN_MAX 47  // 33..44 remain native chart banks; 45/46 (XX/PHOENIX) and 47 (RISE 1) are selectable.\n#define VISIBLE 4          // PRIME 2, XX, PHOENIX, RISE 1 in the noteskin category\n#define HIDDEN_AT (MOD_COUNT + VISIBLE)  // hidden help entries: XX, PHOENIX, RISE'),
 ('static const char *new_names[] = {"skin_prime", "skin_xx", "skin_phoenix", "skin_xx_help", "skin_phoenix_help"};',
  'static const char *new_names[] = {"skin_prime", "skin_xx", "skin_phoenix", "skin_rise1", "skin_xx_help", "skin_phoenix_help", "skin_rise_help"};\nstatic const uint32_t new_ids[] = {0x54, 0x55, 0x56, 0x59, 0x57, 0x58, 0x5e};  // ids <= 0x5e keep the menu sprite slot (id+category+1) inside the 100-slot layouts'),
 ('''            if (id==0x55 || id==0x56) {
                uint32_t sprite=((uint32_t *)(mods+(83+id-0x55)*MOD_SIZE))[3];''',
  '''            if (id==0x55 || id==0x56 || id==0x59) {
                uint32_t help = id==0x55 ? 0 : id==0x56 ? 1 : 2;
                uint32_t sprite=((uint32_t *)(mods+(HIDDEN_AT+help)*MOD_SIZE))[3];'''),
 ('''    memcpy(mods+(INSERT_AT+3)*MOD_SIZE,(void *)(MOD_TABLE+INSERT_AT*MOD_SIZE),(MOD_COUNT-INSERT_AT)*MOD_SIZE);
    for(i=0;i<5;i++) {
        uint32_t *e=(uint32_t *)(mods+(i<3?INSERT_AT+i:83+i-3)*MOD_SIZE);
        memset(e,0,MOD_SIZE); e[0]=0x54+i; e[1]=(uintptr_t)new_names[i]; e[2]=i<3;
    }''',
  '''    memcpy(mods+(INSERT_AT+VISIBLE)*MOD_SIZE,(void *)(MOD_TABLE+INSERT_AT*MOD_SIZE),(MOD_COUNT-INSERT_AT)*MOD_SIZE);
    for(i=0;i<sizeof(new_ids)/sizeof(*new_ids);i++) {
        uint32_t *e=(uint32_t *)(mods+(i<VISIBLE?INSERT_AT+i:HIDDEN_AT+i-VISIBLE)*MOD_SIZE);
        memset(e,0,MOD_SIZE); e[0]=new_ids[i]; e[1]=(uintptr_t)new_names[i]; e[2]=i<VISIBLE;
    }'''),
 ('    skins[32*3]=0x54; skins[45*3]=0x55; skins[46*3]=0x56;',
  '    skins[32*3]=0x54; skins[45*3]=0x55; skins[46*3]=0x56;\n    skins[47*3]=0x59;   // RISE 1 -> skin bank 47'),
 ('''        if (categories[i * 3] >= INSERT_AT)
            categories[i * 3]+=3;
        if (categories[i * 3 + 1] >= INSERT_AT - 1)
            categories[i * 3 + 1]+=3;''',
  '''        if (categories[i * 3] >= INSERT_AT)
            categories[i * 3]+=VISIBLE;
        if (categories[i * 3 + 1] >= INSERT_AT - 1)
            categories[i * 3 + 1]+=VISIBLE;'''),
 (r'fprintf(stderr, "mk5_prime: noteskin #32 (skin_prime) plus selectable XX #45 / PHOENIX #46 installed\n");',
  r'fprintf(stderr, "mk5_prime: noteskin #32 (skin_prime) plus selectable XX #45 / PHOENIX #46 / RISE #47 installed\n");'),
]
def patch(text):
    for o,n in REPLACE:
        assert text.count(o)==1,o[:60];text=text.replace(o,n)
    return text

TEST=r'''#define NOTESKIN_TEST
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
 for(unsigned i=0;i<sizeof(mod_bound_sites)/sizeof(*mod_bound_sites);i++)assert(*(uint8_t *)mod_bound_sites[i]==TOTAL_MODS);
 assert(categories[9]==20 && categories[10]==50+VISIBLE && categories[22]==79+VISIBLE);
 for(int i=0;i<3;i++)assert(*(uint8_t *)skin_bounds[i]==SELECT_COUNT);
 for(int i=0;i<6;i++)assert(*(uint8_t *)random_checks[i]==CHART_SKIN_MAX);
 skin_fn apply=(skin_fn)0x8088a80,active=(skin_fn)0x8088b70;
 int ids[]={50,0x54,0x55,0x56,0x59},banks[]={31,32,45,46,47};
 for(int player=0;player<2;player++) {
  for(int j=0;j<5;j++){apply(player,ids[j]);assert(*(int *)(0xab5da00+player*0x21230+0x203dc)==banks[j]);assert(active(player,ids[j])==1);}
  assert(active(player,-1)==0);apply(player,0x59);assert(*(int *)(0xab5da00+player*0x21230+0x203dc)==0);
  unsigned char ctx[128]={0},bga[0x1bc]={0};uint32_t slots[100];int cats[]={3};uint32_t *entries[5];
  for(int j=0;j<100;j++){slots[j]=0xfeed0000+j;*(void **)(bga+20+j*4)=slots+j;}
  for(int j=0;j<5;j++)entries[j]=(uint32_t *)(mods+(50+j)*24);
  *(int *)(ctx+4)=player;*(void **)(ctx+12)=cats;*(void **)(ctx+16)=cats+1;*(void **)(ctx+0x74)=bga;
  uint32_t ***v=(uint32_t ***)(0xab10d80+player*96+36);v[0]=entries;v[1]=entries+5;
  ((uint32_t *)(mods+HIDDEN_AT*24))[3]=0xaabb0011;((uint32_t *)(mods+(HIDDEN_AT+1)*24))[3]=0xaabb0022;((uint32_t *)(mods+(HIDDEN_AT+2)*24))[3]=0xaabb0033;
  uintptr_t expected[]={0xfeed0036,0xfeed0058,0xaabb0011,0xaabb0022,0xaabb0033};
  for(int j=0;j<5;j++){*(int *)(ctx+0x2c)=j;assert((uintptr_t)((description_fn)0x8062010)(ctx)==expected[j]);}
 }
 puts("RISE_NOTESKINS_PASS native engine: both players, PRIME2/XX/PHOENIX/RISE1 select+toggle, descriptions, chart banks, category bounds");return 0;
}
'''

// Selectable native PRIME 2, XX and PHOENIX skins; chart banks 33..44 remain reserved.
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

#include "modtable_sites.h"

#define MOD_TABLE   0x081fa8a0u
#define MOD_COUNT   80
#define MOD_SIZE    24
#define SKIN_TABLE  0x081b2200u
#define SKIN_COUNT  32
#define CATEGORIES  0x081ab4c4u   // 8 x {first index, last index, next}
#define CATEGORY_IMM 0x0805d682u  // mov ebp,0x81ab4c4 in the command menu builder
#define INSERT_AT   51
#define SKIN_PRIME_ID 0x54  // free id; the command menu sprite slot is id + category + 1 = 88, an empty slot
#define FIESTA2_ID    0x32
#define SELECT_COUNT 48
#define TOTAL_MODS 87
#define CHART_SKIN_MAX 47  // 33..44 remain native chart banks; 45/46 (XX/PHOENIX) and 47 (RISE 1) are selectable.
#define VISIBLE 4          // PRIME 2, XX, PHOENIX, RISE 1 in the noteskin category
#define HIDDEN_AT (MOD_COUNT + VISIBLE)  // hidden help entries: XX, PHOENIX, RISE

static uint8_t mods[TOTAL_MODS * MOD_SIZE] __attribute__((aligned(16)));
static uint32_t skins[SELECT_COUNT * 3];
static int32_t categories[8 * 3];
static const char *new_names[] = {"skin_prime", "skin_xx", "skin_phoenix", "skin_rise1", "skin_xx_help", "skin_phoenix_help", "skin_rise_help"};
static const uint32_t new_ids[] = {0x54, 0x55, 0x56, 0x59, 0x57, 0x58, 0x5e};  // ids <= 0x5e keep the menu sprite slot (id+category+1) inside the 100-slot layouts
typedef void *(__attribute__((regparm(1))) *description_fn)(unsigned char *);
static description_fn original_description;
static void *__attribute__((regparm(1))) description(unsigned char *ctx)
{
    int player=*(int *)(ctx+4), selected=*(int *)(ctx+0x18);
    int *begin=*(int **)(ctx+0xc), *end=*(int **)(ctx+0x10);
    if (player>=0 && player<2 && begin && selected>=0 && selected<end-begin && begin[selected]==3) {
        uint32_t ***v=(uint32_t ***)(0xab10d80u+player*96+3*12);
        int choice=*(int *)(ctx+0x2c);
        if (v[0] && choice>=0 && choice<v[1]-v[0]) {
            uint32_t id=v[0][choice][0];
            if (id==0x55 || id==0x56 || id==0x59) {
                uint32_t help = id==0x55 ? 0 : id==0x56 ? 1 : 2;
                uint32_t sprite=((uint32_t *)(mods+(HIDDEN_AT+help)*MOD_SIZE))[3];
                if (sprite) return (void *)sprite;
                return NULL;
            }
        }
    }
    return original_description(ctx);
}


static const uint32_t skin_imm[] = {0x08088aefu, 0x08088c0bu, 0x080b4881u};   // mov ecx,imm / [eax*4+disp]
static const uint32_t skin_bounds[] = {0x08088b59u, 0x08088c20u, 0x08088c37u}; // cmp reg,0x20
static const uint32_t random_checks[] = {0x08098d6au, 0x08098d9du, 0x08098dd0u, 0x08098e03u, 0x08098e36u, 0x08098e69u};

static int writable(uintptr_t a, size_t n)
{
    uintptr_t p = a & ~(uintptr_t)0xfff;
    return mprotect((void *)p, ((a + n + 0xfff) & ~(uintptr_t)0xfff) - p, PROT_READ | PROT_WRITE | PROT_EXEC);
}

#ifndef NOTESKIN_TEST
__attribute__((constructor))
#endif
static void install_noteskin(void)
{
    size_t i;

    const uint8_t head[6]={0x57,0xb9,0x40,0,0,0};
    if (memcmp((void *)0x8062010,head,6)) goto bad;
    // check everything before touching anything
    for (i = 0; i < sizeof(mod_imm_sites) / sizeof(*mod_imm_sites); i++)
        if (*(uint32_t *)mod_imm_sites[i][0] != mod_imm_sites[i][1])
            goto bad;
    for (i = 0; i < sizeof(mod_bound_sites) / sizeof(*mod_bound_sites); i++)
        if (*(uint8_t *)mod_bound_sites[i] != MOD_COUNT)
            goto bad;
    for (i = 0; i < 3; i++)
        if ((*(uint32_t *)skin_imm[i] & ~0xfu) != SKIN_TABLE || *(uint8_t *)skin_bounds[i] != SKIN_COUNT)
            goto bad;
    for (i = 0; i < 6; i++)
        if (*(uint8_t *)random_checks[i] != SKIN_COUNT - 1)
            goto bad;
    if (*(uint32_t *)CATEGORY_IMM != CATEGORIES || ((int32_t *)CATEGORIES)[3 * 3 + 1] != INSERT_AT - 1 ||
        ((uint32_t *)(MOD_TABLE + (INSERT_AT - 1) * MOD_SIZE))[0] != FIESTA2_ID || ((uint32_t *)MOD_TABLE)[0] != 0 ||
        ((uint32_t *)SKIN_TABLE)[31 * 3] != FIESTA2_ID)
        goto bad;

    uint8_t *trampoline=mmap(NULL,4096,7,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if (trampoline==MAP_FAILED) goto bad;
    memcpy(trampoline,head,6); trampoline[6]=0xe9;
    *(int32_t *)(trampoline+7)=(uintptr_t)0x8062016-(uintptr_t)(trampoline+11);
    original_description=(description_fn)trampoline;
    memcpy(mods, (void *)MOD_TABLE, INSERT_AT * MOD_SIZE);
    memcpy(mods+(INSERT_AT+VISIBLE)*MOD_SIZE,(void *)(MOD_TABLE+INSERT_AT*MOD_SIZE),(MOD_COUNT-INSERT_AT)*MOD_SIZE);
    for(i=0;i<sizeof(new_ids)/sizeof(*new_ids);i++) {
        uint32_t *e=(uint32_t *)(mods+(i<VISIBLE?INSERT_AT+i:HIDDEN_AT+i-VISIBLE)*MOD_SIZE);
        memset(e,0,MOD_SIZE); e[0]=new_ids[i]; e[1]=(uintptr_t)new_names[i]; e[2]=i<VISIBLE;
    }
    memcpy(skins,(void *)SKIN_TABLE,SKIN_COUNT*12);
    for(i=32;i<SELECT_COUNT;i++) {
        skins[i*3]=0xf0000000u+i; skins[i*3+1]=3; skins[i*3+2]=0;
    }
    skins[32*3]=0x54; skins[45*3]=0x55; skins[46*3]=0x56;
    skins[47*3]=0x59;   // RISE 1 -> skin bank 47
    memcpy(categories, (void *)CATEGORIES, sizeof(categories));
    for (i = 0; i < 8; i++) {  // Three visible entries; hidden descriptions are outside category ranges.
        if (categories[i * 3] >= INSERT_AT)
            categories[i * 3]+=VISIBLE;
        if (categories[i * 3 + 1] >= INSERT_AT - 1)
            categories[i * 3 + 1]+=VISIBLE;
    }
    for (i = 0; i < sizeof(mod_imm_sites) / sizeof(*mod_imm_sites); i++) {
        writable(mod_imm_sites[i][0], 4);
        uint32_t offset=mod_imm_sites[i][1]-MOD_TABLE;
        if (offset>=MOD_COUNT*MOD_SIZE) offset+=(TOTAL_MODS-MOD_COUNT)*MOD_SIZE;
        *(uint32_t *)mod_imm_sites[i][0] = (uint32_t)(uintptr_t)mods + offset;
    }
    for (i = 0; i < sizeof(mod_bound_sites) / sizeof(*mod_bound_sites); i++) {
        writable(mod_bound_sites[i], 1);
        *(uint8_t *)mod_bound_sites[i] = TOTAL_MODS;
    }
    for (i = 0; i < 3; i++) {
        writable(skin_imm[i], 4), writable(skin_bounds[i], 1);
        *(uint32_t *)skin_imm[i] = (uint32_t)(uintptr_t)skins + (*(uint32_t *)skin_imm[i] - SKIN_TABLE);
        *(uint8_t *)skin_bounds[i] = SELECT_COUNT;
    }
    for (i = 0; i < 6; i++) {
        writable(random_checks[i], 1);
        *(uint8_t *)random_checks[i] = CHART_SKIN_MAX;
    }
    writable(CATEGORY_IMM, 4);
    *(uint32_t *)CATEGORY_IMM = (uint32_t)(uintptr_t)categories;
    writable(0x8062010,6);
    *(uint8_t *)0x8062010=0xe9;
    *(int32_t *)0x8062011=(uintptr_t)description-0x8062015;
    fprintf(stderr, "mk5_prime: noteskin #32 (skin_prime) plus selectable XX #45 / PHOENIX #46 / RISE #47 installed\n");
    return;
bad:
    fprintf(stderr, "mk5_prime: noteskin #32 skipped: unexpected bytes\n");
}

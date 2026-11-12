// Selector resource fixes: preserve catalog text literally and retain every
// texture slot across native lookup, drawing, screen cleanup and reset paths.
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/mman.h>

#define SELECTOR_TEXTURES 8192u
#define OLD_TEXTURE_BASE 0x0e3361a0u
// Native record zero starts at base+4. The preceding word is a separate loader
// scratch pointer and deliberately remains at its original engine address.
static uint8_t selector_texture_table[SELECTOR_TEXTURES * 52 + 64];
#include "selector_texture_sites.h"

// PRIME reads the selection screen's cursor (+0x38 of its 0xf40-byte object) in Basic Mode before setting it
// (0x8095870 -> 0x80c8cf0). On a fresh heap that memory is zero; with the large catalog the block reuses freed
// memory and the stale bytes index past the layout table (MK9 crash on entering the selector). Hand the game
// zeroed blocks from operator new, as a fresh heap would.
void *_Znwj(size_t n)
{
    void *p=calloc(1,n?n:1);
    if(!p) abort();
    return p;
}
void *_Znaj(size_t n) { return _Znwj(n); }

extern int __vsprintf_chk(char *, int, size_t, const char *, va_list);
static int selector_catalog_label(const char *text)
{
    if (!strchr(text, '%')) return 0;
    const uint32_t *songs=*(const uint32_t **)0x0ac2d6b0u;
    const char *pool=*(const char **)0x0ac2d6b8u;
    const uint32_t *offset=*(const uint32_t **)0x0ac2d6bcu;
    int count=*(int *)0x0ac2d6a8u;
    if (!songs || !pool || !offset || count<1 || count>65535) return 0;
    for (int i=1;i<count;i++) for (int field=1;field<=2;field++) {
        uint32_t index=songs[i*9+field];
        if (index!=UINT32_MAX && text==pool+offset[index]) return 1;
    }
    return 0;
}

static int selector_vsprintf(char *dst,int flag,size_t size,const char *fmt,va_list ap)
{
    // Only song titles/artists in LIST are data. Keep real UI format strings
    // and their arguments on the original checked formatting path.
    int n=selector_catalog_label(fmt) ? snprintf(dst,size,"%s",fmt)
                                    : __vsprintf_chk(dst,flag,size,fmt,ap);
#ifdef SELECTOR_FORMAT_OBSERVER
    SELECTOR_FORMAT_OBSERVER(dst);
#endif
    return n;
}

#ifndef SELECTOR_RESOURCES_TEST
__attribute__((constructor))
#endif
static void install_selector_resources(void)
{
    const uint8_t format_call[5]={0xe8,0x2a,0x00,0xfe,0xff};
    const size_t total=sizeof(texture_sites)/sizeof(texture_sites[0]);
    if (memcmp((void *)0x08072721u,format_call,5)) goto mismatch;
    for(size_t i=0;i<total;i++)
        if (*(uint32_t *)texture_sites[i].address!=texture_sites[i].old) goto mismatch;
    // Validate every site before changing any code. The cache allocation is
    // owned by this module for its whole lifetime, including screen transitions.
    for(size_t i=0;i<=total;i++) {
        uintptr_t a=i<total?texture_sites[i].address:0x08072721u;
        uintptr_t page=a&~(uintptr_t)4095;
        if(mprotect((void *)page,8192,PROT_READ|PROT_WRITE|PROT_EXEC)) {
            perror("mk5_prime: selector resources mprotect"); return;
        }
    }
    for(size_t i=0;i<total;i++) {
        const struct texture_site *s=texture_sites+i;
        uint32_t value=s->kind==0 ? (uint32_t)(uintptr_t)selector_texture_table+s->old-OLD_TEXTURE_BASE :
                       s->kind==1 ? SELECTOR_TEXTURES : s->kind==2 ? SELECTOR_TEXTURES*52 :
                       (uint32_t)(uintptr_t)selector_texture_table+SELECTOR_TEXTURES*52+0x30;
        memcpy((void *)s->address,&value,4);
    }
    int32_t rel=(int32_t)((uintptr_t)selector_vsprintf-0x08072726u);
    memcpy((void *)0x08072722u,&rel,4);
    fprintf(stderr,"mk5_prime: selector literal catalog text and %u texture slots installed\n",SELECTOR_TEXTURES);
    return;
mismatch:
    fprintf(stderr,"mk5_prime: selector resource fix skipped: unexpected native bytes\n");
}

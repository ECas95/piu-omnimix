// Loading wallpapers: PRIME picks user_interface/loading/prime_%02d.tga with rand() % 7 + 1.
// PRIME 2 occupies 08..14, XX 15..21 and PHOENIX 22..28, INFINITY 29..38 (HD and SD).
#define _GNU_SOURCE
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

#define PICK_START 0x080cf349u   // call rand; ...; add ecx,1  (ends before lea edx,[esp+0x11c])
#define PICK_END   0x080cf38bu
#define WALLPAPERS 38

static int pick(void)
{
    return rand() % WALLPAPERS;
}

__attribute__((constructor)) static void install_wallpapers(void)
{
    static const uint8_t head[] = {0xe8, 0xb2, 0x2f, 0xf8, 0xff, 0xb9, 0x93, 0x24, 0x49, 0x92};  // call rand; mov ecx,7-magic
    static const uint8_t tail[] = {0x89, 0xd9, 0x83, 0xc1, 0x01};                              // mov ecx,ebx; add ecx,1
    uint8_t code[PICK_END - PICK_START];
    int32_t rel;
    size_t n = 0;

    if (memcmp((void *)PICK_START, head, sizeof(head)) || memcmp((void *)(PICK_END - sizeof(tail)), tail, sizeof(tail))) {
        fprintf(stderr, "mk5_prime: wallpapers skipped: unexpected bytes at %08x\n", PICK_START);
        return;
    }
    memset(code, 0x90, sizeof(code));
    code[n++] = 0xe8;                                           // call pick -> eax = 0..27
    rel = (int32_t)((uintptr_t)pick - (PICK_START + 5));
    memcpy(code + n, &rel, 4), n += 4;
    // the sprintf arguments the original code stored in between: fmt, size 0x20, flag 1
    static const uint8_t args[] = {0xc7, 0x44, 0x24, 0x0c, 0x77, 0x4f, 0x1b, 0x08,
                                   0xc7, 0x44, 0x24, 0x08, 0x20, 0x00, 0x00, 0x00,
                                   0xc7, 0x44, 0x24, 0x04, 0x01, 0x00, 0x00, 0x00,
                                   0x89, 0xc3,                    // mov ebx,eax (as the original remainder)
                                   0x8d, 0x48, 0x01};             // lea ecx,[eax+1]
    memcpy(code + n, args, sizeof(args));

    uintptr_t page = PICK_START & ~(uintptr_t)0xfff;
    if (mprotect((void *)page, ((PICK_END + 0xfff) & ~(uintptr_t)0xfff) - page, PROT_READ | PROT_WRITE | PROT_EXEC)) {
        perror("mk5_prime: wallpapers mprotect");
        return;
    }
    memcpy((void *)PICK_START, code, sizeof(code));
    fprintf(stderr, "mk5_prime: loading wallpapers 1..%d\n", WALLPAPERS);
}

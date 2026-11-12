// Debug aid: in-process write watchpoint. If /mnt/mk5/watch.cfg holds "ADDR LEN" (hex), the page(s)
// around [ADDR, ADDR+LEN) are made read-only; every write into the range logs the writing EIP and
// the new value, then the page is reopened for one single-stepped instruction and protected again.
// No watch.cfg -> nothing is installed.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <ucontext.h>

static uintptr_t lo, hi, page_lo, page_hi;
static struct sigaction old_segv;
static volatile uintptr_t pending;  // address of the write being single-stepped (0 = none)
static int logged;

static void protect(int on)
{
    mprotect((void *)page_lo, page_hi - page_lo, on ? PROT_READ : PROT_READ | PROT_WRITE);
}

static void on_segv(int sig, siginfo_t *si, void *ctx)
{
    uintptr_t a = (uintptr_t)si->si_addr;
    ucontext_t *uc = ctx;
    if (a < page_lo || a >= page_hi) {  // a real crash: hand over to the previous handler
        if (old_segv.sa_flags & SA_SIGINFO)
            old_segv.sa_sigaction(sig, si, ctx);
        else if (old_segv.sa_handler != SIG_DFL && old_segv.sa_handler != SIG_IGN)
            old_segv.sa_handler(sig);
        else {
            signal(SIGSEGV, SIG_DFL);
            raise(SIGSEGV);
        }
        return;
    }
    if (a >= lo && a < hi)
        pending = a;
    protect(0);
    uc->uc_mcontext.gregs[REG_EFL] |= 0x100;  // trap after this one instruction
    if (pending && logged < 400) {
        fprintf(stderr, "WATCH write @%08lx by eip=%08x esp=%08x ret=%08x\n", (unsigned long)a,
                (unsigned)uc->uc_mcontext.gregs[REG_EIP], (unsigned)uc->uc_mcontext.gregs[REG_ESP],
                *(unsigned *)uc->uc_mcontext.gregs[REG_ESP]);
        logged++;
    }
}

static void on_trap(int sig, siginfo_t *si, void *ctx)
{
    ucontext_t *uc = ctx;
    (void)sig, (void)si;
    uc->uc_mcontext.gregs[REG_EFL] &= ~0x100;
    if (pending) {
        fprintf(stderr, "WATCH   value @%08lx = %u\n", (unsigned long)pending, *(unsigned *)(pending & ~3u));
        pending = 0;
    }
    protect(1);
}

__attribute__((constructor(65535))) static void install_watch(void)
{
    unsigned long a, n;
    FILE *f = fopen("/mnt/mk5/watch.cfg", "r");
    if (!f)
        return;
    if (fscanf(f, "%lx %lx", &a, &n) != 2) {
        fclose(f);
        return;
    }
    fclose(f);
    lo = a, hi = a + n;
    page_lo = lo & ~0xfffUL, page_hi = (hi + 0xfff) & ~0xfffUL;
    // crashdump.c overrides sigaction() to keep its fatal-signal handler: go to libc directly
    int (*real_sigaction)(int, const struct sigaction *, struct sigaction *) = dlsym(RTLD_NEXT, "sigaction");
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = on_segv;
    sa.sa_flags = SA_SIGINFO | SA_NODEFER;
    real_sigaction(SIGSEGV, &sa, &old_segv);
    sa.sa_sigaction = on_trap;
    real_sigaction(SIGTRAP, &sa, NULL);
    protect(1);
    fprintf(stderr, "WATCH armed %08lx..%08lx\n", (unsigned long)lo, (unsigned long)hi);
}

// Crash reporter: logs EIP/fault address/registers/stack on SIGSEGV and keeps
// the game from replacing it, so faults can be located in piu-PRIME122.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <ucontext.h>
#include <unistd.h>

static void report(int sig, siginfo_t *info, void *ctx)
{
    ucontext_t *uc = ctx;
    greg_t *r = uc->uc_mcontext.gregs;
    unsigned *sp = (unsigned *)r[REG_ESP];
    char line[256];
    FILE *maps;

    fprintf(stderr, "CRASH sig=%d addr=%p eip=%08x tid=%ld\n", sig, info->si_addr, (unsigned)r[REG_EIP],
            (long)syscall(SYS_gettid));
    fprintf(stderr, "CRASH eax=%08x ebx=%08x ecx=%08x edx=%08x esi=%08x edi=%08x ebp=%08x esp=%08x\n",
            (unsigned)r[REG_EAX], (unsigned)r[REG_EBX], (unsigned)r[REG_ECX], (unsigned)r[REG_EDX],
            (unsigned)r[REG_ESI], (unsigned)r[REG_EDI], (unsigned)r[REG_EBP], (unsigned)r[REG_ESP]);
    // On stack overflow the page at ESP is unmapped; scan from the next page up
    // and print values that look like return addresses into the main binary.
    sp = (unsigned *)(((unsigned)sp + 0x1000) & ~0xfffu);
    for (int i = 0, n = 0; i < 0x8000 && n < 120; i++)
        if (sp[i] >= 0x08048000 && sp[i] < 0x08200000) {
            fprintf(stderr, "CRASH ret %p: %08x\n", (void *)&sp[i], sp[i]);
            n++;
        }
    maps = fopen("/proc/self/maps", "r");
    while (maps && fgets(line, sizeof(line), maps))
        if (strstr(line, "r-xp"))
            fprintf(stderr, "CRASH map %s", line);
    _exit(139);
}

static int is_fatal(int sig)
{
    return sig == SIGSEGV || sig == SIGBUS || sig == SIGILL || sig == SIGFPE || sig == SIGABRT;
}

int sigaction(int sig, const struct sigaction *act, struct sigaction *old)
{
    static int (*real)(int, const struct sigaction *, struct sigaction *);
    if (!real)
        real = dlsym(RTLD_NEXT, "sigaction");
    if (act && is_fatal(sig) && act->sa_sigaction != report)
        return old ? real(sig, NULL, old) : 0;
    return real(sig, act, old);
}

sighandler_t signal(int sig, sighandler_t handler)
{
    static sighandler_t (*real)(int, sighandler_t);
    if (!real)
        real = dlsym(RTLD_NEXT, "signal");
    if (is_fatal(sig))
        return SIG_DFL;
    return real(sig, handler);
}

__attribute__((constructor)) static void install_crash_reporter(void)
{
    static char altstack[1 << 16];
    stack_t ss = {.ss_sp = altstack, .ss_size = sizeof(altstack)};
    struct sigaction sa;
    sigaltstack(&ss, NULL);
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = report;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    for (int sig = 1; sig < 32; sig++)
        if (is_fatal(sig))
            sigaction(sig, &sa, NULL);
    fprintf(stderr, "CRASH reporter installed pid=%d\n", getpid());
}

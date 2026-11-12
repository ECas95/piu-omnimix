// Debug aid for hangs: if /root/sample_eip exists, every 20 s the main thread logs its EIP and the
// return addresses on its stack ("SAMPLE ..." lines in prime_run.log). No file -> nothing installed.
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <time.h>
#include <ucontext.h>
#include <unistd.h>

#define SAMPLE_SIG (SIGRTMIN + 3)

static int samples;
static unsigned stack_end;  // top of the main thread stack ([stack] in /proc/self/maps)

static void sample(int sig, siginfo_t *si, void *ctx)
{
    ucontext_t *uc = ctx;
    greg_t *r = uc->uc_mcontext.gregs;
    unsigned *sp = (unsigned *)r[REG_ESP];
    (void)sig, (void)si;
    fprintf(stderr, "SAMPLE %d eip=%08x esp=%08x eax=%08x ebx=%08x ecx=%08x edx=%08x esi=%08x edi=%08x\n", samples++,
            (unsigned)r[REG_EIP], (unsigned)r[REG_ESP], (unsigned)r[REG_EAX], (unsigned)r[REG_EBX], (unsigned)r[REG_ECX],
            (unsigned)r[REG_EDX], (unsigned)r[REG_ESI], (unsigned)r[REG_EDI]);
    for (int i = 0, n = 0; i < 0x2000 && n < 24 && (unsigned)&sp[i] < stack_end; i++)
        if (sp[i] >= 0x08048000 && sp[i] < 0x08200000) {
            fprintf(stderr, "SAMPLE   ret %08x\n", sp[i]);
            n++;
        }
}

__attribute__((constructor)) static void install_sampler(void)
{
    if (access("/root/sample_eip", F_OK) != 0)
        return;
    char line[256];
    FILE *maps = fopen("/proc/self/maps", "r");
    while (maps && fgets(line, sizeof(line), maps))
        if (strstr(line, "[stack]"))
            sscanf(line, "%*x-%x", &stack_end);
    if (maps)
        fclose(maps);
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_sigaction = sample;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    sigaction(SAMPLE_SIG, &sa, NULL);
    struct sigevent ev;
    memset(&ev, 0, sizeof(ev));
    ev.sigev_notify = SIGEV_THREAD_ID;
    ev.sigev_signo = SAMPLE_SIG;
    ev._sigev_un._tid = (pid_t)syscall(SYS_gettid);  // the main thread (constructors run on it)
    timer_t t;
    struct itimerspec its = {.it_value = {20, 0}, .it_interval = {20, 0}};
    if (timer_create(CLOCK_MONOTONIC, &ev, &t) == 0 && timer_settime(t, 0, &its, NULL) == 0)
        fprintf(stderr, "SAMPLE sampler armed\n");
}

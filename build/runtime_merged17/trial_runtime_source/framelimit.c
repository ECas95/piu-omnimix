// 60 FPS cap: the game is frame-locked and runs too fast when the (virtual) GPU
// does not block on vsync. PIU_FPS overrides the rate; PIU_FPS=0 disables the cap.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <time.h>

void glXSwapBuffers(void *display, unsigned long drawable)
{
    static void (*real)(void *, unsigned long);
    static struct timespec next;
    static long period_ns = -1;

    if (!real)
        real = dlsym(RTLD_NEXT, "glXSwapBuffers");
    if (period_ns < 0) {
        const char *env = getenv("PIU_FPS");
        int fps = env ? atoi(env) : 60;
        period_ns = fps > 0 ? 1000000000L / fps : 0;
        clock_gettime(CLOCK_MONOTONIC, &next);
    }
    real(display, drawable);
    if (!period_ns)
        return;

    next.tv_nsec += period_ns;
    if (next.tv_nsec >= 1000000000L) {
        next.tv_sec++;
        next.tv_nsec -= 1000000000L;
    }
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    // If we fell more than a frame behind, resync instead of racing to catch up.
    if (now.tv_sec > next.tv_sec + 1 ||
        (now.tv_sec - next.tv_sec) * 1000000000L + (now.tv_nsec - next.tv_nsec) > period_ns)
        next = now;
    else
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);
}

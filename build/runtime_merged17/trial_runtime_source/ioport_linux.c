#define _GNU_SOURCE
#include <stdio.h>
#include <signal.h>
#include <ucontext.h>
#include <sys/io.h>

#include "am030614.h"
#include "ioport.h"

static struct sigaction old_action_sigill;
static struct sigaction old_action_sigsegv;

static void call_old_handler(int signum, siginfo_t *si, void* arg)
{
  struct sigaction *old_action = (signum == SIGILL) ? &old_action_sigill : &old_action_sigsegv;
  if (old_action->sa_handler == NULL || old_action->sa_handler == SIG_IGN) {
    return;
  }
  if (old_action->sa_flags & SA_SIGINFO) {
    old_action->sa_sigaction(signum, si, arg);
  } else {
    old_action->sa_handler(signum);
  }
}

void ioport_handler(int mysignal, siginfo_t *si, void* arg){    
  ucontext_t *context = (ucontext_t *)arg;    

  switch(context->uc_mcontext.gregs[REG_EDX] & 0xFFFF){
    case IOPORT_PIUIO_P1_OUT:
      PIUIO_HandleOutput_1(context->uc_mcontext.gregs[REG_EAX] & 0xFFFF);
      context->uc_mcontext.gregs[REG_EIP]+=2;
      return;
    case IOPORT_PIUIO_P2_OUT:
      PIUIO_HandleOutput_2(context->uc_mcontext.gregs[REG_EAX] & 0xFFFF);
      context->uc_mcontext.gregs[REG_EIP]+=2;
      return;
    case IOPORT_PIUIO_P1_IN:
      context->uc_mcontext.gregs[REG_EAX] = PIUIO_HandleInput_1();
      context->uc_mcontext.gregs[REG_EIP]+=2;
      return;
    case IOPORT_PIUIO_P2_IN:
      context->uc_mcontext.gregs[REG_EAX] = PIUIO_HandleInput_2();
      context->uc_mcontext.gregs[REG_EIP]+=2;
      return;
    default:
      call_old_handler(mysignal, si, arg);
      return;
  }
}
void IOPort_Init(){
  struct sigaction action;
  ioperm(IOPORT_PIUIO_P1_OUT, 1, 0);
  ioperm(IOPORT_PIUIO_P2_OUT, 1, 0);
  ioperm(IOPORT_PIUIO_P1_IN, 1, 0);
  ioperm(IOPORT_PIUIO_P2_IN, 1, 0);
  action.sa_sigaction = &ioport_handler;
  sigemptyset(&action.sa_mask);
  action.sa_flags = SA_SIGINFO;
  sigaction(SIGSEGV,&action,&old_action_sigsegv);
  sigaction(SIGILL,&action,&old_action_sigill);
}

#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include <x86intrin.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>

#include <base/log.h>
#include <base/assert.h>
#include <base/init.h>
#include <base/thread.h>
#include <runtime/uintr.h>
#include <runtime/preempt.h>

#include "defs.h"
#include "sched.h"
#ifdef DIRECTPATH
#include "net/directpath/mlx5/mlx5.h"
#endif 

#ifndef __NR_uintr_register_handler
#define __NR_uintr_register_handler	471
#define __NR_uintr_unregister_handler	472
#define __NR_uintr_create_fd		473
#define __NR_uintr_register_sender	474
#define __NR_uintr_unregister_sender	475
#define __NR_uintr_wait			476
#endif

#define uintr_register_handler(handler, flags)	syscall(__NR_uintr_register_handler, handler, flags)
#define uintr_unregister_handler(flags)		syscall(__NR_uintr_unregister_handler, flags)
#define uintr_create_fd(vector, flags)		syscall(__NR_uintr_create_fd, vector, flags)
#define uintr_register_sender(fd, flags)	syscall(__NR_uintr_register_sender, fd, flags)
#define uintr_unregister_sender(ipi_idx, flags)	syscall(__NR_uintr_unregister_sender, ipi_idx, flags)
#define uintr_wait(flags)			syscall(__NR_uintr_wait, flags)

#define TOKEN 0
#define MAX_KTHREADS 32


int uintr_fd[MAX_KTHREADS];
int uipi_index[MAX_KTHREADS];
long long uintr_sent[MAX_KTHREADS], uintr_recv[MAX_KTHREADS];
volatile int uintr_timer_flag = 0;

volatile int *cpu_preempt_points[MAX_KTHREADS];
__thread int concord_preempt_now;

long long TIMESLICE = 1000000;
long long HARD_TIMESLICE = 1000000;
long long start, end;

void concord_func() {
    concord_preempt_now = 0;
    // uintr_recv[myk()->kthread_idx]++;

#ifndef PREEMPT_MEASURE
#if defined(UNSAFE_PREEMPT_FLAG) || defined(UNSAFE_PREEMPT_SIMDREG)
    if (likely(preempt_enabled())) {
        // uintr_recv[myk()->kthread_idx]++;
    #ifdef PREEMPTED_RQ
     	thread_preempt_yield();
    #else
     	thread_yield();
    #endif
	}
    else {
        set_upreempt_needed();
    }
#else
    #ifdef PREEMPTED_RQ
     	thread_preempt_yield();
    #else
     	thread_yield();
    #endif
#endif
#endif
}

void concord_disable() {
    preempt_disable();
}

void concord_enable() {
    preempt_enable();
}

void concord_set_preempt_flag(int flag) {
    concord_preempt_now = flag;
}

void signal_block() {
    sigset_t mask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGUSR1);
    pthread_sigmask(SIG_BLOCK, &mask, NULL);
}

void signal_unblock(void) {
    sigset_t mask;
    sigemptyset(&mask);
    sigaddset(&mask, SIGUSR1);
    pthread_sigmask(SIG_UNBLOCK, &mask, NULL);
}

void set_thread_affinity(int core) {
	cpu_set_t mask;
	CPU_ZERO(&mask);
	CPU_SET(core, &mask);
	sched_setaffinity(0, sizeof(mask), &mask);
}

long long now() {
	struct timespec ts;
	timespec_get(&ts, TIME_UTC);
	return ts.tv_sec * 1e9 + ts.tv_nsec;
}

void __attribute__ ((interrupt))
    __attribute__((target("general-regs-only" /*, "inline-all-stringops"*/)))
     ui_handler(struct __uintr_frame *ui_frame,
		unsigned long long vector) {
		
	// ++uintr_recv[vector];    
    uintr_recv[myk()->kthread_idx]++;   
#ifndef PREEMPT_MEASURE 
#if defined(UNSAFE_PREEMPT_FLAG) || defined(UNSAFE_PREEMPT_SIMDREG)
    if (likely(preempt_enabled())) {
        // ++uintr_recv[vector];
    #ifdef PREEMPTED_RQ
     	thread_preempt_yield();
    #else
     	thread_yield();
    #endif
	}
    else {
        set_upreempt_needed();
    }
 
#else
    #ifdef PREEMPTED_RQ
     	thread_preempt_yield();
    #else
     	thread_yield();
    #endif
#endif
#endif
}

void signal_handler(int signum) {
    // uintr_recv[myk()->kthread_idx]++;

#ifndef PREEMPT_MEASURE 
#if defined(UNSAFE_PREEMPT_FLAG) || defined(UNSAFE_PREEMPT_SIMDREG)
    if (!preempt_enabled()) {
		set_upreempt_needed();
		return;
	}
    #ifdef PREEMPTED_RQ
     	thread_preempt_yield();
    #else
     	thread_yield();
    #endif
#else
    #ifdef PREEMPTED_RQ
     	thread_preempt_yield();
    #else
     	thread_yield();
    #endif
#endif
#endif
}

bool pending_cqe(int kidx) {
#ifdef DIRECTPATH
    return mlx5_rxq_pending(&rxqs[kidx]);
#else
    return true;
#endif
}

#define pending_uthreads(i) (ACCESS_ONCE(ks[i]->q_ptrs->rq_tail) != ACCESS_ONCE(ks[i]->q_ptrs->rq_head))
#define has_new_tasks(i) (pending_uthreads(i) || pending_cqe(i))
#ifdef PREEMPTED_RQ
#define has_old_tasks(i) (ACCESS_ONCE(ks[i]->q_ptrs->preempted_rq_tail) != ACCESS_ONCE(ks[i]->q_ptrs->preempted_rq_head))
#endif

long long last_check[MAX_KTHREADS], last_preempt[MAX_KTHREADS];

void* uintr_timer(void*) {
    _clui();

    base_init_thread();

    set_thread_affinity(55);

#ifdef SIGNAL_PREEMPT
    signal_block();
// #define SIGNAL_ALIGN 1000 * 4 * 2
//     long long last_signal = rdtsc();
#endif 

    int i;

#ifdef UINTR_PREEMPT
    for (i = 0; i < maxks; ++i) {
        uipi_index[i] = uintr_register_sender(uintr_fd[i], 0);
        // log_info("uipi_index %d %d", i, uipi_index[i]);
        if (uipi_index[i] < 0) {
            log_err("failure to register uintr sender");
        }
    }	    
#endif

    long long current;

#ifdef TIMER_LOG
#define ONE_SEC 1000000000
#define RUNTIME_GHZ 2
    long long last_log = rdtsc();
#endif

    for (i = 0; i < maxks; ++i) {
        #ifdef PREEMPTED_RQ
        last_preempt[i] = rdtsc();
        #endif
        last_check[i] = rdtsc();
    }

    while (uintr_timer_flag != -1) {
        current = rdtsc();
        for (i = 0; i < maxks; ++i) {
            if (!uintr_timer_flag) {
                #ifdef PREEMPTED_RQ
                last_preempt[i] = current;
                #endif
                last_check[i] = current;
                continue;
            }
            
            long long start_ts = ACCESS_ONCE(ks[i]->uthread_start_ts);
            if (last_check[i] < start_ts) {
                // log_info("============ last_check: %llu", start_ts - last_check[i]);
                #ifdef PREEMPTED_RQ
                last_preempt[i] = start_ts;
                #endif
                last_check[i] = start_ts;
            }

            // log_info("diff: %lld - %lld = %lld %lld", current, last_check[i], current - last_check[i], TIMESLICE);
            current = rdtsc();
            if (current - last_check[i] < TIMESLICE)
                continue;
            last_check[i] = current;    

#if SMART_PREEMPT
    #ifdef PREEMPTED_RQ
            long task_type = ACCESS_ONCE(ks[i]->is_preempted);
            if (  (task_type == 0 && (has_new_tasks(i) || has_old_tasks(i))) // a new task is running 
               || (task_type == 1 && (has_new_tasks(i) || (current - last_preempt[i] > HARD_TIMESLICE && has_old_tasks(i)))) ) {
    #else 
            if (pending_uthreads(i) || pending_cqe(i)) {
    #endif
#endif

#ifdef UINTR_PREEMPT
                _senduipi(uipi_index[i]);
#elif defined(CONCORD_PREEMPT)
                *(cpu_preempt_points[i]) = 1;
#elif defined(SIGNAL_PREEMPT)
                // while (rdtsc() - last_signal < SIGNAL_ALIGN);
                // last_signal = rdtsc();
                pthread_kill(ktids[i], SIGUSR1);
#endif
                ++uintr_sent[i];

#ifdef SMART_PREEMPT        
    #ifdef PREEMPTED_RQ
                last_preempt[i] = current;
    #endif
            }
#endif
          
        }

#ifdef TIMER_LOG
        current = rdtsc();
        if (unlikely(current - last_log > ONE_SEC * RUNTIME_GHZ)) {
            fprintf(stderr, "====== Timer log starts ====== \n");
            long long all_recv = 0;
            double avg_quantum = 0;
            for (i = 0; i < maxks; ++i) {
                avg_quantum = 0;
                if (uintr_recv[i] > 0) {
                    avg_quantum = 1. * ONE_SEC / 1000 / uintr_recv[i];
                }
                fprintf(stderr, "kthread %d: %lld sent, %lld recv, %.1f us quantum\n", i, uintr_sent[i], uintr_recv[i], avg_quantum);
                all_recv += uintr_recv[i];
                uintr_sent[i] = 0;
                uintr_recv[i] = 0;
            }

            avg_quantum = 0;
            if (all_recv > 0) {
                avg_quantum = 1. * maxks * ONE_SEC / 1000 / all_recv;
            }
            fprintf(stderr, "all kthreads: %.1f us quantum\n", avg_quantum);
            last_log = current;
        }
#endif
    } 

    return NULL;
}

void uintr_timer_start() {
    uintr_timer_flag = 1;
	start = now();
}

void uintr_timer_end() {
	end = now();
	uintr_timer_flag = -1;
}

#define GHZ 2
int uintr_init(void) {
    memset(uintr_fd, 0, sizeof(uintr_fd));
    memset(uintr_sent, 0, sizeof(uintr_sent));
    memset(uintr_recv, 0, sizeof(uintr_recv));

    TIMESLICE = uthread_quantum_us * 1000 * GHZ;
    HARD_TIMESLICE = uthread_hard_quantum_us * 1000 * GHZ;
	log_info("quantum: %lld us", TIMESLICE / 1000 / GHZ);
	log_info("hard quantum: %lld us", HARD_TIMESLICE / 1000 / GHZ);
    return 0;
}

int uintr_init_thread(void) {
    int kth_id = myk()->kthread_idx;
    assert(kth_id >= 0 && kth_id < MAX_KTHREADS);

    ktids[kth_id] = pthread_self();

    // For concord:
    concord_preempt_now = 0;
    cpu_preempt_points[kth_id] = &concord_preempt_now;

    // For uintr:
	if (uintr_register_handler(ui_handler, 0)) {
		log_err("failure to register uintr handler");
    }

	int uintr_fd_ = uintr_create_fd(kth_id, 0);
	if (uintr_fd_ < 0) {
		log_err("failure to create uintr fd");
    }
    uintr_fd[kth_id] = uintr_fd_; 

    _stui();

    return 0;
}

int uintr_init_late(void) {
#ifdef SIGNAL_PREEMPT
    struct sigaction action;
    action.sa_handler = signal_handler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    if (sigaction(SIGUSR1, &action, NULL) != 0) {
        log_err("signal handler registeration failed");
    }
#endif

    pthread_t timer_thread;
    int ret = pthread_create(&timer_thread, NULL, uintr_timer, NULL);
	BUG_ON(ret);
    log_info("UINTR timer pthread creates");

    return 0;
}

void uintr_timer_summary(void) {
    fprintf(stderr, "Execution: %.9f\n", 1.*(end - start) / 1e9);

    long long uintr_sent_total = 0, uintr_recv_total = 0;
    int i;
    for (i = 0; i < maxks; ++i) {
        uintr_sent_total += uintr_sent[i];
        uintr_recv_total += uintr_recv[i];
    }
    fprintf(stderr, "Preemption_sent: %lld\n", uintr_sent_total);
    fprintf(stderr, "Preemption_received: %lld\n", uintr_recv_total);
}
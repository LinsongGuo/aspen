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

uint64_t TIMESLICE = 1000000;
uint64_t HARD_TIMESLICE = 1000000;
long long start, end;

void concord_func() {
    concord_preempt_now = 0;
    // uintr_recv[myk()->kthread_idx]++;
    
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
		
	++uintr_recv[vector];        
#if defined(UNSAFE_PREEMPT_FLAG) || defined(UNSAFE_PREEMPT_SIMDREG)
    if (likely(preempt_enabled())) {
       //  ++uintr_recv[vector];
    #ifdef PREEMPTED_RQ
     	thread_preempt_yield();
    #else
        //uint64_t ss = rdtsc();
     	thread_yield();
        //uint64_t ee = rdtsc();
        //print(ee - ss);
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
}

void signal_handler(int signum) {
    // uintr_recv[myk()->kthread_idx]++;
        
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
}

// bool pending_uthreads(int kidx) {
// // #ifdef DIRECTPATH
//     // return ACCESS_ONCE(ks[kidx]->rq_tail) != ACCESS_ONCE(ks[kidx]->rq_head);
//     return ACCESS_ONCE(ks[kidx]->q_ptrs->rq_tail) != ACCESS_ONCE(ks[kidx]->q_ptrs->rq_head);
// // #else
// //     return true;
// // #endif
// }

bool pending_cqe(int kidx) {
#ifdef DIRECTPATH
    return mlx5_rxq_pending(&rxqs[kidx]);
#else
    return true;
#endif
}

// bool has_new_tasks(kidx) {
//     return pending_uthreads(kidx) || pending_cqe(kidx);
// }

// #ifdef PREEMPTED_RQ
// inline bool has_old_tasks(int kidx) {
// //     return ACCESS_ONCE(ks[kidx]->preempted_rq_tail) != ACCESS_ONCE(ks[kidx]->preempted_rq_head);
//     return ACCESS_ONCE(ks[kidx]->q_ptrs->preempted_rq_tail) != ACCESS_ONCE(ks[kidx]->q_ptrs->preempted_rq_head);
// }
// #endif

#define pending_uthreads(i) (ACCESS_ONCE(ks[i]->q_ptrs->rq_tail) != ACCESS_ONCE(ks[i]->q_ptrs->rq_head))
#define has_new_tasks(i) (pending_uthreads(i) || pending_cqe(i))
#ifdef PREEMPTED_RQ
#define has_old_tasks(i) (ACCESS_ONCE(ks[i]->q_ptrs->preempted_rq_tail) != ACCESS_ONCE(ks[i]->q_ptrs->preempted_rq_head))
#endif

uint64_t last_check[MAX_KTHREADS], last_preempt[MAX_KTHREADS];

// void uintr_timer_upd(int kidx) {
//     ACCESS_ONCE(last[kidx]) = rdtsc();
// }

void* uintr_timer(void*) {
    _clui();

    base_init_thread();

    set_thread_affinity(55);

#ifdef SIGNAL_PREEMPT
    signal_block();
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
#ifdef SIGNAL_PREEMPT
    // for (i = 0; i < (maxks >> 1); ++i) {
    // for (i = 0; i < maxks/3; ++i) {
    for (i = 0; i < maxks; ++i) {
#else 
    for (i = 0; i < maxks; ++i) {
#endif 
        #ifdef PREEMPTED_RQ
        last_preempt[i] = rdtsc();
        #endif
        last_check[i] = rdtsc();
    }

    while (uintr_timer_flag != -1) { 
#ifdef SIGNAL_PREEMPT
        // for (i = 0; i < (maxks >> 1); ++i) {
        // for (i = 0; i < maxks/3; ++i) {
        for (i = 0; i < maxks; ++i) {
#else 
        for (i = 0; i < maxks; ++i) {
#endif      
            current = rdtsc();
            if (!uintr_timer_flag) {
                #ifdef PREEMPTED_RQ
                last_preempt[i] = current;
                #endif
                last_check[i] = current;
                continue;
            }
            
            uint64_t start_ts = ACCESS_ONCE(ks[i]->uthread_start_ts);
            if (last_check[i] < start_ts) {
                // log_info("============ last_check: %llu", start_ts - last_check[i]);
                #ifdef PREEMPTED_RQ
                last_preempt[i] = start_ts;
                #endif
                last_check[i] = start_ts;
            }

            if (current - last_check[i] < TIMESLICE)
                continue;
            last_check[i] = current;    

            #ifdef PREEMPTED_RQ
            long task_type = ACCESS_ONCE(ks[i]->is_preempted);
            if (  (task_type == 0 && (has_new_tasks(i) || has_old_tasks(i))) // a new task is running 
               || (task_type == 1 && (has_new_tasks(i) || (current - last_preempt[i] > HARD_TIMESLICE && has_old_tasks(i)))) ) {
            #elif SMART_PREEMPT
            if (pending_uthreads(i) || pending_cqe(i)) {
            #endif

#ifdef UINTR_PREEMPT
                _senduipi(uipi_index[i]);
#elif defined(CONCORD_PREEMPT)
                *(cpu_preempt_points[i]) = 1;
#elif defined(SIGNAL_PREEMPT)
                pthread_kill(kth_tid[i], SIGUSR1);
#endif
                ++uintr_sent[i];
            
            #ifdef PREEMPTED_RQ
                last_preempt[i] = current;
            }
            #elif SMART_PREEMPT
            }
            #endif
          
        }
    } 

    return NULL;
}

#ifdef SIGNAL_PREEMPT
void* signal_timer2(void*) {
    signal_block();

    set_thread_affinity(53);
    
    int i;
    long long current;
    for (i = (maxks>>1); i < maxks; ++i) {
    // for (i = maxks/3; i < maxks/3*2; ++i) {
        ACCESS_ONCE(last[i]) = rdtsc();
    }
    while (uintr_timer_flag != -1) {
        for (i = (maxks>>1); i < maxks; ++i) {
        // for (i = maxks/3; i < maxks/3*2; ++i) {
            current = rdtsc();
		
            if (!uintr_timer_flag) {
                ACCESS_ONCE(last[i]) = current;
                continue;
            }   
            if (current - ACCESS_ONCE(last[i]) >= TIMESLICE) {
                if (pending_uthreads(i) || pending_cqe(i)) {
                    //printf("kill %d (%d): %lld | %lld, %lld\n", i, kth_tid[i], current - ACCESS_ONCE(last[i]), uintr_sent[i], uintr_recv[i]);
                    pthread_kill(kth_tid[i], SIGUSR1);
                    ++uintr_sent[i];
                    ACCESS_ONCE(last[i]) = current;
                }
            }   
        }
    } 

    return NULL;
}

void* signal_timer3(void*) {
    signal_block();

    set_thread_affinity(1);
    
    int i;
    long long current;
    for (i = maxks/3*2; i < maxks; ++i) {
        ACCESS_ONCE(last[i]) = rdtsc();
    }
    while (uintr_timer_flag != -1) {
        for (i = maxks/3*2; i < maxks; ++i) {
            current = rdtsc();
		
            if (!uintr_timer_flag) {
                ACCESS_ONCE(last[i]) = current;
                continue;
            }   
            if (current - ACCESS_ONCE(last[i]) >= TIMESLICE) {
                if (pending_uthreads(i) || pending_cqe(i)) {
                    //printf("kill %d (%d): %lld | %lld, %lld\n", i, kth_tid[i], current - ACCESS_ONCE(last[i]), uintr_sent[i], uintr_recv[i]);
                    pthread_kill(kth_tid[i], SIGUSR1);
                    ++uintr_sent[i];
                    ACCESS_ONCE(last[i]) = current;
                }
            }   
        }
    } 

    return NULL;
}
#endif 

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
    if (uthread_quantum_us > 100) {
        HARD_TIMESLICE = 100000000LL * 1000 * GHZ;
    } else {
        HARD_TIMESLICE = 100 * 1000 * GHZ;
    }
	log_info("quantum: %ld us", TIMESLICE / 1000 / GHZ);
	log_info("quantum2: %ld us", HARD_TIMESLICE / 1000 / GHZ);
    return 0;
}

int uintr_init_thread(void) {
    int kth_id = myk()->kthread_idx;
    assert(kth_id >= 0 && kth_id < MAX_KTHREADS);

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

#ifdef SIGNAL_PREEMPT
    // pthread_t timer_thread2;
    // int ret2 = pthread_create(&timer_thread2, NULL, signal_timer2, NULL);
	// BUG_ON(ret2);
    // log_info("Signal timer pthread2 creates");

    // pthread_t timer_thread3;
    // int ret3 = pthread_create(&timer_thread3, NULL, signal_timer3, NULL);
	// BUG_ON(ret3);
    // log_info("Signal timer pthread3 creates");
#endif

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
/*
 * uintr.h - Functions for user interrupts.
 */

#pragma once

#include <base/thread.h>
#include <x86intrin.h>
#include <runtime/thread.h>

enum rq_type_t {
    NEW_TASK,
    PREEMPTED_TASK
};

extern void uintr_timer_start(void);
extern void uintr_timer_end(void);
extern void uintr_timer_summary(void);

extern void signal_block(void);
extern void signal_unblock(void);

extern void concord_func(void);
extern void concord_disable(void);
extern void concord_enable(void);
extern void concord_set_preempt_flag(int);
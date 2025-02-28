/*
 * preempt.h - support for kthread preemption
 */

#pragma once

#include <base/stddef.h>
#include <base/thread.h>
#include <runtime/thread.h>

#include <x86intrin.h>
#include <stdio.h>

DECLARE_PERTHREAD(unsigned int, preempt_cnt);
DECLARE_PERTHREAD(unsigned int, upreempt_cnt);
extern void preempt(void);
extern void signal_unblock(void);

#ifdef USE_XSAVE
/* maximum size in bytes needed for xsave */
extern size_t xsave_max_size;
/* extended processor features to save */
extern size_t xsave_features;
#endif

/* this flag is set whenever there is _not_ a pending preemption */
#define PREEMPT_NOT_PENDING	(1 << 31)

/**
 * preempt_enabled - returns true if preemption is enabled
 */
static inline bool preempt_enabled(void)
{
	return (perthread_read(preempt_cnt) & ~PREEMPT_NOT_PENDING) == 0;
}

/**
 * assert_preempt_disabled - asserts that preemption is disabled
 */
static inline void assert_preempt_disabled(void)
{
	assert(!preempt_enabled());
}

/**
 * preempt_needed - returns true if a preemption event is stuck waiting
 */
static inline bool preempt_needed(void)
{
#ifdef UNSAFE_PREEMPT_CLUI
	return false;
#else
	return (perthread_read(preempt_cnt) & PREEMPT_NOT_PENDING) == 0;
#endif
}

static inline bool upreempt_needed(void) 
{
#ifdef UNSAFE_PREEMPT_CLUI
	return false;
#else	
	return (perthread_read(upreempt_cnt) & PREEMPT_NOT_PENDING) == 0; 
#endif
}

static inline void set_upreempt_needed(void)
{
	BUILD_ASSERT(~PREEMPT_NOT_PENDING == 0x7fffffff);
	perthread_andi(upreempt_cnt, 0x7fffffff);
}

/**
 * clear_preempt_needed - clear the flag that indicates a preemption request is
 * pending
 */
static inline void clear_preempt_needed(void)
{
	BUILD_ASSERT(PREEMPT_NOT_PENDING == 0x80000000);
	perthread_ori(preempt_cnt, 0x80000000);
}

static inline void clear_upreempt_needed(void)
{
	BUILD_ASSERT(PREEMPT_NOT_PENDING == 0x80000000);
	perthread_ori(upreempt_cnt, 0x80000000);
}

/**
 * preempt_disable - disables preemption
 *
 * Can be nested.
 */
static inline void preempt_disable(void)
{
#ifdef UNSAFE_PREEMPT_CLUI
	if (likely(preempt_enabled()))
		_clui();
#endif
	perthread_incr(preempt_cnt);
	barrier();
	// printf("disable\n");
}

/**
 * preempt_enable_nocheck - reenables preemption without checking for conditions
 *
 * Can be nested.
 */
static inline void preempt_enable_nocheck(void)
{
	barrier();
	perthread_decr(preempt_cnt);
}

/**
 * preempt_enable - reenables preemption
 *
 * Can be nested.
 */
static inline void preempt_enable(void)
{
#ifndef __GCC_ASM_FLAG_OUTPUTS__
	preempt_enable_nocheck();
	#ifdef UNSAFE_PREEMPT_CLUI
		if (likely(preempt_enabled()))
			_stui();
	#else
		if (unlikely(perthread_read(preempt_cnt) == 0))
			preempt();
		else if (unlikely(preempt_enabled() && perthread_read(upreempt_cnt) == 0)) {
#ifndef PREEMPTED_RQ
			thread_yield();
#else
			thread_preempt_yield();
#endif
		}
	#endif
#else
	int zero;
	barrier();
	asm volatile("subl $1, %%gs:__perthread_preempt_cnt(%%rip)"
		     : "=@ccz" (zero) :: "memory", "cc");

	// printf("p: %u, u: %u\n", perthread_read(preempt_cnt) & 7, perthread_read(upreempt_cnt) > 0);
	#ifdef UNSAFE_PREEMPT_CLUI
		if (likely(preempt_enabled()))
			_stui();
	#else
		if (unlikely(zero))
			preempt();
		else if (unlikely(preempt_enabled() && perthread_read(upreempt_cnt) == 0)) {
			clear_upreempt_needed();
#ifndef PREEMPTED_RQ
			thread_yield();
#else
			thread_preempt_yield();
#endif
		}
	#endif
#endif
}



#pragma once

#include <base/pci.h>
#include <base/tcache.h>
#include <base/thread.h>
#include <iokernel/queue.h>

#include "../defs.h"


#define RQ_NUM_DESC			1024
#define SQ_NUM_DESC			128
#define SQ_CLEAN_THRESH			RUNTIME_RX_BATCH_SIZE
#define SQ_CLEAN_MAX			SQ_CLEAN_THRESH

/* space for the mbuf struct */
#define RX_BUF_HEAD \
 (align_up(sizeof(struct mbuf), 2 * CACHE_LINE_SIZE))
/* some NICs expect enough padding for CRC etc., even if they strip it */
#define RX_BUF_TAIL			64

enum {
	DIRECTPATH_MODE_ALLOW_ANY = 0,
	DIRECTPATH_MODE_FLOW_STEERING,
	DIRECTPATH_MODE_QUEUE_STEERING,
	DIRECTPATH_MODE_EXTERNAL,
};
extern int directpath_mode;

static inline unsigned int directpath_get_buf_size(void)
{
	return align_up(net_get_mtu() + RX_BUF_HEAD + RX_BUF_TAIL,
			2 * CACHE_LINE_SIZE);
}

extern struct pci_addr nic_pci_addr;
extern struct mempool directpath_buf_mp;
extern struct tcache *directpath_buf_tcache;
extern DEFINE_PERTHREAD(struct tcache_perthread, directpath_buf_pt);
extern void directpath_rx_completion(struct mbuf *m);

extern int mlx5_init(void);
extern int mlx5_init_thread(void);

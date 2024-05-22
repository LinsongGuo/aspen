# include this Makefile in all subprojects
# define ROOT_PATH before including
ifndef ROOT_PATH
$(error ROOT_PATH is not set)
endif

# load configuration parameters
include $(ROOT_PATH)/build/config

# shared toolchain definitions
INC = -I$(ROOT_PATH)/inc
FLAGS  = -g -Wall -D_GNU_SOURCE $(INC)
LDFLAGS = -T $(ROOT_PATH)/base/base.ld
LD      = gcc
CC      = gcc
LDXX	= g++
CXX	= g++
AR      = ar
SPARSE  = sparse

ifeq ($(CONFIG_CLANG),y)
LD	= clang
CC	= clang
LDXX	= clang++
CXX	= clang++
FLAGS += -Wno-sync-fetch-and-nand-semantics-changed
endif

# libraries to include
RUNTIME_DEPS = $(ROOT_PATH)/libruntime.a $(ROOT_PATH)/libnet.a \
	       $(ROOT_PATH)/libbase.a
RUNTIME_LIBS = $(ROOT_PATH)/libruntime.a $(ROOT_PATH)/libnet.a \
	       $(ROOT_PATH)/libbase.a -lpthread

# PKG_CONFIG_PATH
PKG_CONFIG_PATH := $(ROOT_PATH)/rdma-core/build/lib/pkgconfig:$(PKG_CONFIG_PATH)
PKG_CONFIG_PATH := $(ROOT_PATH)/dpdk/build/lib/x86_64-linux-gnu/pkgconfig:$(PKG_CONFIG_PATH)
PKG_CONFIG_PATH := $(ROOT_PATH)/spdk/build/lib/pkgconfig:$(PKG_CONFIG_PATH)

# mlx5 build
MLX5_INC = -I$(ROOT_PATH)/rdma-core/build/include
MLX5_LIBS = -L$(ROOT_PATH)/rdma-core/build/lib/
MLX5_LIBS += -L$(ROOT_PATH)/rdma-core/build/lib/statics/
MLX5_LIBS += -L$(ROOT_PATH)/rdma-core/build/util/
MLX5_LIBS += -L$(ROOT_PATH)/rdma-core/build/ccan/
MLX5_LIBS += -l:libmlx5.a -l:libibverbs.a -lnl-3 -lnl-route-3 -lrdmacm -lrdma_util -lccan

# parse configuration options
ifeq ($(CONFIG_DEBUG),y)
FLAGS += -DDEBUG -rdynamic -O0 -ggdb -mssse3 -muintr
LDFLAGS += -rdynamic
else
# FLAGS += -DNDEBUG -O3 -mssse3
FLAGS += -DNDEBUG -O3 -mavx512f
# FLAGS += -DNDEBUG -O3 -mavx2
ifeq ($(CONFIG_OPTIMIZE),y)
FLAGS += -march=native -flto -ffast-math
ifeq ($(CONFIG_CLANG),y)
LDFLAGS += -flto
endif
else
# FLAGS += -mssse3 -muintr
FLAGS += -muintr
endif
endif
ifeq ($(CONFIG_MLX5),y)
FLAGS += -DMLX5
else
ifeq ($(CONFIG_MLX4),y)
$(error mlx4 support is not available currently)
FLAGS += -DMLX4
endif
endif
ifeq ($(CONFIG_SPDK),y)
FLAGS += -DDIRECT_STORAGE
RUNTIME_LIBS += $(shell PKG_CONFIG_PATH="$(PKG_CONFIG_PATH)" pkg-config --libs --static libdpdk)
RUNTIME_LIBS += $(shell PKG_CONFIG_PATH="$(PKG_CONFIG_PATH)" pkg-config --libs --static spdk_nvme)
RUNTIME_LIBS += $(shell PKG_CONFIG_PATH="$(PKG_CONFIG_PATH)" pkg-config --libs --static spdk_env_dpdk)
RUNTIME_LIBS += $(shell PKG_CONFIG_PATH="$(PKG_CONFIG_PATH)" pkg-config --libs --static spdk_syslibs)
INC += -I$(ROOT_PATH)/spdk/include
endif
ifeq ($(CONFIG_DIRECTPATH),y)
RUNTIME_LIBS += $(MLX5_LIBS)
INC += $(MLX5_INC)
FLAGS += -DDIRECTPATH
endif
ifeq ($(CONFIG_UNSAFE_PREEMPT),flag)
FLAGS += -DUNSAFE_PREEMPT_FLAG
endif
ifeq ($(CONFIG_UNSAFE_PREEMPT),clui)
FLAGS += -DUNSAFE_PREEMPT_CLUI
endif
ifeq ($(CONFIG_UNSAFE_PREEMPT),simdreg)
FLAGS += -DUNSAFE_PREEMPT_SIMDREG
endif
ifeq ($(CONFIG_UNSAFE_PREEMPT),simdreg_sse)
FLAGS += -DUNSAFE_PREEMPT_SIMDREG
FLAGS += -DUNSAFE_PREEMPT_SIMDREG_SSE
endif
ifeq ($(CONFIG_UNSAFE_PREEMPT),simdreg_512)
FLAGS += -DUNSAFE_PREEMPT_SIMDREG
FLAGS += -DUNSAFE_PREEMPT_SIMDREG_512
endif
ifeq ($(CONFIG_UNSAFE_PREEMPT),simdreg_custom)
FLAGS += -DUNSAFE_PREEMPT_SIMDREG
FLAGS += -DUNSAFE_PREEMPT_SIMDREG_CUSTOM
endif
ifeq ($(CONFIG_UNSAFE_PREEMPT),simdreg_linpack)
FLAGS += -DUNSAFE_PREEMPT_SIMDREG
FLAGS += -DUNSAFE_PREEMPT_SIMDREG_LINPACK
endif

ifeq ($(CONFIG_PREEMPT),signal)
FLAGS += -DSIGNAL_PREEMPT
endif 
ifeq ($(CONFIG_PREEMPT),uintr)
FLAGS += -DUINTR_PREEMPT
endif 
ifeq ($(CONFIG_PREEMPT),concord)
FLAGS += -DCONCORD_PREEMPT
endif 

ifeq ($(CONFIG_GPR_ONLY),y)
FLAGS += -DGPR_ONLY
endif

ifeq ($(CONFIG_USE_XSAVE),y)
FLAGS += -DUSE_XSAVE -m64 -mxsavec
endif

ifeq ($(CONFIG_SMART_PREEMPT), y)
FLAGS += -DSMART_PREEMPT
endif

ifeq ($(CONFIG_PREEMPTED_RQ), y)
FLAGS += -DPREEMPTED_RQ
endif

ifeq ($(CONFIG_TIMER_LOG), y)
FLAGS += -DTIMER_LOG
endif

WRAP_FLAGS = -Wl,-wrap=malloc -Wl,-wrap=free -Wl,-wrap=realloc -Wl,-wrap=calloc -Wl,-wrap=aligned_alloc -Wl,-wrap=posix_memalign
ifeq ($(CONFIG_UNSAFE_PREEMPT),flag)
WRAP_FLAGS += -Wl,-wrap=memcpy -Wl,-wrap=memcmp -Wl,-wrap=memmove -Wl,-wrap=memset -Wl,-wrap=strcmp -Wl,-wrap=strncmp   
endif 
ifeq ($(CONFIG_UNSAFE_PREEMPT),clui)
WRAP_FLAGS += -Wl,-wrap=memcpy -Wl,-wrap=memcmp -Wl,-wrap=memmove -Wl,-wrap=memset -Wl,-wrap=strcmp -Wl,-wrap=strncmp   
endif 

CFLAGS = -std=gnu11 $(FLAGS)
CXXFLAGS = -std=gnu++20 $(FLAGS)

# handy for debugging
print-%  : ; @echo $* = $($*)

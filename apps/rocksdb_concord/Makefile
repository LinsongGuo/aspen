

LLVM_VERSION=11

CC=clang-$(LLVM_VERSION)
OPT=opt-$(LLVM_VERSION)
CXX=clang++-$(LLVM_VERSION)

# CFLAGS=-O3 -g -Wall -D_GNU_SOURCE -mavx512f -Wno-sync-fetch-and-nand-semantics-changed
CFLAGS=-O3 -g -Wall -D_GNU_SOURCE -Wno-sync-fetch-and-nand-semantics-changed
PASS_FLAGS=-c -emit-llvm
WRAP_FLAGS=-Wl,-wrap=malloc -Wl,-wrap=free -Wl,-wrap=realloc -Wl,-wrap=calloc -Wl,-wrap=aligned_alloc -Wl,-wrap=posix_memalign
# WRAP_FLAGS += -Wl,-wrap=memcpy -Wl,-wrap=memcmp -Wl,-wrap=memmove -Wl,-wrap=memset -Wl,-wrap=strcmp -Wl,-wrap=strncmp   # rmb to uncomment

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

CALADAN_PATH=$(ROOT_DIR)/../..
CALADAN_INC=-I$(CALADAN_PATH)/inc -I$(CALADAN_PATH)/bindings/cc
CALADAN_LIBS=$(CALADAN_PATH)/shim/libshim.a \
		$(CALADAN_PATH)/bindings/cc/librt++.a $(CALADAN_PATH)/libruntime.a \
		$(CALADAN_PATH)/libnet.a $(CALADAN_PATH)/libbase.a 

MLX5_LIBS=-L$(CALADAN_PATH)/rdma-core/build/lib/
MLX5_LIBS += -L$(CALADAN_PATH)/rdma-core/build/lib/statics/
MLX5_LIBS += -L$(CALADAN_PATH)/rdma-core/build/util/
MLX5_LIBS += -L$(CALADAN_PATH)/rdma-core/build/ccan/
MLX5_LIBS += -l:libmlx5.a -l:libibverbs.a -lnl-3 -lnl-route-3 -lrdmacm -lrdma_util -lccan
CALADAN_LIBS += $(MLX5_LIBS)

LDFLAGS=-T $(CALADAN_PATH)/base/base.ld

BENCH=rocksdb
# ROCKSDB_INC=-Irocksdb_avx_pic/include/rocksdb/
# ROCKSDB_LIB=rocksdb_avx_pic/librocksdb.a
# ROCKSDB_LIB_CONCORD=rocksdb_avx_pic/librocksdb_concord.a

# ROCKSDB_INC=-Irocksdb_pic/include/rocksdb/
# ROCKSDB_LIB=rocksdb_pic/librocksdb.a
# ROCKSDB_LIB_CONCORD=rocksdb_pic/librocksdb_concord.a

ROCKSDB_INC=-Irocksdb/include/rocksdb/
ROCKSDB_LIB=rocksdb/librocksdb.a
ROCKSDB_LIB_CONCORD=rocksdb/librocksdb_concord.a

ROCKSDB_INCFL=-Irocksdb_func_loop/include/rocksdb/
ROCKSDB_LIB_CONCORDFL=rocksdb_func_loop/librocksdb_concord.a

ROCKSDB_INCF=-Irocksdb_func/include/rocksdb/
ROCKSDB_LIB_CONCORDF=rocksdb_func/librocksdb_concord.a

# ROCKSDB_INC=-Irocksdb_nopt/include/rocksdb/
# ROCKSDB_LIB=rocksdb_nopt/librocksdb.a
# ROCKSDB_LIB_CONCORD=rocksdb_nopt/librocksdb_concord.a

OPT_CONFIG=-postdomtree -mem2reg -indvars -loop-simplify -branch-prob -scalar-evolution 
CONCORD_PASS=$(ROOT_DIR)/../../../concord/src/cache-line-pass/build/src/libConcordPass.so

all: clean concord-rocksdb rocksdb_server rocksdb_server_concord rocksdb_server_concord_fl rocksdb_server_concord_f

concord-rocksdb:
	$(CC) $(ROCKSDB_INC) $(CFLAGS) $(PASS_FLAGS) concord-rocksdb.c -o $(BENCH).bc
	$(OPT) -S $(OPT_CONFIG) < $(BENCH).bc > $(BENCH).opt.bc

	$(OPT) -S -load $(CONCORD_PASS) -yield < $(BENCH).opt.bc > $(BENCH).pass.opt.bc
	
	$(CC) $(BENCH).bc $(CFLAGS) -c -o concord_apirocksdb.a
	$(CC) $(BENCH).pass.opt.bc $(CFLAGS) -c -o concord_apirocksdb_concord.a
	
# rocksdb_server:
# 	$(CXX) $(CFLAGS) -fPIC $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INC) $(CALADAN_INC) -o rocksdb_server -ldl rocksdb_server.cc concord_apirocksdb.a $(ROCKSDB_LIB) $(CALADAN_LIBS) -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc

# rocksdb_server_concord:
# 	$(CXX) $(CFLAGS) -fPIC $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INC) $(CALADAN_INC) -o rocksdb_server_concord -ldl rocksdb_server.cc concord_apirocksdb.a $(ROCKSDB_LIB_CONCORD) $(CALADAN_LIBS) -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc

rocksdb_server:
	$(CXX) $(CFLAGS) $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INC) $(CALADAN_INC) -o rocksdb_server -ldl rocksdb_server.cc concord_apirocksdb.a $(ROCKSDB_LIB) $(CALADAN_LIBS) -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc

rocksdb_server_concord:
	$(CXX) $(CFLAGS) $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INC) $(CALADAN_INC) -o rocksdb_server_concord -ldl rocksdb_server.cc concord_apirocksdb.a $(ROCKSDB_LIB_CONCORD) $(CALADAN_LIBS) -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc

rocksdb_server_concord_fl:
	$(CXX) $(CFLAGS) $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INCFL) $(CALADAN_INC) -o rocksdb_server_concord_fl -ldl rocksdb_server.cc concord_apirocksdb.a $(ROCKSDB_LIB_CONCORDFL) $(CALADAN_LIBS) -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc

rocksdb_server_concord_f:
	$(CXX) $(CFLAGS) $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INCF) $(CALADAN_INC) -o rocksdb_server_concord_f -ldl rocksdb_server.cc concord_apirocksdb.a $(ROCKSDB_LIB_CONCORDF) $(CALADAN_LIBS) -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc

clean:
	rm -f rocksdb_server rocksdb_server_concord rocksdb_server_concord_fl rocksdb_server_concord_f


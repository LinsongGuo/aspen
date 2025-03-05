
ROOT_PATH=../..
include $(ROOT_PATH)/build/shared.mk

LLVM_VERSION=11

librt_libs = $(ROOT_PATH)/bindings/cc/librt++.a
INC += -I$(ROOT_PATH)/bindings/cc
RUNTIME_LIBS := $(RUNTIME_LIBS)
lib_shim = $(ROOT_PATH)/shim/libshim.a

CC=clang-$(LLVM_VERSION)
OPT=opt-$(LLVM_VERSION)
CXX=clang++-$(LLVM_VERSION)
PASS_FLAGS=-c -emit-llvm

CFLAGS := $(filter-out -muintr, $(CFLAGS))
CXXFLAGS := $(filter-out -muintr, $(CXXFLAGS))

BENCH=rocksdb

ROCKSDB_INC=-Irocksdb/include/rocksdb/
ROCKSDB_LIB=rocksdb/librocksdb.a
ROCKSDB_LIB_CONCORD=rocksdb/librocksdb_concord.a

ROCKSDB_INCFL=-Irocksdb_func_loop/include/rocksdb/
ROCKSDB_LIB_CONCORDFL=rocksdb_func_loop/librocksdb_concord.a

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
OPT_CONFIG=-postdomtree -mem2reg -indvars -loop-simplify -branch-prob -scalar-evolution 
CONCORD_PASS=$(ROOT_DIR)/rocksdb/concord/src/cache-line-pass/build/src/libConcordPass.so

THIRD_LIBS=-lgflags -lsnappy -lz -llz4 -lbz2 -lzstd -lpthread -ljemalloc

all: clean concord-rocksdb rocksdb_server rocksdb_server_concord rocksdb_server_concord_fl

concord-rocksdb:
	$(CC) $(ROCKSDB_INC) $(CFLAGS) $(PASS_FLAGS) concord-rocksdb.c -o $(BENCH).bc
	$(OPT) -S $(OPT_CONFIG) < $(BENCH).bc > $(BENCH).opt.bc

	$(OPT) -S -load $(CONCORD_PASS) -yield < $(BENCH).opt.bc > $(BENCH).pass.opt.bc
	
	$(CC) $(BENCH).bc $(CFLAGS) -c -o concord_apirocksdb.a
	$(CC) $(BENCH).pass.opt.bc $(CFLAGS) -c -o concord_apirocksdb_concord.a
	
rocksdb_server:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INC) $(CALADAN_INC) -o rocksdb_server -ldl rocksdb_server.cc concord_apirocksdb.a $(ROCKSDB_LIB) $(lib_shim) $(librt_libs) $(RUNTIME_LIBS) $(THIRD_LIBS)

rocksdb_server_concord:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INC) $(CALADAN_INC) -o rocksdb_server_concord -ldl rocksdb_server.cc concord_apirocksdb_concord.a $(ROCKSDB_LIB_CONCORD) $(lib_shim) $(librt_libs) $(RUNTIME_LIBS) $(THIRD_LIBS)

rocksdb_server_concord_fl:
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(WRAP_FLAGS) $(ROCKSDB_INCFL) $(CALADAN_INC) -o rocksdb_server_concord_fl -ldl rocksdb_server.cc concord_apirocksdb_concord.a $(ROCKSDB_LIB_CONCORDFL) $(lib_shim) $(librt_libs) $(RUNTIME_LIBS) $(THIRD_LIBS)

clean:
	rm -f rocksdb_server rocksdb_server_concord rocksdb_server_concord_fl


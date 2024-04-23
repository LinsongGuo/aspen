ROOT_PATH=../..
include $(ROOT_PATH)/build/shared.mk

LLVM_VERSION=11

CC=clang-$(LLVM_VERSION)
OPT=opt-$(LLVM_VERSION)
CXX=clang++-$(LLVM_VERSION)


librt_libs = $(ROOT_PATH)/bindings/cc/librt++.a
INC += -I$(ROOT_PATH)/bindings/cc
LIBS += -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc
lib_shim = $(ROOT_PATH)/shim/libshim.a

INC += -IDataFrame/include
lib_df = DataFrame/build/libDataFrame.a
lib_df = DataFrame/build/libDataFrame.a

main_src = main.cc
main_obj = $(main_src:.cc=.o)

src = $(main_src)
obj = $(main_obj)
dep = $(obj:.o=.d)

CFLAGS := $(filter-out -muintr, $(CFLAGS))
CXXFLAGS := $(filter-out -muintr, $(CXXFLAGS))

PASS_FLAGS = -c -emit-llvm

# must be first
all: main

main: $(main_obj) $(lib_df) $(lib_shim) $(librt_libs) $(RUNTIME_DEPS) $(LIBS)
	$(CXX) -o $@ $(LDFLAGS) $(WRAP_FLAGS) -ldl $(main_obj) $(lib_df) $(lib_shim) $(librt_libs) $(RUNTIME_LIBS) $(LIBS) 

ifneq ($(MAKECMDGOALS),clean)
-include $(dep)   # include all dep files in the makefile
endif

%.d: %.cc
	@$(CXX) $(CXXFLAGS) $< -MM -MT $(@:.d=.o) >$@
%.o: %.cc
	@echo "CXXFLAGS: ${CXXFLAGS}"
	@echo "LDFLAGS: ${LDFLAGS}"
	@echo "RUNTIME_LIBS: ${RUNTIME_DEPS}"
	@echo "LIBS: ${LIBS}"
	$(CXX) $(CXXFLAGS) -c $< -o $@
# %.bc: %.cc
# 	$(CXX) $(CXXFLAGS) $(PASS_FLAGS) $< -o $@
%.o: %.c 
	$(CC) $(CFLAGS) -c $< -o $@

.PHONY: clean
clean:
	rm -f $(obj) $(dep) main

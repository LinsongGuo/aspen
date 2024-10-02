# Makefile for uintr_bench
ROOT_PATH=../..
include $(ROOT_PATH)/build/shared.mk

librt_libs = $(ROOT_PATH)/bindings/cc/librt++.a
INC += -I$(ROOT_PATH)/bindings/cc
RUNTIME_LIBS := $(RUNTIME_LIBS) -lnuma
lib_shim = $(ROOT_PATH)/shim/libshim.a

bench_src = bench.cc
bench_obj = $(bench_src:.cc=.o)
bench_dep = $(bench_obj:.cc=.o)

program_src = $(wildcard programs/*.c)
program_obj = $(patsubst %.c,%.o,$(program_src))

# # For chase:
# chase_obj = $(wildcard programs/chase.o)
# program_obj += $(chase_obj)

# For array:
array_obj = $(wildcard programs/array.o)
program_obj += $(array_obj)

# For mcf:
mcf_src = $(wildcard programs/mcf/src/*.c)
mcf_obj =  $(patsubst %.c,%.o,$(mcf_src))
program_obj += $(mcf_obj)

new_src = new.cc
new_obj = $(new_src:.cc=.o)

# must be first
all: bench 

bench: $(bench_obj) $(program_obj) $(lib_shim) $(librt_libs) $(RUNTIME_DEPS)  
	$(LDXX) -g -o $@ $(LDFLAGS) $(WRAP_FLAGS) $(bench_obj) $(program_obj) $(lib_shim) $(librt_libs) $(RUNTIME_LIBS)

ifneq ($(MAKECMDGOALS),clean)
-include $(dep)   # include all dep files in the makefile
endif

# rule to generate a dep file by using the C preprocessor
# (see man cpp for details on the -MM and -MT options)
%.d: %.cc
	@$(CXX) $(CXXFLAGS) -muintr -Iprograms $< -MM -MT $(@:.d=.o) >$@
%.o: %.cc
	$(CXX) $(CXXFLAGS) -g -muintr -Iprograms -c $< -o $@

wrap.o: wrap.c
	$(CC) $(CFLAGS) -g -muintr -c $< -o $@

.PHONY: clean
clean:
	rm -f $(bench_obj) $(bench_dep) bench
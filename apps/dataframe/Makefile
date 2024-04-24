ROOT_PATH=../..
include $(ROOT_PATH)/build/shared.mk

LLVM_VERSION=11

CC=clang-$(LLVM_VERSION)
OPT=opt-$(LLVM_VERSION)
CXX=clang++-$(LLVM_VERSION)
LLC=llc-11

librt_libs = $(ROOT_PATH)/bindings/cc/librt++.a
INC += -I$(ROOT_PATH)/bindings/cc
LIBS += -lgflags -lsnappy -lz -llz4 -lpthread -ljemalloc
lib_shim = $(ROOT_PATH)/shim/libshim.a

INC += -IDataFrame/include
lib_df = DataFrame/build/lib/libDataFrame.a
# INC += -IDataFrame_1_19_clang/include
# lib_df = DataFrame_1_19_clang/build/lib/libDataFrame.a

main_src = main.cc
main_obj = $(main_src:.cc=.a)
main_concord_obj = $(main_src:.cc=_concord.a)
main_bc = $(main_src:.cc=.bc)
main_concord_bc = $(main_src:.cc=_concord.bc)
main_opt_bc = $(main_src:.cc=.opt.bc)
main_pass_opt_bc = $(main_src:.cc=.pass.opt.bc)

src = $(main_src)
obj = $(main_obj) $(main_concord_obj)
bc = $(main_bc) $(main_concord_bc) $(main_opt_bc) $(main_pass_opt_bc)
dep = $(main_src:.cc=.d)

CFLAGS := $(filter-out -muintr, $(CFLAGS))
CXXFLAGS := $(filter-out -muintr, $(CXXFLAGS))

PASS_FLAGS = -c -emit-llvm

OPT_CONFIG=-postdomtree -mem2reg -indvars -loop-simplify -branch-prob -scalar-evolution 
CONCORD_PASS=concord/src/cache-line-pass/build/src/libConcordPass.so
CONCORD_PASS_OPT = -load $(CONCORD_PASS) -yield # -loop_body_size 200

# must be first
all: main main_concord

main: $(main_obj) $(lib_df) $(lib_shim) $(librt_libs) $(RUNTIME_DEPS) $(LIBS)
	$(CXX) -o $@ $(LDFLAGS) $(WRAP_FLAGS) -ldl $(main_obj) $(lib_df) $(lib_shim) $(librt_libs) $(RUNTIME_LIBS) $(LIBS) 

main_concord: $(main_concord_obj) $(main_pass_opt_bc) $(main_opt_bc) $(lib_df) $(lib_shim) $(librt_libs) $(RUNTIME_DEPS) $(LIBS)
	$(CXX) -o $@ $(LDFLAGS) $(WRAP_FLAGS) -ldl $(main_concord_obj) $(lib_df) $(lib_shim) $(librt_libs) $(RUNTIME_LIBS) $(LIBS) 

ifneq ($(MAKECMDGOALS),clean)
-include $(dep)   # include all dep files in the makefile
endif

%.d: %.cc
	@$(CXX) $(CXXFLAGS) $< -MM -MT $(@:.d=.o) >$@

%.a: %.bc
	$(CXX) $(CXXFLAGS) -c $< -o $@

%_concord.a: %.pass.opt.bc
	$(CXX) $(CXXFLAGS) -c $< -o $@

# Apply concord pass:
%.pass.opt.bc: %.opt.bc
	$(OPT) -S $(CONCORD_PASS_OPT) < $< > $@
#	$(OPT) -S -load $(CONCORD_PASS) -yield < $< > $@
%.opt.bc: %_concord.bc
	$(OPT) -S $(OPT_CONFIG) < $< > $@

%.bc: %.cc
	$(CXX) $(CXXFLAGS) $(PASS_FLAGS) $< -o $@

%_concord.bc: %.cc
	$(CXX) $(CXXFLAGS) $(PASS_FLAGS) -DCONCORD_UNROLL $< -o $@

.PHONY: clean
clean:
	rm -f $(obj) $(dep) $(bc) main main_concord

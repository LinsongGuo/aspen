#!/bin/bash
# This script builds the RocksDB library in two configurations:
# 1. Functions-only instrumentation: Output at `apps/rocksdb_concord/rocksdb/librocksdb.a`
# 2. Functions and loops instrumentation: Output at `apps/rocksdb_concord/rocksdb_func_loop/librocksdb.a`

set -e

# Function to compile RocksDB
compile_rocksdb() {
    pushd concord/src/cache-line-pass
    ./setup-pass.sh
    popd
    make clean
    make static_lib -j
}

SCRIPT_DIR=$(dirname "$(realpath "$0")")
EXP_DIR=$(dirname "$SCRIPT_DIR")
HOME_DIR=$(dirname "$EXP_DIR")

pushd $HOME_DIR/apps/rocksdb_concord

# Compile RocksDB using Clang (only function calls instrumented)
if pushd rocksdb; then
    compile_rocksdb
    popd
else
    echo "Error: Directory 'rocksdb' not found!"
    exit 1
fi

# Compile RocksDB using Clang (functions and loops instrumented)
if pushd rocksdb_func_loop; then
    compile_rocksdb
    popd
else
    echo "Error: Directory 'rocksdb_func_loop' not found!"
    exit 1
fi

# Return to the original directory
popd
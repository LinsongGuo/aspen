#!/bin/bash
# This script compiles the rocksdb runtime with different preemption mechanisms
# based on the provided option: non-preemptive, signal, uintr, concord, or concord-fine_tuned.

set -e

FIG5_DIR=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$FIG5_DIR")
EXP_DIR=$(dirname "$SCRIPT_DIR")
HOME_DIR=$(dirname "$EXP_DIR")

# Check if the option is provided
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 {non-preemptive|signal|uintr|concord|concord-fine_tuned}"
    exit 1
fi

option=$1

# Copy the corresponding config file
if [[ "$option" == "concord-fine_tuned" ]]; then
    cp "$FIG5_DIR/configs/concord_config" "$HOME_DIR/build/config"
else
    cp "$FIG5_DIR/configs/$option_config" "$HOME_DIR/build/config"
fi

# Build the iokernel and Caladan runtime
$SCRIPT_DIR/caladan.sh

# Navigate to the RocksDB applications directory
pushd $HOME_DIR/apps/rocksdb_concord

make clean
make

# Return to the original directory
popd
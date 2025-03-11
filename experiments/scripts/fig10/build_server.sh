#!/bin/bash
# This script compiles the Rocksdb runtime with different preemption policies
set -e

FIG10_DIR=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$FIG10_DIR")
EXP_DIR=$(dirname "$SCRIPT_DIR")
HOME_DIR=$(dirname "$EXP_DIR")

# Check if the option is provided
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 {non-preemptive|aspen|aspen_wo2queue|aspen_wo2queue_woskip|libpreemptible}"
    exit 1
fi

option=$1

# If option is 'libpreemptible', change it to 'aspen_wo2queue_woskip'
if [[ "$option" == "libpreemptible" ]]; then
    option="aspen_wo2queue_woskip"
fi

cp $FIG10_DIR/configs/$option_config $HOME_DIR/build/config

# Build the iokernel and Caladan runtime
$SCRIPT_DIR/caladan.sh

# Navigate to the RocksDB application directory
pushd $HOME_DIR/apps/rocksdb_concord

make clean
make

# Return to the original directory
popd
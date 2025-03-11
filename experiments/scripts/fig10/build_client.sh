#!/bin/bash
# This script compiles the client runtime (load generator).

set -e

FIG10_DIR=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$FIG10_DIR")
EXP_DIR=$(dirname "$SCRIPT_DIR")
HOME_DIR=$(dirname "$EXP_DIR")

# Copy the config file of load generator.
cp "$FIG10_DIR/configs/client_config" "$HOME_DIR/build/config"

# Build the iokernel and Caladan runtime
$SCRIPT_DIR/caladan.sh

# Navigate to the load generator directory
pushd $HOME_DIR/apps/loadgen
cargo clean
cargo update
cargo build --release

# Return to the original directory
popd
#!/bin/bash
# This script compiles the BadgerDB server using aspen-Go.
set -e

FIG7_DIR=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$FIG7_DIR")
EXP_DIR=$(dirname "$SCRIPT_DIR")
HOME_DIR=$(dirname "$EXP_DIR")

# Build the Aspen-Go binary
pushd $HOME_DIR/aspen-go/go/src
./make.bash
popd 
echo "Aspen-Go build completed."

# Build the BadgerDB server
pushd $HOME_DIR/aspen-go/badger-bench/server
make clean
make
popd
echo "BadgerDB server build completed."

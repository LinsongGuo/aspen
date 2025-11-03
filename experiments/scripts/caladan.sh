#!/bin/bash
set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
EXP_DIR=$(dirname "$SCRIPT_DIR")
HOME_DIR=$(dirname "$EXP_DIR")

pushd $HOME_DIR

make clean
make -j

pushd ksched
make clean
make -j
popd
sudo ./scripts/setup_machine.sh

pushd bindings/cc
make clean
make -j
popd

pushd shim
make clean
make -j
popd

# Return to the original directory
popd

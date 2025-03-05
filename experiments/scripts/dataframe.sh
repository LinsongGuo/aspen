#!/bin/bash
# This script builds the DataFrame library and places it in:
# `apps/dataframe/DataFrame/build/lib/libDataFrame.a`

set -e

SCRIPT_DIR=$(dirname "$(realpath "$0")")
EXP_DIR=$(dirname "$SCRIPT_DIR")
HOME_DIR=$(dirname "$EXP_DIR")

pushd $HOME_DIR/apps/dataframe/DataFrame

rm -rf build # if exists
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make DataFrame

# Return to the original directory
popd
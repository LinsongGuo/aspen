#!/bin/bash
# This script compiles the DataFrame runtime with different preemption mechanisms
# based on the provided option: non-preemptive, signal, uintr, concord, or concord-fine_tuned.

set -e

FIG6_DIR=$(dirname "$(realpath "$0")")
SCRIPT_DIR=$(dirname "$FIG6_DIR")
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
    cp "$FIG6_DIR/configs/concord.config" "$HOME_DIR/build/config"
else
    cp "$FIG6_DIR/configs/$option.config" "$HOME_DIR/build/config"
fi

# Build the iokernel and Caladan runtime
$SCRIPT_DIR/caladan.sh

# Navigate to the DataFrame application directory
pushd $HOME_DIR/apps/dataframe

make clean
if [[ "$option" == "non-preemptive" || "$option" == "signal" || "$option" == "uintr" ]]; then
    make main
elif [[ "$option" == "concord" ]]; then
    make main_concord
elif [[ "$option" == "concord-fine_tuned" ]]; then
    make main_concord UNROLL=1
else
    echo "Error: Invalid option '$option'."
    exit 1
fi

# Return to the original directory
popd
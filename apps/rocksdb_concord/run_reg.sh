#!/bin/bash

task=$1
work=$2
mode=$3

taskpath="reg_results/$task"
if [ ! -d "$taskpath" ]; then
    mkdir $taskpath
fi 

# echo "Work: $work, mode: $mode"

for run in {1..15}; do
    workpath="reg_results/$task/$work"
    if [ ! -d "$workpath" ]; then
        mkdir $workpath
    fi 

    modepath="$workpath/$mode"
    if [ ! -d "$modepath" ]; then
        mkdir $modepath
    fi 

    sudo rm -rf /tmp/my_db/
    sudo timeout 300s ./rocksdb_server ../../server.config local $work &>$modepath/$run
done
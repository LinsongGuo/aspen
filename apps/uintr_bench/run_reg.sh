#!/bin/bash

task='mcf'
num=(24) # 3 4 5 6 7 8 10 12 14 16 20 24 28 32)

taskpath="reg_results/$task/5"
if [ ! -d "$taskpath" ]; then
    mkdir $taskpath
fi 

for n in "${num[@]}"; do
    
    work="$task*$n"
    workpath="$taskpath/$work"
    if [ ! -d "$workpath" ]; then
        mkdir $workpath
    fi 
    
    echo "Work: $work"

    # =========== saving all ===========
    mode='save_all'
    cd ../..
    sed -i "22s/.*/CONFIG_GPR_ONLY=n/" build/config
    ./compile2.sh
    cd apps/uintr_bench
    make clean
    make

    modepath="$workpath/$mode"
    if [ ! -d "$modepath" ]; then
        mkdir $modepath
    fi 
    
    for run in {30..45}; do
        sudo timeout 200s ./bench ../../server.config $work &>$modepath/$run
    done

    # =========== saving ess ===========
    mode='save_ess'
    cd ../..
    sed -i "22s/.*/CONFIG_GPR_ONLY=y/" build/config
    ./compile2.sh
    cd apps/uintr_bench
    make clean
    make

    modepath="$workpath/$mode"
    if [ ! -d "$modepath" ]; then
        mkdir $modepath
    fi 

    for run in {30..45}; do
        sudo timeout 200s ./bench ../../server.config $work &>$modepath/$run
    done

done
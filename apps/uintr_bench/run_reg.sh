#!/bin/bash

task='mcf'
num=(8 12 16 20 24 28 32)

taskpath="reg_results_test/$task/5"
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


    # =========== saving general  ===========
    mode='save_gen'
    cd ../..
    sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg/" build/config
    sed -i "22s/.*/CONFIG_GPR_ONLY=y/" build/config
    sed -i "24s/.*/CONFIG_USE_XSAVE=n/" build/config
    ./compile2.sh
    cd apps/uintr_bench
    make clean
    make

    modepath="$workpath/$mode"
    if [ ! -d "$modepath" ]; then
        mkdir $modepath
    fi 

    for run in {1..33}; do
        sudo timeout 200s ./bench ../../server.config $work &>$modepath/$run
    done


    # =========== saving all 256 ===========
    mode='save_256'
    cd ../..
    sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg/" build/config
    sed -i "22s/.*/CONFIG_GPR_ONLY=n/" build/config
    sed -i "24s/.*/CONFIG_USE_XSAVE=n/" build/config
    ./compile2.sh
    cd apps/uintr_bench
    make clean
    make

    modepath="$workpath/$mode"
    if [ ! -d "$modepath" ]; then
        mkdir $modepath
    fi 
    
    for run in {1..33}; do
        sudo timeout 200s ./bench ../../server.config $work &>$modepath/$run
    done


    # =========== saving all 512 ===========
    mode='save_512'
    cd ../..
    sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg_512/" build/config
    sed -i "22s/.*/CONFIG_GPR_ONLY=n/" build/config
    sed -i "24s/.*/CONFIG_USE_XSAVE=n/" build/config
    ./compile2.sh
    cd apps/uintr_bench
    make clean
    make

    modepath="$workpath/$mode"
    if [ ! -d "$modepath" ]; then
        mkdir $modepath
    fi 
    
    for run in {1..33}; do
        sudo timeout 200s ./bench ../../server.config $work &>$modepath/$run
    done

   
    # =========== xsave  ===========
    mode='xsave'
    cd ../..
    sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg/" build/config
    sed -i "22s/.*/CONFIG_GPR_ONLY=n/" build/config
    sed -i "24s/.*/CONFIG_USE_XSAVE=y/" build/config
    ./compile2.sh
    cd apps/uintr_bench
    make clean
    make

    modepath="$workpath/$mode"
    if [ ! -d "$modepath" ]; then
        mkdir $modepath
    fi 

    for run in {1..33}; do
        sudo timeout 200s ./bench ../../server.config $work &>$modepath/$run
    done


done
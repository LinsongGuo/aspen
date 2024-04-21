#!/bin/bash

tasks=('scan' 'scan+get' 'get')

if [ "$task" = "scan+get" ]; then
    echo "The task is scan+get."
    num=(1 2 3 4 6 8 10 12 14 16) 
else
    echo "The task is not scan+get."
    num=(2 4 6 8 12 16 20 24 28 32)  
fi

for task in "${tasks[@]}"; do
    for n in "${num[@]}"; do
        work="$task"
        for ((i=1; i<$n; i++)); do
            work="$work+$task"
        done

        mode='save_512'
        cd ../..
        sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg_512/" build/config
        sed -i "24s/.*/CONFIG_USE_XSAVE=n/" build/config
        ./compile2.sh
        cd apps/rocksdb_concord
        make clean
        make

        echo "run_reg.sh $task $work $mode"
        ./run_reg.sh $task $work $mode

        #=====================================================#
        

        mode='xsavec'
        cd ../..
        sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg/" build/config
        sed -i "24s/.*/CONFIG_USE_XSAVE=y/" build/config
        ./compile2.sh
        cd apps/rocksdb_concord
        make clean
        make

        echo "run_reg.sh $task $work $mode"
        ./run_reg.sh $task $work $mode

        #=====================================================#
        
        mode='save_ess'
        cd ../..
        sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg_custom/" build/config
        sed -i "24s/.*/CONFIG_USE_XSAVE=n/" build/config
        ./compile2.sh
        cd apps/rocksdb_concord
        make clean
        make

        echo "run_reg.sh $task $work $mode"
        ./run_reg.sh $task $work $mode

        #=====================================================#
        
        mode='save_256'
        cd ../..
        sed -i "18s/.*/CONFIG_UNSAFE_PREEMPT=simdreg/" build/config
        sed -i "24s/.*/CONFIG_USE_XSAVE=n/" build/config
        ./compile2.sh
        cd apps/rocksdb_concord
        make clean
        make

        echo "run_reg.sh $task $work $mode"
        ./run_reg.sh $task $work $mode


    done
done

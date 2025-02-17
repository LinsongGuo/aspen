#!/bin/bash


# Get the absolute path of the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the main directory
MAIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

run_iokernel() {
    sudo $MAIN_DIR/iokerneld simple numanode 1 nobw noht nicpci 0000:b5:00.1 &
}

kill_iokernel() {
    sudo pkill iokerneld
}

run_experiment() {
    local mechanism=$1
    local cost=$2

    if [[ "$mechanism" != "signal" && "$mechanism" != "uintr" && "$mechanism" != "concord" ]]; then
        echo "Error: The first argument must be 'signal', 'uintr' or 'concord'."
        return 1
    fi

    if [[ "$cost" != "all" && "$cost" != "preempt" ]]; then
        echo "Error: The second argument must be either 'all' cost or 'preempt' cost."
        return 1
    fi

    if [ "$mechanism" == "signal" ]; then
        cmd=$MAIN_DIR/apps/dataframe/main
    elif [ "$mechanism" == "uintr" ]; then
        cmd=$MAIN_DIR/apps/dataframe/main
    else 
        cmd=$MAIN_DIR/apps/dataframe/main_concord
    fi

    # modify the build/config file
    sed -i "20s/.*/CONFIG_PREEMPT=$mechanism/" $MAIN_DIR/build/config
    if [ "$cost" == "all" ]; then
        sed -i "32s/.*/CONFIG_PREEMPT_MEASURE=n/" $MAIN_DIR/build/config
        # works=(ad decay rmv ppo kmeans ad+rmv ad+ppo ad+kmeans decay+rmv decay+ppo decay+kmeans rmv+rmv ppo+ppo kmeans+kmeans rmv+ppo+kmeans rmv+ppo+kmeans+rmv+ppo+kmeans ad+rmv+ad+ppo+ad+kmeans decay+rmv+decay+ppo+decay+kmeans ad+rmv+decay+ppo+ad+kmeans)
        works=(ad+decay+rmv+ppo+kmeans)
        mechanism=${mechanism}_all
        quanta=(5)
    else
        sed -i "32s/.*/CONFIG_PREEMPT_MEASURE=y/" $MAIN_DIR/build/config
        # works=(ad decay rmv ppo kmeans ad+rmv ad+ppo ad+kmeans decay+rmv decay+ppo decay+kmeans rmv+rmv ppo+ppo kmeans+kmeans rmv+ppo+kmeans rmv+ppo+kmeans+rmv+ppo+kmeans ad+rmv+ad+ppo+ad+kmeans decay+rmv+decay+ppo+decay+kmeans ad+rmv+decay+ppo+ad+kmeans)
        works=(ad+decay+rmv+ppo+kmeans)
        quanta=(100000000 5)
    fi 

    # compile the file
    pushd ..
    ./compile.sh
    pushd apps/dataframe
    make clean
    make
    popd
    popd
    
    run_iokernel
    sleep 5

    SERVER_CONFIG=$SCRIPT_DIR/config/measure_cost_df.config
    SERVER_INPUT=$MAIN_DIR/apps/dataframe/DataFrame/data/DT_IBM.csv
    for q in "${quanta[@]}"; do
        sed -i "8s/.*/runtime_uthread_quantum_us $q/" $SERVER_CONFIG

        resultpath="$SCRIPT_DIR/results/cost_df"
        if [ ! -d "$resultpath" ]; then
            mkdir -p "$resultpath"
        fi 
        
        qpath="$resultpath/$q"
        if [ ! -d "$qpath" ]; then
            mkdir -p "$qpath"
        fi 
        
        for run in {1..99}; do
            # echo "Run: $run"

            for work in "${works[@]}"; do
                # echo "Work: $work"

                workpath="$qpath/$work"
                if [ ! -d "$workpath" ]; then
                    mkdir -p "$workpath"
                fi 

                mechpath="$workpath/$mechanism"
                if [ ! -d "$mechpath" ]; then
                    mkdir -p "$mechpath"
                fi 

                sudo rm -rf /tmp/my_db/
                sudo timeout 60s $cmd $SERVER_CONFIG local $SERVER_INPUT $work &>$mechpath/$run

            done
        done
    done

    kill_iokernel
}

# Call the function with provided arguments
run_experiment uintr preempt
run_experiment uintr all
run_experiment concord preempt
run_experiment concord all
run_experiment signal preempt
run_experiment signal all

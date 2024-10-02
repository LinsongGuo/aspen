#!/bin/bash

start=20000
endd=500000
inc=20000

try=23

for (( N=$start; N<=$endd; N+=$inc )); do
    path=reg_results/L2/general/${N}
    mkdir -p $path

    sed -i "29s/.*/#define N ${N}/" rocksdb_server.cc
    make

    outpath="$path/getbase"
    mkdir -p $outpath
    for (( t=1; t<=$try; t++ ))
    do
        sudo rm -rf /tmp/my_db/
        sudo timeout 120s ./rocksdb_server ../../server.config local get >$outpath/$t 2>&1
    done


    for (( n=1; n<=2; n++ ))
    do
        work=""
        for (( i=1; i<=$n; i++ ))
        do
            if [ $i -eq 1 ]; then
                work="get"
            else
                work="${work}+get"
            fi
        done

        echo "N = $N, work = $work"
        
        outpath="$path/$work"
        mkdir -p $outpath
        for (( t=5; t<=$try; t++ ))
        do
            sudo rm -rf /tmp/my_db/
            sudo timeout 120s ./rocksdb_server ../../server5.config local $work >$outpath/$t 2>&1
        done

    done

done
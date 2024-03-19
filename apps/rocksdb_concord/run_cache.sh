#!/bin/bash

works=(get get+get get+get+get get+get+get+get scan scan+scan scan+scan+scan scan+scan+scan+scan get+scan get+scan+scan get+scan+scan+scan get+get+scan get+get+scan+scan get+get+get+scan)

for run in {32..51}; do
    echo "Run: $run"

    for ((k=0; k<${#works[@]}; k++)); do 
        work=${works[k]}
        
        echo "Work: $work"

        workpath="cache_results/random_get/$work"
        if [ ! -d "$workpath" ]; then
            mkdir $workpath
        fi 

        pathbase="$workpath/base"
        if [ ! -d "$pathbase" ]; then
            mkdir $pathbase
        fi 

        sudo rm -rf /tmp/my_db/
        sudo timeout 60s ./rocksdb_server ../../server.config local $work &>$pathbase/$run


        path10="$workpath/10"
        if [ ! -d "$path10" ]; then
            mkdir $path10
        fi 

        sudo rm -rf /tmp/my_db/
        sudo timeout 60s ./rocksdb_server ../../server_10.config local $work &>$path10/$run


        path5="$workpath/5"
        if [ ! -d "$path5" ]; then
            mkdir $path5
        fi 

        sudo rm -rf /tmp/my_db/
        sudo timeout 60s ./rocksdb_server ../../server_5.config local $work &>$path5/$run


        path20="$workpath/20"
        if [ ! -d "$path20" ]; then
            mkdir $path20
        fi 

        sudo rm -rf /tmp/my_db/
        sudo timeout 60s ./rocksdb_server ../../server_20.config local $work &>$path20/$run
    done
done
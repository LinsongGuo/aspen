#!/bin/bash

# works=(max max+max max+max+max max+max+max+max kmeans kmeans+kmeans kmeans+kmeans+kmeans kmeans+kmeans+kmeans+kmeans max+kmeans max+kmeans+kmeans max+kmeans+kmeans+kmeans max+max+kmeans max+max+kmeans+kmeans max+max+max+kmeans)


# works=(kmeans+kmeans+kmeans)

works=(max+max+max)

# works=(max+max+kmeans)

for run in {1..1}; do
    echo "Run: $run"

    for ((k=0; k<${#works[@]}; k++)); do 
        work=${works[k]}
        
        echo "Work: $work"

        workpath="comb_results/$work"
        if [ ! -d "$workpath" ]; then
            mkdir $workpath
        fi 

        # pathbase="$workpath/base"
        # if [ ! -d "$pathbase" ]; then
        #     mkdir $pathbase
        # fi 
        # sudo ./main ../../server.config $work &>$pathbase/$run

        # path10="$workpath/10"
        # if [ ! -d "$path10" ]; then
        #     mkdir $path10
        # fi 
        # sudo ./main ../../server_10.config $work &>$path10/$run

        # path5="$workpath/5"
        # if [ ! -d "$path5" ]; then
        #     mkdir $path5
        # fi 
        # sudo ./main ../../server_5.config $work &>$path5/$run

        path20="$workpath/20"
        if [ ! -d "$path20" ]; then
            mkdir $path20
        fi 
        sudo ./main ../../server_20.config $work &>$path20/$run
    done

done
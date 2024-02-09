#!/bin/bash

bench=$1
work=$2
Tus=(100000000 100 50 20 15 10 5 3 2)
trial=13

respath="cache_pollution_results/$bench/$work"
if [ ! -d "$respath" ]; then
	mkdir $respath
fi 

for ((j=1; j<=trial; j++)); do
	for ((i=0; i<${#Tus[@]}; i++)); do 
    	tus=${Tus[i]}

		uspath="$respath/$tus"
		if [ ! -d "$uspath" ]; then
			mkdir $uspath
		fi 
		
		echo $j $work $tus 

		export TIMESLICE=$tus 
		resfile="$uspath/$j"
        sudo -E ./bench ../../server.config $work >$resfile 
		sleep 1
    done
done

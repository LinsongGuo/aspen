bench=$1
# times=(8)
times=(1 2 3 4 6 8)


if [ ! -d "cache_pollution_results/$bench" ]; then
	mkdir cache_pollution_results/$bench
fi 

for ((i=0; i<${#times[@]}; i++)); do
    ./run_cache_pollution_single.sh $bench $bench*${times[i]}
done

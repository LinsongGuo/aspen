# benches=(mcf base64 matmul)
# benches=(cache_unfriendly cache_friendly cache_stripe)
benches=(cache_unfriendly)

for ((i=0; i<${#benches[@]}; i++)); do
    ./run_cache_pollution.sh ${benches[i]}
done

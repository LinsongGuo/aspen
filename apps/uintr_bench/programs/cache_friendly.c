#include <stdio.h>
#include <stdlib.h>
#include "programs.h"

#define N (1024 * 4)
#define M (1024 * 128)

long long cache_friendly() {
    unsigned* val = (unsigned*) malloc(N * sizeof(unsigned));

    unsigned i, k;
    val[0] = 333;
    for (i = 1; i < N; ++i) {
        val[i] = val[i - 1] + i;
    }

    for (k = 0; k < M; ++k) {
        for (i = 1; i < N; ++i) {
            val[i] += val[i - 1] * i;
        }
    }
    
    // int j;
    // for (k = 0; k < M; ++k) {
    //     for (j = N - 2; j >= 0; --j) {
    //         val[j] += val[j + 1] * j; 
    //     }
    // } 

    // unsigned j;
    // for (k = 0; k < M; ++k) {
    //     for (i = 32; i < N; i += 32) {
    //         val[i] += val[i - 1] * i;
    //     }
    //     for (j = 1; j < 32; ++j) {
    //         for (i = j; i < N; i += 32) {
    //             val[i] += val[i - 1] * i;
    //         }
    //     }
    //     // for (i = 1; i < N; ++i) {
    //     //     val[i] += val[i - 1] * i;
    //     // }
    // }

    unsigned sum = 0;
    for (i = 0; i < N; i += 32) {
        sum += val[i] * i;
    }

    free(val);

    return (long long)sum;
}
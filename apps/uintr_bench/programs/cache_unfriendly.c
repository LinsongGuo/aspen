#include <stdio.h>
#include <stdlib.h>
#include "programs.h"

#define N (1024 * 1024 * 256)

long long cache_unfriendly() {
    unsigned* val = (unsigned*) malloc(N * sizeof(unsigned));

    unsigned i;
    val[0] = 333;
    for (i = 1; i < N; ++i) {
        val[i] = val[i - 1] + i;
    }

    for (i = 1; i < N; ++i) {
        val[i] += val[i - 1] * i;
    }

    unsigned sum = 0;
    for (i = 0; i < N; i += 32) {
        sum += val[i] * i;
    }

    free(val);

    return (long long)sum;
}
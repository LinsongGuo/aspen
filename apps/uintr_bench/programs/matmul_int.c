// Writen by Attractive Chaos; distributed under the MIT license

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <x86intrin.h>

#include "programs.h"

int mod = 1023;

int **mm_init_int(int n) {
  // _clui();
  int **m = (int **)malloc(n * sizeof(void *));
  for (int i = 0; i < n; ++i) {
    m[i] = calloc(n, sizeof(int));
  }
  // _stui();
  return m;
}

void mm_destroy_int(int n, int **m) {
  // _clui();
  for (int i = 0; i < n; ++i) {
    free(m[i]);
  }
  free(m);
  // _stui();
}

int **mm_gen_int(int n, int seed) {
  // _clui();
  int **m = mm_init_int(n);
  // _stui();
  for (int i = 0; i < n; ++i) {
    for (int j = 0; j < n; ++j) {
      m[i][j] = (seed * (i + j)) & mod;
    }
  }
  return m;
}

// better cache performance by transposing the second matrix
int **mm_mul_int(int n, int *const *a, int *const *b) {
  //_clui();
  int **m = mm_init_int(n);
  int **c = mm_init_int(n);
  // _stui();
  for (int i = 0; i < n; ++i) { // transpose
    for (int j = 0; j < n; ++j) {
      c[i][j] = b[j][i];
    }
  }
  for (int i = 0; i < n; ++i) {
    int *p = a[i], *q = m[i];
    for (int j = 0; j < n; ++j) {
      int t = 0, *r = c[j];
      for (int k = 0; k < n; ++k) {
        t = (t + p[k] * r[k]) & mod;
      }
      q[j] = t;
    }
  }
  mm_destroy_int(n, c);
  return m;
}

int calc_int(int n) {
  n = n / 2 * 2;
  int **a = mm_gen_int(n, 13);
  int **b = mm_gen_int(n, 17);
  int **m = mm_mul_int(n, a, b);
  int result = m[n / 2][n / 2];
  mm_destroy_int(n, a);
  mm_destroy_int(n, b);
  mm_destroy_int(n, m);
  return result;
}

long long matmul_int() {
  int n = 1000;

  int results = calc_int(n);

  return (long long) results;
}

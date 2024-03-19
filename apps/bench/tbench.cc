#include "runtime.h"
#include "thread.h"
#include "sync.h"

#include <vector>
#include <chrono>
#include <iostream>
#include <algorithm>
#include <random>  
#include <ctime>
#include <cstdlib>
#include <immintrin.h>

namespace {

unsigned long long now() {
	struct timespec ts;
	timespec_get(&ts, TIME_UTC);
	return ts.tv_sec * 1e9 + ts.tv_nsec;
}


using us = std::chrono::duration<double, std::micro>;
constexpr int kMeasureRounds = 10000000;

void BenchSpawnJoin() {
  for (int i = 0; i < kMeasureRounds; ++i) {
    auto th = rt::Thread([](){;});
    th.Join();
  }
}

void BenchUncontendedMutex() {
  rt::Mutex m;
  volatile unsigned long foo = 0;

  for (int i = 0; i < kMeasureRounds; ++i) {
    rt::ScopedLock<rt::Mutex> l(&m);
    foo++;
  }
}

void BenchYield() {
  auto th = rt::Thread([](){
    for (int i = 0; i < kMeasureRounds / 2; ++i)
      rt::Yield();
  });

  for (int i = 0; i < kMeasureRounds / 2; ++i)
    rt::Yield();

  th.Join();
}

void BenchYield(int n) {
  std::vector<rt::Thread> threads_;
  for (int i = 0; i < n - 1; ++i) {
    threads_.emplace_back(
      rt::Thread([n, i](){
        for (int j = 0; j < kMeasureRounds / n; ++j) {
          rt::Yield();
        }
      })
    );
  }
  
  for (int j = 0; j < kMeasureRounds - kMeasureRounds / n * (n - 1); ++j)
    rt::Yield();

  for (int i = 0; i < n - 1; ++i) {
    threads_[i].Join();
  }
}

void BenchCondvarPingPong() {
  rt::Mutex m;
  rt::CondVar cv;
  bool dir = false; // shared and protected by @m.

  auto th = rt::Thread([&](){
    rt::ScopedLock<rt::Mutex> l(&m);
    for (int i = 0; i < kMeasureRounds / 2; ++i) {
      while (dir)
        cv.Wait(&m);
      dir = true;
      cv.Signal();
    }
  });

  rt::ScopedLock<rt::Mutex> l(&m);
  for (int i = 0; i < kMeasureRounds / 2; ++i) {
    while (!dir)
      cv.Wait(&m);
    dir = false;
    cv.Signal();
  }

  th.Join();
}

#define DATA_SIZE (1024 * 8)
#define N (DATA_SIZE/sizeof(unsigned) - 1)
unsigned *next[256];

void work_init(int num) {
  for (int th = 0; th < num; ++th) {
    next[th] = (unsigned*) malloc(N * sizeof(unsigned));
  
    int i; 
    int *ring = (int*) malloc(sizeof(int) * N);
    for (i = 0; i < N; ++i) {
      ring[i] = i;
    }  
    srand(th);
    shuffle(ring, ring + N, std::default_random_engine(time(NULL)));

    for (i = 0; i+1 < N; ++i) {
      next[th][ring[i]] = ring[i+1];
    }
    next[th][ring[N-1]] = ring[0];

    free(ring);
  }
}

unsigned work(int loop, int th) {
  unsigned *nx = next[th];
  unsigned sum = 0;
  // unsigned long long total = 0;
  for (int l = 0; l < loop; ++l) {
    rt::Yield();
    // barrier();
    // unsigned long long start = __rdtsc();
    barrier();
    unsigned i = l % N;
    for (unsigned l = 0; l < N; ++l) {
      i = nx[i];
      sum += i;
    }
    barrier();
    // unsigned long long end = __rdtsc();
    // total += end - start;
  }
  // printf("%llu\n", total / loop);
  free(nx);
  return sum;
}

// int work(int loop, int th) {
//   unsigned *array = (unsigned*) malloc(N * sizeof(unsigned));
//   unsigned sum = 0;
//   for (unsigned i = 0; i < N; ++i) {
//     array[i] = i*i;
//   }
  
//   unsigned long long total = 0;
//   for (int l = 0; l < loop; ++l) {
//     // unsigned long long start = now();
//     rt::Yield();
//     barrier();
//     unsigned v = (unsigned) (1LL * l * l * l);
//     for (unsigned i = 0; i < N; ++i) {
//       array[i] ^= v;
//       // array[i] += i;
//       sum += array[i]; 
//     }
//     barrier();
//   }
//   free(array);
//   return sum;
// }

// int work(int loop, int th) {
//   unsigned *array = (unsigned*) malloc(N * sizeof(unsigned));
//   unsigned sum = 0;
//   for (unsigned i = 0; i < N; ++i) {
//     array[i] = (i + 1) % N;
//   }
//   while (loop--) {
//     rt::Yield();
//     // printf("th: %d\n", th);
//     barrier();
//     for (unsigned i = 0; i < N; ++i) {
//       array[i] = array[array[i]];
//       sum += array[i];
//     }
//     barrier();
//   }
//   free(array);
//   // printf("sum: %u\n", sum);
//   return sum;
// }

unsigned BenchYield_work(int n) {
  work_init(n);
  
  unsigned sum = 0;
  std::vector<rt::Thread> threads_;
  for (int i = 0; i < n - 1; ++i) {
    threads_.emplace_back(
      rt::Thread([n, i, &sum](){
        sum += work(kMeasureRounds / n, i);
      })
    );
  }
  sum += work(kMeasureRounds - kMeasureRounds / n * (n - 1), n-1);

  for (int i = 0; i < n - 1; ++i) {
    threads_[i].Join();
  }
  return sum;
}

unsigned BenchMalloc() {
  unsigned sum = 0;
  for (int i = 0; i < kMeasureRounds; ++i) {
    unsigned* p = (unsigned*) malloc(sizeof(int) * 4);
    p[0] = ((unsigned long long)p) & 65535;
    sum += p[0];
    free(p);
  }
  return sum;
}

void PrintResult(std::string name, us time) {
  time /= kMeasureRounds;
  std::cout << "test '" << name << "' took "<< time.count() << " us."
            << std::endl;
}

void MainHandler(void *arg) {
  // auto start = std::chrono::steady_clock::now();
  // BenchSpawnJoin();
  // auto finish = std::chrono::steady_clock::now();
  // PrintResult("SpawnJoin",
	// std::chrono::duration_cast<us>(finish - start));

  // start = std::chrono::steady_clock::now();
  // BenchUncontendedMutex();
  // finish = std::chrono::steady_clock::now();
  // PrintResult("UncontendedMutex",
  //   std::chrono::duration_cast<us>(finish - start));

  auto start = std::chrono::steady_clock::now();
  BenchYield();
  auto finish = std::chrono::steady_clock::now();
  PrintResult("Yield",
  std::chrono::duration_cast<us>(finish - start));

  // auto start = std::chrono::steady_clock::now();
  // BenchYield(2);
  // auto finish = std::chrono::steady_clock::now();
  // PrintResult("Yield",
  // std::chrono::duration_cast<us>(finish - start));

  // int nth = *((int*)arg);
  // printf("nth: %d\n", nth);
  // auto start = std::chrono::steady_clock::now();
  // unsigned sum = BenchYield_work(nth);
  // auto finish = std::chrono::steady_clock::now();
  // PrintResult("BenchYield_work",
  // std::chrono::duration_cast<us>(finish - start));
  // printf("sum: %u\n", sum);
  
  // auto start = std::chrono::steady_clock::now();
  // unsigned sum = BenchMalloc();
  // auto finish = std::chrono::steady_clock::now();
  // PrintResult("BenchMalloc",
  // std::chrono::duration_cast<us>(finish - start));
  // printf("sum: %u\n", sum);
  
  // start = std::chrono::steady_clock::now();
  // BenchCondvarPingPong();
  // finish = std::chrono::steady_clock::now();
  // PrintResult("CondvarPingPong",
  //   std::chrono::duration_cast<us>(finish - start));
}

} // anonymous namespace

int main(int argc, char *argv[]) {
  int ret;

  if (argc < 2) {
    printf("arg must be config file\n");
    return -EINVAL;
  }
  int nth = atoi(argv[3]);
  ret = runtime_init(argv[1], MainHandler, &nth);
  if (ret) {
    printf("failed to start runtime\n");
    return ret;
  }
  return 0;
}

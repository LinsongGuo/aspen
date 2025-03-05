#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <new>
#include <x86intrin.h>

void* operator new(size_t sz) {
    void *res = malloc(sz);

    if (!res) {
        throw std::bad_alloc();
    }

    return res;
}

void* operator new(std::size_t size, std::align_val_t alignment) {
    void* ptr;
    if (posix_memalign(&ptr, static_cast<std::size_t>(alignment), size) != 0) {
        throw std::bad_alloc();
    }
    return ptr;
}

void* operator new[](size_t sz) {
    return ::operator new(sz);
}

void operator delete(void *p) {
    free(p);
}

void operator delete[](void *p) {
    ::operator delete(p);
}

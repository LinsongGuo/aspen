#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <new>
#include <x86intrin.h>

void* operator new(size_t sz) {
    // printf("new\n");
    void *res = malloc(sz);

    if (!res) {
        unsigned char uif = _testui();
        if (uif)
            _clui();
        throw std::bad_alloc();
    }

    return res;
}

void* operator new[](size_t sz) {
    return ::operator new(sz);
}

void operator delete(void *p) {
    // printf("free\n");
    free(p);
}

void operator delete[](void *p) {
    ::operator delete(p);
}

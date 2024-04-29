#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <new>
#include <x86intrin.h>

void* operator new(size_t sz) {
    // printf("new\n");
    void *res = malloc(sz);

    // unsigned char uif = _testui();
    // if (uif)
    //     _clui();    
    // printf("new: %p\n", res);
    // if (uif)
    //     _stui();

    if (!res) {
        throw std::bad_alloc();
    }

    return res;
}

void* operator new(std::size_t size, std::align_val_t alignment) {
    // Allocate memory with the requested alignment
    void* ptr;
    if (posix_memalign(&ptr, static_cast<std::size_t>(alignment), size) != 0) {
        throw std::bad_alloc();
    }
    // printf("new_align: %p\n", ptr);
    return ptr;
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

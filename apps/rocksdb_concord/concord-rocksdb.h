#include <c.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

extern void DoGet(rocksdb_t *db, rocksdb_readoptions_t *readoptions, char* key, int key_len);

extern void DoScan(rocksdb_t *db, rocksdb_readoptions_t *readoptions);

extern void DoRangeScan(rocksdb_t *db, rocksdb_readoptions_t *readoptions, char* key, int key_len);
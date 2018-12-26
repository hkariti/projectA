#include <stdio.h>
#include <unistd.h>

struct hint {
    unsigned long long fd;
    unsigned long long offset;
    unsigned long long count;
};

int main() {
    struct hint dummy_hint = {
    .fd = 123,
    .offset = 0,
    .count = 0
    };
    
    while (1) {
        write(1, &dummy_hint, sizeof(struct hint));
        dummy_hint.count++;
        sleep(1);
    }
}

#include <stdint.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdbool.h>

#define DEV "/dev/file_trace"
#define BUFFER_SIZE 100

typedef struct __attribute__((packed)) _log_t {
    uint32_t pid;
    uint32_t major, minor;
    uint64_t inode;
    int64_t offset;
    uint64_t count;
    uint8_t write;
} log_t;

int main() {
    int fd;
    ssize_t entries_read;
    log_t buffer[BUFFER_SIZE];

    fd = open(DEV, O_RDONLY);
    if (fd < 0) {
        printf("Error opening file\n");
        return -1;
    }

    while (1) {
        entries_read = read(fd, buffer, BUFFER_SIZE * sizeof(log_t));
        entries_read = entries_read/sizeof(log_t);
        if (entries_read < 0) {
            printf("Error reading from file\n");
            close(fd);
            return -1;
        }
        for (int i = 0; i < entries_read; i++) {
            printf("PID: %d major: %d minor: %d inode: %ld offset: %ld count: %ld write: %d\n", buffer[i].pid, buffer[i].major, buffer[i].minor, buffer[i].inode, buffer[i].offset, buffer[i].count, buffer[i].write);
        }
        sleep(1);
    }
    return 0;
}

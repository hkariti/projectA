#include <linux/types.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

#define DEV "post_cache"
#define BUFFER_SIZE 100

typedef struct _log_t {
    unsigned int pid;
    unsigned int major, minor;
    unsigned long inode;
    unsigned long offset;
    int id;

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
        entries_read = read(fd, buffer, BUFFER_SIZE);
        if (entries_read < 0) {
            printf("Error reading from file\n");
            close(fd);
            return -1;
        }
        for (int i = 0; i < entries_read; i++) {
            printf("kp: %d PID: %d major: %d minor: %d inode: %ld offset: %ld\n", buffer[i].id, buffer[i].pid, buffer[i].major, buffer[i].minor, buffer[i].inode, buffer[i].offset);
        }
        sleep(1);
    }
    return 0;
}

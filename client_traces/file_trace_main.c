#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/file.h>
#include <linux/fdtable.h>
#include <linux/kdev_t.h>
#include <linux/uaccess.h>

#include "trace_log.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Hagai");
MODULE_DESCRIPTION("Performs a file-based IO trace");
MODULE_VERSION("0.1");

#define MY_MODULE "file_trace"
#define MAX_SYMBOL_LEN 64
#define LOG_ENTRIES_BUFFER_SIZE 100

static char read_symbol[MAX_SYMBOL_LEN] = "vfs_read";
static char write_symbol[MAX_SYMBOL_LEN] = "vfs_write";
int target_major = 8;
int target_minor = 1;

module_param(target_major, int, S_IRUSR | S_IWUSR);
MODULE_PARM_DESC(target_major, "Major number of device to trace");
module_param(target_minor, int, S_IRUSR | S_IWUSR);
MODULE_PARM_DESC(target_minor, "Minor number of device to trace");

// Structure for our log entries
typedef struct _log_t {
    unsigned int pid;
    unsigned int major, minor;
    unsigned long inode;
    loff_t offset;
    size_t count;
    bool write;
} log_t;

static void log_write(unsigned int pid, unsigned int major, unsigned int minor, unsigned long inode, loff_t offset, size_t count, bool write) {
    log_t* log_entry = log_get_write_slot();

    *log_entry = (log_t){
        .pid = pid,
        .major = major,
        .minor = minor,
        .inode = inode,
        .offset = offset,
        .count = count,
        .write = write
    };
}

int match_device(int major, int minor) {
    return major == target_major && minor == target_minor;
}

// kprobe structure
static struct kprobe read_kp = {
    .symbol_name = read_symbol,
};
static struct kprobe write_kp = {
    .symbol_name = write_symbol,
};

static int handler_pre(struct kprobe *p, struct pt_regs *regs) {
    struct file* f = (struct file*)regs->di;
    //void *buf = regs->rsi;
    size_t count = regs->dx;
    loff_t* offset = (loff_t*)regs->cx;

    unsigned int pid = current->pid;
    struct super_block *sb;
    struct inode *f_inode;
    unsigned long inode_n;
    unsigned int major, minor;
    bool write;

    if (!log_clients_count()) return 0;

    if (p == &read_kp) {
        write = false;
    } else {
        write = true;
    }
    f_inode = f->f_inode;
    sb = f_inode->i_sb;
    inode_n = f_inode->i_ino;
    major = MAJOR(sb->s_dev);
    minor = MINOR(sb->s_dev);
    if (match_device(major, minor))
        log_write(pid, major, minor, inode_n, *offset, count, write);
    return 0;
}
static void handler_post(struct kprobe *p, struct pt_regs *regs, unsigned long flags) {
}
static int handler_fault(struct kprobe *p, struct pt_regs *regs, int trapnr) {
    return 0;
}

static int init_kprobe(struct kprobe *p) {
    p->pre_handler = handler_pre;
    p->post_handler = handler_post;
    p->fault_handler = handler_fault;
    return register_kprobe(p);
}

static int read_tp_init_module(void) {
    int ret;
    pr_info("file_trace: starting pre-cache file trace module");

    ret = log_init(sizeof(log_t), LOG_ENTRIES_BUFFER_SIZE, MY_MODULE);
    if (ret != 0) {
        pr_err("file_trace: error allocating log buffer");
        return -1;
    }

    ret = init_kprobe(&read_kp);
    if (ret < 0) {
        pr_err("file_trace: register_kprobe failed for read, returned %d\n", ret);
        log_destroy();
        return ret;
    }
    ret = init_kprobe(&write_kp);
    if (ret < 0) {
        pr_err("file_trace: register_kprobe failed for write, returned %d\n", ret);
        unregister_kprobe(&read_kp);
        log_destroy();
        return ret;
    }
    pr_info("file_trace: planted kprobes for read and write");
    pr_info("file_trace: init done\n");

    return 0;
}

static void read_tp_exit_module(void) {
    unregister_kprobe(&read_kp); 
    unregister_kprobe(&write_kp); 
    pr_info("file_trace: kprobes unregistered");
    log_destroy();
    pr_info("file_trace: trace log destroyed");
    pr_info("file_trace: module exiting\n");
}

module_init(read_tp_init_module);
module_exit(read_tp_exit_module);

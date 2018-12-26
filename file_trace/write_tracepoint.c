#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/file.h>
#include <linux/fdtable.h>
#include <linux/kdev_t.h>
#include <linux/uaccess.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Hagai");
MODULE_DESCRIPTION("dana");
MODULE_VERSION("0.1");

#define MY_MODULE "write_tracepoint"

#define MAX_SYMBOL_LEN 64
static char symbol[MAX_SYMBOL_LEN] = "sys_write";
module_param_string(symbol, symbol, sizeof(symbol), 0644);

#define LOG_ENTRIES_BUFFER_SIZE 100

// Structure for our log entries
typedef struct _log_t {
    unsigned int pid;
    unsigned int major, minor;
    unsigned long inode;
    loff_t offset;
    size_t count;
} log_t;

log_t* logs;
unsigned int log_read_head, log_write_head;
unsigned int overruns;
unsigned int logging_enabled;
static int log_entries_count(void) {
    int diff = log_write_head - log_read_head;
    if (diff < 0)
        diff += LOG_ENTRIES_BUFFER_SIZE;
    return diff;
}

// TODO: add locking so it works on multiple cpus
static void log_increment_read_head(int count) {
    log_read_head = (log_read_head + count) % LOG_ENTRIES_BUFFER_SIZE;
}

static void log_increment_write_head(void) {
    log_write_head = (log_write_head + 1) % LOG_ENTRIES_BUFFER_SIZE;
    // Check if we rolled over the read head, i.e. overrun
    if (log_write_head == log_read_head) {
        log_increment_read_head(1);
        overruns++;
        printk(KERN_WARNING "log overrun. total overruns is %d", overruns);
    }
}

static void log_write(unsigned int pid, unsigned int major, unsigned int minor, unsigned long inode, loff_t offset, size_t count) {
    log_t* log_entry = logs + log_write_head;

    *log_entry = (log_t){
        .pid = pid,
        .major = major,
        .minor = minor,
        .inode = inode,
        .offset = offset,
        .count = count
    };
    log_increment_write_head();
}
// Structures for our control device
static int dev_major;

static int logger_open(struct inode * in, struct file * fd) {
    logging_enabled++;
    printk(KERN_INFO "added reader, number is now %d", logging_enabled);
    return 0;
}

static char* _logger_read(char *buffer, size_t count) {
    copy_to_user(buffer, logs + log_read_head, count * sizeof(log_t));
    log_increment_read_head(count);
    return buffer + count*sizeof(log_t);
}

static ssize_t logger_read(struct file *fd, char *buffer, size_t count, loff_t *offset) {
    size_t first_read_size, second_read_size;
    size_t log_count = log_entries_count();
    if (count > log_count)
        count = log_count;
    first_read_size = count;
    second_read_size = 0;
    if (log_read_head + count > LOG_ENTRIES_BUFFER_SIZE) {
        first_read_size = LOG_ENTRIES_BUFFER_SIZE - log_read_head;
        second_read_size = count - first_read_size;
    }
    buffer = _logger_read(buffer, first_read_size);
    buffer = _logger_read(buffer, second_read_size);
    return count;
}

static int logger_release(struct inode *in, struct file *fd) {
    logging_enabled--;
    printk(KERN_INFO "removed reader, number is now %d", logging_enabled);
    return 0;
}

static struct file_operations my_fops = {
    .read = logger_read,
    .open = logger_open,
    .release = logger_release
};

// kprobe structure
static struct kprobe kp = {
    .symbol_name = symbol,
};

static int handler_pre(struct kprobe *p, struct pt_regs *regs) {
    int fd = regs->di;
    //void *buf = regs->rsi;
    size_t count = regs->dx;

    unsigned int pid = current->pid;
    struct file* f;
    struct super_block *sb;
    struct inode *f_inode;
    unsigned long inode_n;
    unsigned int major, minor;
    loff_t offset;

    if (!logging_enabled) return 0;

    rcu_read_lock();
    f = fcheck(fd);
    if (f) {
        offset = f->f_pos;
        f_inode = f->f_inode;
        sb = f_inode->i_sb;
        inode_n = f_inode->i_ino;
        major = MAJOR(sb->s_dev);
        minor = MINOR(sb->s_dev);
        if (major > 0)
            log_write(pid, major, minor, inode_n, offset, count);
    } else {
        printk(KERN_ERR "error when checking fd %d", fd);
    }
    rcu_read_unlock();
    return 0;
}
static void handler_post(struct kprobe *p, struct pt_regs *regs, unsigned long flags) {
}
static int handler_fault(struct kprobe *p, struct pt_regs *regs, int trapnr) {
    return 0;
}

static int write_tp_init_module(void) {
    int ret;
    printk(KERN_INFO "Starting tracepoint module");

    logs = kmalloc(LOG_ENTRIES_BUFFER_SIZE * sizeof(log_t), GFP_KERNEL);
    if (!logs) {
        printk(KERN_ERR "Error allocating log buffer");
        return -1;
    }
    log_read_head = log_write_head = overruns = 0;

    logging_enabled = 0;
    kp.pre_handler = handler_pre;
    kp.post_handler = handler_post;
    kp.fault_handler = handler_fault;
    ret = register_kprobe(&kp);
    if (ret < 0) {
        printk(KERN_ERR "register_kprobe failed, returned %d\n", ret);
        kfree(logs);
        return ret;
    }
    printk(KERN_INFO "Planted kprobe at %p\n", kp.addr);

    dev_major = register_chrdev(0, MY_MODULE, &my_fops);

    return 0;
}

static void write_tp_exit_module(void) {
    unregister_kprobe(&kp); 
    unregister_chrdev(dev_major, MY_MODULE);
    printk(KERN_INFO "kprobe at %p unregistered\n", kp.addr);
}

module_init(write_tp_init_module);
module_exit(write_tp_exit_module);

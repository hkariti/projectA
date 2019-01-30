#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/file.h>
#include <linux/fs.h>
#include <linux/fdtable.h>
#include <linux/kdev_t.h>
#include <linux/uaccess.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Tome");
MODULE_DESCRIPTION("post page cache file trace");
MODULE_VERSION("0.1");

#define MY_MODULE "post_cache_read_tracepoint"

#define MAX_SYMBOL_LEN 64
static char symbol[MAX_SYMBOL_LEN] = "ext4_readpages";
static char symbol2[MAX_SYMBOL_LEN] = "ext4_readpage";
module_param_string(symbol, symbol, sizeof(symbol), 0644);

#define LOG_ENTRIES_BUFFER_SIZE 100

// Structure for our log entries
typedef struct _log_t {
    unsigned int pid;
    unsigned int major, minor;
    unsigned long inode;
    unsigned long offset;
    int id;
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

static void log_write(unsigned int pid, unsigned int major, unsigned int minor, unsigned long inode, unsigned long offset, int id) {
    log_t* log_entry = logs + log_write_head;

    *log_entry = (log_t){
        .pid = pid,
        .major = major,
        .minor = minor,
        .inode = inode,
	.offset = offset,
	.id = id
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
static struct kprobe kp2 = {
    .symbol_name = symbol2,
};


static int handler_pre(struct kprobe *p, struct pt_regs *regs) {
    struct file* file = (struct file*)regs->di;
    struct page *page = (struct page*)regs->si;
    //struct page *page = (struct page*)regs->dx;

    unsigned int pid = current->pid;
    struct super_block *sb;
    struct inode *f_inode;
    unsigned long inode_n;
    unsigned int major, minor;
    loff_t offset;
    int id = 1;
    if (p == &kp2) {
	    id = 2;
    }

    if (!logging_enabled) return 0;

    rcu_read_lock();
    f_inode = file->f_inode;
    sb = f_inode->i_sb;
    inode_n = f_inode->i_ino;
    offset = file->f_pos;
    major = MAJOR(sb->s_dev);
    minor = MINOR(sb->s_dev);
    if (major > 0)
       log_write(pid, major, minor, inode_n, offset, id);
    rcu_read_unlock();
    return 0;
}
static void handler_post(struct kprobe *p, struct pt_regs *regs, unsigned long flags) {
}
static int handler_fault(struct kprobe *p, struct pt_regs *regs, int trapnr) {
    return 0;
}

static int read_tp_init_module(void) {
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
    kp2.pre_handler = handler_pre;
    kp2.post_handler = handler_post;
    kp2.fault_handler = handler_fault;
    ret = register_kprobe(&kp);
    if (ret < 0) {
        printk(KERN_ERR "register_kprobe failed, returned %d\n", ret);
        kfree(logs);
        return ret;
    }
    printk(KERN_INFO "Planted kprobe at %p\n", kp.addr);
    ret = register_kprobe(&kp2);
    if (ret < 0) {
        printk(KERN_ERR "register_kprobe2 failed, returned %d\n", ret);
        kfree(logs);
        return ret;
    }
    printk(KERN_INFO "Planted kprobe2 at %p\n", kp2.addr);

    dev_major = register_chrdev(0, MY_MODULE, &my_fops);

    return 0;
}

static void read_tp_exit_module(void) {
    unregister_kprobe(&kp); 
    unregister_kprobe(&kp2); 
    unregister_chrdev(dev_major, MY_MODULE);
    kfree(logs);
    printk(KERN_INFO "kprobe at %p unregistered\n", kp.addr);
    printk(KERN_INFO "kprobe2 at %p unregistered\n", kp2.addr);
}

module_init(read_tp_init_module);
module_exit(read_tp_exit_module);

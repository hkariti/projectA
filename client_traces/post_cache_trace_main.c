#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/file.h>
#include <linux/uio.h>
#include <linux/fs.h>
#include <linux/fdtable.h>
#include <linux/kdev_t.h>
#include <linux/uaccess.h>

#include "trace_log.h"
#include "post_cache_trace.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Tome");
MODULE_DESCRIPTION("post page cache file trace");
MODULE_VERSION("0.1");

#define MY_MODULE "post_cache_trace"
#define MAX_SYMBOL_LEN 64
#define LOG_ENTRIES_BUFFER_SIZE 100

static char read_symbol[MAX_SYMBOL_LEN] = "ext4_mpage_readpages";
static char write_symbol[MAX_SYMBOL_LEN] = "ext4_io_submit";
static char dio_symbol[MAX_SYMBOL_LEN] = "ext4_direct_IO";
int target_major = 8;
int target_minor = 1;

module_param(target_major, int, S_IRUSR | S_IWUSR);
MODULE_PARM_DESC(target_major, "Major number of device to trace");
module_param(target_minor, int, S_IRUSR | S_IWUSR);
MODULE_PARM_DESC(target_minor, "Minor number of device to trace");

// Structure for our log entries
typedef struct __attribute__((packed)) _log_t {
    uint32_t pid;
    uint32_t major, minor;
    uint64_t inode;
    int64_t offset;
    uint64_t size;
    uint8_t is_readahead;
    uint8_t write;
} log_t;

static void log_write(unsigned int pid, unsigned int major, unsigned int minor, unsigned long inode, unsigned long offset, unsigned long size, bool is_readahead, bool write) {
    log_t log_entry = {
        .pid = pid,
        .major = major,
        .minor = minor,
        .inode = inode,
        .offset = offset,
        .size = size,
        .is_readahead = is_readahead,
        .write = write
    };
    log_write_entry(&log_entry);
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
static struct kprobe dio_kp = {
    .symbol_name = dio_symbol,
};

static int read_handler_pre(struct kprobe *p, struct pt_regs *regs) {
    struct address_space* mapping = (struct address_space*)regs->di;
    struct list_head* pages = (struct list_head*)regs->si;
    struct page* page = (struct page*)regs->dx;
    unsigned nr_pages = regs->cx;
    bool is_readahead = regs->r8;

    unsigned int pid = current->pid;
    struct super_block *sb;
    struct inode *f_inode;
    unsigned long inode_n;
    unsigned int major, minor;
    size_t size;
    loff_t offset;

    if (!log_clients_count()) return 0;

    f_inode = mapping->host;
    if (pages)
        page = list_entry(pages->prev, struct page, lru);
    sb = f_inode->i_sb;
    inode_n = f_inode->i_ino;
    offset = page->index << PAGE_SHIFT;
    size = nr_pages << PAGE_SHIFT;
    major = MAJOR(sb->s_dev);
    minor = MINOR(sb->s_dev);
    if (match_device(major, minor))
       log_write(pid, major, minor, inode_n, offset, size, is_readahead, false);
    return 0;
}

static int write_handler_pre(struct kprobe *p, struct pt_regs *regs) {
	struct ext4_io_submit *io = (struct ext4_io_submit*)regs->di;

	struct bio *bio = io->io_bio;
    unsigned int pid = current->pid;
    struct super_block *sb;
    struct inode *f_inode;
    unsigned long inode_n;
    unsigned int major, minor;
    loff_t offset;
    long size;

	if (!bio || !log_clients_count()) return 0;

	f_inode = io->io_end->inode;
	//offset = io->io_end->offset;
	offset = io->io_bio->bi_io_vec[0].bv_page->index << PAGE_SHIFT;
	size = io->io_bio->bi_iter.bi_size;
    inode_n = f_inode->i_ino;
    sb = f_inode->i_sb;
    major = MAJOR(sb->s_dev);
    minor = MINOR(sb->s_dev);
    if (match_device(major, minor))
       log_write(pid, major, minor, inode_n, offset, size, false, true);
    return 0;
}

static int dio_handler_pre(struct kprobe *p, struct pt_regs *regs) {
	struct kiocb* iocb = (struct kiocb*)regs->di;
    struct iov_iter* iter = (struct iov_iter*)regs->si;

    unsigned int pid = current->pid;
    struct file *file = iocb->ki_filp;
	struct inode *f_inode = file->f_mapping->host;
	size_t size = iov_iter_count(iter);
	loff_t offset = iocb->ki_pos;
    bool write = iov_iter_rw(iter);

    struct super_block *sb;
    unsigned long inode_n;
    unsigned int major, minor;

	if (!log_clients_count()) return 0;

    inode_n = f_inode->i_ino;
    sb = f_inode->i_sb;
    major = MAJOR(sb->s_dev);
    minor = MINOR(sb->s_dev);
    if (match_device(major, minor))
       log_write(pid, major, minor, inode_n, offset, size, false, write);
    return 0;
}

static void handler_post(struct kprobe *p, struct pt_regs *regs, unsigned long flags) {
}
static int handler_fault(struct kprobe *p, struct pt_regs *regs, int trapnr) {
    return 0;
}

static int init_post_cache_module(void) {
    int ret;
    pr_info("post_cache_trace: Starting up");

    ret = log_init(sizeof(log_t), LOG_ENTRIES_BUFFER_SIZE, "post_cache_trace");
    if (ret) {
        pr_err("post_cache_trace: Error allocating log buffer\n");
        return -1;
    }

    read_kp.pre_handler = read_handler_pre;
    read_kp.post_handler = handler_post;
    read_kp.fault_handler = handler_fault;
    write_kp.pre_handler = write_handler_pre;
    write_kp.post_handler = handler_post;
    write_kp.fault_handler = handler_fault;
    dio_kp.pre_handler = dio_handler_pre;
    dio_kp.post_handler = handler_post;
    dio_kp.fault_handler = handler_fault;
    ret = register_kprobe(&read_kp);
    if (ret < 0) {
        pr_err("post_cache_trace: register_kprobe for read failed, returned %d\n", ret);
        log_destroy();
        return ret;
    }
    ret = register_kprobe(&write_kp);
    if (ret < 0) {
        pr_err("post_cache_trace: register_kprobe for write failed, returned %d\n", ret);
        unregister_kprobe(&read_kp);
        log_destroy();
        return ret;
    }
    ret = register_kprobe(&dio_kp);
    if (ret < 0) {
        pr_err("post_cache_trace: register_kprobe for dio failed, returned %d\n", ret);
        unregister_kprobe(&read_kp);
        unregister_kprobe(&write_kp);
        log_destroy();
        return ret;
    }
    pr_info("post_cache_trace: kprobes planted");
    
    pr_info("post_cache_trace: init done\n");
    return 0;
}

static void exit_post_cache_module(void) {
    pr_info("post_cache_trace: shutting down");
    unregister_kprobe(&read_kp); 
    unregister_kprobe(&write_kp); 
    unregister_kprobe(&dio_kp); 
    pr_info("post_cache_trace: removed kprobes");
    log_destroy();
    pr_info("post_cache_trace: destroyed log buffer");
    pr_info("post_cache_trace: exit\n");
}

module_init(init_post_cache_module);
module_exit(exit_post_cache_module);

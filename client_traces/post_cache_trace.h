#ifndef POST_CACHE_TRACE_H
#define POST_CACHE_TRACE_H
// This is copied from fs/ext4/ext4.h
#include <linux/writeback.h>
typedef struct ext4_io_end {
    struct list_head	list;		/* per-file finished IO list */
    void                *handle;	/* handle reserved for extent
                                     * conversion */
    struct inode		*inode;		/* file being written to */
    struct bio		    *bio;		/* Linked list of completed
                                     * bios covering the extent */
    unsigned int		flag;		/* unwritten or not */
    atomic_t		    count;		/* reference counter */
    loff_t			    offset;		/* offset in the file */
    ssize_t			    size;		/* size of the extent */
} ext4_io_end_t;

struct ext4_io_submit {
	struct writeback_control    *io_wbc;
	struct bio		            *io_bio;
	ext4_io_end_t		        *io_end;
	sector_t		            io_next_block;
};
#endif

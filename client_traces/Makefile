EXTRA_CFLAGS += -D_GNU_SOURCE
obj-m += file_trace.o post_cache_trace.o
file_trace-objs := file_trace_main.o trace_log.o
post_cache_trace-objs := post_cache_trace_main.o trace_log.o

all:
	make -C /usr/src/linux-headers-$(shell uname -r) SUBDIRS=$(PWD) modules

clean:
	make -C /usr/src/linux-headers-$(shell uname -r) SUBDIRS=$(PWD) clean

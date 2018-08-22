from bcc import BPF
import ctypes

# Declare data format
class WriteEvt(ctypes.Structure):
    _fields_ = [
        ("fd",   ctypes.c_ulonglong),
        ("count",   ctypes.c_ulonglong),
    ]

# Hello BPF Program
bpf_text = """ 
#include <bcc/proto.h>

// Define output
struct write_evt {
    u64 fd;
    u64 count;
};
BPF_PERF_OUTPUT(write_evt);

// define probe
TRACEPOINT_PROBE(syscalls, sys_enter_write)
{
    struct write_evt evt = {
	.fd = args->fd,
	.count = args->count,
    };
    u32 current_pid = bpf_get_current_pid_tgid();
    if (current_pid == 10277)
        write_evt.perf_submit(args, &evt, sizeof(evt));
    return 0;
};
"""

# 2. Build and Inject program
b = BPF(text=bpf_text)
# Declare event printer
def print_event(cpu, data, size):
    event = ctypes.cast(data, ctypes.POINTER(WriteEvt)).contents
    print("Writing to fd %d size %d" % (
        event.fd,
        event.count,
    ))

# Replace the event loop
b["write_evt"].open_perf_buffer(print_event)
while True:
    b.kprobe_poll()

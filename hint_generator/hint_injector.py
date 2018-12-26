#!/usr/bin/python
from __future__ import print_function
from __future__ import division
import sys
import socket
import json
import struct
from collections import namedtuple

class BlockTraceSource:
    # Data format for block trace
    _unpack_format = "QQQ?"
    _record_length = struct.calcsize(_unpack_format)
    RecordFormat = namedtuple('BlockTraceRecord', ['fd', 'offset', 'count', 'write'])

    def __init__(self, devpath):
        """
        devpath - path to /dev file that outputs the trace events
        """
        self._trace_file = open(devpath, 'rb')
    def read_record(self):
        data = self._trace_file.read(self._record_length)
        unpacked_data = struct.unpack(self._unpack_format, data)
        record = self.RecordFormat(*unpacked_data)
        return record._asdict()

class HintsGenerator:
    DEFAULT_PORT = 1337

    def __init__(self, target_host, target_port=DEFAULT_PORT, insights_source=None):
        self._socket = socket.create_connection((target_host, target_port))
        self._insights_source = insights_source

    def _get_hint(self, io_request):
        if not self._insights_source:
            return 0, None
        # TODO: Implement logic here

    def generate_by_block_trace(self, block_trace_record):
        hint_type, hint_data = self._get_hint(block_trace_record)
        block_trace_record['hint_type'] = hint_type
        block_trace_record['hint_data'] = hint_data
        serialized = json.dumps(block_trace_record) + "\n"
        self._socket.send(serialized)

def do_block_trace(path, block_trace_db=None, hints_generator=None):
    block_trace = BlockTraceSource(path)
    while True:
        record = block_trace.read_record()
        if block_trace_db:
            block_trace_db.add(record)
        if hints_generator:
            hints_generator.generate_by_block_trace(record)


if __name__ == '__main__':
    hints_generator = HintsGenerator('localhost')
    do_block_trace(sys.argv[1], hints_generator=hints_generator)

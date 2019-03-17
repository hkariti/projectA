import asyncio
import struct
from collections import namedtuple
import logging

NODATA_SLEEP_TIME = 1

class TraceSource:
    """
    Base class for trace sources. It describes a trace that's read as a binary log of entries.
    
    To use it, subclass it and define the following:
        * type - a string type name for this trace, to be used for differentiating different traces
        * _unpack_format - the binary format of the entry (see struct.unpack)
        * RecordFormat - a namedtuple that gives a name for each part of the entry
    """
    def __init__(self, devpath):
        """
        Open a trace log file

        devpath - path to /dev file that outputs the trace events
        """
        self.devpath = devpath
        self._trace_file = open(devpath, 'rb')
        self._record_length = struct.calcsize(self._unpack_format)
        self._logger = logging.getLogger(self.type)

    def read_record(self):
        """
        Read one record from the log. If no entry is available, return None.
        """
        data = self._trace_file.read(self._record_length)
        self._logger.debug(f'Read {len(data)} bytes')
        if not data:
            return None
        unpacked_data = struct.unpack(self._unpack_format, data)
        record = self.RecordFormat(*unpacked_data)
        record_dict = record._asdict()
        record_dict['type'] = self.type
        return record_dict

    async def async_read_into(self, queue):
        """
        Continually (async) read from the log and put the results into the given queue.
        If an error occurs, print it and continue reading.
        
        This is an asyncio coroutine. queue should be an asyncio queue. 
        """
        loop = asyncio.get_event_loop()
        while True:
            try:
                self._logger.debug("Reading from log device")
                record = await loop.run_in_executor(None, self.read_record)
                if record:
                    self._logger.debug("Read log record", record)
                    await queue.put(record)
                else:
                    self._logger.debug(f"Read nothing, sleeping for {NODATA_SLEEP_TIME}")
                    await asyncio.sleep(NODATA_SLEEP_TIME)
            except asyncio.CancelledError:
                logger.info(f'cancelling')
                raise
            except Exception as e:
                logger.exception('error while reading record')

class FileTraceSource(TraceSource):
    """
    pre-cache (syscall level) file trace
    """
    type = "file"
    _unpack_format = "=IIIQqQ?"
    RecordFormat = namedtuple('FileTraceRecord', ['pid', 'major', 'minor', 'inode', 'offset', 'size', 'is_write'])

class PostCacheTraceSource(TraceSource):
    """
    post-cache file trace
    """
    type = "post_cache"
    _unpack_format = "=IIIQqQ??"
    RecordFormat = namedtuple('FileTraceRecord', ['pid', 'major', 'minor', 'inode', 'offset', 'size', 'is_readahead', 'is_write'])

class BlockTraceSource(TraceSource):
    """
    Block trace. Note that offset and size are in _blocks_ and not bytes.
    """
    type = "block"
    _unpack_format = "=I?qQ"
    RecordFormat = namedtuple('BlockTraceRecord', ['pid', 'is_write', 'offset', 'size'])

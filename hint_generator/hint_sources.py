import asyncio
import struct
from collections import namedtuple
import logging
import signal

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
        self.nodata_sleep_time = NODATA_SLEEP_TIME
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
                    await asyncio.sleep(self.nodata_sleep_time)
            except asyncio.CancelledError:
                self._logger.info(f'cancelling')
                raise
            except Exception as e:
                self._logger.exception('error while reading record')

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

class BlockTraceSource:
    """
    Block trace. See self.async_read_record for format.

    This is implemented differently, because we don't control the scsi client module. Instead we wrap blktrace.
    """
    type = "block"

    def __init__(self, devpath):
        self._shell_command = f'exec blktrace -a issue -o - -d {devpath} | blkparse -i - -f "%p,%S,%N,%d\n"'
        self._logger = logging.getLogger(self.type)
        self._blktrace = None
        # our read_record is blocking, no need to sleep
        self.nodata_sleep_time = 0

    async def cleanup_blktrace(self):
        self._logger.debug("Cleaning previous pipelines")
        pkill = await asyncio.create_subprocess_exec("pkill","blktrace")
        await pkill.wait()

    async def start_blktrace(self):
        """
        Start the blktrace|blkparse command pipe if it's not started already
        """
        if not self._blktrace:
            await self.cleanup_blktrace()
            self._logger.debug("Starting blktrace pipeline")
            self._blktrace = await asyncio.create_subprocess_shell(self._shell_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE)
        return self._blktrace

    async def stop_blktrace(self):
        """
        Stop the blktrace command pipe.

        This currently doesn't really work on a live pipe, as blktrace ignores our signals.
        """
        self._logger.debug("Stopping blktrace")
        if not self._blktrace:
            return

        try:
            self._blktrace.terminate()
        except ProcessLookupError:
            pass
        await self._blktrace.wait()
        output_err = await self._blktrace.stderr.read()
        self._logger.debug(f"blktrace pipe stopped. stderr: {output_err}")
        self._blktrace = None

    async def async_read_record(self):
        """
        Read a single record. Expects the start_blktrace() to have been called already.

        Record format is:
            - pid
            - offset (sectors)
            - size (bytes)
            - is_write (bool)

        This is an asyncio coroutine
        """
        line = await self._blktrace.stdout.readline()
        if not line:
            await self.stop_blktrace()
            raise ValueError("unexpected EOF")
        self._logger.debug(f"read line: {line}")
        pid, offset, size, op = line.strip().split(b",")
        pid = int(pid)
        offset = int(offset)
        size = int(size)
        is_write = self._is_write(op.decode())
        if is_write is None:
            return None

        record = dict(pid=pid, offset=offset, size=size, is_write=is_write, type=self.type)

        return record

    async def async_read_into(self, queue):
        """
        Continually (async) read from the log and put the results into the given queue.
        If an error occurs, print it and continue reading.
        
        This is an asyncio coroutine. queue should be an asyncio queue. 
        """
        await self.start_blktrace()
        while True:
            try:
                self._logger.debug("Reading from blkparse")
                record = await self.async_read_record()
                if record:
                    self._logger.debug("Read log record", record)
                    await queue.put(record)
                else:
                    self._logger.debug("Ignored record with N op")
            except asyncio.CancelledError:
                self._logger.info(f'cancelling')
                await self.stop_blktrace()
                raise
            except Exception as e:
                self._logger.exception('error while reading record')
                await asyncio.sleep(1)
                await self.start_blktrace()

    def _is_write(self, op):
        if op[0] == 'R':
            return False
        elif op[0] in ['W', 'D']:
            return True
        # neither read nor write, ignore it
        return None


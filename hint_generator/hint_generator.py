import json
import asyncio
import logging

logger = logging.getLogger('hints_generator')

class HintGenerator:
    def __init__(self):
        self._pid_to_tier = dict()

    async def handle_trace_record(self, record):
        """
        Digest a trace record and optionally return a hint based on it.
        
        Record that correspond to a block write always return a hint and have a 'match' flag set.
        This is because the code on the other side holds write requests until a hint arrives.
        """
        logger.debug(f"Processing record: {record}");
        hint = self._handle_trace_record(record)

        if record['type'] == 'block' and record['is_write']:
            if hint is None:
                logger.debug("Generating empty hint for block write")
                hint = self._empty_hint(record)
            hint['match'] = True
        return hint

    def _handle_trace_record(self, record):
        """
        Actual code that handles a trace record. You can do anything here.
        """
        pid = record['pid']
        if record['type'] == 'block':
            if not pid in self._pid_to_tier:
                return
            hint = dict(offset=record['offset'], size=record['size'], hint_type=1, hint_data=self._pid_to_tier[pid]) # type is a made-up number
            return hint

        # non-block records have the inode attribute
        inode = record['inode']
        if pid in self._pid_to_tier:
            return
        if inode == 13: # ssdfile
            self._pid_to_tier[pid] = 1
        elif inode == 14: #hddfile
            self._pid_to_tier[pid] = 2

    def _empty_hint(self, block_trace_record):
        hint_type = 0
        hint_data = None
        offset = block_trace_record['offset']
        size = block_trace_record['size']
        hint = dict(offset=offset, size=size, hint_type=0)

        return hint

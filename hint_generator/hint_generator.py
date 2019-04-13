import json
import asyncio
import logging

logger = logging.getLogger('hints_generator')

class HintGenerator:
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
        return None

    def _empty_hint(self, block_trace_record):
        hint_type = 0
        hint_data = None
        offset = block_trace_record['offset']
        size = block_trace_record['size']
        hint = dict(offset=offset, size=size, hint_type=0)

        return hint

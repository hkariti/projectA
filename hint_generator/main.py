#!/usr/bin/python
import sys
import asyncio
import logging
import argparse
import signal
import functools

from hint_generator import HintGenerator
from hint_client import HintClient, stdout_hint_consumer
from hint_sources import FileTraceSource, PostCacheTraceSource, BlockTraceSource

DEFAULT_PORT = 1337
DEFAULT_HOST = 'localhost'
HINT_CLIENTS = dict(remote=HintClient, stdout=stdout_hint_consumer)

logger = logging.getLogger('main') 

def shutdown(loop):
    logger.info('received stop signal, cancelling tasks...')
    for task in asyncio.Task.all_tasks():
        task.cancel()
    logger.info('bye, exiting in a minute...')

async def consume_trace(trace_queue, handle_trace_record, handle_hint):
    """
    Continuously does the following:
        - Read from the given asyncio queue
        - Feed the trace record to handle_trace_record, returning an optional hint
        - If there's a hint, feed it to  handle_hint.

        handle_trace_record and handle_hint should be asyncio coroutines.
    """
    logger.info('Consuming from trace queue')
    while True:
        try:
            trace_record = await trace_queue.get()
            hint = await handle_trace_record(trace_record)
            if hint:
                logger.debug("Writing hint", hint)
                await handle_hint(hint)
            else:
                logger.debug("No hint returned")
            trace_queue.task_done()
        except asyncio.CancelledError:
            logger.info('Stopping reading from queue')
            raise
        except Exception as e:
            logger.exception('Got error, skipping')
            trace_queue.task_done()

async def main(options):
    logging.basicConfig(level=logging.DEBUG)
    logger.info('Initializing')
    logger.debug('Creating trace sources')
    file_trace = FileTraceSource('/dev/file_trace')
    post_cache_trace = PostCacheTraceSource('/dev/post_cache_trace')
    block_trace = BlockTraceSource('/dev/sdc')
    logger.debug('Creating queue')
    trace_queue = asyncio.Queue(maxsize=1000)
    logger.debug('Creating generator')
    generator = HintGenerator()
    logger.debug('Creating client')
    if options.hint_client == 'stdout':
        client = stdout_hint_consumer
    else:
        client = HintClient(options.host, options.port).send_hint

    tasks = []
    for t in file_trace, post_cache_trace, block_trace:
        task = asyncio.ensure_future(t.async_read_into(trace_queue))
        tasks.append(task)
    logger.info('Started all sources')

    tasks.append(asyncio.ensure_future(consume_trace(trace_queue, generator.handle_trace_record, client)))
    logger.info('Started consumer')

    await asyncio.gather(*tasks)

def parse_args():
    parser = argparse.ArgumentParser(description='Process IO activity trace and genereate hints')
    parser.add_argument('--hint-client', type=str, default='remote', help=f'Hint client type', choices=['remote', 'stdout'])
    parser.add_argument('--host', type=str, default=DEFAULT_HOST, help=f'Remote host to send hints to (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'Remote port to send hints to (default: {DEFAULT_PORT})')

    return parser.parse_args()

if __name__ == '__main__':
    options = parse_args()
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGHUP, functools.partial(shutdown, loop))
    loop.add_signal_handler(signal.SIGTERM, functools.partial(shutdown, loop))
    try:
        loop.run_until_complete(main(options))
        loop.close()
    except asyncio.CancelledError:
        logger.info("Exiting")
    except Exception as e:
        logger.exception("Error")

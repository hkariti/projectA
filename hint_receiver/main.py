#!/usr/bin/python
import asyncio
import sys
import logging
import argparse

from hint_handler import HintHandler
from hint_receiver import TCPHintReceiver

DEFAULT_PORT = 1337
DEFAULT_LISTEN_HOST = '0.0.0.0'

logger = logging.getLogger('main')

async def consume_hints(hint_queue, handle_hint):
    logger.info("Consuming from hint queue")
    while True:
        try:
            hint = await hint_queue.get()
            logger.debug("Received hint", hint)
            await handle_hint(hint)
            hint_queue.task_done()
        except asyncio.CancelledError:
            logger.info('cancelled')
            raise
        except Exception as e:
            logger.exception('Error handling hint, skipping')
            hint_queue.task_done()

async def main():
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Initializing")
    logger.debug("Creating queue")
    queue = asyncio.Queue()
    logger.debug("Creating receiver")
    receiver = TCPHintReceiver(queue, DEFAULT_LISTEN_HOST, DEFAULT_PORT)
    logger.debug("Creating handler")
    handler = HintHandler()

    logger.debug('Starting up receiver')
    await receiver.start()

    await consume_hints(queue, handler.handle_hint)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
    #if len(sys.argv) > 1:
    #    btier_hints_file_name = sys.argv[1]
    #print("Starting server on {}".format((hostname, port)))
    #SocketServer.TCPServer.allow_reuse_address = True
    #server = SocketServer.TCPServer((hostname, port), RequestHandler)
    #server.btier_device = btier_device
    #server.serve_forever()

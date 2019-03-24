import asyncio
import json
import logging


class TCPHintReceiver:
    """
    Receives hints using TCP
    """
    def __init__(self, queue, host, port):
        self.host = host
        self.port = port
        self.queue = queue
        self._logger = logging.getLogger('receiver')

    async def start(self):
        """
        Start listening on the given host and port.

        This is an asyncio coroutine
        """
        self._server = await asyncio.start_server(self._serve_client, host=self.host, port=self.port)
        self._logger.info("Listening on {}:{}".format(self.host, self.port))

    async def stop(self):
        """
        Stop the server.

        This is an asayncio coroutine
        """
        self._logger.info("Stopping")
        self._server.close()

        await self._server.wait_closed()

    async def _serve_client(self, reader, writer):
        """
        Handles a connected client. Meant to be used by asyncio.start_server().

        Expects each message to be a json-encoded line.
        """
        addr = writer.get_extra_info('peername')
        self._logger.info("Got connection from {}".format(addr))
        try:
            while True:
                message = await reader.readline()
                if not message:
                    break
                message = message.decode().strip()
                try:
                    parsed_message = json.loads(message)
                    await self.queue.put(parsed_message)
                except ValueError as e:
                    self._logger.info("Bad message, ignoring")
                    self._logger.debug("Message:", message, "Caused error:", e)
        finally:
            writer.close()
            self._logger.info("Connection to {} closed".format(addr))

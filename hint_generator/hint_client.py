import asyncio
import socket
import logging
import json

class HintClient:
    def __init__(self, target_host, target_port):
        self._logger = logging.getLogger('client')
        self._logger.info(f"Connecting to {target_host}:{target_port}")
        self._socket = socket.create_connection((target_host, target_port))
        self._logger.info("Connected")

    async def send_hint(self, hint):
        self._logger.debug("Sending hint")
        serialized = json.dumps(hint) + "\n"
        self._socket.send(serialized.encode())

async def stdout_hint_consumer(hint):
    print(f'Got hint: {hint}')

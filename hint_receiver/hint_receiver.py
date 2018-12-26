#!/usr/bin/python
from __future__ import print_function
from __future__ import division
import fcntl
import sys
import SocketServer
import struct
import json

TIER_HINTINJECT = 0xFE0B
PLACEMENT_DONTCARE = -1

port = 1337
hostname = '0.0.0.0'
btier_device_name = '/dev/tiercontrol'

def push_to_tier_manager(hint_entry):
    pass

def get_target_tier(hint_entry):
    return PLACEMENT_DONTCARE

def pack_hint_entry(hint_entry, placement_decision):
    pack_format = 'QQi'
    pack_fields = (hint_entry['offset'],
                   hint_entry['count'],
                   placement_decision)
    packed_hint = struct.pack(pack_format, *pack_fields)
    return packed_hint


class RequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        while True:
            line = self.rfile.readline().strip()
            if not line:
                print("Client {} disconnected".format(self.client_address))
                break
            hint_entry = json.loads(line)
            push_to_tier_manager(hint_entry)
            placement_decision = get_target_tier(hint_entry)
            print("Got hint:", hint_entry, "placement decision:", placement_decision)
            packed_hint = pack_hint_entry(hint_entry, placement_decision)
            fcntl.ioctl(self.server.btier_device, TIER_HINTINJECT, packed_hint)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        btier_hints_file_name = sys.argv[1]
    print("Starting server on {}".format((hostname, port)))
    btier_device = open(btier_device_name, 'wb', 0)
    SocketServer.TCPServer.allow_reuse_address = True
    server = SocketServer.TCPServer((hostname, port), RequestHandler)
    server.btier_device = btier_device
    server.serve_forever()

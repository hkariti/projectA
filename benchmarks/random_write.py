#!/usr/bin/python
import sys
import random
import os

DEFAULT_SIZE = 1000
BLOCK_SIZE = 512

file_name = None
block_count = None
try:
    file_name = sys.argv[1]
    block_count = int(sys.argv[2])
except:
    print(f"Usage: {sys.argv[0]} FILE_NAME BLOCK_COUNT")
    print(f"Write BLOCK_COUNT blocks (size={BLOCK_SIZE}) at random offsets to FILE_NAME")
    sys.exit(1)

print(f"Opening {file_name}")
stat_file = os.stat(file_name)
src_size = stat_file.st_size / BLOCK_SIZE
if not src_size:
    print(f"{file_name}: couldn't figure out size. Using default value of {DEFAULT_SIZE} blocks")
    src_size = DEFAULT_SIZE
src_file = open(file_name, 'ab')

for i in range(block_count):
    block_nr = random.randint(0, src_size)
    block_content = bytearray(BLOCK_SIZE)
    src_file.seek(block_nr * BLOCK_SIZE)
    src_file.write(block_content)

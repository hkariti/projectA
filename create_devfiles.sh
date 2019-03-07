#!/bin/bash

for i in file_trace post_cache_trace block_trace; do
    major=`cat /proc/devices | grep $i | awk '{print $1}'`
    if [ -z "$major" ]; then
        echo "Couldn't find major for $i. is it loaded?"
        continue;
    fi
    echo Creating device file for $i in /dev major $major
    mknod /dev/$i c $major 0
done

#!/bin/bash
set -e

REPOSITORY_ROOT=$(cd $(dirname "$0"); git rev-parse --show-toplevel)
device=$1
btier_optimal_io_size=$2
if [ -z "$device" ] || [ -z "$btier_optimal_io_size" ]; then
    echo Usage: $0 ISCSI_DEVICE BTIER_OPTIMAL_IO_SIZE
    exit 1
fi

device_basename=`basename $device`
max_sectors_kb=$((btier_optimal_io_size / 1024))

if [ -z "$max_sectors_kb" ] || [ "$max_sectors_kb" = 0 ]; then
    echo Bad io size: $btier_optimal_io_size. Should be int over 1024.
    exit 1
fi

# use ls -l /dev/sdb to get the target major and minor number (8, 16 in our case)
ls_output=`ls -l $device`
major=`echo "$ls_output" | awk '{print $5}' | sed -s 's/,//'`
minor=`echo "$ls_output" | awk '{print $6}'`

echo "*** Target device has major: $major minor: $minor"
echo '*** Loading trace modules'
cd $REPOSITORY_ROOT/client_traces
sudo insmod file_trace.ko target_major=$major target_minor=$minor
sudo insmod post_cache_trace.ko target_major=$major target_minor=$minor

# create device files for traces
echo '*** Creating device files for traces'
sudo bash $REPOSITORY_ROOT/setup_scripts/create_devfiles.sh

# set the max_sectors_kb according to optimal_io_size in btier (divided by 1024). was 1024 in our case
echo "*** Setting max request size to $max_sectors_kb KB"
echo $max_sectors_kb | sudo tee /sys/block/$device_basename/queue/max_sectors_kb

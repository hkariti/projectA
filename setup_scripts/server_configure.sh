#!/bin/bash
set -e

ISCSI_TARGET_NAME=$HOSTNAME

# create the scsi config
echo '*** Configuring iSCSI target'
sudo tgtadm --lld iscsi -o new --mode target --tid 1  --targetname $ISCSI_TARGET_NAME
sudo tgtadm --lld iscsi -o new --mode logicalunit --tid 1 --lun 1 --backing-store /dev/sdtiera --bsoflags=direct
sudo tgtadm --lld iscsi -o bind --mode target --tid 1 -I ALL

echo '*** Loading btier module'
sudo modprobe btier

# create a 1G ram block device as cache on /dev/ram0
echo '*** Setting up /dev/ram0'
sudo modprobe brd rd_nr=1 rd_size=$((1 * 1024 * 1024)) max_part=0

# create the tiered storage device (top to bottom tier)
echo '*** Configuring tiered storage device'
sudo btier_setup  -f /dev/ram0:/dev/sda:/dev/sdb2 -c

# get the optimal io size
io_size=`cat /sys/block/sdtiera/queue/optimal_io_size`

echo Done. Optimal IO size for btier device: $io_size

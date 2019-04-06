#!/bin/bash

sudo tgtadm --lld iscsi -o new --mode target --tid 1  --targetname `hostname`
sudo tgtadm --lld iscsi -o new --mode logicalunit --tid 1 --lun 1 --backing-store /dev/sdtiera --bsoflags=direct
sudo tgtadm --lld iscsi -o bind --mode target --tid 1 -I ALL

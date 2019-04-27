#!/bin/bash
set -e

REPOSITORY_ROOT=$(cd $(dirname "$0"); git rev-parse --show-toplevel)

echo '*** Installing base packages'
sudo apt-get update
sudo apt-get install -y git open-iscsi build-essential blktrace

# build and start the file trace modules
echo '*** Building trace modules'
cd $REPOSITORY_ROOT/client_traces
make

echo Done

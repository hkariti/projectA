#!/bin/bash
set -e

TARGET_REPO_DIR=$HOME

if [ ! -d "$TARGET_REPO_DIR" ]; then
    echo Creating target for repo clones at $TARGET_REPO_DIR
    mkdir -p $TARGET_REPO_DIR
fi

echo '*** Installing basic packages'
apt-get update
apt-get install -y build-essential tgt libsystemd-dev

echo Building btier
if [ ! -d "$TARGET_REPO_DIR/btier" ]; then 
    git clone http://github.com/hkariti/btier $TARGET_REPO_DIR/btier
fi
cd $TARGET_REPO_DIR/btier
make
sudo make install

# Install our custom tgt daemon
echo '*** Building the tgt iSCSI daemon'
sudo service tgt stop
if [ ! -d "$TARGET_REPO_DIR"/tgt ]; then
    git clone http://github.com/hkariti/tgt $TARGET_REPO_DIR/tgt
fi
cd $TARGET_REPO_DIR/tgt
make SD_NOTIFY=1 # Tell it to support systemd.
sudo make install
sudo service tgt start

echo Done

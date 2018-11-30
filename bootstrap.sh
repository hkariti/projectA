#!/bin/bash

# Set up tmux with vi mode
cat > ~/.tmux.conf <<EOF
# bind vi key-mapping
set -g status-keys vi
# vi-style controls for copy mode
setw -g mode-keys vi
EOF

# Install bcc (https://github.com/iovisor/bcc)
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys D4284CDD
echo "deb https://repo.iovisor.org/apt/bionic bionic main" | sudo tee /etc/apt/sources.list.d/iovisor.list
sudo apt-get update
sudo apt-get install -y bcc-tools libbcc-examples linux-headers-$(uname -r) python-pip

## System Structure
The system contains the following components:
- IO Traces on the client. These are used for discovering application access patterns. Traces are from 3 different places:
    - file-access IO
    - file-access after the IO cache
    - block IO
- Hint Generator. This digests the io traces and generates hints based on them for the storage server
- Hint Receiver. Runs on the storage server, receives the hints from the generator and controls and server's storage tiers accordingly.

The current system is built on top of a patched [btier](https://github.com/hkariti/btier) to implement a multi-tiered storage box. We also patched the iSCSI [tgtd](https://github.com/hkariti/tgt) to disable WRITE_SAME support.

## Installation
On the server (running ubuntu xenial. doesn't run on bionic):
- clone this repo
- run `setup_scripts/server_install_pkgs.sh`
- run `setup_scripts/server_configure.sh` and note the optimal io size
- start the hint receiver `sudo python3 hint_receiver/main.py`

On the client (running ubuntu bionic):
- clone this repo
- run `setup_scripts/client_install_pkgs.sh`
- setup iscsi:

```
sudo iscsiadm -m discovery -t st -p $STORAGE_SERVER_IP
sudo iscsiadm -m node --login
```

- run `setup_scripts/client_configure_traces.sh SCSI_DEVICE OPTIMAL_IO_SIZE`
- start the hint generator: `sudo python3 hint_generator/main.py $STORAGE_SERVER_IP`

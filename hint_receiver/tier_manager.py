#!/usr/bin/python
from collections import namedtuple
from contextlib import contextmanager

BlockInfo = namedtuple('BlockInfo', ['device', 'offset', 'atime', 'readcount', 'writecount'])

class TierManager:
    """
    Manage btier's block location manually. Uses the btier sysfs inteface to get block info and manually migrate a block.

    Examples:
    manager = TierManager('/dev/sdtiera')
    block1_info = manager.get_block_info(1)
    print('Block 1 has been read {} times'.format(block1_info.readcount))
    manager.migrate_block(1, 2)
    print('Block 1 is being migrated to tier number 2')
    """
    def __init__(self, device_name):
        self.device_name = device_name

    def migrate(self, blocknr, dest_tier):
        """
        Migrate blocknr to tier number dest_tier. Will re-enable auto migration afterwards.
        Note that the migration process is async, and may fail silently. Currently failure is only reported in dmesg
        """
        path = self._get_sysfs_path('migrate_block')
        with self.pause_auto_migration(), open(path, 'w') as migrate_block:
                migrate_block.write("{}/{}\n".format(blocknr, dest_tier))

    def get_block_info(self, blocknr):
        """
        Get btier's statistics about a block.
        Return type is BlockInfo, which is a namedtuple of the fields from btier
        """
        path = self._get_sysfs_path('show_blockinfo')
        with open(path, 'w+') as show_blockinfo:
            show_blockinfo.write("{}\n".format(blocknr))
            block_info = show_blockinfo.read()
        return BlockInfo(*block_info.split(','))

    @contextmanager
    def pause_auto_migration(self):
        """
        A context manager that can be used to pause the auto migration of blocks while your code runs and re-enable it afterwards
        """
        path = self._get_sysfs_path('migration_enabled')
        with open(path, 'w') as migration_enabled:
            migration_enabled.write("0\n")
            yield
            migration_enabled.write("1\n")

    def _get_sysfs_path(self, entry):
        return "/sys/block/{}/tier/{}".format(self.device_name, entry)

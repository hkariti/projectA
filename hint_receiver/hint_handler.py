import asyncio
import fcntl
import struct
import logging

from tier_manager import TierManager

TIER_HINTINJECT = 0xFE0B
PLACEMENT_DONTCARE = -1

class HintHandler:
    """
    Manage btier using hints.

    This performs the following for each received hint:
        * If the hint is marked with 'match', then assume it's a write request that will wait in btier
          for a placement decision. Generate this decision and inject it to btier (see inject_to_btier)
        * Optionally migrate blocks based on this hint (see trigger_block_migration)

    Format of the hint should be a dictionary with the following keys:
        * offset - block offset into the device of the corresponding io request
        * size - size of the reqest, in blocks
        * hint_type: int, specifying the hint type (you can choose anything here). Zero means a null hint.
        * hint_data: data for the hint. Can be missing if hint_type==0. Can be anything.
        * match: bool. Should be True if the hint is for a pending write request.
    """
    def __init__(self, btier_control_device='/dev/tiercontrol', btier_data_device='/dev/sdtiera'):
        """
        Init the handler, controlling the tiered device in btier_data_device using btier_control_device
        """
        self.btier_control_device = btier_control_device
        self.btier_data_device = btier_data_device
        self._btier_control = open(btier_control_device, 'wb', 0)
        self._tier_manager = TierManager(btier_data_device)
        self._logger = logging.getLogger('hint_handler')

    async def handle_hint(self, hint):
        """
        Receive a hint to be handled. The actual work is done in inject_to_btier() and trigger_block_migration()

        This is an asyncio coroutine
        """
        self._logger.debug("Handling hint", hint)
        if hint.get('match'):
            self._logger.debug("Hint should be injected")
            self.inject_to_btier(hint)
        self.trigger_block_migration(hint)

    def inject_to_btier(self, hint):
        """
        For a hint that is to be injected, decide on a target tier for the request it represents,
        then inject it into btier using TIER_HINTINJECT ioctl
        """
        target_tier = self._get_target_tier(hint)
        packed_hint = self._pack_hint_entry(hint, target_tier)
        self._logger.debug("Injecting hint: {} with target tier: {}".format(hint, target_tier))
        fcntl.ioctl(self._btier_control, TIER_HINTINJECT, packed_hint)

    def trigger_block_migration(self, hint):
        """
        Optionally triggers block migrations based on the given hint
        """
        self._logger.debug("Trigerring block migration for hint", hint)

    def _get_target_tier(self, hint):
        return PLACEMENT_DONTCARE

    def _pack_hint_entry(self, hint_entry, placement_decision):
        pack_format = 'qQi'
        pack_fields = (hint_entry['offset'],
                       hint_entry['size'],
                       placement_decision)
        packed_hint = struct.pack(pack_format, *pack_fields)
        return packed_hint

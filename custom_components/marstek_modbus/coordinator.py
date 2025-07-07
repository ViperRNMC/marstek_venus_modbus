"""
Coordinator for managing data updates from Marstek Venus Modbus devices.
This coordinator handles connection setup and periodic data refresh scheduling.
"""

from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .helpers.modbus_client import MarstekModbusClient
from .const import SCAN_INTERVAL

# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)

class MarstekCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        # Store Home Assistant instance and connection details from config entry
        self.hass = hass
        self.host = entry.data["host"]
        self.port = entry.data["port"]
        self.interval = entry.data.get("scan_interval", SCAN_INTERVAL)

        # Initialize and connect the Modbus client to the device
        self.client = MarstekModbusClient(self.host, self.port)
        self.client.connect()

        # Initialize the DataUpdateCoordinator with update interval and logging
        super().__init__(
            hass,
            _LOGGER,
            name="Marstek Venus Modbus Coordinator",
            update_interval=timedelta(seconds=self.interval),
        )

    async def _async_update_data(self):
        # This method is called periodically to refresh data.
        # Actual register reading is performed individually by each sensor entity.
        return True
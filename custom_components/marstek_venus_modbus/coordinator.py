from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .helpers.modbus_client import MarstekModbusClient
from .const import SCAN_INTERVAL

import logging
_LOGGER = logging.getLogger(__name__)

class MarstekCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.host = entry.data["host"]
        self.port = entry.data["port"]
        self.client = MarstekModbusClient(self.host, self.port)
        self.client.connect()

        super().__init__(
            hass,
            _LOGGER,
            name="Marstek Venus Modbus Coordinator",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )

    async def _async_update_data(self):
        # Sensordata wordt gelezen in de sensor.py per entiteit
        return True
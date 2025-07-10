"""
Coordinator for managing data updates from Marstek Venus Modbus devices.
This coordinator handles connection setup and periodic data refresh scheduling.
"""

from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .helpers.modbus_client import MarstekModbusClient
from .const import SCAN_INTERVAL, SENSOR_DEFINITIONS

# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)

SCAN_INTERVALS_MAP = {
    "scan_interval.power": 10,
    "scan_interval.electrical": 30,
    "scan_interval.energy": 60,
    "scan_interval.soc": 30,
    "scan_interval.state": 5,
}

class MarstekCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        def _get_scan_interval(value):
            if isinstance(value, int):
                return value
            return SCAN_INTERVALS_MAP.get(value, 10)

        # Store Home Assistant instance and connection details from config entry
        self.hass = hass
        self.host = entry.data["host"]
        self.port = entry.data["port"]
        self.message_wait_ms = entry.data.get("message_wait_milliseconds", 35)
        self.timeout = entry.data.get("timeout", 5)

        self._poll_list = [
            {
                "key": s["key"],
                "register": s["register"],
                "count": s.get("count", 1),
                "data_type": s["data_type"],
                "scale": s.get("scale", 1),
                "scan_interval": s.get("scan_interval", 10),
                "background_read": s.get("background_read", False),
            }
            for s in SENSOR_DEFINITIONS
        ]

        # Determine the fastest interval among **all** sensors, ensuring all are ints
        self.interval = min(_get_scan_interval(item["scan_interval"]) for item in self._poll_list)

        # Initialize and connect the Modbus client to the device
        self.client = MarstekModbusClient(
            self.host,
            self.port,
            message_wait_ms=self.message_wait_ms,
            timeout=self.timeout,
        )
        self.client.connect()

        # Initialize data dictionary to store background sensor values
        self.data = {}

        # Initialize the DataUpdateCoordinator with update interval and logging
        super().__init__(
            hass,
            _LOGGER,
            name="Marstek Venus Modbus Coordinator",
            update_interval=timedelta(seconds=self.interval),
        )

    async def _async_update_data(self):
        """Refresh data by reading all background registers."""
        data: dict[str, float | int | None] = {}

        for sensor in self._poll_list:
            try:
                value = self.client.read_register(
                    sensor["register"],
                    sensor["data_type"],
                    count=sensor["count"],
                )
                if sensor["scale"] != 1:
                    value = round(value * sensor["scale"], 3)
                data[sensor["key"]] = value
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error(
                    "Error reading register %s (%s): %s",
                    sensor["register"],
                    sensor["key"],
                    err,
                )
                data[sensor["key"]] = None

        # Store collected data in coordinator for use by sensors
        self.data = data
        return data
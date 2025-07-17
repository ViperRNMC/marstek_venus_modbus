"""
Coordinator for managing data updates from Marstek Venus Modbus devices.
Handles connection setup and periodic data refresh scheduling.
"""

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .helpers.modbus_client import MarstekModbusClient
from .const import (
    SCAN_INTERVAL,
    DEFAULT_MESSAGE_WAIT_MS,
    SENSOR_DEFINITIONS,
    SWITCH_DEFINITIONS,
    BUTTON_DEFINITIONS,
    NUMBER_DEFINITIONS,
    SELECT_DEFINITIONS,
)

_LOGGER = logging.getLogger(__name__)


class MarstekCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates from Marstek Venus Modbus devices.

    Handles connection setup, sensor polling intervals, and data refreshes.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize coordinator with hass instance and config entry.

        Args:
            hass (HomeAssistant): Home Assistant instance.
            entry (ConfigEntry): Configuration entry with device info.
        """
        def _get_scan_interval(val):
            """Convert scan interval value to seconds as int."""
            if isinstance(val, int):
                return val
            if isinstance(val, str):
                if val.startswith("scan_interval."):
                    val = val.split(".", 1)[1]
                return SCAN_INTERVAL.get(val, 10)
            return 10

        # Store Home Assistant instance and connection details
        self.hass = hass
        self.host = entry.data["host"]
        self.port = entry.data["port"]
        self.message_wait_ms = entry.data.get(
            "message_wait_milliseconds", DEFAULT_MESSAGE_WAIT_MS
        )
        self.timeout = entry.data.get("timeout", 5)

        # Prepare sensor polling list with metadata (intervals, register, etc.)
        self._poll_list = []
        all_definitions = (
            SENSOR_DEFINITIONS
            + SELECT_DEFINITIONS
            + SWITCH_DEFINITIONS
            + BUTTON_DEFINITIONS
            + NUMBER_DEFINITIONS
        )

        for entity in all_definitions:
            if "register" not in entity or "data_type" not in entity or "key" not in entity:
                continue  # Skip incomplete definitions

            scan_interval = _get_scan_interval(entity.get("scan_interval", 10))
            self._poll_list.append(
                {
                    "key": entity["key"],
                    "register": entity["register"],
                    "count": entity.get("count", 1),
                    "data_type": entity["data_type"],
                    "scale": entity.get("scale", 1),
                    "scan_interval": scan_interval,
                    "background_read": entity.get("background_read", False),
                }
            )

        # Determine update interval as the shortest scan interval among sensors
        self.interval = min((sensor["scan_interval"] for sensor in self._poll_list), default=10)

        # Initialize Modbus client (connection not made yet)
        self.client = MarstekModbusClient(
            self.host,
            self.port,
            message_wait_ms=self.message_wait_ms,
            timeout=self.timeout,
        )

        # Initialize empty data store for sensor values
        self.data = {}

        # Call parent constructor with update_interval=None to prevent
        # automatic updates until connection is established
        super().__init__(
            hass,
            _LOGGER,
            name="Coordinator",
            update_interval=None,
        )

    async def async_init(self):
        """Async initialize coordinator and connect to Modbus device.

        Waits for successful connection before starting periodic updates.

        Returns:
            bool: True if connection succeeded, False otherwise.
        """
        # Attempt to connect to Modbus device asynchronously
        connected = await self.client.async_connect()
        if connected:

            # Set update interval now that connection is confirmed
            self.update_interval = timedelta(seconds=self.interval)

            # Trigger first data refresh and start periodic update loop
            await self.async_refresh()
        else:
            _LOGGER.error(
                "Failed to connect to Modbus device at %s:%d", self.host, self.port
            )
        return connected

    async def _async_update_data(self):
        """Fetch new data from device for background sensors.

        Only polls sensors with a valid register and count > 0,
        respecting each sensor's scan interval.

        Returns:
            dict: Sensor key to value mapping.
        """
        data = {}

        # Update internal data store with latest readings
        self.data = data
        return data
    
    async def async_update_sensor(
        self, key: str, value, *, register=None, scale=None, unit=None, entity_type="unknown"
    ):
        """Update a single entity value in the coordinator and log it."""
        self.data[key] = value

        if register is not None:
            _LOGGER.debug(
                "Updated %s '%s': register=%d (0x%04X), value=%s, scale=%s, unit=%s",
                entity_type,
                key,
                register,
                register,
                value,
                scale if scale is not None else 1,
                unit if unit is not None else "N/A",
            )
        else:
            _LOGGER.debug(
                "Updated %s '%s' with value %s",
                entity_type,
                key,
                value,
            )
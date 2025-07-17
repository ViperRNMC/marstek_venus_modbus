"""
Coordinator for managing data updates from Marstek Venus Modbus devices.
Handles connection setup and periodic data refresh scheduling.
"""

from datetime import timedelta
from time import monotonic
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .helpers.modbus_client import MarstekModbusClient
from .const import SCAN_INTERVAL, SENSOR_DEFINITIONS, DEFAULT_MESSAGE_WAIT_MS

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
        for sensor in SENSOR_DEFINITIONS:
            scan_interval = _get_scan_interval(sensor.get("scan_interval", 10))
            self._poll_list.append(
                {
                    "key": sensor["key"],
                    "register": sensor["register"],
                    "count": sensor.get("count", 1),
                    "data_type": sensor["data_type"],
                    "scale": sensor.get("scale", 1),
                    "scan_interval": scan_interval,
                    "background_read": sensor.get("background_read", False),
                    # Set last read time in the past to allow immediate first read
                    "last_read": monotonic() - scan_interval,
                }
            )

        # Determine update interval as the shortest scan interval among sensors
        self.interval = min(sensor["scan_interval"] for sensor in self._poll_list)

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
            name="Marstek Venus Modbus Coordinator",
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
            _LOGGER.info("Connected to Modbus device at %s:%d", self.host, self.port)

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
        now = monotonic()

        for sensor in self._poll_list:
            # Skip sensors with no valid register or zero count (non-physical)
            if sensor["count"] <= 0 or sensor["register"] == 0:
                continue

            # Skip sensor if its scan interval has not yet elapsed
            if now - sensor["last_read"] < sensor["scan_interval"]:
                continue

            # Update last read timestamp to current time
            sensor["last_read"] = now

            try:
                # Read register value asynchronously from Modbus device, passing sensor_key
                value = await self.client.async_read_register(
                    register=sensor["register"],
                    data_type=sensor["data_type"],
                    count=sensor["count"],
                    sensor_key=sensor["key"],
                )

                # Apply scaling factor if specified
                if sensor["scale"] != 1:
                    value = round(value * sensor["scale"], 3)

                old_value = data.get(sensor["key"])
                if value != old_value:
                    _LOGGER.debug(
                        "Sensor '%s' updated: register=0x%04X old=%s new=%s",
                        sensor["key"],
                        sensor["register"],
                        old_value,
                        value,
                    )

                # Store the new sensor value
                data[sensor["key"]] = value

            except Exception as err:
                # Log and store None on read failure
                _LOGGER.error(
                    "Error reading register 0x%04X (%s): %s",
                    sensor["register"],
                    sensor["key"],
                    err,
                )
                data[sensor["key"]] = None

        # Update internal data store with latest readings
        self.data = data
        return data
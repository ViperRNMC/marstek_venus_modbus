"""
Coordinator for managing data updates from Marstek Venus Modbus devices.
This coordinator handles connection setup and periodic data refresh scheduling.
"""

from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .helpers.modbus_client import MarstekModbusClient
from .const import SCAN_INTERVAL, SENSOR_DEFINITIONS, DEFAULT_MESSAGE_WAIT_MS

# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)

class MarstekCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
       # Initialize the coordinator with Home Assistant instance and configuration entry.
        def _get_scan_interval(val):
            if isinstance(val, int):
                return val
            # val is dan bv. "power", "state", "energy", ...
            return SCAN_INTERVAL.get(val, 10)

        # Store Home Assistant instance and connection details from config entry
        self.hass = hass
        self.host = entry.data["host"]
        self.port = entry.data["port"]
        self.message_wait_ms = entry.data.get("message_wait_milliseconds", DEFAULT_MESSAGE_WAIT_MS)
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
        """Refresh data by reading all background registers.

        This method polls all sensors defined in _poll_list except virtual or
        dummy sensors (which have count <= 0 or register == 0).

        It reads each register from the Modbus device, applies scaling if defined,
        and collects the results into a dictionary keyed by sensor keys.

        Errors during reading are logged and stored as None in the data dictionary.

        Returns:
            dict[str, float|int|None]: Mapping of sensor keys to their current values.
        """
        data: dict[str, float | int | None] = {}

        for sensor in self._poll_list:
            # Skip sensors that do not correspond to real Modbus registers
            # Virtual sensors often have count 0 or register 0 as placeholders.
            if sensor["count"] <= 0 or sensor["register"] == 0:
                continue

            try:
                # Read raw register value(s) from the Modbus device using the client
                value = self.client.read_register(
                    sensor["register"],
                    sensor["data_type"],
                    count=sensor["count"],
                )

                # Apply scaling factor to raw value if specified
                if sensor["scale"] != 1:
                    value = round(value * sensor["scale"], 3)

                # Store the scaled value in the data dict using the sensor's key
                data[sensor["key"]] = value

            except Exception as err:  # pylint: disable=broad-except
                # Log any errors encountered during reading to help troubleshooting
                _LOGGER.error(
                    "Error reading register %s (%s): %s",
                    sensor["register"],
                    sensor["key"],
                    err,
                )
                # Store None to indicate failure to read this sensor's data
                data[sensor["key"]] = None

        # Save the collected sensor data in the coordinator's data attribute
        self.data = data

        # Return the collected data for any awaiting processes
        return data
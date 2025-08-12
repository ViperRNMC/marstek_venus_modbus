"""
Coordinator for managing data updates from Marstek Venus Modbus devices.
Handles connection setup and periodic data refresh scheduling.
"""

import datetime
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import entity_registry as er

from .const import (
    BUTTON_DEFINITIONS,
    DEFAULT_MESSAGE_WAIT_MS,
    NUMBER_DEFINITIONS,
    SCAN_INTERVAL,
    SELECT_DEFINITIONS,
    SENSOR_DEFINITIONS,
    SWITCH_DEFINITIONS,
)
from .helpers.modbus_client import MarstekModbusClient

_LOGGER = logging.getLogger(__name__)


class MarstekCoordinator(DataUpdateCoordinator):
    """
    Coordinator to manage data updates from Marstek Venus Modbus devices.

    Handles connection setup, sensor polling intervals, and data refreshes.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """
        Initialize coordinator with Home Assistant instance and config entry.

        Args:
            hass (HomeAssistant): Home Assistant instance.
            entry (ConfigEntry): Configuration entry with device info.
        """
        def _get_scan_interval(val):
            """
            Convert scan interval value to seconds as int.

            Args:
                val (int or str): The scan interval value or key.

            Returns:
                int: Scan interval in seconds.
            """
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

        # Iterate over all entity definitions to build polling list
        for entity in all_definitions:
            # Skip incomplete definitions missing required keys
            if "register" not in entity or "data_type" not in entity or "key" not in entity:
                continue

            # Determine scan interval for the sensor
            scan_interval = _get_scan_interval(entity.get("scan_interval", 10))

            # Append sensor metadata to polling list
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
        self.interval = min(
            (sensor["scan_interval"] for sensor in self._poll_list), default=10
        )

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
        """
        Asynchronously initialize coordinator and connect to Modbus device.

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
        data = {}
        """ 
        Asynchronously update data from Modbus registers.
        Reads values from Modbus registers based on the polling list.
        Returns:
            dict: Updated data dictionary with sensor values.
        """
        # Iterate over polling list to read values from Modbus registers
        if self.data is None:
            self.data = {}

        # Iterate over polling list to read values from Modbus registers
        self.data.update(data)
        return self.data

    async def async_update_value(
        self,
        key: str,
        value,
        *,
        register=None,
        scale=None,
        unit=None,
        entity_type="unknown",
    ):
        """
        Update a single entity value in the coordinator and log it.

        Args:
            key (str): Entity key.
            value: New value to set.
            register (int, optional): Register address.
            scale (optional): Scale factor.
            unit (optional): Unit of measurement.
            entity_type (str, optional): Type of entity.
        """
        # Update internal data dictionary
        self.data[key] = value

        # Log update with detailed info if register is provided
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
            # Log update without register info
            _LOGGER.debug(
                "Updated %s '%s' with value %s",
                entity_type,
                key,
                value,
            )

    async def async_write_value(
        self,
        *,
        register: int,
        value: int,
        data_type: str,
        key: str,
        scale=None,
        unit=None,
        entity_type="unknown",
    ):
        """
        Write a value to a Modbus register asynchronously.

        Args:
            register (int): Register address to write to.
            value (int): Value to write.
            data_type (str): Data type of the value.
            key (str): Entity key.
            scale (optional): Scale factor.
            unit (optional): Unit of measurement.
            entity_type (str, optional): Type of entity.

        Returns:
            bool: True if write succeeded, False otherwise.
        """
        try:
            # Perform asynchronous write to Modbus register
            await self.client.async_write_register(
                register=register,
                value=value,
            )
            # Log successful write
            _LOGGER.debug(
                "Wrote to %s '%s': register=%d (0x%04X), value=%s, scale=%s, unit=%s",
                entity_type,
                key,
                register,
                register,
                value,
                scale if scale is not None else 1,
                unit if unit is not None else "N/A",
            )
            return True
        except Exception as e:
            # Log failure to write value
            _LOGGER.error(
                "Failed to write value %s to register 0x%X: %s", value, register, e
            )
            return False
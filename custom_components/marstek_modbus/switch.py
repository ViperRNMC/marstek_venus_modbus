"""
Module for creating sensor entities for Marstek Venus battery devices.
The sensors retrieve data by reading Modbus registers.
"""

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import SWITCH_DEFINITIONS, DOMAIN
from .coordinator import MarstekCoordinator

# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
):
    """
    Setup function that is called when the integration is loaded.
    Creates a coordinator that manages data retrieval and tracking.
    Creates sensors based on the sensor configurations and registers them with Home Assistant.
    """
    # Create a coordinator that handles communication with the device
    coordinator = MarstekCoordinator(hass, entry)

    # Create a sensor object for each sensor definition
    sensors = [
        MarstekSwitch(coordinator, sensor_def)
        for sensor_def in SWITCH_DEFINITIONS
    ]

    # Add the sensors to Home Assistant so they become visible and usable
    async_add_entities(sensors)


class MarstekSwitch(SwitchEntity):
    """
    Representation of a single sensor for a Marstek Venus battery.
    This sensor reads the value from the Modbus register via the coordinator.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initializes the sensor with the coordinator and sensor definition.
        
        Parameters:
        - coordinator: the data coordinator that handles communication
        - definition: a dict with configuration (name, register address, scale, etc.)
        """
        self.coordinator = coordinator
        self.definition = definition

        # Set the name of the switch, e.g. "Battery 1 RS485 Control Mode"
        self._attr_name = f"{coordinator.config_entry.title} {definition['name']}"

        # Create a unique ID consisting of the config entry ID + sensor key
        self._attr_unique_id = f"marstek_{coordinator.config_entry.entry_id}_{definition['key']}"

        # Ensure the sensor is polled periodically to get current data
        self._attr_should_poll = True

        # Internal boolean state of the switch
        self._state = False

    def update(self):
        """
        Retrieves the latest sensor value by reading the Modbus register.
        Updates the boolean state based on the register value compared to command_on and command_off.
        """
        raw_value = self.coordinator.client.read_register(
            address=self.definition["address"],
            data_type=self.definition.get("type", "uint16"),
            count=self.definition.get("count", 1)
        )

        if raw_value is not None:

            command_on = self.definition.get("command_on")
            command_off = self.definition.get("command_off")

            if command_on is not None and raw_value == command_on:
                self._state = True
            elif command_off is not None and raw_value == command_off:
                self._state = False
            else:
                _LOGGER.warning(
                    f"Unknown register value {raw_value} for switch {self._attr_name}"
                )
        else:
            _LOGGER.warning(f"No register data received for switch {self._attr_name}")

    @property
    def is_on(self):
        """
        Returns True if the switch is on, False otherwise.
        """
        return self._state

    def turn_on(self, **kwargs):
        """
        Turns the switch on by writing the command_on value to the Modbus register.
        Updates internal state and schedules a state update in Home Assistant.
        """
        command_on = self.definition.get("command_on")
        if command_on is None:
            _LOGGER.warning(f"No command_on value defined for switch {self._attr_name}")
            return

        success = self.coordinator.client.write_register(self.definition["address"], command_on)
        if success:
            self._state = True
            self.schedule_update_ha_state()
        else:
            _LOGGER.warning(f"Failed to turn on switch {self._attr_name}")

    def turn_off(self, **kwargs):
        """
        Turns the switch off by writing the command_off value to the Modbus register.
        Updates internal state and schedules a state update in Home Assistant.
        """
        command_off = self.definition.get("command_off")
        if command_off is None:
            _LOGGER.warning(f"No command_off value defined for switch {self._attr_name}")
            return

        success = self.coordinator.client.write_register(self.definition["address"], command_off)
        if success:
            self._state = False
            self.schedule_update_ha_state()
        else:
            _LOGGER.warning(f"Failed to turn off switch {self._attr_name}")

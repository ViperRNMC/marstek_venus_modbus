"""
Module for creating switch entities for Marstek Venus battery devices.
Switches read and write Modbus registers asynchronously via the coordinator.
"""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, SWITCH_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


def get_entity_type(entity) -> str:
    """
    Determine the entity type based on its class inheritance.

    Args:
        entity: The entity instance.

    Returns:
        A lowercase string representing the entity type
        (e.g., 'switch', 'sensor', 'select').
    """
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Set up switch entities when the config entry is loaded.

    This function retrieves the coordinator from hass.data,
    creates switch entities based on SWITCH_DEFINITIONS,
    and registers them with Home Assistant.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry.
        async_add_entities: Callback to add entities.
    """
    # Retrieve coordinator instance from hass.data
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Await the first data refresh to populate coordinator data before entities use it
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Create switch entities for each definition
    for definition in SWITCH_DEFINITIONS:
        entities.append(MarstekSwitch(coordinator, definition))

    # Register all created switch entities with Home Assistant
    async_add_entities(entities)


class MarstekSwitch(SwitchEntity):
    """
    Representation of a Modbus switch entity for Marstek Venus.

    Switch state is read and controlled asynchronously via
    the coordinator communicating with the Modbus device.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the switch entity.

        Args:
            coordinator: The data update coordinator instance.
            definition: Dictionary containing switch configuration.
        """
        self.coordinator = coordinator
        self.definition = definition

        # Initialize attributes from the definition
        self._attr_name = definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_has_entity_name = True

        # Internal state tracking
        self._state = None
        self._key = definition["key"]
        self._register = definition["register"]

        # Disable entity by default if specified
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self):
        """Handle entity added to Home Assistant by fetching initial state."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if coordinator update succeeded and state is known."""
        return self.coordinator.last_update_success and (self._state is not None)

    @property
    def is_on(self) -> bool | None:
        """Return True if switch is on, False if off, None if unknown."""
        return self._state

    async def async_update(self):
        """
        Fetch the latest switch state from the coordinator's Modbus client.

        Reads the configured register asynchronously and updates internal state.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self._register
        count = self.definition.get("count", 1)

        try:
            # Read value from the Modbus register asynchronously
            value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self._key,
            )
        except Exception as e:
            _LOGGER.error("Error reading register 0x%X: %s", register, e)
            self._state = None
            return

        if value is not None:
            command_on = self.definition.get("command_on")
            command_off = self.definition.get("command_off")

            # Interpret the read value according to configured commands
            if command_on is not None and value == command_on:
                self._state = True
            elif command_off is not None and value == command_off:
                self._state = False
            else:
                _LOGGER.warning(
                    "Unknown register value %s for switch %s", value, self._attr_name
                )
                self._state = None
        else:
            self._state = None

        # Update the coordinator data with the new state
        await self.coordinator.async_update_value(
            self._key,
            self._state,
            register=register,
            scale=self.definition.get("scale"),
            unit=self.definition.get("unit"),
            entity_type=get_entity_type(self),
        )

    async def async_turn_on(self, **kwargs):
        """
        Turn the switch on by writing the 'command_on' value to the register.
        """
        command_on = self.definition.get("command_on")
        if command_on is None:
            _LOGGER.warning("No command_on value defined for switch %s", self._attr_name)
            return

        success = await self.coordinator.async_write_value(
            register=self._register,
            value=command_on,
            data_type=self.definition.get("data_type", "uint16"),
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=get_entity_type(self),
        )
        if success:
            self._state = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """
        Turn the switch off by writing the 'command_off' value to the register.
        """
        command_off = self.definition.get("command_off")
        if command_off is None:
            _LOGGER.warning("No command_off value defined for switch %s", self._attr_name)
            return

        success = await self.coordinator.async_write_value(
            register=self._register,
            value=command_off,
            data_type=self.definition.get("data_type", "uint16"),
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=get_entity_type(self),
        )
        if success:
            self._state = False
            self.async_write_ha_state()

    @property
    def device_info(self) -> dict:
        """
        Return device info for device registry grouping.

        This information groups entities under the same device.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }
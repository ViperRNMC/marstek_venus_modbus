"""
Module for creating switch entities for Marstek Venus battery devices.
Switches read and write Modbus registers asynchronously via the
coordinator.
"""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, SWITCH_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


def get_entity_type(entity) -> str:
    """Determine entity type based on its class inheritance."""
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

    This function retrieves the coordinator instance,
    creates switch entities based on definitions,
    and registers them with Home Assistant.
    """
    # Retrieve coordinator for this config entry
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Ensure coordinator has latest data before creating entities
    await coordinator.async_config_entry_first_refresh()

    # Create MarstekSwitch entities for all defined switches
    entities = [
        MarstekSwitch(coordinator, definition)
        for definition in SWITCH_DEFINITIONS
    ]

    # Register all created entities with Home Assistant
    async_add_entities(entities)


class MarstekSwitch(SwitchEntity):
    """
    Representation of a Modbus switch entity for Marstek Venus.

    Switch state is read and controlled asynchronously via
    the coordinator communicating with the Modbus device.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the switch entity with coordinator and configuration.

        Args:
            coordinator: Data update coordinator instance.
            definition: Dictionary with switch configuration.
        """
        self.coordinator = coordinator
        self.definition = definition

        # Set entity name and unique ID for Home Assistant
        self._attr_name = definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_has_entity_name = True

        # Internal state variables
        self._state = None
        self._key = definition["key"]
        self._register = definition["register"]

        # Set entity category (e.g., diagnostic) if defined
        if "category" in definition:
            try:
                self._attr_entity_category = EntityCategory(definition["category"])
            except ValueError:
                _LOGGER.warning(
                    "Unknown entity category %s for switch %s",
                    definition["category"],
                    self._attr_name,
                )

        # Set custom icon if provided
        if "icon" in definition:
            self._attr_icon = definition["icon"]

        # Disable entity by default if specified
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self):
        """
        Called when entity is added to Home Assistant.

        Fetch the initial state to ensure correct representation.
        """
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self.coordinator.last_update_success and self._state is not None

    @property
    def is_on(self) -> bool | None:
        """Return True if the switch is on, False if off, None if unknown."""
        return self._state

    async def async_update(self):
        """
        Update the switch state by reading the Modbus register asynchronously.

        Reads the configured register and interprets the value based on
        command_on and command_off definitions.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self._register
        count = self.definition.get("count", 1)

        try:
            # Read register value from Modbus client
            value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self._key,
            )
        except Exception as exc:
            _LOGGER.error("Error reading register 0x%X: %s", register, exc)
            self._state = None
            return

        # Interpret register value according to configured commands
        if value is not None:
            command_on = self.definition.get("command_on")
            command_off = self.definition.get("command_off")

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

        # Update the coordinator data cache with new state
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
        Turn the switch on by writing the 'command_on' value to the Modbus register.
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
        Turn the switch off by writing the 'command_off' value to the Modbus register.
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
        Return device info to group entities under the same device in HA.

        This metadata is used by Home Assistant's device registry.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }
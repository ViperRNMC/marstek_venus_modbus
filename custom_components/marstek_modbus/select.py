"""
This module defines a SelectEntity for setting and reading the user work mode
and force mode of a Marstek Venus battery via Modbus within Home Assistant.
"""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceEntryType

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import MarstekCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up select entities when the config entry is loaded.
    """
    coordinator: MarstekCoordinator = hass.data[DOMAIN][entry.entry_id]

    sel_defs = getattr(coordinator, "SELECT_DEFINITIONS", None)

    # Defensive Normalisierung: akzeptiere Liste (bevorzugt) oder Mapping
    try:
        if isinstance(sel_defs, dict):
            # Mapping {key: def} -> Liste mit gesetztem 'key'
            normalized: list[dict[str, Any]] = []
            for key, definition in sel_defs.items():
                d = dict(definition or {})
                d.setdefault("key", key)
                normalized.append(d)
            sel_defs = normalized
        elif isinstance(sel_defs, list):
            # Sicherstellen, dass 'key' vorhanden ist
            for d in sel_defs:
                if "key" not in d:
                    raise ValueError(f"Select definition ohne 'key': {d}")
        else:
            _LOGGER.error("SELECT_DEFINITIONS ist leer oder unbekannter Typ: %r", type(sel_defs))
            sel_defs = []
    except Exception as err:
        _LOGGER.exception("Fehler beim Normalisieren von SELECT_DEFINITIONS: %s", err)
        sel_defs = []

    entities: list[MarstekSelect] = []
    for definition in sel_defs:
        try:
            entities.append(MarstekSelect(coordinator, definition))
        except Exception as err:
            _LOGGER.exception("Fehler beim Erstellen einer Select-Entity aus %r: %s", definition, err)

    _LOGGER.debug(
        "Richte %d Select-Entities ein: %s",
        len(entities),
        [getattr(e, "_key", "?") for e in entities],
    )

    if entities:
        # update_before_add: sorgt für schnelleren ersten Status
        async_add_entities(entities, update_before_add=True)


class MarstekSelect(CoordinatorEntity, SelectEntity):
    """
    Representation of a Modbus select entity for Marstek Venus.

    Select state is read and write asynchronously via
    the coordinator communicating with the Modbus device.
    """

    def __init__(
        self, coordinator: MarstekCoordinator, definition: dict[str, Any]
    ) -> None:
        """
        Initialize the select entity.

        Args:
            coordinator: The MarstekCoordinator instance managing data updates.
            definition: A dictionary defining the select entity's properties.
        """
        super().__init__(coordinator)

        # Store the key and definition
        self._key = definition["key"]
        self.definition = definition

        # Defensive: Stelle sicher, dass die Map im Coordinator existiert
        if not hasattr(self.coordinator, "_entity_types") or self.coordinator._entity_types is None:
            self.coordinator._entity_types = {}
        # Assign the entity type to the coordinator mapping
        self.coordinator._entity_types[self._key] = self.entity_type

        # Set entity attributes from definition
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self._key}"
        self._attr_has_entity_name = True

        # Use key as translation_key for automatic translations
        self._attr_translation_key = definition["key"]

        # Internal state variables
        self._state = None
        self._register = definition["register"]

        # Set category if defined in the definition
        if "category" in self.definition:
            self._attr_entity_category = EntityCategory(self.definition.get("category"))

        # Set icon if defined in the definition
        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        # Optional: disable entity by default if specified in the definition
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

        # Force entity_id to use key regardless of language setting
        # This ensures English entity_ids while friendly_name follows user language
        self._attr_suggested_object_id = definition["key"]

        # You can rely on the property below, but pre-fill for HA caching behavior
        self._attr_options = list(self.definition.get("options", {}).keys())

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "select"

    @property
    def available(self) -> bool:
        """
        Return True if the coordinator has successfully fetched data.
        Used by Home Assistant to determine entity availability.
        """
        return self.coordinator.last_update_success

    @property
    def options(self) -> list[str]:
        """
        Return a list of available options for selection.
        """
        return list(self.definition.get("options", {}).keys())

    @property
    def current_option(self) -> str | None:
        """
        Return the currently selected option.

        The value is obtained from the coordinator's shared data dictionary.
        Maps the numeric register value back to the option string.
        """
        data = self.coordinator.data
        if data is None:
            return None

        value = data.get(self._key)
        if value is None:
            return None

        options_map = self.definition.get("options", {})
        # Reverse the mapping: {int_value: option_name}
        try:
            reversed_map = {int(v): k for k, v in options_map.items()}
            return reversed_map.get(int(value))
        except Exception:
            _LOGGER.debug("current_option: value=%r passt nicht zu options_map=%r", value, options_map)
            return None

    async def async_select_option(self, option: str) -> None:
        """
        Change the selected option by writing to the device register.
        """
        options_map = self.definition.get("options", {})
        if option not in options_map:
            _LOGGER.warning("Invalid option '%s' for %s", option, self._key)
            return

        value = options_map[option]

        # Optimistisch aktualisieren, damit HA sofort den neuen State zeigt
        self.coordinator.data[self._key] = value
        self.async_write_ha_state()

        # Write the new value to the register via the coordinator
        await self.coordinator.async_write_value(
            register=self._register,
            value=value,
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=self.entity_type,
        )

    @property
    def device_info(self) -> dict:
        """
        Return device information for Home Assistant's device registry.
        Includes identifiers, name, manufacturer, model, and entry type.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": DeviceEntryType.SERVICE,
        }

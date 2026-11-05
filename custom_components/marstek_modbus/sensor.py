"""Sensors for the Marstek Venus Modbus integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import MarstekConfigEntry
from .entity import MarstekEntity, MarstekEntityDescription, descriptions_for
from .venus import VenusD, VenusDevice, VenusEV3, VenusEV12
from .venus.components import ems_version_number

_LOGGER = logging.getLogger(__name__)

INVERTER_STATES = {
    0: "Sleep",
    1: "Standby",
    2: "Charge",
    3: "Discharge",
    4: "Backup Mode",
    5: "OTA Upgrade",
    6: "Bypass",
}


@dataclass(frozen=True, kw_only=True)
class MarstekSensorEntityDescription(MarstekEntityDescription, SensorEntityDescription):
    """Describe a Marstek sensor."""

    # Maps the field's decoded value to the state.
    value_fn: Callable[[Any], StateType] | None = None
    # Computes the state from the device, for a sensor that reads several fields.
    device_value_fn: Callable[[VenusDevice], StateType] | None = None


def _efficiency(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(min(abs(numerator) / abs(denominator) * 100, 100.0), 1)


def _round_trip_efficiency(
    charge: float | None, discharge: float | None
) -> float | None:
    if charge is None or discharge is None:
        return None
    return _efficiency(discharge, charge)


def _conversion_efficiency(device: VenusDevice) -> float | None:
    """Output over input of the inverter, whichever way the power flows."""
    battery_power = device.battery.battery_power
    ac_power = device.grid.ac_power
    if battery_power is None or ac_power is None:
        return None
    if battery_power > 0:
        return _efficiency(battery_power, ac_power)
    return _efficiency(ac_power, battery_power)


def _stored_energy(device: VenusDevice) -> float | None:
    soc = device.battery.battery_soc
    capacity = device.battery_info.battery_total_energy
    if soc is None or capacity is None:
        return None
    return round(soc / 100 * capacity, 2)


def _battery_cycles(device: VenusDevice) -> float | None:
    discharge = device.energy.total_discharging_energy
    capacity = device.battery_info.battery_total_energy
    if discharge is None or not capacity:
        return None
    return round(discharge / capacity, 2)


SENSORS: tuple[MarstekSensorEntityDescription, ...] = (
    MarstekSensorEntityDescription(
        key="device_name",
        component="identity",
        icon="mdi:package-variant-closed",
    ),
    MarstekSensorEntityDescription(
        key="sn_code",
        component="identity",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="software_version",
        component="versions",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ticket-confirmation-outline",
    ),
    MarstekSensorEntityDescription(
        key="bms_version",
        component="versions",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-check-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="ems_version",
        component="versions",
        value_fn=ems_version_number,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ticket-confirmation-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="comm_module_firmware",
        component="comms",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ticket-confirmation-outline",
    ),
    MarstekSensorEntityDescription(
        key="ble_mac_address",
        component="comms",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:bluetooth",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="battery_soc",
        component="battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
    ),
    MarstekSensorEntityDescription(
        key="battery_total_energy",
        component="battery_info",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
    ),
    MarstekSensorEntityDescription(
        key="battery_voltage",
        component="battery",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    MarstekSensorEntityDescription(
        key="battery_current",
        component="battery",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
    ),
    MarstekSensorEntityDescription(
        key="battery_power",
        component="battery",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    MarstekSensorEntityDescription(
        key="internal_temperature",
        component="temperatures",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
    ),
    MarstekSensorEntityDescription(
        key="internal_mos1_temperature",
        component="temperatures",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="internal_mos2_temperature",
        component="temperatures",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="ac_voltage",
        component="grid",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    MarstekSensorEntityDescription(
        key="ac_current",
        component="grid",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
    ),
    MarstekSensorEntityDescription(
        key="ac_power",
        component="grid",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
    ),
    MarstekSensorEntityDescription(
        key="ac_frequency",
        component="grid",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        suggested_display_precision=2,
    ),
    MarstekSensorEntityDescription(
        key="total_charging_energy",
        component="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    MarstekSensorEntityDescription(
        key="total_discharging_energy",
        component="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    MarstekSensorEntityDescription(
        key="total_daily_charging_energy",
        component="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="total_daily_discharging_energy",
        component="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="total_monthly_charging_energy",
        component="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="total_monthly_discharging_energy",
        component="energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="max_cell_temperature",
        component="temperatures",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="min_cell_temperature",
        component="temperatures",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="max_cell_voltage",
        component="cells",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=3,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="min_cell_voltage",
        component="cells",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=3,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="inverter_state",
        component="inverter",
        value_fn=INVERTER_STATES.get,
        icon="mdi:state-machine",
    ),
    MarstekSensorEntityDescription(
        key="fault_status",
        component="alarms",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert",
    ),
    MarstekSensorEntityDescription(
        key="alarm_status",
        component="alarms",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert",
    ),
    MarstekSensorEntityDescription(
        key="modbus_address",
        component="identity",
        icon="mdi:home-automation",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="ac_offgrid_voltage",
        component="offgrid",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="ac_offgrid_current",
        component="offgrid",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="ac_offgrid_power",
        component="offgrid",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="wifi_signal_strength",
        component="network",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        suggested_display_precision=0,
        icon="mdi:wifi",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="bluetooth_status",
        component="network",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:bluetooth",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="vms_version",
        component="versions",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-check-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="battery_cycle_count",
        component="battery_info",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        icon="mdi:counter",
    ),
    MarstekSensorEntityDescription(
        key="device_ip",
        component="comms",
        value_fn=str,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="gateway_ip",
        component="comms",
        value_fn=str,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt1_voltage",
        component="mppt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt1_current",
        component="mppt",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt1_power",
        component="mppt",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt2_voltage",
        component="mppt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt2_current",
        component="mppt",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt2_power",
        component="mppt",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt3_voltage",
        component="mppt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt3_current",
        component="mppt",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt3_power",
        component="mppt",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt4_voltage",
        component="mppt",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt4_current",
        component="mppt",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    MarstekSensorEntityDescription(
        key="mppt4_power",
        component="mppt",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    ),
    *(
        MarstekSensorEntityDescription(
            key=f"battery_soc_{pack}",
            component=f"pack_{pack}",
            field="soc",
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            suggested_display_precision=1,
            entity_registry_enabled_default=False,
        )
        for pack in range(1, 7)
    ),
    *(
        MarstekSensorEntityDescription(
            key=f"battery_{pack}_cell_{cell}_voltage",
            component=f"pack_{pack}",
            field=f"cell_{cell}_voltage",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            suggested_display_precision=3,
            entity_registry_enabled_default=False,
        )
        for pack in range(1, 7)
        for cell in range(1, 17)
    ),
    MarstekSensorEntityDescription(
        key="firmware_version",
        requires=(
            ("versions", "ems_version"),
            ("versions", "vms_version"),
            ("versions", "bms_version"),
        ),
        device_value_fn=lambda device: device.versions.firmware_version,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    MarstekSensorEntityDescription(
        key="round_trip_efficiency_total",
        requires=(
            ("energy", "total_charging_energy"),
            ("energy", "total_discharging_energy"),
        ),
        device_value_fn=lambda device: _round_trip_efficiency(
            device.energy.total_charging_energy, device.energy.total_discharging_energy
        ),
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
    ),
    MarstekSensorEntityDescription(
        key="round_trip_efficiency_monthly",
        requires=(
            ("energy", "total_monthly_charging_energy"),
            ("energy", "total_monthly_discharging_energy"),
        ),
        device_value_fn=lambda device: _round_trip_efficiency(
            device.energy.total_monthly_charging_energy,
            device.energy.total_monthly_discharging_energy,
        ),
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
    ),
    MarstekSensorEntityDescription(
        key="conversion_efficiency",
        requires=(("battery", "battery_power"), ("grid", "ac_power")),
        device_value_fn=_conversion_efficiency,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    MarstekSensorEntityDescription(
        key="stored_energy",
        requires=(("battery", "battery_soc"), ("battery_info", "battery_total_energy")),
        device_value_fn=_stored_energy,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    MarstekSensorEntityDescription(
        key="battery_cycle_count_calc",
        requires=(
            ("energy", "total_discharging_energy"),
            ("battery_info", "battery_total_energy"),
        ),
        device_value_fn=_battery_cycles,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
    ),
    MarstekSensorEntityDescription(
        key="solar_power_total",
        requires=tuple(("mppt", f"mppt{index}_power") for index in range(1, 5)),
        device_value_fn=lambda device: (
            device.mppt.solar_power_total if device.mppt is not None else None
        ),
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        icon="mdi:solar-power",
    ),
)

_EFFICIENCY_WITHOUT_CATEGORY = {"entity_category": None}

OVERRIDES: dict[type[VenusDevice], dict[str, dict[str, Any]]] = {
    VenusEV12: {
        "bms_version": {"entity_registry_enabled_default": True},
        "ems_version": {"entity_registry_enabled_default": True},
        "firmware_version": {
            "requires": (("versions", "ems_version"), ("versions", "bms_version"))
        },
    },
    VenusEV3: {
        "battery_soc": {"suggested_display_precision": 2},
        "battery_voltage": {"suggested_display_precision": 2},
        "ac_voltage": {"entity_registry_enabled_default": False},
        "ac_frequency": {"entity_registry_enabled_default": False},
    },
    VenusD: {
        "alarm_status": {"entity_registry_enabled_default": False},
        "round_trip_efficiency_total": _EFFICIENCY_WITHOUT_CATEGORY,
        "round_trip_efficiency_monthly": _EFFICIENCY_WITHOUT_CATEGORY,
        "conversion_efficiency": _EFFICIENCY_WITHOUT_CATEGORY,
    },
}


def descriptions(device: VenusDevice) -> list[MarstekSensorEntityDescription]:
    """Return the sensors this device model has."""
    return descriptions_for(device, SENSORS, OVERRIDES)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MarstekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        (
            MarstekTotalSensor
            if description.state_class
            in (SensorStateClass.TOTAL, SensorStateClass.TOTAL_INCREASING)
            else MarstekSensor
        )(coordinator, description)
        for description in descriptions(coordinator.device)
    )


class MarstekSensor(MarstekEntity, SensorEntity):
    """A sensor reading the battery."""

    entity_description: MarstekSensorEntityDescription

    @property
    def current_value(self) -> StateType:
        """The value the device reports now."""
        description = self.entity_description
        if description.device_value_fn is not None:
            return description.device_value_fn(self.device)
        value = self.field_value
        if value is None or description.value_fn is None:
            return value
        return description.value_fn(value)

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return self.current_value


class MarstekTotalSensor(MarstekSensor, RestoreSensor):
    """A long-term statistic.

    It holds its last value while the battery does not answer, and across a
    restart, so statistics and the energy dashboard keep their history.
    """

    # The last value accepted from the device in this run, to spot glitches.
    _last_read: StateType = None

    @property
    def available(self) -> bool:
        """Always available, so a gap does not break statistics."""
        return True

    @property
    def native_value(self) -> StateType:
        """Return the last accepted value."""
        return self._attr_native_value

    async def async_added_to_hass(self) -> None:
        """Restore the last value, then take the current one."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value
        self._process_value()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._process_value()
        super()._handle_coordinator_update()

    def _process_value(self) -> None:
        value = self.current_value
        if value is None:
            return
        last = self._last_read
        if self._is_glitch(value, last):
            _LOGGER.warning(
                "Ignoring a drop for %s: %s after %s", self.entity_id, value, last
            )
            return
        self._last_read = value
        self._attr_native_value = value

    def _is_glitch(self, value: Any, last: Any) -> bool:
        """Whether a counter reading is a firmware glitch rather than real.

        The firmware sometimes reports a lifetime total lower than before, such
        as a tenth of it. Daily and monthly counters reset, so a drop is real
        for them.
        """
        key = self.entity_description.key
        if (
            self.entity_description.state_class is not SensorStateClass.TOTAL_INCREASING
            or "_daily_" in key
            or "_monthly_" in key
            or not isinstance(value, (int, float))
            or not isinstance(last, (int, float))
        ):
            return False
        return value < last

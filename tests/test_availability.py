import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from homeassistant.util.dt import utcnow

from custom_components.marstek_modbus.binary_sensor import MarstekBinarySensor, MarstekConnectionBinarySensor
from custom_components.marstek_modbus.coordinator import MarstekCoordinator
from custom_components.marstek_modbus.number import MarstekNumber
from custom_components.marstek_modbus.select import MarstekSelect
from custom_components.marstek_modbus.sensor import MarstekSensor, MarstekSolarPowerSensor
from custom_components.marstek_modbus.switch import MarstekSwitch


def make_coordinator(last_read_seconds_ago, suspended=False):
    """A coordinator that still holds the data of its last successful poll."""
    coordinator = object.__new__(MarstekCoordinator)
    coordinator.scan_intervals = {"high": 10, "medium": 30}
    coordinator._connection_suspended = suspended
    coordinator._last_successful_read = (
        None if last_read_seconds_ago is None else utcnow() - timedelta(seconds=last_read_seconds_ago)
    )
    coordinator.last_update_success = True  # a failed poll returns the previous data
    coordinator.data = {"ac_power": -837, "force_mode": 1}
    return coordinator


def make_entity(cls, coordinator, key="ac_power"):
    entity = object.__new__(cls)
    entity.coordinator = coordinator
    entity._key = key
    return entity


ENTITY_CLASSES = (MarstekSensor, MarstekSolarPowerSensor, MarstekBinarySensor, MarstekNumber, MarstekSelect, MarstekSwitch)


def test_entities_are_available_while_the_connection_is_healthy():
    coordinator = make_coordinator(last_read_seconds_ago=5)
    assert coordinator.is_connection_healthy()
    for cls in ENTITY_CLASSES:
        assert make_entity(cls, coordinator).available is True, cls.__name__


def test_a_short_gap_keeps_the_last_value():
    coordinator = make_coordinator(last_read_seconds_ago=45)  # below the threshold of 60 s
    for cls in ENTITY_CLASSES:
        assert make_entity(cls, coordinator).available is True, cls.__name__


def test_entities_go_unavailable_once_the_connection_counts_as_lost():
    for coordinator in (
        make_coordinator(last_read_seconds_ago=300),
        make_coordinator(last_read_seconds_ago=5, suspended=True),
        make_coordinator(last_read_seconds_ago=None),
    ):
        assert not coordinator.is_connection_healthy()
        for cls in ENTITY_CLASSES:
            assert make_entity(cls, coordinator).available is False, cls.__name__


def test_the_connection_sensor_itself_stays_available():
    coordinator = make_coordinator(last_read_seconds_ago=300)
    sensor = make_entity(MarstekConnectionBinarySensor, coordinator)
    assert sensor.available is True
    assert sensor.is_on is False

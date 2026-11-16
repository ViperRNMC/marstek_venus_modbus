"""Tests for the Home Assistant layer."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit, WriteEvent
from modbus_connection.model import UpdateReport
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.marstek_modbus.const import DOMAIN
from custom_components.marstek_modbus.diagnostics import (
    async_get_config_entry_diagnostics,
)


def entity_id(
    hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str
) -> str:
    """Look an entity up by the unique id the integration gives it."""
    found = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )
    assert found is not None, key
    return found


def state(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str:
    """The state of an entity, by its key."""
    entity_state = hass.states.get(entity_id(hass, entry, platform, key))
    assert entity_state is not None, key
    return entity_state.state


async def test_sets_up_and_polls(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The first poll backs register and calculated entities."""
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED

    assert state(hass, entry, "sensor", "battery_power") == "-200"
    assert state(hass, entry, "sensor", "battery_voltage") == "53.12"
    assert state(hass, entry, "sensor", "battery_soc") == "55.0"
    assert state(hass, entry, "sensor", "device_name") == "VENUS"
    assert state(hass, entry, "sensor", "inverter_state") == "Charge"
    assert state(hass, entry, "sensor", "firmware_version") == "V147.6.117.112"
    assert state(hass, entry, "sensor", "stored_energy") == "2.82"
    assert state(hass, entry, "sensor", "round_trip_efficiency_total") == "83.3"
    assert state(hass, entry, "select", "user_work_mode") == "anti_feed"
    assert state(hass, entry, "switch", "backup_function") == STATE_ON
    assert state(hass, entry, "binary_sensor", "modbus_connection") == STATE_ON


async def test_disabled_entities_are_not_read(
    hass: HomeAssistant, setup_integration: MockConfigEntry, unit: MockModbusUnit
) -> None:
    """Registers behind disabled entities stay off the wire.

    The firmware version still reads the version registers, although their
    own entities are disabled.
    """
    read = {event.address for event in unit.read_events}

    assert 34018 not in read  # cell voltages, disabled by default
    assert 43100 not in read  # schedules, disabled by default
    assert 30200 in read  # versions, for the firmware version


async def test_enabling_an_entity_reads_its_register(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_get_unit: None,
    unit: MockModbusUnit,
) -> None:
    """An entity enabled in the registry is polled from the next setup on."""
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{config_entry.entry_id}_battery_1_cell_2_voltage",
        config_entry=config_entry,
    )
    unit.holding[34019] = 3302

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert state(hass, config_entry, "sensor", "battery_1_cell_2_voltage") == "3.302"
    assert (34019, 1) in {(event.address, event.count) for event in unit.read_events}


async def test_select_writes_and_holds_the_written_option(
    hass: HomeAssistant, setup_integration: MockConfigEntry, unit: MockModbusUnit
) -> None:
    """A write shows at once, before the device reports it back."""
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    select_entity = entity_id(hass, setup_integration, "select", "user_work_mode")

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": select_entity, "option": "trade_mode"},
        blocking=True,
    )

    assert [(event.address, event.values) for event in events] == [(43000, [2])]
    assert hass.states.get(select_entity).state == "trade_mode"


@pytest.mark.parametrize("other_control_write", [False, True])
async def test_rs485_write_warns_when_readback_differs(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    config_entry: MockConfigEntry,
    mock_get_unit: None,
    unit: MockModbusUnit,
    caplog: pytest.LogCaptureFixture,
    other_control_write: bool,
) -> None:
    """An acknowledged write can still be ignored by the battery."""
    er.async_get(hass).async_get_or_create(
        "switch",
        DOMAIN,
        f"{config_entry.entry_id}_rs485_control_mode",
        config_entry=config_entry,
    )
    unit.holding[42000] = 21947
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": entity_id(hass, config_entry, "switch", "rs485_control_mode")},
        blocking=True,
    )
    if other_control_write:
        await config_entry.runtime_data.async_write("control", "backup_function", 1)
    unit.holding[42000] = 21947
    freezer.tick(timedelta(seconds=4))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert "RS485 control mode" in caplog.text
    assert "21930" in caplog.text
    assert "21947" in caplog.text


@pytest.mark.parametrize(
    "scenario", ["accepted", "read_failed", "read_rejected", "superseded"]
)
async def test_rs485_write_does_not_warn_without_a_mismatch(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    config_entry: MockConfigEntry,
    mock_get_unit: None,
    unit: MockModbusUnit,
    caplog: pytest.LogCaptureFixture,
    scenario: str,
) -> None:
    """Only a successful readback of a different value signals a mismatch."""
    er.async_get(hass).async_get_or_create(
        "switch",
        DOMAIN,
        f"{config_entry.entry_id}_rs485_control_mode",
        config_entry=config_entry,
    )
    unit.holding[42000] = 21947
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    switch_entity = entity_id(hass, config_entry, "switch", "rs485_control_mode")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": switch_entity}, blocking=True
    )
    if scenario == "read_failed":
        unit.fail_read(42000, ModbusTimeoutError("response timeout"))
    elif scenario == "read_rejected":
        unit.fail_read(42000, IllegalDataAddressError())
    elif scenario == "superseded":
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": switch_entity}, blocking=True
        )

    freezer.tick(timedelta(seconds=4))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert "RS485 control mode readback" not in caplog.text
    if scenario == "read_failed":
        assert "Reading control back after a write failed" in caplog.text
    elif scenario == "read_rejected":
        assert "control" in config_entry.runtime_data.failed
    else:
        assert state(hass, config_entry, "switch", "rs485_control_mode") == (
            "off" if scenario == "superseded" else "on"
        )


async def test_failing_sub_system_marks_only_its_entities(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_integration: MockConfigEntry,
    unit: MockModbusUnit,
) -> None:
    """A sub-system the firmware refuses takes only its own entities down."""
    entry = setup_integration
    unit.fail_read(35100, IllegalDataAddressError())

    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert state(hass, entry, "sensor", "inverter_state") == STATE_UNAVAILABLE
    assert state(hass, entry, "sensor", "battery_power") == "-200"


async def test_later_component_timeout_preserves_successful_reads(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    unit: MockModbusUnit,
) -> None:
    """A timeout after an answer only makes the failed component unavailable."""
    coordinator = setup_integration.runtime_data
    coordinator._last_polled.clear()
    unit.fail_read(35100, ModbusTimeoutError("response timeout"))

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert "inverter" in coordinator.failed
    assert "battery" not in coordinator.failed
    assert state(hass, setup_integration, "sensor", "inverter_state") == STATE_UNAVAILABLE
    assert state(hass, setup_integration, "sensor", "battery_power") == "-200"


async def test_totals_hold_while_the_battery_is_away(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_integration: MockConfigEntry,
    unit: MockModbusUnit,
) -> None:
    """Energy totals keep their value when the battery does not answer."""
    entry = setup_integration
    unit.fail_requests(ModbusConnectionError())

    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert state(hass, entry, "sensor", "battery_power") == STATE_UNAVAILABLE
    assert state(hass, entry, "sensor", "total_charging_energy") == "1200.0"
    assert state(hass, entry, "binary_sensor", "modbus_connection") == "off"


async def test_first_read_timeout_recycles_and_retries_once(
    setup_integration: MockConfigEntry,
    unit: MockModbusUnit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A timeout before any response gets one fresh-connection retry."""
    coordinator = setup_integration.runtime_data
    coordinator._last_polled.clear()
    disconnect = AsyncMock()
    poll = AsyncMock(
        side_effect=[
            ModbusTimeoutError("response timeout"),
            UpdateReport(updated={"battery"}),
        ]
    )
    monkeypatch.setattr(unit, "disconnect", disconnect)
    monkeypatch.setattr(coordinator.device, "async_poll", poll)

    await coordinator._async_update_data()

    disconnect.assert_awaited_once()
    assert poll.await_count == 2
    assert coordinator.failed == set()


async def test_timeout_recovery_is_bounded_and_cooled_down(
    setup_integration: MockConfigEntry,
    unit: MockModbusUnit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed retry is not repeated until the recovery cooldown expires."""
    coordinator = setup_integration.runtime_data
    coordinator._last_polled.clear()
    disconnect = AsyncMock()
    poll = AsyncMock(
        side_effect=[
            ModbusTimeoutError("first timeout"),
            ModbusTimeoutError("retry timeout"),
            ModbusTimeoutError("cooldown timeout"),
        ]
    )
    monkeypatch.setattr(unit, "disconnect", disconnect)
    monkeypatch.setattr(coordinator.device, "async_poll", poll)

    with pytest.raises(UpdateFailed, match="after reconnect"):
        await coordinator._async_update_data()
    with pytest.raises(UpdateFailed, match="cooldown timeout"):
        await coordinator._async_update_data()

    disconnect.assert_awaited_once()
    assert poll.await_count == 3


async def test_total_ignores_a_drop(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_integration: MockConfigEntry,
    unit: MockModbusUnit,
) -> None:
    """A lifetime counter that reads lower than before is a firmware glitch."""
    entry = setup_integration
    unit.holding[33000] = [0x0000, 0x2EE0, 0x0001, 0x86A0]  # a tenth of before

    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert state(hass, entry, "sensor", "total_charging_energy") == "1200.0"


async def test_slow_sub_systems_wait_for_their_interval(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_integration: MockConfigEntry,
    unit: MockModbusUnit,
) -> None:
    """The energy counters are read on the low interval only."""
    unit.read_events.clear()

    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert 33000 not in {event.address for event in unit.read_events}

    freezer.tick(timedelta(seconds=50))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert 33000 in {event.address for event in unit.read_events}


async def test_unreachable_battery_defers_setup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_get_unit: None,
    unit: MockModbusUnit,
) -> None:
    """A battery that does not answer leaves the entry retrying."""
    unit.fail_requests(ModbusConnectionError())

    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize("device_version", ["v3"])
async def test_legacy_device_version(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Entries from before the model rename still set up."""
    assert setup_integration.state is ConfigEntryState.LOADED
    assert state(hass, setup_integration, "sensor", "battery_soc") == "55.0"


@pytest.mark.parametrize("device_version", ["Z"])
async def test_unknown_device_version(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_get_unit: None
) -> None:
    """An unknown model fails setup instead of guessing a register map."""
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_polling_options_apply_at_once(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The options flow changes the poll interval of the running entry."""
    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "polling"}
    )
    await hass.config_entries.options.async_configure(
        result["flow_id"], {"high": 5, "low": 30}
    )

    assert setup_integration.runtime_data.update_interval == timedelta(seconds=5)


async def test_unload(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    """The entry unloads cleanly."""
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert setup_integration.state is ConfigEntryState.NOT_LOADED


async def test_diagnostics_leave_out_the_mac_address(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_get_unit: None,
    unit: MockModbusUnit,
) -> None:
    """Diagnostics carry the raw registers, without the battery's identity."""
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{config_entry.entry_id}_ble_mac_address",
        config_entry=config_entry,
    )
    unit.holding[30304] = [0x3031, 0x6132, 0x4233, 0x6334, 0x4435, 0x6536]
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, config_entry, "sensor", "ble_mac_address") == "01:A2:B3:C4:D5:E6"

    result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert result["failed"] == []
    assert result["registers"]["holding"][30001] == 0xFF38
    assert 30304 not in result["registers"]["holding"]


@pytest.mark.parametrize(
    ("device_version", "expected"),
    [
        # The counts the YAML register maps defined, plus the connection sensor.
        (
            "E v1/v2",
            {
                "sensor": 44,
                "binary_sensor": 4,
                "select": 9,
                "switch": 8,
                "number": 25,
                "button": 2,
            },
        ),
        (
            "E v3",
            {
                "sensor": 60,
                "binary_sensor": 3,
                "select": 8,
                "switch": 8,
                "number": 23,
                "button": 2,
            },
        ),
        (
            "D",
            {
                "sensor": 127,
                "binary_sensor": 3,
                "select": 8,
                "switch": 8,
                "number": 23,
                "button": 2,
            },
        ),
        (
            "A",
            {
                "sensor": 139,
                "binary_sensor": 3,
                "select": 8,
                "switch": 8,
                "number": 23,
                "button": 2,
            },
        ),
    ],
)
async def test_every_model_sets_up_its_entities(
    hass: HomeAssistant, setup_integration: MockConfigEntry, expected: dict[str, int]
) -> None:
    """Each model gets the entities its register map has."""
    assert setup_integration.state is ConfigEntryState.LOADED
    entries = er.async_entries_for_config_entry(
        er.async_get(hass), setup_integration.entry_id
    )
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry.domain] = counts.get(entry.domain, 0) + 1
    assert counts == expected

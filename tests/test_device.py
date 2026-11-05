"""Tests for the device library against the in-memory backend."""

from __future__ import annotations

from ipaddress import IPv4Address

import pytest
from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusConnection, MockModbusUnit, WriteEvent

from custom_components.marstek_modbus.venus import (
    VenusA,
    VenusD,
    VenusEV3,
    VenusEV12,
)
from custom_components.marstek_modbus.venus.components import ems_version_number


@pytest.fixture(name="unit")
def unit_fixture() -> MockModbusUnit:
    """An in-memory unit with nothing seeded."""
    return MockModbusConnection().for_unit(1)


async def test_ev12_decodes_its_own_layout(unit: MockModbusUnit) -> None:
    """E v1/v2 keeps power as 32-bit words and versions at 31100."""
    unit.holding[32100] = [5312, 0xFF9C, 0xFFFF, 0xFF38, 87]
    unit.holding[31100] = [123, 1476, 112]
    unit.holding[31000] = [0x5645, 0x4E55, 0x5300, 0x4142]  # "VENUS", NUL, junk
    unit.holding[30402] = [0x3031, 0x6132, 0x4233, 0x6334, 0x4435, 0x6536]
    device = VenusEV12(unit)

    report = await device.async_poll(("battery", "versions", "identity", "comms"))

    assert report.updated == {"battery", "versions", "identity", "comms"}
    assert device.battery.battery_voltage == 53.12
    assert device.battery.battery_current == -1.0
    assert device.battery.battery_power == -200
    assert device.battery.battery_soc == 87
    assert device.versions.software_version == 1.23
    assert device.versions.firmware_version == "V147.6.112"
    assert device.identity.device_name == "VENUS"
    assert device.comms.ble_mac_address == "01:A2:B3:C4:D5:E6"


async def test_ev3_reads_soc_and_cells_from_the_pack(unit: MockModbusUnit) -> None:
    """E v3 reports state of charge and cell voltages at the pack registers."""
    unit.holding[34002] = 555
    unit.holding[34018] = [3301, 3302]
    unit.holding[34033] = 3316
    unit.holding[30200] = [158, 0, 117, 0, 112]
    unit.holding[30400] = [0xC0A8, 0x0132, 0xC0A8, 0x0101]
    device = VenusEV3(unit)

    await device.async_poll(("battery", "pack_1", "versions", "comms"))

    assert device.battery.battery_soc == 55.5
    assert device.pack_1.cell_1_voltage == 3.301
    assert device.pack_1.cell_2_voltage == 3.302
    assert device.pack_1.cell_16_voltage == 3.316
    assert device.versions.firmware_version == "V158.117.112"
    assert device.comms.device_ip == IPv4Address("192.168.1.50")
    assert device.comms.gateway_ip == IPv4Address("192.168.1.1")


@pytest.mark.parametrize("model", [VenusD, VenusA])
async def test_packs_are_100_registers_apart(
    unit: MockModbusUnit, model: type[VenusD | VenusA]
) -> None:
    """Pack N keeps its state of charge at 34002 + 100 * (N - 1)."""
    unit.holding[34202] = 612
    unit.holding[34218] = 3290
    device = model(unit)

    await device.async_poll(("pack_3",))

    assert device.pack_3.soc == 61.2
    assert device.pack_3.cell_1_voltage == 3.29


async def test_mppt_total(unit: MockModbusUnit) -> None:
    """The solar total adds up the four inputs."""
    unit.holding[30037] = [1000, 2005, 0, 15]
    device = VenusD(unit)

    await device.async_poll(("mppt",))

    assert device.mppt.solar_power_total == 302.0


async def test_schedule_writes_at_its_own_offset(unit: MockModbusUnit) -> None:
    """Schedule N sits at 43100 + 5 * (N - 1), and its power is signed."""
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    device = VenusA(unit)

    await device.schedule_4.write("mode", -1500)

    assert [(event.address, event.values) for event in events] == [(43118, [0xFA24])]


async def test_restricted_component_reads_only_kept_fields(
    unit: MockModbusUnit,
) -> None:
    """A component narrowed to some fields reads only their registers."""
    device = VenusA(unit)
    device.pack_2.restrict_fields(["soc"])

    await device.async_poll(("pack_2",))

    assert [(event.address, event.count) for event in unit.read_events] == [(34102, 1)]


async def test_refused_component_does_not_fail_the_rest(
    unit: MockModbusUnit,
) -> None:
    """A sub-system the firmware refuses lands in the report's failures."""
    unit.fail_read(35100, IllegalDataAddressError())
    unit.holding[30001] = 100
    device = VenusEV3(unit)

    report = await device.async_poll(("battery", "inverter"))

    assert report.updated == {"battery"}
    assert set(report.failed) == {"inverter"}
    assert device.battery.battery_power == 100


async def test_message_spacing(unit: MockModbusUnit) -> None:
    """The device asks for quiet between requests."""
    VenusEV3(unit)

    assert unit.message_spacing == 0.08


@pytest.mark.parametrize(("raw", "expected"), [(158, 158), (1476, 147.6), (1470, 147)])
def test_ems_version_number(raw: int, expected: float) -> None:
    """Four-digit EMS versions end in a decimal."""
    assert ems_version_number(raw) == expected

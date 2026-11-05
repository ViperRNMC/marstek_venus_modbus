"""The top-level device objects, one per Venus model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection.model import Component, Device

from .components import (
    Alarms,
    Battery,
    BatteryInfo,
    Cells,
    Commands,
    Comms,
    Control,
    Energy,
    EV3Battery,
    EV3Comms,
    EV3Offgrid,
    EV12Battery,
    EV12Comms,
    EV12Control,
    EV12Grid,
    EV12Identity,
    EV12Temperatures,
    EV12Versions,
    Grid,
    Identity,
    Inverter,
    Mppt,
    Network,
    Offgrid,
    Pack13,
    Pack16,
    PackBatteryInfo,
    PackCells16,
    PackSoc,
    Schedule,
    Temperatures,
    Versions,
)

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

# The battery drops requests that follow each other too closely.
MESSAGE_SPACING = 0.08

_FAST = (
    "battery",
    "grid",
    "offgrid",
    "temperatures",
    "inverter",
    "cells",
    "network",
    "control",
    "alarms",
    "mppt",
    "pack_1",
    "pack_2",
    "pack_3",
    "pack_4",
    "pack_5",
    "pack_6",
)
_SLOW = ("identity", "versions", "comms", "battery_info", "energy")
_SCHEDULES = tuple(f"schedule_{index}" for index in range(1, 7))


class VenusDevice(Device):
    """A Marstek Venus battery reached through a ``ModbusUnit``."""

    #: Sub-systems that change by the second, for the fast poll.
    FAST: tuple[str, ...] = _FAST
    #: Sub-systems that change slowly, for the slow poll.
    SLOW: tuple[str, ...] = _SLOW + _SCHEDULES

    battery: Battery
    grid: Grid
    offgrid: Offgrid
    temperatures: Temperatures
    control: Control
    identity: Identity
    versions: Versions | EV12Versions
    comms: Comms
    battery_info: BatteryInfo
    alarms: Alarms | None = None
    mppt: Mppt | None = None
    pack_1: Component | None = None
    pack_2: Component | None = None
    pack_3: Component | None = None
    pack_4: Component | None = None
    pack_5: Component | None = None
    pack_6: Component | None = None

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        unit.set_message_spacing(MESSAGE_SPACING)
        self.inverter = Inverter(unit)
        self.cells = Cells(unit)
        self.network = Network(unit)
        self.energy = Energy(unit)
        self.commands = Commands(unit)
        self.schedule_1 = Schedule(unit, index=1)
        self.schedule_2 = Schedule(unit, index=2)
        self.schedule_3 = Schedule(unit, index=3)
        self.schedule_4 = Schedule(unit, index=4)
        self.schedule_5 = Schedule(unit, index=5)
        self.schedule_6 = Schedule(unit, index=6)


class VenusEV12(VenusDevice):
    """A Venus E v1 or v2."""

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.battery = EV12Battery(unit)
        self.grid = EV12Grid(unit)
        self.offgrid = Offgrid(unit)
        self.temperatures = EV12Temperatures(unit)
        self.control = EV12Control(unit)
        self.alarms = Alarms(unit)
        self.identity = EV12Identity(unit)
        self.versions = EV12Versions(unit)
        self.comms = EV12Comms(unit)
        self.battery_info = BatteryInfo(unit)


class VenusEV3(VenusDevice):
    """A Venus E v3."""

    FAST = _FAST + _SCHEDULES[:2]
    SLOW = _SLOW + _SCHEDULES[2:]

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.battery = EV3Battery(unit)
        self.grid = Grid(unit)
        self.offgrid = EV3Offgrid(unit)
        self.temperatures = Temperatures(unit)
        self.control = Control(unit)
        self.identity = Identity(unit)
        self.versions = Versions(unit)
        self.comms = EV3Comms(unit)
        self.battery_info = PackBatteryInfo(unit)
        self.pack_1 = PackCells16(unit, index=1)


class VenusD(VenusDevice):
    """A Venus D: up to six 16-cell packs, cell voltages for the first four."""

    FAST = _FAST + _SCHEDULES[:2]
    SLOW = _SLOW + _SCHEDULES[2:]

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.battery = Battery(unit)
        self.grid = Grid(unit)
        self.offgrid = Offgrid(unit)
        self.temperatures = Temperatures(unit)
        self.control = Control(unit)
        self.alarms = Alarms(unit)
        self.mppt = Mppt(unit)
        self.identity = Identity(unit)
        self.versions = Versions(unit)
        self.comms = Comms(unit)
        self.battery_info = PackBatteryInfo(unit)
        self.pack_1 = Pack16(unit, index=1)
        self.pack_2 = Pack16(unit, index=2)
        self.pack_3 = Pack16(unit, index=3)
        self.pack_4 = Pack16(unit, index=4)
        self.pack_5 = PackSoc(unit, index=5)
        self.pack_6 = PackSoc(unit, index=6)


class VenusA(VenusDevice):
    """A Venus A: up to six 13-cell packs."""

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.battery = Battery(unit)
        self.grid = Grid(unit)
        self.offgrid = Offgrid(unit)
        self.temperatures = Temperatures(unit)
        self.control = Control(unit)
        self.mppt = Mppt(unit)
        self.identity = Identity(unit)
        self.versions = Versions(unit)
        self.comms = Comms(unit)
        self.battery_info = PackBatteryInfo(unit)
        self.pack_1 = Pack13(unit, index=1)
        self.pack_2 = Pack13(unit, index=2)
        self.pack_3 = Pack13(unit, index=3)
        self.pack_4 = Pack13(unit, index=4)
        self.pack_5 = Pack13(unit, index=5)
        self.pack_6 = Pack13(unit, index=6)

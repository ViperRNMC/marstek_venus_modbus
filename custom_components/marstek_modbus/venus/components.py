"""The sub-systems of a Marstek Venus battery, one Component each.

The plain classes describe the register layout that Venus E v3, D and A share.
Classes prefixed ``EV12`` move fields to where Venus E v1/v2 keeps them.
"""

from __future__ import annotations

from modbus_connection.model import (
    Component,
    gauge,
    int32,
    integer,
    raw_register,
    uint32,
)
from modbus_connection.model.fields import IPv4Field

from .fields import ascii_string, mac_address

PACK_STRIDE = 100
SCHEDULE_STRIDE = 5


class VenusComponent(Component):
    """A sub-system read in blocks of adjacent registers only.

    Which unmapped registers the firmware answers is not known, so a read
    never bridges a hole in the layout.
    """

    max_gap = 1


class Battery(VenusComponent):
    """What the battery is doing now."""

    battery_power = integer(30001, unit="W")
    battery_voltage = gauge(30100, 0.01, signed=False, unit="V")
    battery_current = gauge(30101, 0.1, unit="A")
    battery_soc = integer(32104, signed=False, unit="%")


class EV3Battery(Battery):
    battery_soc = gauge(34002, 0.1, signed=False, unit="%")


class EV12Battery(Battery):
    battery_voltage = gauge(32100, 0.01, signed=False, unit="V")
    battery_current = gauge(32101, 0.01, unit="A")
    battery_power = int32(32102, unit="W")


class Grid(VenusComponent):
    """The AC side towards the grid."""

    ac_power = integer(30006, unit="W")
    ac_voltage = gauge(32200, 0.1, signed=False, unit="V")
    ac_frequency = gauge(32204, 0.1, unit="Hz")
    ac_current = gauge(37004, 0.004, unit="A")


class EV12Grid(Grid):
    ac_current = gauge(32201, 0.01, unit="A")
    ac_power = int32(32202, unit="W")
    ac_frequency = gauge(32204, 0.01, unit="Hz")


class Offgrid(VenusComponent):
    """The backup (off-grid) output."""

    ac_offgrid_voltage = gauge(32300, 0.1, signed=False, unit="V")
    ac_offgrid_current = gauge(32301, 0.01, signed=False, unit="A")
    ac_offgrid_power = int32(32302, unit="W")


class EV3Offgrid(Offgrid):
    ac_offgrid_power = integer(32302, unit="W")


class Temperatures(VenusComponent):
    """Internal and cell temperatures."""

    internal_temperature = gauge(35000, 0.1, unit="°C")
    internal_mos1_temperature = gauge(35001, 0.1, unit="°C")
    internal_mos2_temperature = gauge(35002, 0.1, unit="°C")
    max_cell_temperature = gauge(35010, 0.1, unit="°C")
    min_cell_temperature = gauge(35011, 0.1, unit="°C")


class EV12Temperatures(Temperatures):
    max_cell_temperature = integer(35010, unit="°C")
    min_cell_temperature = integer(35011, unit="°C")


class Inverter(VenusComponent):
    """The inverter state machine."""

    inverter_state = integer(35100, signed=False)


class Cells(VenusComponent):
    """The extremes of the cell voltages."""

    max_cell_voltage = gauge(37007, 0.001, unit="V")
    min_cell_voltage = gauge(37008, 0.001, unit="V")


class Network(VenusComponent):
    """The communication module's link state."""

    wifi_status = integer(30300, signed=False)
    bluetooth_status = integer(30301, signed=False)
    cloud_status = integer(30302, signed=False)
    wifi_signal_strength = gauge(30303, -1, signed=False, unit="dBm")


class Alarms(VenusComponent):
    """The first word of the alarm and fault bitmasks."""

    alarm_status = raw_register(36000)
    fault_status = raw_register(36100)


class Mppt(VenusComponent):
    """The four solar inputs of a Venus D or A."""

    mppt1_voltage = gauge(30020, 0.1, signed=False, unit="V")
    mppt2_voltage = gauge(30021, 0.1, signed=False, unit="V")
    mppt3_voltage = gauge(30022, 0.1, signed=False, unit="V")
    mppt4_voltage = gauge(30023, 0.1, signed=False, unit="V")
    mppt1_current = gauge(30024, 0.1, signed=False, unit="A")
    mppt2_current = gauge(30025, 0.1, signed=False, unit="A")
    mppt3_current = gauge(30026, 0.1, signed=False, unit="A")
    mppt4_current = gauge(30027, 0.1, signed=False, unit="A")
    mppt1_power = gauge(30037, 0.1, signed=False, unit="W")
    mppt2_power = gauge(30038, 0.1, signed=False, unit="W")
    mppt3_power = gauge(30039, 0.1, signed=False, unit="W")
    mppt4_power = gauge(30040, 0.1, signed=False, unit="W")

    @property
    def solar_power_total(self) -> float | None:
        """The power of all four inputs together."""
        powers = (
            self.mppt1_power,
            self.mppt2_power,
            self.mppt3_power,
            self.mppt4_power,
        )
        if any(power is None for power in powers):
            return None
        return round(sum(powers), 2)


class Control(VenusComponent):
    """What the battery is told to do."""

    backup_function = integer(41200, signed=False, writable=True)
    rs485_control_mode = integer(42000, signed=False, writable=True)
    force_mode = integer(42010, signed=False, writable=True)
    charge_to_soc = integer(42011, signed=False, writable=True, unit="%")
    set_charge_power = integer(42020, signed=False, writable=True, unit="W")
    set_discharge_power = integer(42021, signed=False, writable=True, unit="W")
    user_work_mode = integer(43000, signed=False, writable=True)
    max_charge_power = integer(44002, signed=False, writable=True, unit="W")
    max_discharge_power = integer(44003, signed=False, writable=True, unit="W")


class EV12Control(Control):
    discharge_limit_mode = integer(41010, signed=False)
    charging_cutoff_capacity = gauge(44000, 0.1, signed=False, writable=True, unit="%")
    discharging_cutoff_capacity = gauge(
        44001, 0.1, signed=False, writable=True, unit="%"
    )
    grid_standard = integer(44100, signed=False, writable=True)


class Schedule(VenusComponent):
    """One of the six time-of-use schedules, placed by ``index``."""

    days = integer(43100, signed=False, writable=True, stride=SCHEDULE_STRIDE)
    start = integer(43101, signed=False, writable=True, stride=SCHEDULE_STRIDE)
    end = integer(43102, signed=False, writable=True, stride=SCHEDULE_STRIDE)
    mode = integer(43103, writable=True, stride=SCHEDULE_STRIDE)
    enabled = integer(43104, signed=False, writable=True, stride=SCHEDULE_STRIDE)


class Commands(VenusComponent):
    """Write-only commands. Never polled."""

    reset_device = integer(41000, signed=False, writable=True)
    factory_reset = integer(41001, signed=False, writable=True)


class Identity(VenusComponent):
    """The name and bus address of the battery."""

    device_name = ascii_string(31000, 10)
    modbus_address = integer(41100, signed=False)


class EV12Identity(Identity):
    sn_code = ascii_string(31200, 10)


def ems_version_number(raw: int) -> int | float:
    """Decode the EMS version: four digits end in a decimal (1476 is 147.6)."""
    if raw < 1000:
        return raw
    value = raw / 10
    return int(value) if value.is_integer() else value


def _ems_version_text(raw: int) -> str:
    return f"{raw // 10}.{raw % 10}" if raw >= 1000 else str(raw)


class Versions(VenusComponent):
    """Firmware versions of the EMS, VMS and BMS."""

    ems_version = integer(30200, signed=False)
    vms_version = integer(30202, signed=False)
    bms_version = integer(30204, signed=False)

    @property
    def firmware_version(self) -> str | None:
        """The combined version, as the vendor app shows it (V147.6.117.112)."""
        if self.ems_version is None or self.vms_version is None:
            return None
        if self.bms_version is None:
            return None
        ems = _ems_version_text(self.ems_version)
        return f"V{ems}.{self.vms_version}.{self.bms_version}"


class EV12Versions(VenusComponent):
    """Firmware versions of a Venus E v1/v2."""

    software_version = gauge(31100, 0.01, signed=False)
    ems_version = integer(31101, signed=False)
    bms_version = integer(31102, signed=False)

    @property
    def firmware_version(self) -> str | None:
        """The combined version, as the vendor app shows it (V147.6.112)."""
        if self.ems_version is None or self.bms_version is None:
            return None
        return f"V{_ems_version_text(self.ems_version)}.{self.bms_version}"


class Comms(VenusComponent):
    """The communication module."""

    ble_mac_address = mac_address(30304)
    comm_module_firmware = ascii_string(30350, 6)


class EV3Comms(Comms):
    device_ip = IPv4Field(30400, count=2)
    gateway_ip = IPv4Field(30402, count=2)


class EV12Comms(Comms):
    ble_mac_address = mac_address(30402)
    comm_module_firmware = ascii_string(30800, 6)


class BatteryInfo(VenusComponent):
    """Slow-changing battery figures."""

    battery_total_energy = gauge(32105, 0.001, signed=False, unit="kWh")


class PackBatteryInfo(BatteryInfo):
    battery_cycle_count = integer(34003, signed=False)


class Energy(VenusComponent):
    """Energy counters."""

    total_charging_energy = uint32(33000, scale=0.01, unit="kWh")
    total_discharging_energy = int32(33002, scale=0.01, unit="kWh")
    total_daily_charging_energy = uint32(33004, scale=0.01, unit="kWh")
    total_daily_discharging_energy = int32(33006, scale=0.01, unit="kWh")
    total_monthly_charging_energy = uint32(33008, scale=0.01, unit="kWh")
    total_monthly_discharging_energy = int32(33010, scale=0.01, unit="kWh")


class PackSoc(VenusComponent):
    """A battery pack's state of charge, placed by ``index``."""

    soc = gauge(34002, 0.1, signed=False, stride=PACK_STRIDE, unit="%")


class PackCells13(VenusComponent):
    """The cell voltages of a 13-cell pack, placed by ``index``."""

    cell_1_voltage = gauge(34018, 0.001, stride=PACK_STRIDE, unit="V")
    cell_2_voltage = gauge(34019, 0.001, stride=PACK_STRIDE, unit="V")
    cell_3_voltage = gauge(34020, 0.001, stride=PACK_STRIDE, unit="V")
    cell_4_voltage = gauge(34021, 0.001, stride=PACK_STRIDE, unit="V")
    cell_5_voltage = gauge(34022, 0.001, stride=PACK_STRIDE, unit="V")
    cell_6_voltage = gauge(34023, 0.001, stride=PACK_STRIDE, unit="V")
    cell_7_voltage = gauge(34024, 0.001, stride=PACK_STRIDE, unit="V")
    cell_8_voltage = gauge(34025, 0.001, stride=PACK_STRIDE, unit="V")
    cell_9_voltage = gauge(34026, 0.001, stride=PACK_STRIDE, unit="V")
    cell_10_voltage = gauge(34027, 0.001, stride=PACK_STRIDE, unit="V")
    cell_11_voltage = gauge(34028, 0.001, stride=PACK_STRIDE, unit="V")
    cell_12_voltage = gauge(34029, 0.001, stride=PACK_STRIDE, unit="V")
    cell_13_voltage = gauge(34030, 0.001, stride=PACK_STRIDE, unit="V")


class PackCells16(PackCells13):
    """The cell voltages of a 16-cell pack, placed by ``index``."""

    cell_14_voltage = gauge(34031, 0.001, stride=PACK_STRIDE, unit="V")
    cell_15_voltage = gauge(34032, 0.001, stride=PACK_STRIDE, unit="V")
    cell_16_voltage = gauge(34033, 0.001, stride=PACK_STRIDE, unit="V")


class Pack13(PackSoc, PackCells13):
    """A 13-cell pack with its state of charge."""


class Pack16(PackSoc, PackCells16):
    """A 16-cell pack with its state of charge."""

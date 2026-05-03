"""
coordinator.py  –  Marstek Venus Modbus DataUpdateCoordinator (tmodbus edition).

Changes vs. the original pymodbus version
------------------------------------------
- AsyncModbusTcpClient (pymodbus) → create_async_tcp_client (tmodbus)
- response.registers[n]          → list[int] returned directly
- response.isError() / exception → TModbusError exception hierarchy
- All pymodbus imports removed
- modbus_client helpers used for every register access
- Auto-reconnect is handled by tmodbus natively (no manual reconnect logic needed)
- Lock-race/hung-write fix from sphings79#184 preserved via asyncio.Lock + timeout

Drop this file into:
  custom_components/marstek_modbus/coordinator.py
"""

from __future__ import annotations

import asyncio
import logging
import struct
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_UNIT_ID,
    CONF_VERSION,
    VERSION_E_V3,
    SCAN_INTERVAL_HIGH,
    SCAN_INTERVAL_MEDIUM,
    SCAN_INTERVAL_LOW,
    SCAN_INTERVAL_VERY_LOW,
    DEFAULT_SCAN_INTERVAL_HIGH,
    DEFAULT_SCAN_INTERVAL_MEDIUM,
    DEFAULT_SCAN_INTERVAL_LOW,
    DEFAULT_SCAN_INTERVAL_VERY_LOW,
)
from .modbus_client import (
    create_client,
    disconnect_client,
    read_uint16,
    read_int16,
    read_uint32,
    read_int32,
    read_string,
    read_registers,
    write_register as _write_register,
    write_registers as _write_registers,
)
from tmodbus.client import AsyncModbusClient
from tmodbus.exceptions import TModbusError

_LOGGER = logging.getLogger(__name__)

# Timeout for acquiring the write lock (seconds).
# Prevents permanent freeze if a write hangs (sphings79 fix #184).
_WRITE_LOCK_TIMEOUT = 10.0


class MarstekCoordinator(DataUpdateCoordinator):
    """Coordinator that polls Marstek Venus battery registers via tmodbus."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        host: str,
        port: int,
        unit_id: int,
        version: str,
        options: dict[str, Any],
    ) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.version = version
        self._options = options
        self._client: AsyncModbusClient | None = None
        # Single lock shared by reads AND writes to serialise all Modbus traffic.
        self._lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=options.get(SCAN_INTERVAL_HIGH, DEFAULT_SCAN_INTERVAL_HIGH)
            ),
        )

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def async_connect(self) -> None:
        """Open the tmodbus TCP connection. Raises ConfigEntryNotReady on failure."""
        try:
            self._client = await create_client(
                self.host,
                self.port,
                self.unit_id,
                timeout=5.0,
            )
        except (ConnectionError, OSError, TModbusError) as exc:
            raise ConfigEntryNotReady(
                f"Cannot connect to Marstek at {self.host}:{self.port} – {exc}"
            ) from exc

    async def async_disconnect(self) -> None:
        """Close the tmodbus connection cleanly."""
        await disconnect_client(self._client)
        self._client = None

    # ------------------------------------------------------------------
    # DataUpdateCoordinator main update method
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all register data from the battery. Called by the coordinator."""
        if self._client is None:
            # Connection was lost; try to reconnect once.
            _LOGGER.warning("Modbus client is None – attempting reconnect")
            await self.async_connect()

        try:
            async with asyncio.timeout(30):
                async with self._lock:
                    return await self._fetch_all()
        except TimeoutError as exc:
            raise UpdateFailed("Timeout while polling Marstek registers") from exc
        except (ConnectionError, OSError, TModbusError) as exc:
            # tmodbus already tries to reconnect; if it still fails we mark data stale.
            raise UpdateFailed(f"Modbus communication error: {exc}") from exc

    # ------------------------------------------------------------------
    # Register reading  (version-aware)
    # ------------------------------------------------------------------

    async def _fetch_all(self) -> dict[str, Any]:
        """Read all registers for the configured firmware version."""
        client = self._client
        assert client is not None

        is_v3 = self.version == VERSION_E_V3

        data: dict[str, Any] = {}

        # ── Real-time / high-priority ────────────────────────────────────
        data["battery_voltage"]     = await read_uint16(client, 32100) * 0.01
        data["battery_current"]     = await read_int16(client,  32101) * 0.01
        data["battery_soc"]         = await read_uint16(client, 32104 if not is_v3 else 37005)
        data["battery_total_energy"] = await read_uint16(client, 32105) * 0.001

        if is_v3:
            data["battery_power"] = await read_int16(client, 30001)
            data["ac_power"]      = await read_int16(client, 30006)
        else:
            data["battery_power"] = await read_int32(client, 32102)
            data["ac_power"]      = await read_int32(client, 32202)

        data["ac_voltage"]     = await read_uint16(client, 32200) * 0.1
        data["ac_current"]     = await read_int16(client,  32201) * 0.01
        data["ac_frequency"]   = await read_int16(client,  32204) * 0.01

        data["ac_offgrid_voltage"] = await read_uint16(client, 32300) * 0.1
        data["ac_offgrid_current"] = await read_uint16(client, 32301) * 0.01
        if not is_v3:
            data["ac_offgrid_power"] = await read_int32(client, 32302)

        # ── State / control registers ────────────────────────────────────
        data["inverter_state"]      = await read_uint16(client, 35100)
        data["rs485_control_mode"]  = await read_uint16(client, 42000)
        data["force_mode"]          = await read_uint16(client, 42010)
        data["charge_to_soc"]       = await read_uint16(client, 42011)
        data["forcible_charge_power"]    = await read_uint16(client, 42020)
        data["forcible_discharge_power"] = await read_uint16(client, 42021)
        data["user_work_mode"]      = await read_uint16(client, 43000)
        data["backup_function"]     = await read_uint16(client, 41200)
        data["max_charge_power"]    = await read_uint16(client, 44002)
        data["max_discharge_power"] = await read_uint16(client, 44003)

        if not is_v3:
            data["charging_cutoff_capacity"]    = await read_uint16(client, 44000) * 0.1
            data["discharging_cutoff_capacity"] = await read_uint16(client, 44001) * 0.1
            data["grid_standard"]               = await read_uint16(client, 44100)
            data["discharge_limit"]             = await read_uint16(client, 41010)

        # ── Medium priority – temperatures ───────────────────────────────
        data["internal_temperature"]  = await read_int16(client, 35000) * 0.1
        data["internal_mos1_temp"]    = await read_int16(client, 35001) * 0.1
        data["internal_mos2_temp"]    = await read_int16(client, 35002) * 0.1
        data["max_cell_temperature"]  = await read_int16(client, 35010)
        data["min_cell_temperature"]  = await read_int16(client, 35011)
        data["max_cell_voltage"]      = await read_uint16(client, 37007) * 0.001
        data["min_cell_voltage"]      = await read_uint16(client, 37008) * 0.001

        # ── Low priority – energy totals ─────────────────────────────────
        data["total_charging_energy"]          = await read_uint32(client, 33000) * 0.01
        data["total_discharging_energy"]       = await read_uint32(client, 33002) * 0.01
        data["daily_charging_energy"]          = await read_uint32(client, 33004) * 0.01
        data["daily_discharging_energy"]       = await read_uint32(client, 33006) * 0.01
        data["monthly_charging_energy"]        = await read_uint32(client, 33008) * 0.01
        data["monthly_discharging_energy"]     = await read_uint32(client, 33010) * 0.01

        # ── Very low priority – device info ──────────────────────────────
        data["wifi_status"]   = await read_uint16(client, 30300)
        data["cloud_status"]  = await read_uint16(client, 30302)
        data["wifi_signal"]   = await read_int16(client,  30303)  # signed dBm
        data["modbus_address"] = await read_uint16(client, 41100)

        if is_v3:
            data["bms_version"] = await read_uint16(client, 30204)
            data["vms_version"] = await read_uint16(client, 30202)
            data["ems_version"] = await read_uint16(client, 30200)
            data["mac_address"] = await read_string(client, 30304, 6)
            data["comm_firmware"] = await read_string(client, 30350, 6)
        else:
            data["bms_version"] = await read_uint16(client, 30399)
            data["ems_version"] = await read_uint16(client, 30401)
            data["mac_address"] = await read_string(client, 30402, 6)
            data["comm_firmware"] = await read_string(client, 30800, 6)
            data["software_version"] = await read_uint16(client, 31100)
            try:
                data["sn_code"] = await read_string(client, 31200, 10)
            except (OSError, ConnectionError):
                data["sn_code"] = ""

        try:
            data["device_name"] = await read_string(client, 31000, 10)
        except (OSError, ConnectionError):
            data["device_name"] = ""

        # ── Alarms / Faults ──────────────────────────────────────────────
        if not is_v3:
            alarm_regs = await read_registers(client, 36000, 2)
            data["alarm_status"] = (alarm_regs[0] << 16) | alarm_regs[1]

            fault_regs = await read_registers(client, 36100, 4)
            data["fault_status"] = (
                (fault_regs[0] << 48)
                | (fault_regs[1] << 32)
                | (fault_regs[2] << 16)
                | fault_regs[3]
            )

        # ── Calculated sensors ──────────────────────────────────────────
        data.update(self._calculate_derived(data))

        return data

    # ------------------------------------------------------------------
    # Derived / calculated sensors
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_derived(data: dict[str, Any]) -> dict[str, Any]:
        derived: dict[str, Any] = {}

        total_charge    = data.get("total_charging_energy", 0)
        total_discharge = data.get("total_discharging_energy", 0)
        monthly_charge    = data.get("monthly_charging_energy", 0)
        monthly_discharge = data.get("monthly_discharging_energy", 0)
        soc = data.get("battery_soc", 0)
        total_energy = data.get("battery_total_energy", 0)

        # Round-trip efficiency (total)
        if total_charge and total_charge > 0:
            derived["roundtrip_efficiency_total"] = round(
                (total_discharge / total_charge) * 100, 1
            )
        else:
            derived["roundtrip_efficiency_total"] = None

        # Round-trip efficiency (monthly)
        if monthly_charge and monthly_charge > 0:
            derived["roundtrip_efficiency_monthly"] = round(
                (monthly_discharge / monthly_charge) * 100, 1
            )
        else:
            derived["roundtrip_efficiency_monthly"] = None

        # Stored energy
        if soc and total_energy:
            derived["stored_energy"] = round(soc / 100 * total_energy, 3)
        else:
            derived["stored_energy"] = None

        return derived

    # ------------------------------------------------------------------
    # Write interface  (used by switches, numbers, selects, buttons)
    # ------------------------------------------------------------------

    async def async_write_register(self, address: int, value: int) -> None:
        """
        Write a single Modbus register.

        Uses the same shared lock as the polling cycle.
        Lock acquisition is time-bounded to avoid permanent freezes
        (sphings79 fix for issue #184).
        """
        if self._client is None:
            raise UpdateFailed("Cannot write – Modbus client is not connected")

        try:
            async with asyncio.timeout(_WRITE_LOCK_TIMEOUT):
                async with self._lock:
                    await _write_register(self._client, address, value)
        except TimeoutError as exc:
            raise UpdateFailed(
                f"Timeout acquiring write lock for reg {address}"
            ) from exc
        except (ConnectionError, OSError, TModbusError) as exc:
            raise UpdateFailed(
                f"Failed to write Modbus register {address} = {value}: {exc}"
            ) from exc

    async def async_write_registers(self, address: int, values: list[int]) -> None:
        """Write multiple consecutive Modbus registers (FC 16)."""
        if self._client is None:
            raise UpdateFailed("Cannot write – Modbus client is not connected")

        try:
            async with asyncio.timeout(_WRITE_LOCK_TIMEOUT):
                async with self._lock:
                    await _write_registers(self._client, address, values)
        except TimeoutError as exc:
            raise UpdateFailed(
                f"Timeout acquiring write lock for regs at {address}"
            ) from exc
        except (ConnectionError, OSError, TModbusError) as exc:
            raise UpdateFailed(
                f"Failed to write Modbus registers at {address}: {exc}"
            ) from exc

"""
coordinator.py  –  Marstek Venus Modbus DataUpdateCoordinator
                   (tmodbus + YAML-driven batch block-read)

Interface expected by __init__.py:
    coordinator = MarstekCoordinator(hass, entry)
    await coordinator.async_load_registers(version_string)
    await coordinator.async_init()
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_close()
    coordinator._update_scan_intervals(scan_interval_dict)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVALS
from .helpers.modbus_client import (
    create_client,
    disconnect_client,
    batch_read,
    extract_typed_value,
    write_register as _write_register,
    write_registers as _write_registers,
)
from tmodbus.client import AsyncModbusClient
from tmodbus.exceptions import TModbusError

_LOGGER = logging.getLogger(__name__)

_WRITE_LOCK_TIMEOUT = 10.0


# Map SUPPORTED_VERSIONS display strings → YAML filename in registers/
_VERSION_YAML: dict[str, str] = {
    "e v1/v2": "e_v12.yaml",
    "e v3":    "e_v3.yaml",
    "d":       "d.yaml",
    "a":       "a.yaml",
}

_READABLE_SECTIONS = (
    "SENSOR_DEFINITIONS",
    "BINARY_SENSOR_DEFINITIONS",
    "SELECT_DEFINITIONS",
    "SWITCH_DEFINITIONS",
    "NUMBER_DEFINITIONS",
)

_DEFAULT_COUNT: dict[str, int] = {
    "uint16": 1, "int16": 1, "uint32": 2, "int32": 2, "char": 1,
}

CONF_UNIT_ID    = "unit_id"
CONF_DEVICE_VER = "device_version"


@dataclass(slots=True)
class ReadableEntry:
    key: str; address: int; data_type: str; count: int; scale: float; priority: str


def _load_groups(yaml_path: Path) -> dict[str, list[ReadableEntry]]:
    with open(yaml_path, encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    groups: dict[str, list[ReadableEntry]] = {
        "high": [], "medium": [], "low": [], "very_low": []
    }
    skipped: list[str] = []

    for section in _READABLE_SECTIONS:
        sec = raw.get(section)
        if not isinstance(sec, dict):
            continue
        for key, entry in sec.items():
            if not isinstance(entry, dict) or "register" not in entry:
                continue

            # ── Only poll registers that are enabled by default ───────────
            # Registers with enabled_by_default: false may not be supported by
            # all device variants and can cause connection timeouts if polled
            # unconditionally.  Entities that the user explicitly enables in HA
            # are added to the polling groups afterwards via
            # async_register_enabled_entities() which reads the entity registry.
            if not entry.get("enabled_by_default", True):
                continue
            # ────────────────────────────────────────────────────────────

            raw_prio = str(entry.get("scan_interval", "")).strip().lower()
            raw_prio = raw_prio.replace(" ", "_").replace("-", "_")

            if raw_prio not in groups:
                if raw_prio == "":
                    # No scan_interval defined → use "very_low" as safe default
                    priority = "very_low"
                else:
                    # Unknown value → skip and warn
                    skipped.append(f"{key}(unknown:{raw_prio})")
                    continue
            else:
                priority = raw_prio

            data_type = str(entry.get("data_type", "uint16")).lower()
            if data_type not in _DEFAULT_COUNT:
                data_type = "uint16"
            count = int(entry.get("count", _DEFAULT_COUNT[data_type]))
            if data_type in ("uint16", "int16"):
                count = 1
            groups[priority].append(ReadableEntry(
                key=key, address=int(entry["register"]),
                data_type=data_type, count=count,
                scale=float(entry.get("scale", 1.0)), priority=priority,
            ))

    if skipped:
        _LOGGER.warning("Skipped entries with unknown scan_interval value: %s", skipped)

    total = sum(len(v) for v in groups.values())
    _LOGGER.debug(
        "Loaded %d register entries from %s (high=%d medium=%d low=%d very_low=%d)",
        total, yaml_path.name,
        len(groups["high"]), len(groups["medium"]),
        len(groups["low"]), len(groups["very_low"]),
    )
    return groups


def _addresses_for(entries: list[ReadableEntry]) -> list[int]:
    addrs: list[int] = []
    for e in entries:
        addrs.extend(range(e.address, e.address + e.count))
    return addrs


def _ticks_for(interval_s: float, tick_s: float) -> int:
    return max(1, round(interval_s / tick_s))


class MarstekCoordinator(DataUpdateCoordinator):
    """Polls Marstek battery registers using tmodbus block-read."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.host    = entry.data.get(CONF_HOST, "")
        self.port    = int(entry.data.get(CONF_PORT, 502))
        self.unit_id = int(entry.data.get(CONF_UNIT_ID, 1))

        self._entry  = entry
        self._client: AsyncModbusClient | None = None
        self._lock   = asyncio.Lock()
        self._tick   = 0

        self._groups:   dict[str, list[ReadableEntry]] = {
            "high": [], "medium": [], "low": [], "very_low": []
        }
        self._raw_yaml: dict[str, Any] = {}

        # Bad-gap tracking: when a batch_read block fails, the specific gaps
        # between consecutive needed addresses inside that block are recorded
        # here. _build_blocks will avoid bridging these gaps in future requests
        # so the device is never asked to read unsupported register ranges again.
        # The YAML registers themselves are NEVER removed – only the bridging
        # of gaps between them is suppressed.
        self._bad_gaps: set[tuple[int, int]] = set()
        # Flag set by async_register_enabled_entities() to ensure the very_low
        # group is polled once immediately after user-enabled entities are added,
        # regardless of when tick 1 fired relative to entity registration.
        self._needs_very_low_poll: bool = False
        # Gaps that have been successfully bridged at least once.
        # These are protected from bad_gaps poisoning during TCP outages:
        # if a connection drop causes ALL blocks to fail, we do not want
        # previously working gaps to be recorded as bad.
        self._good_gaps: set[tuple[int, int]] = set()


        # Registries used by entity classes to store metadata on the coordinator.
        self._entity_types: dict[str, str] = {}
        self._scales: dict[str, float] = {}
        self._dependencies: dict = {}
        self._precision: dict = {}
        self._unit: dict = {}
        self._device_class: dict = {}
        self._state_class: dict = {}
        self._enabled_by_default: dict = {}
        self._icon: dict = {}
        self._category: dict = {}

        # Merge defaults with any saved options
        opts = {**DEFAULT_SCAN_INTERVALS, **entry.options}
        high = opts.get("high", DEFAULT_SCAN_INTERVALS["high"])
        self._interval_high  = high
        self._medium_every   = _ticks_for(opts.get("medium",   DEFAULT_SCAN_INTERVALS["medium"]),   high)
        self._low_every      = _ticks_for(opts.get("low",      DEFAULT_SCAN_INTERVALS["low"]),      high)
        self._very_low_every = _ticks_for(opts.get("very_low", DEFAULT_SCAN_INTERVALS["very_low"]), high)

        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=high),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def async_load_registers(self, version_string: str | None) -> None:
        """Load register YAML for the given device version string."""
        if not version_string:
            _LOGGER.warning("No device_version set – skipping register load")
            return

        yaml_file = _VERSION_YAML.get(version_string.strip().lower())
        if yaml_file is None:
            _LOGGER.warning(
                "Unknown device_version '%s'. Known: %s",
                version_string, list(_VERSION_YAML),
            )
            return

        yaml_path = Path(__file__).parent / "registers" / yaml_file
        if not yaml_path.exists():
            _LOGGER.error("Register file not found: %s", yaml_path)
            return

        # File I/O must run in the executor – HA forbids blocking calls in the event loop
        def _load() -> tuple[dict, dict]:
            with open(yaml_path, encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
            return _load_groups(yaml_path), raw

        self._groups, self._raw_yaml = await self.hass.async_add_executor_job(_load)

    async def async_init(self) -> None:
        """Connect to the Modbus gateway. Raises ConfigEntryNotReady on failure."""
        try:
            self._client = await create_client(
                self.host, self.port, self.unit_id, timeout=5.0
            )
        except (ConnectionError, OSError, TModbusError) as exc:
            raise ConfigEntryNotReady(
                f"Cannot connect to Marstek at {self.host}:{self.port} – {exc}"
            ) from exc

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        await disconnect_client(self._client)
        self._client = None

    def add_to_polling(self, key: str, definition: dict) -> None:
        """
        Dynamically add a single register definition to the polling groups.

        Called for entities that are enabled in HA but have
        enabled_by_default: false in their YAML definition.
        Silently skips entries that are already polled.
        """
        # Skip if already in any group
        for group in self._groups.values():
            if any(e.key == key for e in group):
                return

        if "register" not in definition:
            return

        # Force very_low for all dynamically-registered non-default entities.
        # Their YAML scan_interval may be "high" or "medium", but reading
        # registers the device does not support causes per-register fallback
        # reads of up to 5 s each.  At very_low (default 180 s) even a full
        # block of 16 unsupported registers (16 × 5 s = 80 s) only blocks
        # the coordinator once every three minutes instead of every 10–30 s.
        priority = "very_low"

        data_type = str(definition.get("data_type", "uint16")).lower()
        if data_type not in _DEFAULT_COUNT:
            data_type = "uint16"
        count = int(definition.get("count", _DEFAULT_COUNT[data_type]))
        if data_type in ("uint16", "int16"):
            count = 1

        entry = ReadableEntry(
            key=key,
            address=int(definition["register"]),
            data_type=data_type,
            count=count,
            scale=float(definition.get("scale", 1.0)),
            priority=priority,
        )
        self._groups[priority].append(entry)
        _LOGGER.debug(
            "Dynamically added '%s' (reg %s) to %s polling group",
            key, definition["register"], priority,
        )

    async def async_register_enabled_entities(self) -> None:
        """
        Inspect the HA entity registry and add any enabled-but-not-default
        entities to the coordinator polling groups.

        Called once from async_setup_entry after all platforms have been
        forwarded so that async_added_to_hass has completed for all entities.
        """
        from homeassistant.helpers import entity_registry as er

        ent_reg = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(ent_reg, self._entry.entry_id)

        # Build a flat lookup of all YAML register definitions
        all_defs: dict[str, dict] = {}
        for section in _READABLE_SECTIONS:
            sec = self._raw_yaml.get(section)
            if isinstance(sec, dict):
                all_defs.update(sec)

        added = 0
        for reg_entry in entries:
            if reg_entry.disabled:
                continue  # entity is disabled in HA – skip

            # unique_id format: "{entry_id}_{key}"
            prefix = f"{self._entry.entry_id}_"
            if not reg_entry.unique_id.startswith(prefix):
                continue
            key = reg_entry.unique_id[len(prefix):]

            defn = all_defs.get(key)
            if defn is None:
                continue  # not a polled register (e.g. calculated sensor)
            if defn.get("enabled_by_default", True):
                continue  # already in polling groups from _load_groups

            self.add_to_polling(key, defn)
            added += 1

        _LOGGER.debug(
            "async_register_enabled_entities: added %d non-default enabled entities "
            "to very_low polling group",
            added,
        )
        if added:
            # Signal _fetch_tick to include very_low on the next poll so that
            # user-enabled entities get an immediate value even if tick 1 fired
            # (via select platform's update_before_add=True) before this method
            # ran and therefore polled very_low without these entries.
            self._needs_very_low_poll = True

    def _update_scan_intervals(self, intervals: dict[str, int]) -> None:
        """Update polling intervals at runtime (called from options flow)."""
        high = intervals.get("high", self._interval_high)
        self._interval_high  = high
        self._medium_every   = _ticks_for(intervals.get("medium",   DEFAULT_SCAN_INTERVALS["medium"]),   high)
        self._low_every      = _ticks_for(intervals.get("low",      DEFAULT_SCAN_INTERVALS["low"]),      high)
        self._very_low_every = _ticks_for(intervals.get("very_low", DEFAULT_SCAN_INTERVALS["very_low"]), high)
        self.update_interval = timedelta(seconds=high)
        _LOGGER.debug(
            "Scan intervals updated: high=%ds medium_every=%d low_every=%d very_low_every=%d",
            high, self._medium_every, self._low_every, self._very_low_every,
        )

    # ── DataUpdateCoordinator ─────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, Any]:
        if self._client is None:
            _LOGGER.warning("Modbus client is None – attempting reconnect")
            await self.async_init()

        self._tick += 1
        _LOGGER.debug("Coordinator poll tick %d", self._tick)

        try:
            # 120 s gives enough headroom even when many unsupported registers
            # each hit the 5 s per-register fallback timeout
            # (e.g. 16 cell-voltage registers × 5 s = 80 s).
            async with asyncio.timeout(120):
                async with self._lock:
                    return await self._fetch_tick()
        except TimeoutError as exc:
            raise UpdateFailed("Timeout polling Marstek registers") from exc
        except (ConnectionError, OSError, TModbusError) as exc:
            raise UpdateFailed(f"Modbus communication error: {exc}") from exc

    async def _fetch_tick(self) -> dict[str, Any]:
        client = self._client
        assert client is not None

        data: dict[str, Any] = dict(self.data) if self.data else {}

        if self._tick == 1:
            # ── Initial full poll ────────────────────────────────────────────
            # Poll all 4 groups once so every entity has an immediate value.
            # We deliberately poll group-by-group (not a single merged list)
            # so that failures in very_low (user-enabled non-default registers
            # that may not exist on this device variant) cannot contaminate
            # the good_gaps of the vetted default registers in high/medium/low.
            # Each group gets its own batch_read call with its own block layout.
            _LOGGER.debug("Tick 1: initial full poll of all groups")
            due = ["high", "medium", "low", "very_low"]
        else:
            due = ["high"]
            if self._tick % self._medium_every == 0:
                due.append("medium")
            if self._tick % self._low_every == 0:
                due.append("low")
            if self._tick % self._very_low_every == 0:
                due.append("very_low")
            # If async_register_enabled_entities() added user-enabled entries to
            # the very_low group AFTER tick 1 already fired without them, poll
            # very_low once immediately so those entities get values right away.
            if self._needs_very_low_poll and "very_low" not in due:
                due.append("very_low")
                self._needs_very_low_poll = False
                _LOGGER.debug(
                    "Tick %d: adding one-shot very_low poll for newly registered "
                    "user-enabled entities",
                    self._tick,
                )

        _LOGGER.debug("Tick %d polling groups: %s", self._tick, due)

        for priority in due:
            entries = self._groups[priority]
            if not entries:
                continue
            try:
                cache = await batch_read(
                    client,
                    _addresses_for(entries),
                    bad_gaps=self._bad_gaps,
                    good_gaps=self._good_gaps,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "batch_read for %s group failed, skipping: %s", priority, exc
                )
                continue
            for entry in entries:
                value = extract_typed_value(
                    cache, entry.address, entry.data_type, entry.count, entry.scale
                )
                if value is not None:
                    data[entry.key] = value
                elif entry.key not in data:
                    data[entry.key] = None

        data.update(_calculate_derived(data, self._raw_yaml))
        return data



    # ── Public accessors ──────────────────────────────────────────────────

    @property
    def raw_yaml(self) -> dict[str, Any]:
        return self._raw_yaml

    # ── YAML section properties (used by entity platform builders) ────────

    def _yaml_section_as_list(self, section: str) -> list[dict]:
        """Return a YAML section as list[dict], each with "key" injected."""
        return [
            {"key": k, **v}
            for k, v in self._raw_yaml.get(section, {}).items()
            if isinstance(v, dict)
        ]

    @property
    def SENSOR_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("SENSOR_DEFINITIONS")

    @property
    def BINARY_SENSOR_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("BINARY_SENSOR_DEFINITIONS")

    @property
    def SELECT_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("SELECT_DEFINITIONS")

    @property
    def SWITCH_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("SWITCH_DEFINITIONS")

    @property
    def NUMBER_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("NUMBER_DEFINITIONS")

    @property
    def BUTTON_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("BUTTON_DEFINITIONS")

    @property
    def EFFICIENCY_SENSOR_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("EFFICIENCY_SENSOR_DEFINITIONS")

    @property
    def STORED_ENERGY_SENSOR_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("STORED_ENERGY_SENSOR_DEFINITIONS")

    @property
    def CYCLE_SENSOR_DEFINITIONS(self) -> list[dict]:
        return self._yaml_section_as_list("CYCLE_SENSOR_DEFINITIONS")

    # ── Write interface ───────────────────────────────────────────────────

    async def async_write_register(self, address: int, value: int) -> None:
        if self._client is None:
            raise UpdateFailed("Cannot write – Modbus client not connected")
        try:
            async with asyncio.timeout(_WRITE_LOCK_TIMEOUT):
                async with self._lock:
                    await _write_register(self._client, address, value)
        except TimeoutError as exc:
            raise UpdateFailed(f"Timeout acquiring write lock for reg {address}") from exc
        except (ConnectionError, OSError, TModbusError) as exc:
            raise UpdateFailed(f"Failed writing reg {address}={value}: {exc}") from exc

    async def async_write_registers(self, address: int, values: list[int]) -> None:
        if self._client is None:
            raise UpdateFailed("Cannot write – Modbus client not connected")
        try:
            async with asyncio.timeout(_WRITE_LOCK_TIMEOUT):
                async with self._lock:
                    await _write_registers(self._client, address, values)
        except TimeoutError as exc:
            raise UpdateFailed(f"Timeout acquiring write lock for regs at {address}") from exc
        except (ConnectionError, OSError, TModbusError) as exc:
            raise UpdateFailed(f"Failed writing regs at {address}: {exc}") from exc

    async def async_write_value(
        self,
        register: int,
        value: int,
        key: str = "",
        scale: float = 1,
        unit: str | None = None,
        entity_type: str = "",
    ) -> bool:
        """
        Write a single raw integer value to a Modbus register.

        This is the unified write entry-point used by all entity platforms
        (switch, select, number, button).  The caller is responsible for
        converting engineering-unit values to raw register integers before
        calling this method.

        Returns True on success, False on failure.
        """
        try:
            await self.async_write_register(register, int(value))
            _LOGGER.debug(
                "async_write_value: key=%s reg=%s raw=%s (scale=%s unit=%s type=%s)",
                key, register, value, scale, unit, entity_type,
            )
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "async_write_value failed: key=%s reg=%s value=%s – %s",
                key, register, value, exc,
            )
            return False

    async def async_read_value(
        self,
        definition: dict,
        key: str,
        track_failure: bool = True,
    ) -> None:
        """
        Re-read a single register and update coordinator.data in place.

        Used by number entities after a failed write to restore the
        actual device state without triggering a full coordinator refresh.
        """
        if self._client is None:
            return
        try:
            from .helpers.modbus_client import batch_read, extract_typed_value

            address = int(definition["register"])
            data_type = str(definition.get("data_type", "uint16")).lower()
            count_map = {"uint16": 1, "int16": 1, "uint32": 2, "int32": 2, "char": 1}
            count = int(definition.get("count", count_map.get(data_type, 1)))
            if data_type in ("uint16", "int16"):
                count = 1
            scale = float(definition.get("scale", 1.0))

            cache = await batch_read(self._client, list(range(address, address + count)), max_gap=0)
            value = extract_typed_value(cache, address, data_type, count, scale)
            if value is not None and isinstance(self.data, dict):
                self.data[key] = value
        except Exception as exc:  # noqa: BLE001
            if track_failure:
                _LOGGER.debug("async_read_value failed for %s: %s", key, exc)


# ---------------------------------------------------------------------------
# Calculated sensors
# ---------------------------------------------------------------------------

def _calculate_derived(data: dict[str, Any], raw_yaml: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, defn in raw_yaml.get("EFFICIENCY_SENSOR_DEFINITIONS", {}).items():
        dep  = defn.get("dependency_keys", {})
        mode = defn.get("mode", "round_trip")
        if mode == "round_trip":
            charge    = data.get(dep.get("charge", "")) or 0.0
            discharge = data.get(dep.get("discharge", "")) or 0.0
            result[key] = round(discharge / charge * 100, 1) if charge > 0 else None
        elif mode == "conversion":
            batt = data.get(dep.get("battery_power", "")) or 0.0
            ac   = data.get(dep.get("ac_power", "")) or 0.0
            result[key] = round(abs(ac / batt) * 100, 1) if batt != 0 else 0.0
        _LOGGER.debug(
            "Calculated value for %s: %s (input values: %s)",
            key, result.get(key), {k: data.get(v) for k, v in dep.items()},
        )

    for key, defn in raw_yaml.get("STORED_ENERGY_SENSOR_DEFINITIONS", {}).items():
        dep      = defn.get("dependency_keys", {})
        soc      = data.get(dep.get("soc", "")) or 0
        capacity = data.get(dep.get("capacity", "")) or 0.0
        result[key] = round(soc / 100 * capacity, 3) if soc and capacity else None
        _LOGGER.debug(
            "Calculated value for %s: %s (input values: %s)",
            key, result.get(key), {k: data.get(v) for k, v in dep.items()},
        )

    for key, defn in raw_yaml.get("CYCLE_SENSOR_DEFINITIONS", {}).items():
        dep       = defn.get("dependency_keys", {})
        discharge = data.get(dep.get("discharge", "")) or 0.0
        capacity  = data.get(dep.get("capacity", "")) or 0.0
        result[key] = round(discharge / capacity, 2) if capacity > 0 else None
        _LOGGER.debug(
            "Calculated value for %s: %s (input values: %s)",
            key, result.get(key), {k: data.get(v) for k, v in dep.items()},
        )

    return result

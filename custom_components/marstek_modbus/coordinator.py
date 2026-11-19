"""Poll a Marstek Venus battery, its fast and slow sub-systems on their own intervals."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta
from functools import partial
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HassJob, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusTimeoutError
from modbus_connection.model import UpdateReport

from .const import DEFAULT_SCAN_INTERVALS, DOMAIN
from .venus import VenusDevice

_LOGGER = logging.getLogger(__name__)

# How long after a write the written sub-system is read back.
POST_WRITE_REFRESH_SECONDS = 3.5
TIMEOUT_RECOVERY_COOLDOWN_SECONDS = 60.0
PARTIAL_TIMEOUT_RECOVERY_THRESHOLD = 3

type MarstekConfigEntry = ConfigEntry[MarstekCoordinator]


def scan_intervals(options: Mapping[str, Any]) -> dict[str, int]:
    """Return the "high" and "low" scan intervals in seconds from entry options.

    Older entries name them "medium" and "very_low".
    """
    legacy = {"high": "medium", "low": "very_low"}
    intervals = dict(DEFAULT_SCAN_INTERVALS)
    for key, old_key in legacy.items():
        value = options.get(key, options.get(old_key))
        if value is None:
            continue
        try:
            intervals[key] = int(value)
        except (TypeError, ValueError):
            _LOGGER.warning("Invalid scan interval for %s: %s", key, value)
    return intervals


class MarstekCoordinator(DataUpdateCoordinator[None]):
    """Poll the fast sub-systems every tick and the slow ones when they are due.

    A tick is the shorter of the two scan intervals. A dropped link is not a
    reload: the next request reconnects, so the next good poll brings the
    entities back.
    """

    config_entry: MarstekConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: MarstekConfigEntry,
        device: VenusDevice,
        fast: Sequence[str],
        slow: Sequence[str],
    ) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN)
        self.device = device
        self._groups = {"high": tuple(fast), "low": tuple(slow)}
        self._last_polled: dict[str, float] = {}
        self._last_timeout_recovery: float | None = None
        self._refresh_cancels: dict[str, Callable[[], None]] = {}
        self._pending_rs485_write: tuple[int, object] | None = None
        # Sub-systems whose last read failed.
        self.failed: set[str] = set()
        self.set_scan_intervals(scan_intervals(entry.options))
        entry.async_on_unload(self._cancel_refreshes)

    @property
    def polled(self) -> tuple[str, ...]:
        """The sub-systems this coordinator reads."""
        return self._groups["high"] + self._groups["low"]

    def set_scan_intervals(self, intervals: Mapping[str, int]) -> None:
        """Poll the "high" and "low" groups at these intervals in seconds."""
        self._intervals = dict(intervals)
        self.update_interval = timedelta(seconds=min(self._intervals.values()))

    async def _async_update_data(self) -> None:
        now = monotonic()
        assert self.update_interval is not None
        # Half a tick of slack, so a tick that fires a little early still counts.
        slack = self.update_interval.total_seconds() / 2
        due = [
            group
            for group, names in self._groups.items()
            if names
            and (
                group not in self._last_polled
                or now - self._last_polled[group] >= self._intervals[group] - slack
            )
        ]
        names = [name for group in due for name in self._groups[group]]
        if not names:
            return
        try:
            report = await self.device.async_poll(names)
            timed_out = tuple(
                name
                for name, error in report.failed.items()
                if isinstance(error, ModbusTimeoutError)
            )
            now = monotonic()
            if (
                len(timed_out) >= PARTIAL_TIMEOUT_RECOVERY_THRESHOLD
                and (
                    self._last_timeout_recovery is None
                    or now - self._last_timeout_recovery
                    >= TIMEOUT_RECOVERY_COOLDOWN_SECONDS
                )
            ):
                self._last_timeout_recovery = now
                try:
                    await self.device.modbus_unit.disconnect()
                except Exception as disconnect_err:
                    _LOGGER.debug(
                        "Disconnect after clustered Modbus timeouts failed: %s",
                        disconnect_err,
                    )
                try:
                    report = await self.device.async_poll(timed_out, report=report)
                except ModbusError as retry_err:
                    _LOGGER.debug(
                        "Retrying timed-out sub-systems after reconnect failed for %s: %s",
                        self.config_entry.title,
                        retry_err,
                    )
                else:
                    recovered = sum(name in report.updated for name in timed_out)
                    _LOGGER.debug(
                        "Retried %d timed-out sub-systems after reconnect for %s "
                        "(%d recovered, %d still failed)",
                        len(timed_out),
                        self.config_entry.title,
                        recovered,
                        len(timed_out) - recovered,
                    )
        except ModbusTimeoutError as err:
            now = monotonic()
            if (
                self._last_timeout_recovery is not None
                and now - self._last_timeout_recovery
                < TIMEOUT_RECOVERY_COOLDOWN_SECONDS
            ):
                raise UpdateFailed(f"Error talking to the battery: {err}") from err
            self._last_timeout_recovery = now
            try:
                await self.device.modbus_unit.disconnect()
            except Exception as disconnect_err:
                _LOGGER.debug("Disconnect after Modbus timeout failed: %s", disconnect_err)
            try:
                report = await self.device.async_poll(names)
            except ModbusError as retry_err:
                raise UpdateFailed(
                    f"Error talking to the battery after reconnect: {retry_err}"
                ) from retry_err
            _LOGGER.debug(
                "Modbus timeout recovered after reconnect for %s: %s "
                "(%d sub-systems updated, %d failed)",
                self.config_entry.title,
                err,
                len(report.updated),
                len(report.failed),
            )
        except ModbusError as err:
            raise UpdateFailed(f"Error talking to the battery: {err}") from err
        if not report.updated:
            errors = list(report.failed.values())
            raise UpdateFailed(
                f"No sub-system answered: {errors[0]}"
            ) from ExceptionGroup("every sub-system failed", errors)
        for group in due:
            self._last_polled[group] = now
        self._record(report)

    def _record(self, report: UpdateReport) -> None:
        for name in sorted(report.failed.keys() - self.failed):
            _LOGGER.warning("Failed to read %s: %s", name, report.failed[name])
        self.failed -= report.updated
        self.failed |= report.failed.keys()

    async def async_write(self, component: str, field: str, value: Any) -> None:
        """Write a field, then read its sub-system back once the device settles."""
        try:
            await getattr(self.device, component).write(field, value)
        except ModbusError as err:
            raise HomeAssistantError(f"Error writing {field}: {err}") from err
        if component in self.polled:
            if component == "control" and field == "rs485_control_mode":
                self._pending_rs485_write = (value, object())
            self._schedule_component_refresh(component)

    @callback
    def _schedule_component_refresh(self, component: str) -> None:
        if cancel := self._refresh_cancels.pop(component, None):
            cancel()
        self._refresh_cancels[component] = async_call_later(
            self.hass,
            POST_WRITE_REFRESH_SECONDS,
            HassJob(
                partial(self._async_refresh_component, component),
                cancel_on_shutdown=True,
            ),
        )

    async def _async_refresh_component(self, component: str, _now: Any) -> None:
        self._refresh_cancels.pop(component, None)
        pending = self._pending_rs485_write if component == "control" else None
        try:
            report = await self.device.async_poll((component,))
        except ModbusError as err:
            _LOGGER.debug("Reading %s back after a write failed: %s", component, err)
            if pending is not None and self._pending_rs485_write is pending:
                self._pending_rs485_write = None
            return
        if pending is not None and self._pending_rs485_write is pending:
            self._pending_rs485_write = None
            actual = self.device.control.rs485_control_mode
            if component in report.updated and actual is not None and actual != pending[0]:
                _LOGGER.warning(
                    "RS485 control mode readback for %s does not match the requested value "
                    "(requested %s, read %s); the battery may not have applied the write",
                    self.config_entry.title,
                    pending[0],
                    actual,
                )
        self._record(report)
        self.async_update_listeners()

    @callback
    def _cancel_refreshes(self) -> None:
        for cancel in self._refresh_cancels.values():
            cancel()
        self._refresh_cancels.clear()
        self._pending_rs485_write = None

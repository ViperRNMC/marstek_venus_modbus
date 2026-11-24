"""Tests for the Marstek Venus Modbus config flow."""

from __future__ import annotations

import socket
import threading
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.marstek_modbus.const import DOMAIN

USER_INPUT = {
    CONF_HOST: "venus.local",
    CONF_PORT: 502,
    "unit_id": 1,
    "device_version": "E v3",
}


async def test_host_is_resolved_outside_the_event_loop(hass: HomeAssistant) -> None:
    """Resolving the host must not block the event loop."""
    threads: list[int] = []

    def resolve(host: str) -> str:
        threads.append(threading.get_ident())
        return "192.168.1.50"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with (
        patch(
            "custom_components.marstek_modbus.config_flow.socket.gethostbyname",
            # A plain function: the test harness runs mocks in the event loop.
            new=resolve,
        ),
        patch(
            "custom_components.marstek_modbus.config_flow.async_test_modbus_connection",
            return_value=None,
        ),
        patch(
            "custom_components.marstek_modbus.async_setup_entry", return_value=True
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(threads) == 1
    assert threads[0] != threading.get_ident()


@pytest.mark.parametrize(
    "error", [socket.gaierror("not found"), TypeError("not a host")]
)
async def test_unresolvable_host_is_reported(
    hass: HomeAssistant, error: Exception
) -> None:
    """A host that does not resolve shows an error in the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.marstek_modbus.config_flow.socket.gethostbyname",
        side_effect=error,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_host"}

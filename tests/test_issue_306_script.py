"""Tests for the issue 306 diagnostic script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "test_issue_306.py"
)


@pytest.fixture(name="issue_script")
def issue_script_fixture():
    spec = importlib.util.spec_from_file_location("test_issue_306", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeConnection:
    def __init__(self, unit) -> None:
        self.unit = unit

    def for_unit(self, unit_id: int):
        assert unit_id == 1
        return self.unit

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None


async def test_issue_306_script_read_only(issue_script, monkeypatch, capsys):
    unit = type("Unit", (), {})()
    unit.read = AsyncMock(side_effect=[[21930], [1], [0], [0], [1]])
    connection = FakeConnection(unit)
    monkeypatch.setattr(issue_script, "ModbusConnection", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(sys, "argv", ["test_issue_306.py", "192.0.2.10"])

    await issue_script.main()

    output = capsys.readouterr().out
    assert "Before" in output
    assert "Read-only mode" in output
    assert unit.read.await_count == len(issue_script.READ_FIELDS)


async def test_issue_306_script_execute_sequence(issue_script, monkeypatch, capsys):
    unit = type("Unit", (), {})()
    unit.read = AsyncMock(side_effect=lambda **_kwargs: [21930])
    unit.write_register = AsyncMock()
    connection = FakeConnection(unit)
    monkeypatch.setattr(issue_script, "ModbusConnection", lambda *_args, **_kwargs: connection)
    monkeypatch.setattr(
        sys,
        "argv",
        ["test_issue_306.py", "192.0.2.10", "--execute", "--delay", "0"],
    )

    await issue_script.main()

    assert [call.kwargs for call in unit.write_register.await_args_list] == [
        {"address": 42010, "value": 3},
        {"address": 42020, "value": 0},
        {"address": 42021, "value": 0},
    ]
    output = capsys.readouterr().out
    assert "Writing sequence" in output
    assert "Readback" in output

import ast
import json
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "marstek_modbus"


def source(name):
    return (COMPONENT / name).read_text(encoding="utf-8")


def test_host_lookup_runs_in_the_executor():
    text = source("config_flow.py")
    assert "async_add_executor_job(socket.gethostbyname, host)" in text
    assert "\n                socket.gethostbyname(host)" not in text


def test_reauth_does_not_await_the_entry_update_or_create_an_entry():
    text = source("config_flow.py")
    assert "await self.hass.config_entries.async_update_entry" not in text
    reauth = text.split("async def async_step_reauth", 1)[1].split("def async_get_options_flow", 1)[0]
    assert "async_create_entry" not in reauth
    assert 'async_abort(reason="reauth_successful")' in reauth
    for lang in ("en", "de", "nl"):
        data = json.loads((COMPONENT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
        assert data["config"]["abort"]["reauth_successful"]


def test_coordinator_data_is_a_dict_after_the_base_class_init():
    tree = ast.parse(source("coordinator.py"))
    init = next(
        node
        for cls in tree.body
        if isinstance(cls, ast.ClassDef) and cls.name == "MarstekCoordinator"
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    super_line = next(
        node.lineno
        for node in ast.walk(init)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "__init__"
        and isinstance(node.func.value, ast.Call)
        and getattr(node.func.value.func, "id", "") == "super"
    )
    data_lines = [
        node.lineno
        for node in ast.walk(init)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Attribute) and target.attr == "data"
    ]
    assert max(data_lines) > super_line


def test_schedule_attributes_do_not_log_a_warning_on_every_read():
    assert "Raw schedule data" in source("sensor.py")
    block = source("sensor.py").split("Debug logging for raw schedule data", 1)[1][:80]
    assert "_LOGGER.debug(" in block

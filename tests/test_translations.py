import json
import re
from pathlib import Path

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "marstek_modbus"
LANGUAGES = ("en", "de", "nl")


def load(lang):
    return json.loads((COMPONENT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))


def error_keys_used_by_the_flows():
    """Every error key the config and options flows can show."""
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    keys = set(re.findall(r'errors\["base"\]\s*=\s*"([a-z_]+)"', source))
    keys |= set(re.findall(r'return\s+"([a-z_]+)"', source))  # async_test_modbus_connection
    return keys


def test_every_flow_error_is_translated_in_both_flows():
    keys = error_keys_used_by_the_flows()
    assert {"invalid_port", "invalid_unit_id", "cannot_connect", "unit_id_no_response"} <= keys
    for lang in LANGUAGES:
        data = load(lang)
        for flow in ("config", "options"):
            missing = keys - set(data[flow].get("error", {}))
            assert not missing, f"{lang}.{flow}.error lacks {sorted(missing)}"


def test_every_sensor_name_exists_in_every_language():
    names = {lang: set(load(lang)["entity"]["sensor"]) for lang in LANGUAGES}
    for lang in LANGUAGES:
        assert names["en"] <= names[lang], f"{lang} lacks {sorted(names['en'] - names[lang])}"


def test_select_platform_does_not_refresh_inside_its_setup():
    source = (COMPONENT / "select.py").read_text(encoding="utf-8")
    assert "update_before_add=True" not in source

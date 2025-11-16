# Integration domain name
DOMAIN = "marstek_modbus"

# Manufacturer and model information for the Marstek Venus battery
MANUFACTURER = "Marstek"
MODEL = "Venus E"

# Configuration key for Modbus Unit ID
CONF_UNIT_ID = "unit_id"

# Default network configuration for Modbus connection
DEFAULT_PORT = 502
DEFAULT_MESSAGE_WAIT_MS = 80  # Default wait time for Modbus messages in milliseconds
DEFAULT_UNIT_ID = 1  # Default Modbus Unit ID (unit ID)

# General scan intervals (in seconds)
DEFAULT_SCAN_INTERVALS = {
    "high": 10,       # fast-changing sensors, e.g., power, alarms
    "medium": 30,     # moderately changing sensors, e.g., voltage, current
    "low": 60,        # slow-changing sensors, e.g., cumulative energy counters
    "very_low": 180   # rarely changing info, e.g., device info, firmware versions
}

# Supported device versions
SUPPORTED_VERSIONS = ["v1/v2", "v3"]

# Note: register loading logic (get_registers_for_version) was moved to
# `register_loader.py` to keep `const.py` focused on constants only.
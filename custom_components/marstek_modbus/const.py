from .venus import VenusA, VenusD, VenusDevice, VenusEV3, VenusEV12

# Integration domain name
DOMAIN = "marstek_modbus"

# Manufacturer and model information for the Marstek Venus battery
MANUFACTURER = "Marstek"
MODEL = "Venus"

# Default network configuration for Modbus connection
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1  # Default Modbus Unit ID (unit ID)

# General scan intervals (in seconds)
DEFAULT_SCAN_INTERVALS = {
    "high": 10,  # fast-changing sensors and former medium-priority sensors
    "low": 60,  # slower-changing sensors and former very_low-priority sensors
}

# Device classes by the version the user picks in the config flow
MODELS: dict[str, type[VenusDevice]] = {
    "E v1/v2": VenusEV12,
    "E v3": VenusEV3,
    "D": VenusD,
    "A": VenusA,
}

# Supported device versions
SUPPORTED_VERSIONS = list(MODELS)

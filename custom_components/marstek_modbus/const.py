# Integration domain name
DOMAIN = "marstek_modbus"

# Manufacturer and model information for the Marstek Venus battery
MANUFACTURER = "Marstek"
MODEL = "Venus E"

# Default network configuration for Modbus connection
DEFAULT_PORT = 502

# Time interval (in seconds) between data scans
SCAN_INTERVAL = 10

# Definitions for sensors to be read from the Modbus device
# Each sensor includes metadata for proper interpretation and display
SENSOR_DEFINITIONS = [
    {
        # Device name, stored as a string in multiple registers
        "name": "Device Name",
        "register": 31000,
        "count": 10,  # 20 bytes = 10 registers
        "data_type": "char",
        "unit": None,
        "key": "device_name",
        "enabled_by_default": True,
        "precision": 0
    },
    {
        # SN code, stored as a string in multiple registers
        "name": "SN Code",
        "register": 31200,
        "count": 10,  # 20 bytes = 10 registers
        "data_type": "char",
        "unit": None,
        "key": "sn_code",
        "enabled_by_default": False,
        "precision": 0
    },
    {
        # Software version as scaled unsigned integer
        "name": "Soft Version",
        "register": 31100,
        "scale": 0.01,
        "unit": None,
        "key": "soft_version",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 2
    },
    {
        # Battery State of Charge (SOC) as a percentage
        "name": "Battery SOC",
        "register": 32104,
        "scale": 1,
        "unit": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "key": "battery_soc",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 1
    },    
    {
        # Battery voltage in volts
        "name": "Battery Voltage",
        "register": 32100,
        "scale": 0.01,
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "key": "battery_voltage",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 1
    },
    {
        # Battery current in amperes
        "name": "Battery Current",
        "register": 32101,
        "scale": 0.01,
        "unit": "A",
        "device_class": "current",
        "state_class": "measurement",
        "key": "battery_current",
        "enabled_by_default": True,
        "data_type": "int16",
        "precision": 1
    },
    {
        # Battery power in watts
        "name": "Battery Power",
        "register": 32102,
        "count": 2,
        "scale": 1,
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "key": "battery_power",
        "enabled_by_default": True,
        "data_type": "int32",
        "precision": 1
    },
    {
        # Battery temperature in degrees Celsius
        "name": "Battery Temperature",
        "register": 35000,
        "scale": 0.1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "battery_temperature",
        "enabled_by_default": True,
        "data_type": "int16",
        "precision": 2
    },
    {
        # Battery AC voltage in volts
        "name": "AC Voltage",
        "register": 32200,
        "scale": 0.1,
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "key": "ac_voltage",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 1
    },
    {
        # Battery AC current in amperes
        "name": "AC Current",
        "register": 32201,
        "scale": 0.01,
        "unit": "A",
        "device_class": "current",
        "state_class": "measurement",
        "key": "ac_current",
        "enabled_by_default": True,
        "data_type": "int16",
        "precision": 1
    },
    {
        # Battery AC power in watts
        "name": "AC Power",
        "register": 32202,
        "count": 2,
        "scale": 1,
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "key": "ac_power",
        "enabled_by_default": True,
        "data_type": "int32",
        "precision": 0
    },
    {
        # Battery AC frequency in hertz
        "name": "AC Frequency",
        "register": 32204,
        "scale": 0.01,
        "unit": "Hz",
        "device_class": "frequency",
        "state_class": "measurement",
        "key": "ac_frequency",
        "enabled_by_default": True,
        "data_type": "int16",
        "precision": 2
    },
    {
        # Total energy charged into the battery in kilowatt-hours
        "name": "Total Charging Energy",
        "register": 33000,
        "count": 2,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_charging_energy",
        "enabled_by_default": True,
        "data_type": "uint32",
        "precision": 2
    },
    {
        # Total energy discharged from the battery in kilowatt-hours
        "name": "Total Discharging Energy",
        "register": 33002,
        "count": 2,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_discharging_energy",
        "enabled_by_default": True,
        "data_type": "int32",
        "precision": 2
    },    
    {
        # Current state of the inverter device
        "name": "Inverter State",
        "register": 35100,
        "scale": 1,
        "unit": None,
        "key": "inverter_state",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 0,
        "states": {
            0: "Sleep",
            1: "Standby",
            2: "Charge",
            3: "Discharge",
            4: "Backup Mode",
            5: "OTA Upgrade"
        }
    },
    {
        "name": "Alarm Status",
        "register": 36001,
        "count": 1,
        "data_type": "uint16",
        "key": "alarm_status",
        "enabled_by_default": True,
        "unit": None,
        "precision": 0
    },
    {
        # Modbus address (slave ID)
        "name": "Modbus Address",
        "register": 41100,
        "data_type": "uint16",
        "unit": None,
        "key": "modbus_address",
        "enabled_by_default": False,
        "precision": 0
    }
]

# Definitions for selectable options (e.g. operating modes)
# Each entry includes the register, label options, and conversion mappings
SELECT_DEFINITIONS = [
    {
        # Selectable user work mode for the battery system
        "name": "User Work Mode",
        "register": 43000,
        "key": "user_work_mode",
        "enabled_by_default": True,
        "options": ["Manual", "Anti-Feed", "Trade Mode"],
        "map_to_int": {
            "Manual": 0,
            "Anti-Feed": 1,
            "Trade Mode": 2
        },
        "int_to_map": {
            0: "Manual",
            1: "Anti-Feed",
            2: "Trade Mode"
        }
    },
    {
        # Selectable force mode for charging/discharging the battery
        "name": "Force Mode",
        "register": 42010,
        "key": "force_mode",
        "enabled_by_default": False,
        "options": ["None", "Charge", "Discharge"],
        "map_to_int": {
            "None": 0,
            "Charge": 1,
            "Discharge": 2
        },
        "int_to_map": {
            0: "None",
            1: "Charge",
            2: "Discharge"
        }
    }
]

# Definitions for switch controls that can be toggled on/off
# Each switch includes the Modbus register register and commands for on/off
SWITCH_DEFINITIONS = [
    {
        # Battery backup switch
        "name": "Backup Function",
        "register": 41200,
        "command_on": 0,    # Enable
        "command_off": 1,   # Disable
        "key": "backup_function",
        "enabled_by_default": True,
        "data_type": "uint16"
    },
    {
        # RS485 communication control mode switch
        "name": "RS485 Control Mode",
        "register": 42000,
        "command_on": 21930,  # 0x55AA in decimal
        "command_off": 21947,  # 0x55BB in decimal
        "key": "rs485_control_mode",
        "enabled_by_default": False
    }    
]

# Definitions for numeric configuration parameters
# Each number defines a range and step size for setting values
NUMBER_DEFINITIONS = [
    {
        # Set power limit for forced charging in watts
        "name": "Set Forcible Charge Power",
        "register": 42020,
        "key": "set_charge_power",
        "enabled_by_default": False,
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W"
    },
    {
        # Set power limit for forced discharging in watts
        "name": "Set Forcible Discharge Power",
        "register": 42021,
        "key": "set_discharge_power",
        "enabled_by_default": False,
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W"
    },
    {
        # Maximum power that can be charged into the battery in watts
        "name": "Max Charge Power",
        "register": 44002,
        "key": "max_charge_power",
        "enabled_by_default": False,
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W",
        "data_type": "uint16"
    },
    {
        # Maximum power that can be discharged from the battery in watts
        "name": "Max Discharge Power",
        "register": 44003,
        "key": "max_discharge_power",
        "enabled_by_default": False,
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W",
        "data_type": "uint16"
    }
]

# Definitions for button actions (one-time triggers)
# BUTTON_DEFINITIONS = [
#     {
#         # Reset device via Modbus command
#         "name": "Reset Device",
#         "register": 41000,
#         "command": 21930,  # 0x55AA
#         "key": "reset_device",
#         "enabled_by_default": False,
#         "data_type": "uint16"
#     }
# ]
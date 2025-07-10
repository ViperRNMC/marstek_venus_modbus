# Integration domain name
DOMAIN = "marstek_modbus"

# Manufacturer and model information for the Marstek Venus battery
MANUFACTURER = "Marstek"
MODEL = "Venus E"

# Default network configuration for Modbus connection
DEFAULT_PORT = 502


# Time interval (in seconds) between data scans
# SCAN_INTERVAL = 10

# Default polling intervals (seconds) per sensor category.
# These values can be overridden via modbus.yaml using the
# corresponding keys in each sensor's "scan_interval".
SCAN_INTERVAL = {
    "power": 10,         # high‑frequency power readings
    "electrical": 30,    # voltage, current, frequency
    "energy": 60,        # cumulative kWh counters
    "soc": 30,           # state‑of‑charge
    "state": 5           # fast‑changing state / alarm bits
}

# Definitions for sensors to be read from the Modbus device
# Each sensor includes metadata for proper interpretation and display.
# The "scan_interval" refers to keys inside SCAN_INTERVALS by default.
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
        "precision": 1,
        "background_read": True,
        "scan_interval": "scan_interval.soc"
    },
    {
        # Total stored battery energy in kilowatt-hours
        "name": "Battery Total Energy",
        "register": 32105,
        "scale": 0.001,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "measurement",
        "key": "battery_total_energy",
        "enabled_by_default": False,
        "data_type": "uint16",
        "precision": 3,
        "background_read": True,
        "scan_interval": "scan_interval.energy"
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
        "precision": 1,
        "scan_interval": "scan_interval.electrical"
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
        "precision": 1,
        "scan_interval": "scan_interval.electrical"
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
        "precision": 1,
        "scan_interval": "scan_interval.power"
    },
    {
        # Internal temperature in degrees Celsius
        "name": "Internal Temperature",
        "register": 35000,
        "scale": 0.1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "internal_temperature",
        "enabled_by_default": True,
        "data_type": "int16",
        "precision": 2,
        "scan_interval": "scan_interval.temperature"        
    },
    {
        # Internal MOS 1 temperature in degrees Celsius
        "name": "Internal MOS1 Temperature",
        "register": 35001,
        "scale": 0.1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "internal_mos1_temperature",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 2,
        "scan_interval": "scan_interval.temperature"          
    },
    {
        # Internal MOS 2 temperature in degrees Celsius
        "name": "Internal MOS2 Temperature",
        "register": 35002,
        "scale": 0.1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "internal_mos2_temperature",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 2,
        "scan_interval": "scan_interval.temperature"
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
        "precision": 1,
        "scan_interval": "scan_interval.electrical"
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
        "precision": 1,
        "scan_interval": "scan_interval.electrical"
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
        "precision": 0,
        "scan_interval": "scan_interval.power"
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
        "precision": 2,
        "scan_interval": "scan_interval.electrical"
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
        "precision": 2,
        "background_read": True,
        "scan_interval": "scan_interval.energy"
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
        "precision": 2,
        "background_read": True,
        "scan_interval": "scan_interval.energy"
    },    
    {
        # Total energy charged into the battery in kilowatt-hours per day
        "name": "Total Daily Charging Energy",
        "register": 33004,
        "count": 2,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_daily_charging_energy",
        "enabled_by_default": False,
        "data_type": "uint32",
        "precision": 2,
        "scan_interval": "scan_interval.energy"
    },
    {
        # Total energy discharged from the battery in kilowatt-hours per day
        "name": "Total Daily Discharging Energy",
        "register": 33006,
        "count": 2,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_daily_discharging_energy",
        "enabled_by_default": False,
        "data_type": "int32",
        "precision": 2,
        "scan_interval": "scan_interval.energy"
    },   
    {
        # Total energy charged into the battery in kilowatt-hours per month
        "name": "Total Monthly Charging Energy",
        "register": 33008,
        "count": 2,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_monthly_charging_energy",
        "enabled_by_default": False,
        "data_type": "uint32",
        "precision": 2,
        "background_read": True,
        "scan_interval": "scan_interval.energy"
    },
    {
        # Total energy discharged from the battery in kilowatt-hours per month
        "name": "Total Monthly Discharging Energy",
        "register": 33010,
        "count": 2,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_monthly_discharging_energy",
        "enabled_by_default": False,
        "data_type": "int32",
        "precision": 2,
        "background_read": True,
        "scan_interval": "scan_interval.energy"
    },      
    {
        # Maximum cell temperature in degrees Celsius
        "name": "Max Cell Temperature",
        "register": 35010,
        "scale": 0.1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "max_cell_temperature",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 2,
        "scan_interval": "scan_interval.temperature"
    },
    {
        # Minimum cell temperature in degrees Celsius
        "name": "Min Cell Temperature",
        "register": 35011,
        "scale": 0.1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "min_cell_temperature",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 2,
        "scan_interval": "scan_interval.temperature"
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
        },
        "scan_interval": "scan_interval.state"
    },
    {
        # Selectable grid standard (country / regulation profile)
        "name": "Grid Standard",
        "register": 44100,
        "key": "grid_standard",
        "unit": None,
        "scale": 1,
        "data_type": "uint16",
        "enabled_by_default": True,
        "states": {
            0: "Auto (220-240 V, 50/60 Hz)",
            1: "EN50549",
            2: "NL - Netherlands",
            3: "DE - Germany",
            4: "AT - Austria",
            5: "UK - United Kingdom",
            6: "ES - Spain",
            7: "PL - Poland",
            8: "IT - Italy",
            9: "CN - China"
        },
        "scan_interval": "scan_interval.state"
    },    
    {
        # Grid fault status bits indicating various grid issues
        "name": "Grid Status",
        "register": 36100,
        "count": 1,
        "data_type": "uint16",
        "unit": None,
        "key": "grid_status",
        "enabled_by_default": True,
        "precision": 0,
        "scan_interval": "scan_interval.state"
    },    
    {
        # Alarm status bits indicating various device alarms
        "name": "Alarm Status",
        "register": 36001,
        "count": 1,
        "data_type": "uint16",
        "key": "alarm_status",
        "enabled_by_default": True,
        "unit": None,
        "precision": 0,
        "scan_interval": "scan_interval.state"
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
    },
    {
        # AC Offgrid Voltage in volts
        "name": "AC Offgrid Voltage",
        "register": 32300,
        "scale": 0.1,
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "key": "ac_offgrid_voltage",
        "enabled_by_default": False,
        "data_type": "uint16",
        "precision": 1,
        "scan_interval": "scan_interval.electrical"
    },
    {
        # AC Offgrid Current in amperes
        "name": "AC Offgrid Current",
        "register": 32301,
        "scale": 0.01,
        "unit": "A",
        "device_class": "current",
        "state_class": "measurement",
        "key": "ac_offgrid_current",
        "enabled_by_default": False,
        "data_type": "uint16",
        "precision": 1,
        "scan_interval": "scan_interval.electrical"
    },
    {
        # AC Offgrid Power in watts
        "name": "AC Offgrid Power",
        "register": 32302,
        "count": 2,
        "scale": 1,
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "key": "ac_offgrid_power",
        "enabled_by_default": False,
        "data_type": "int32",
        "precision": 0,
        "scan_interval": "scan_interval.power"
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
        "scan_interval": "scan_interval.state", 
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
        "scan_interval": "scan_interval.state",
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
        "data_type": "uint16",
        "scan_interval": "scan_interval.state"
    },
    {
        # RS485 communication control mode switch
        "name": "RS485 Control Mode",
        "register": 42000,
        "command_on": 21930,  # 0x55AA in decimal
        "command_off": 21947,  # 0x55BB in decimal
        "key": "rs485_control_mode",
        "enabled_by_default": False,
        "scan_interval": "scan_interval.state"

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
BUTTON_DEFINITIONS = [
    # {
    #     # Reset device via Modbus command
    #     "name": "Reset Device",
    #     "register": 41000,
    #     "command": 21930,  # 0x55AA
    #     "key": "reset_device",
    #     "enabled_by_default": False,
    #     "data_type": "uint16"
    # }
]

# Definitions for efficiency sensors
EFFICIENCY_SENSOR_DEFINITIONS = [
    {
        "name": "Round-Trip Efficiency Total",
        "unique_id_key": "round_trip_efficiency_total",
        "charge_key": "total_charging_energy",
        "discharge_key": "total_discharging_energy",
        "soc_key": "battery_soc",
        "max_energy_key": "battery_total_energy"
    },
    {
        "name": "Round-Trip Efficiency Monthly",
        "unique_id_key": "round_trip_efficiency_monthly",
        "charge_key": "total_monthly_charging_energy",
        "discharge_key": "total_monthly_discharging_energy",
        "soc_key": "battery_soc",
        "max_energy_key": "battery_total_energy"
    }
]

# Definitions for stored energy sensors
STORED_ENERGY_SENSOR_DEFINITIONS = [
    {
        "name": "Stored Energy",
        "unique_id_key": "stored_energy",
        "soc_key": "battery_soc",
        "max_energy_key": "battery_total_energy"
    }
]

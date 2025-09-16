# Integration domain name
DOMAIN = "marstek_modbus"

# Manufacturer and model information for the Marstek Venus battery
MANUFACTURER = "Marstek"
MODEL = "Jupiter C"

# Default network configuration for Modbus connection
DEFAULT_PORT = 502
DEFAULT_MESSAGE_WAIT_MS = 80  # Default wait time for Modbus messages in milliseconds
DEFAULT_UNIT_ID = 1  # Default Modbus Unit ID (unit ID)

# General scan intervals (in seconds)
SCAN_INTERVAL = {
    "high": 10,       # fast-changing sensors, e.g., power, alarms
    "medium": 30,     # moderately changing sensors, e.g., voltage, current
    "low": 60,        # slow-changing sensors, e.g., cumulative energy counters
    "very_low": 180   # rarely changing info, e.g., device info, firmware versions
}

# Definitions for sensors to be read from the Modbus device
# Each sensor includes metadata for proper interpretation and display.
# The "scan_interval" refers to keys inside SCAN_INTERVALS by default.
SENSOR_DEFINITIONS = [
    {
        "name": "Device ID",
        "register": 0x001B,
        "count": 10,  # 20 bytes = 10 registers
        "data_type": "char",
        "unit": None,
        "key": "device_id",
        "enabled_by_default": True,
        "scan_interval": "very_low",
        "precision": 0
    },
    {
        # EMS version, stored as a 16-bit unsigned integer
        "name": "EMS Version",
        "register": 0x001C,
        "unit": None,
        "category": "diagnostic",
        "icon": "mdi:ticket-confirmation-outline",
        "key": "ems_version",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 0,
        "scan_interval": "very_low"
    },
    {
        # INV version, stored as a 16-bit unsigned integer
        "name": "INV Version",
        "register": 0x001D,
        "unit": None,
        "category": "diagnostic",
        "icon": "mdi:ticket-confirmation-outline",
        "key": "ems_version",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 0,
        "scan_interval": "very_low"
    },
    {
        # MPPT version, stored as a 16-bit unsigned integer
        "name": "MPPT Version",
        "register": 0x001E,
        "unit": None,
        "category": "diagnostic",
        "icon": "mdi:ticket-confirmation-outline",
        "key": "ems_version",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 0,
        "scan_interval": "very_low"
    },
    {
        # BMS version, stored as a 16-bit unsigned integer
        "name": "BMS Version",
        "register": 0x001F,
        "unit": None,
        "icon": "mdi:battery-check-outline",
        "category": "diagnostic",
        "key": "bms_version",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 0,
        "scan_interval": "very_low"
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
        "scan_interval": "very_low",
        "precision": 0
    },
    {
        # Software version, stored as a 16-bit unsigned integer
        "name": "Software Version",
        "register": 31100,
        "scale": 0.01,
        "unit": None,
        "icon": "mdi:ticket-confirmation-outline",
        "category": "diagnostic",
        "key": "software_version",
        "enabled_by_default": True,
        "data_type": "uint16",
        "precision": 2,
        "scan_interval": "very_low"
    },
    {
        # Communication module firmware version, stored as a string in multiple registers
        "name": "Communication Module Firmware",
        "register": 30800,
        "count": 6,
        "unit": None,
        "category": "diagnostic",
        "icon": "mdi:ticket-confirmation-outline",
        "key": "comm_module_firmware",
        "enabled_by_default": True,
        "data_type": "char",
        "precision": 0,
        "scan_interval": "very_low"
    },
    {
        # MAC address of the device, stored as a string in multiple registers
        "name": "MAC Address",
        "register": 30402,
        "count": 6,
        "unit": None,
        "key": "mac_address",
        "enabled_by_default": True,
        "data_type": "char",
        "precision": 0,
        "scan_interval": "very_low"
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
        "scan_interval": "medium"
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
        "enabled_by_default": True, ###False,
        "data_type": "uint16",
        "precision": 3,
        "scan_interval": "low"
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
        "scan_interval": "medium"
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
        "scan_interval": "medium"
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
        "scan_interval": "high"
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
        "scan_interval": "medium"
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
        "scan_interval": "medium"
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
        "scan_interval": "medium"
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
        "scan_interval": "medium"
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
        "scan_interval": "medium"
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
        "scan_interval": "high"
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
        "scan_interval": "medium"
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
        "scan_interval": "low"
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
        "scan_interval": "low"
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
        "scan_interval": "low"
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
        "scan_interval": "low"
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
        "scan_interval": "low"
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
        "scan_interval": "low"
    },      
    {
        # Maximum cell temperature in degrees Celsius
        "name": "Max Cell Temperature",
        "register": 35010,
        "scale": 1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "max_cell_temperature",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 1,
        "scan_interval": "medium"
    },
    {
        # Minimum cell temperature in degrees Celsius
        "name": "Min Cell Temperature",
        "register": 35011,
        "scale": 1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "min_cell_temperature",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 1,
        "scan_interval": "medium"
    },
    {
        # Minimum cell voltage
        "name": "Max Cell Voltage",
        "register": 37007,
        "scale": 0.001,
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "key": "max_cell_voltage",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 3,
        "scan_interval": "medium"
    },
    {
        # Minimum cell voltage 
        "name": "Min Cell Voltage",
        "register": 37008,
        "scale": 0.001,
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "key": "min_cell_voltage",
        "enabled_by_default": False,
        "data_type": "int16",
        "precision": 3,
        "scan_interval": "medium"
    },
    {
        # Current state of the inverter device
        "name": "Inverter State",
        "register": 35100,
        "scale": 1,
        "unit": None,
        "icon": "mdi:state-machine",
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
            5: "OTA Upgrade",
            6: "Bypass",
        },
        "scan_interval": "high"
    },
    {
        # Fault status bits indicating various device faults
        "name": "Fault Status",
        "register": 36100,
        "count": 4,
        "data_type": "uint16",
        "key": "fault_status",
        "device_class": "problem",
        "icon": "mdi:alert",
        "category": "diagnostic",
        "enabled_by_default": True,
        "scan_interval": "high",
        "bit_descriptions": {
            # Register 36100 (bits 0-15)
            0: "Grid Overvoltage",
            1: "Grid Undervoltage",
            2: "Grid Overfrequency",
            3: "Grid Underfrequency",
            4: "Grid Peak Voltage",
            5: "Current Dcover",
            6: "Voltage Dcover",
            # Register 36101 (bits 16-31)
            16: "BAT Overvoltage",
            17: "BAT Undervoltage",
            18: "BAT Overcurrent",
            19: "BAT low SOC",
            20: "BAT communication failure",
            21: "BMS protect",
            # Register 36102 (bits 32-47)
            32: "Inverter soft start timeout",
            33: "self-checking failure",
            34: "eeprom failure",
            35: "other system failure",
            # Register 36103 (bits 48-63)
            48: "Hardware Bus overvoltage",
            49: "Hardware Output overcurrent",
            50: "Hardware trans overcurrent",
            51: "Hardware battery overcurrent",
            52: "Hardware Protecion",
            53: "Output Overcurrent",
            54: "High Voltage bus overvoltage",
            55: "High Voltage bus undervoltage",
            56: "Overpower Protection",
            57: "FSM abnormal",
            58: "Overtemperature Protection"
        }
    },
    {
        # Alarm status bits indicating various device alarms
        "name": "Alarm Status",
        "register": 36000,
        "count": 2,
        "data_type": "uint16",
        "key": "alarm_status",
        "device_class": "problem",
        "icon": "mdi:alert",
        "enabled_by_default": True,
        "category": "diagnostic",
        "unit": None,
        "precision": 0,
        "scan_interval": "high",
        "bit_descriptions": {
            # Register 36000 (bits 0-15)
            0: "PLL Abnormal Restart",
            1: "Overtemperature Limit",
            2: "Low Temperature Limit",
            3: "Fan Abnormal Warning",
            4: "Low Battery SOC Warning",
            5: "Output Overcurrent Warning",
            6: "Abnormal Line Sequence Detection",
            # Register 36001 (bits 16-31)
            16: "WiFi Abnormal",
            17: "BLE Abnormal",
            18: "Network Abnormal",
            19: "CT Connection Abnormal",
        }
    },
    {
        # Modbus address (unit ID)
        "name": "Modbus Address",
        "register": 41100,
        "data_type": "uint16",
        "unit": None,
        "icon": "mdi:home-automation", 
        "key": "modbus_address",
        "enabled_by_default": False,
        "scan_interval": "very_low",
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
        "scan_interval": "medium"
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
        "scan_interval": "medium"
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
        "scan_interval": "high"
    },
    {
        # WiFi signal strength in dBm
        "name": "WiFi Signal Strength",
        "register": 30303,
        "scale": -1,
        "data_type": "uint16",
        "device_class": "diagnostic",
        "unit": "dBm",
        "icon": "mdi:wifi",
        "category": "diagnostic",
        "key": "wifi_signal_strength",
        "enabled_by_default": False,
        "precision": 0,
        "scan_interval": "high"
    }
]

# Definitions for binary sensors that represent on/off states
# Each binary sensor includes the Modbus register and bit position
BINARY_SENSOR_DEFINITIONS = [
    {
        # WiFi connection status
        "name": "WiFi Status",
        "register": 30300,
        "data_type": "uint16",
        "unit": None,
        "category": "diagnostic",
        "device_class": "connectivity",
        "icon": "mdi:check-network-outline",
        "key": "wifi_status",
        "enabled_by_default": False,
        "scan_interval": "medium"
    },
    {
        # Cloud connection status
        "name": "Cloud Status",
        "register": 30302,
        "data_type": "uint16",
        "unit": None,
        "category": "diagnostic",
        "device_class": "connectivity",
        "icon": "mdi:cloud-outline",
        "key": "cloud_status",
        "enabled_by_default": False,
        "scan_interval": "medium"
    },
    {   
        # Discharge limit mode switch
        "name": "Discharge Limit",
        "register": 41010,
        "data_type": "uint16",
        "unit": None,
        "icon": "mdi:battery-arrow-down-outline",
        "key": "discharge_limit_mode",
        "enabled_by_default": False,
        "scan_interval": "medium",
    },
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
        "scan_interval": "high",
        "options": {
            "Manual": 0,
            "Anti-Feed": 1,
            "Trade Mode": 2
        }
    },
    {
        # Selectable force mode for charging/discharging the battery
        "name": "Force Mode",
        "register": 42010,
        "key": "force_mode",
        "enabled_by_default": False,
        "scan_interval": "high",
        "options": {
            "None": 0,
            "Charge": 1,
            "Discharge": 2
        }
    },
    {
        # Grid‑standard profile (country / regulation)
        "name": "Grid Standard",
        "register": 44100,
        "key": "grid_standard",
        "enabled_by_default": True,
        "scan_interval": "high",
        "options": {
            "Auto": 0,
            "EN50549": 1,
            "Netherlands": 2,
            "Germany": 3,
            "Austria": 4,
            "United Kingdom": 5,
            "Spain": 6,
            "Poland": 7,
            "Italy": 8,
            "China": 9
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
        "scan_interval": "high"
    },
    {
        # RS485 communication control mode switch
        "name": "RS485 Control Mode",
        "register": 42000,
        "command_on": 21930,  # 0x55AA in decimal
        "command_off": 21947,  # 0x55BB in decimal
        "key": "rs485_control_mode",
        "enabled_by_default": False,
        "data_type": "uint16",
        "scan_interval": "high"
    },
    # {   
    #     # Discharge limit mode switch
    #     "name": "Discharge Limit (800 W)",
    #     "register": 41010,
    #     "command_on": 1,   # 1 = Low (800 W)
    #     "command_off": 0,  # 0 = High (2500 W)
    #     "key": "discharge_limit_mode",
    #     "enabled_by_default": False,
    #     "data_type": "uint16",
    #     "scan_interval": "state"
    # } 
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
        "icon": "mdi:battery-arrow-up-outline",
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W",
        "data_type": "uint16",
        "scan_interval": "high"
    },
    {
        # Set power limit for forced discharging in watts
        "name": "Set Forcible Discharge Power",
        "register": 42021,
        "key": "set_discharge_power",
        "enabled_by_default": False,
        "icon": "mdi:battery-arrow-down-outline",
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W",
        "data_type": "uint16",
        "scan_interval": "high"
    },
    {
        # Maximum power that can be charged into the battery in watts
        "name": "Max Charge Power",
        "register": 44002,
        "key": "max_charge_power",
        "enabled_by_default": False,
        "icon": "mdi:battery-arrow-up-outline",
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W",
        "data_type": "uint16",
        "scan_interval": "high"
    },
    {
        # Maximum power that can be discharged from the battery in watts
        "name": "Max Discharge Power",
        "register": 44003,
        "key": "max_discharge_power",
        "enabled_by_default": False,
        "icon": "mdi:battery-arrow-down-outline",
        "min": 0,
        "max": 2500,
        "step": 50,
        "unit": "W",
        "data_type": "uint16",
        "scan_interval": "high"
    },
    {
        # Charging cutoff capacity as a percentage 
        "name": "Charging Cutoff Capacity",
        "register": 44000,
        "key": "charging_cutoff_capacity",
        "enabled_by_default": False,
        "icon": "mdi:battery-arrow-up-outline",
        "min": 80,
        "max": 100,
        "step": 1,
        "unit": "%",
        "scale": 0.1,
        "data_type": "uint16",
        "scan_interval": "high"
    },
    {
        # Discharging cutoff capacity as a percentage
        "name": "Discharging Cutoff Capacity",
        "register": 44001,
        "key": "discharging_cutoff_capacity",
        "enabled_by_default": False,
        "icon": "mdi:battery-arrow-down-outline",
        "min": 12,
        "max": 30,
        "step": 1,
        "unit": "%",
        "scale": 0.1,
        "data_type": "uint16",
        "scan_interval": "high"
    },
    {
        # charge or discharge to SOC as a percentage of total battery capacity
        "name": "Charge to SOC",
        "register": 42011,
        "key": "charge_to_soc",
        "enabled_by_default": False,
        "icon": "mdi:battery-sync-outline",
        "min": 10,
        "max": 100, 
        "step": 1,
        "unit": "%",
        "scale": 1,       
        "data_type": "uint16",        
        "scan_interval": "high"
    }  
]

# Definitions for button actions (one-time triggers)
BUTTON_DEFINITIONS = [
    {
        # Reset device via Modbus command
        "name": "Reset Device",
        "register": 41000,
        "command": 21930,  # 0x55AA
        "icon": "mdi:restart",
        "category": "diagnostic",
        "key": "reset_device",
        "enabled_by_default": False,
        "data_type": "uint16"
    },
    {
        # Factory reset device via Modbus command
        "name": "Factory reset",
        "register": 41001,
        "command": 21930,  # 0x55AA
        "icon": "mdi:factory",
        "category": "diagnostic",
        "key": "factory_reset",
        "enabled_by_default": False,
        "data_type": "uint16"
    }    
]

# Definitions for efficiency sensors
EFFICIENCY_SENSOR_DEFINITIONS = [
    {
        "key": "round_trip_efficiency_total",
        "name": "Round-Trip Efficiency Total",
        "unit": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "mode": "round_trip",
        "dependency_keys": {
            "charge": "total_charging_energy",            
            "discharge": "total_discharging_energy" 
        },             
    },
    {
        "name": "Round-Trip Efficiency Monthly",
        "key": "round_trip_efficiency_monthly",
        "unit": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "mode": "round_trip",
        "dependency_keys": {
            "charge": "total_monthly_charging_energy",            
            "discharge": "total_monthly_discharging_energy" 
        },                 
    },
    {
        "name": "Conversion Efficiency",
        "key": "conversion_efficiency",
        "unit": "%",
        "device_class": "battery",
        "state_class": "measurement",
        "mode": "conversion",
        "dependency_keys": {
            "battery_power": "battery_power",
            "ac_power": "ac_power"
        },
    }

]

# Definitions for stored energy sensors
STORED_ENERGY_SENSOR_DEFINITIONS = [
    {
        "name": "Stored Energy",
        "key": "stored_energy",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
        "dependency_keys": {
            "soc": "battery_soc",            
            "capacity": "battery_total_energy" 
        },   
    },
]

# Marstek Venus Modbus - Custom Home Assistant Integration

📦 A custom Home Assistant integration for monitoring and controlling the **Marstek Venus battery system** via **Modbus TCP**, fully independent from the built-in `modbus:` platform.

---

## ✅ Features

- 📡 Native **Modbus TCP** polling (no `modbus:` YAML required)
- 🔌 Works with **pymodbus 3.x**
- 🔍 Exposes detailed sensors:
  - Battery voltage, current, power, SOC, energy
  - AC input/output status
  - Temperatures, inverter state, charge/discharge limits
- 🔄 Supports switches:
  - Force charge mode
  - Force discharge mode
  - RS485 control enable
- 🎚️ Number entities for:
  - Setting forcible charge and discharge power (`0–2500W`)
- 🔧 Full UI-based setup via **Config Flow**
- ⚡ HACS-compatible

---

## 📐 Example Entities

| Entity                             | Type    | Register | Description                        |
|------------------------------------|---------|----------|------------------------------------|
| `sensor.marstek_battery_voltage`   | Sensor  | 32100    | Battery voltage (scaled ×0.01 V)   |
| `sensor.marstek_battery_soc`       | Sensor  | 32104    | State of Charge (%)                |
| `switch.marstek_force_charge_mode` | Switch  | 42010    | Charge enable/disable              |
| `number.marstek_set_charge_power`  | Number  | 42020    | Set charge power (0–2500W)         |

---

## 🚀 Installation

1. Copy this folder into `custom_components/marstek_venus/` inside your Home Assistant config.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → Marstek Venus**
4. Enter your **Modbus TCP IP address** and port (default: 502).
5. Entities will auto-populate.

---

## 🧪 Development Notes

- Built using `pymodbus>=3.5.2`
- Uses `DataUpdateCoordinator` for polling
- Supports async platform loading (`sensor`, `switch`, `number`)
- Fully compatible with Home Assistant for `2025.x`

---

## 🔧 Configuration Options

No `configuration.yaml` required. All config is done via UI.

---

## 📄 License

MIT

---

## 🙋 Support

This is a community integration. Use at your own risk.  
For bug reports or feature requests, create an issue on GitHub.
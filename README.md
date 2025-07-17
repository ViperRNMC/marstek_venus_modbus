# Marstek Venus Battery - Home Assistant Integration

🇬🇧 **English**

This is a custom HACS-compatible integration for the Marstek Venus E home battery system, using **Modbus TCP** via an **EW11 RS485-to-WiFi gateway**. No YAML required. The integration provides sensors, switches and number controls to monitor and manage the battery directly from Home Assistant.

### 🧩 Requirements

- A configured **EW11 (Modbus RTU to Modbus TCP bridge)** connected to the battery's RS485 port
- The IP address and port of the EW11 (usually port 502)
- Home Assistant Core 2025.6 or later
- HACS installed

### 🔧 Features

- Native Modbus TCP polling via `pymodbus`
- Fully asynchronous operation for optimal performance and responsiveness
- Sensors for voltage, current, SOC, power, energy, and fault/alarm status (combined bits)
- Switches for force charge/discharge control
- Adjustable charge/discharge power (0–2500W)
- Entities grouped under a device in Home Assistant
- Select entity support for multi-state control (e.g., force mode)
- Select entity for control modes (e.g., force mode, grid standard)
- Backup mode control and charge/discharge to SOC included
- Includes calculated sensors: round-trip efficiency (total/monthly) and stored energy
<!-- - Efficient background polling with per-sensor scan intervals -->
- Some advanced sensors are disabled by default to keep the UI clean
- UI-based configuration (Config Flow)
- Fully local, no cloud required

---

🇳🇱 **Nederlands**

Dit is een aangepaste HACS-integratie voor de Marstek Venus E thuisbatterij via **Modbus TCP**, mogelijk gemaakt door een **EW11 RS485–WiFi gateway**. Geen YAML nodig. De integratie biedt sensoren, schakelaars en instelbare vermogens om de batterij volledig vanuit Home Assistant te bedienen.

### 🧩 Vereisten

- Een correct ingestelde **EW11 (Modbus RTU naar Modbus TCP converter)** aangesloten op de RS485-poort van de batterij
- Het IP-adres en poortnummer van de EW11 (meestal poort 502)
- Home Assistant Core 2025.6 of nieuwer
- HACS geïnstalleerd

### 🔧 Functies

- Native Modbus TCP polling via `pymodbus`
- Volledig asynchrone werking voor optimale performance en responsiveness
- Sensoren voor spanning, stroom, SOC, vermogen, energie en fout-/alarmstatus (gecombineerde bits)
- Schakelaars voor geforceerd laden/ontladen
- Instelbaar laad-/ontlaadvermogen (0–2500W)
- Entiteiten gegroepeerd onder één apparaat in Home Assistant
- Ondersteuning voor select-entiteiten voor meervoudige bedieningsstanden (bijv. force mode)
- Select-entiteiten voor bedieningsmodi (bijv. force mode, netstandaard)
- Back-up modus besturing en laden/ontladen tot SOC inbegrepen
- Inclusief berekende sensoren: round-trip rendement (totaal/maandelijks) en opgeslagen energie
<!-- - Efficiënte achtergrondpolling met per-sensor scan-intervallen -->
- Sommige geavanceerde sensoren standaard uitgeschakeld voor een schone gebruikersinterface
- Configuratie via UI (Config Flow)
- Volledig lokaal, geen cloud nodig

---

## 🚀 Installation

1. Add this repository to HACS (Integrations → Custom repositories)
2. Install the “Marstek Venus Modbus” integration
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**
5. Enter the IP and port of your EW11 gateway (default: port 502)

---

## 📘 Modbus Registers Used

The following Modbus registers are used by this integration:

| Register | Name                         | Type     | Count | Scale | Unit | HA Type               | Description / Options / Commands                                      |
|:--------:|:----------------------------|:---------|:-----:|:-----:|:----:|:---------------------:|----------------------------------------------------------------------|
| 30399    | BMS Version                  | uint16   |   -   | 1     |  -   | sensor                | Battery Management System version                                   |
| 30401    | Firmware Version             | uint16   |   -   | 1     |  -   | sensor                | Firmware version                                                   |
| 30402    | MAC Address                  | char     |   6   |  -    |  -   | sensor                | MAC address                                                        |
| 30800    | Communication Module Firmware | char     | 6     |  -    |  -   | sensor                | Firmware version of communication module                 |
| 31000    | Device Name                  | char     |  10   |  -    |  -   | sensor                | Device name stored as string                                       |
| 31100    | Software Version             | uint16   |   -   | 0.01  |  -   | sensor                | Software version                                                  |
| 31200    | SN Code                     | char     |  10   |  -    |  -   | sensor                | Serial number code                                                |
| 32100    | Battery Voltage             | uint16   |   -   | 0.01  |  V   | sensor                | Battery voltage                                                 |
| 32101    | Battery Current             | int16    |   -   | 0.01  |  A   | sensor                | Battery current                                                 |
| 32102    | Battery Power               | int32    |   2   | 1     |  W   | sensor                | Battery power                                                  |
| 32104    | Battery SOC                 | uint16   |   -   | 1     |  %   | sensor                | Battery State of Charge                                         |
| 32105    | Battery Total Energy        | uint16   |   -   | 0.001 | kWh  | sensor                | Total stored battery energy                                     |
| 32200    | AC Voltage                 | uint16   |   -   | 0.1   |  V   | sensor                | Battery AC voltage                                             |
| 32201    | AC Current                 | int16    |   -   | 0.01  |  A   | sensor                | Battery AC current                                             |
| 32202    | AC Power                   | int32    |   2   | 1     |  W   | sensor                | Battery AC power                                              |
| 32204    | AC Frequency               | int16    |   -   | 0.01  | Hz   | sensor                | Battery AC frequency                                          |
| 32300    | AC Offgrid Voltage         | uint16   |   -   | 0.1   |  V   | sensor                | AC Offgrid voltage                                           |
| 32301    | AC Offgrid Current         | uint16   |   -   | 0.01  |  A   | sensor                | AC Offgrid current                                           |
| 32302    | AC Offgrid Power           | int32    |   2   | 1     |  W   | sensor                | AC Offgrid power                                           |
| 33000    | Total Charging Energy      | uint32   |   2   | 0.01  | kWh  | sensor                | Total energy charged into battery                           |
| 33002    | Total Discharging Energy   | int32    |   2   | 0.01  | kWh  | sensor                | Total energy discharged from battery                        |
| 33004    | Total Daily Charging Energy| uint32   |   2   | 0.01  | kWh  | sensor                | Total daily energy charged into battery                     |
| 33006    | Total Daily Discharging Energy | int32 |   2   | 0.01  | kWh  | sensor                | Total daily energy discharged from battery                  |
| 33008    | Total Monthly Charging Energy| uint32  |   2   | 0.01  | kWh  | sensor                | Total monthly energy charged into battery                   |
| 33010    | Total Monthly Discharging Energy | int32 |   2   | 0.01  | kWh  | sensor                | Total monthly energy discharged from battery                |
| 35000    | Internal Temperature       | int16    |   -   | 0.1   | °C   | sensor                | Internal device temperature                                 |
| 35001    | Internal MOS1 Temperature  | int16    |   -   | 0.1   | °C   | sensor                | Internal MOS1 temperature                                   |
| 35002    | Internal MOS2 Temperature  | int16    |   -   | 0.1   | °C   | sensor                | Internal MOS2 temperature                                   |
| 35010    | Max Cell Temperature       | int16    |   -   | 0.1   | °C   | sensor                | Maximum cell temperature                                   |
| 35011    | Min Cell Temperature       | int16    |   -   | 0.1   | °C   | sensor                | Minimum cell temperature                                   |
| 35100    | Inverter State             | uint16   |   -   | 1     |  -   | sensor                | Inverter state (0=Sleep, 1=Standby, 2=Charge, 3=Discharge, 4=Backup Mode, 5=OTA Upgrade) |
| 36000    | Alarm Status               | uint16   |   2   | -     |  -   | sensor                | Alarm status bits (see bit descriptions)                    |
| 36100    | Fault Status               | uint16   |   4   | -     |  -   | sensor                | Fault status bits (64 bits total over 4 registers)          |
| 41010    | Discharge Limit            | uint16   |   -   | 1     |  -   | sensor                | Discharge limit mode switch (0=High (2500 W), 1=Low (800 W))|
| 41100    | Modbus Address             | uint16   |   -   | -     |  -   | sensor                | Modbus address (slave ID)                                   |
| 41200    | Backup Function            | uint16   |   -   | -     |  -   | switch                | Battery backup switch (On=0 Enable, Off=1 Disable)          |
| 42000    | RS485 Control Mode         | uint16   |   -   | -     |  -   | switch                | RS485 control mode (On=21930, Off=21947)                    |
| 42010    | Force Mode                 | uint16   |   -   | -     |  -   | select                | Force mode options (None=0, Charge=1, Discharge=2)          |
| 42011    | Charge to SOC              | uint16   |   -   | 1     |  %   | number                | Charge or discharge to SOC, 10–100%, step 1%                |
| 42020    | Set Forcible Charge Power  | uint16   |   -   | -     |  W   | number                | Power limit for forced charging, 0–2500 W, step 50 W        |
| 42021    | Set Forcible Discharge Power | uint16 |   -   | -     |  W   | number                | Power limit for forced discharging, 0–2500 W, step 50 W     |
| 43000    | User Work Mode             | uint16   |   -   | -     |  -   | select                | User work mode options (Manual=0, Anti-Feed=1, Trade Mode=2)|
| 44000    | Charging Cutoff Capacity   | uint16   |   -   | 0.1   |  %   | number                | Charging cutoff capacity, 80–100%, step 0.1%                |
| 44001    | Discharging Cutoff Capacity| uint16   |   -   | 0.1   |  %   | number                | Discharging cutoff capacity, 12–30%, step 0.1%              |
| 44002    | Max Charge Power           | uint16   |   -   | -     |  W   | number                | Maximum charge power, 0–2500 W, step 50 W                   |
| 44003    | Max Discharge Power        | uint16   |   -   | -     |  W   | number                | Maximum discharge power, 0–2500 W, step 50 W                |
| 44100    | Grid Standard              | uint16   |   -   | -     |  -   | select                | Grid standards (Auto=0, EN50549=1, Netherlands=2, Germany=3, Austria=4, UK=5, Spain=6, Poland=7, Italy=8, China=9) |
|    —     | Round-Trip Efficiency Total |   -   |   -   | -     |   %   | efficiency sensor     | Efficiency from total charging/discharging and SOC           |
|    —     | Round-Trip Efficiency Monthly |   -   |   -   | -     |  %   | efficiency sensor     | Efficiency from monthly charging/discharging and SOC         |
|    —     | Stored Energy                |   -   |   -   | -     |  kWh  | stored energy sensor  | Calculated stored energy from SOC and battery capacity       |

_Note: For access to registers in the 42000–42999 range, the battery must be set to RS485 control mode._

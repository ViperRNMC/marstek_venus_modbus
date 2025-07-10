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
- Sensors for voltage, current, SOC, power, energy, and alarm status (combined bits)
- Switches for force charge/discharge control
- Adjustable charge/discharge power (0–2500W)
- Entities grouped under a device in Home Assistant
- Select entity support for multi-state control (e.g., force mode)
- Select entity for control modes (e.g., force mode, grid standard)
- Some advanced sensors disabled by default for cleaner UI
- Efficient background polling with per-sensor scan intervals
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

- Communicatie via Modbus TCP met `pymodbus`
- Sensordata: spanning, stroom, SOC, vermogen, energie en gecombineerde alarmstatus (bits)
- Schakelaars voor geforceerd laden/ontladen
- Instelbare laad- en ontlaadvermogens (0–2500W)
- Entiteiten gegroepeerd onder één apparaat in Home Assistant
- Ondersteuning voor Select-entity (meerdere standen zoals 'force mode')
- Select-entity voor bedieningsmodi (zoals force mode en netstandaard)
- Geavanceerde sensoren standaard uitgeschakeld voor overzicht
- Efficiënt achtergrond-pollen met per-sensor scan-intervallen
- Geavanceerde sensoren zijn standaard uitgeschakeld voor een overzichtelijke interface
- Configuratie via gebruikersinterface (config flow)
- Volledig lokaal – geen cloudverbinding nodig

---

## 🚀 Installation

1. Add this repository to HACS (Integrations → Custom repositories)
2. Install the “Marstek Venus Modbus” integration
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**
5. Enter the IP and port of your EW11 gateway (default: port 502)

---
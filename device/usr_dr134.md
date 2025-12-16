# USR-DR134 Modbus Gateway

**RS485 to Modbus TCP** • Powered by Marstek (5V) • [AliExpress](https://www.aliexpress.com/w/wholesale-usr-dr134.html)

⚠️ Order **USR-DR134 with RS485** interface (NOT RS232 - they look identical!)

## Wiring

```
Marstek RS485              USR-DR134
┌────────────────┐        ┌──────────────┐
│ Pin 1: +5V     │───────▶│ VCC (5V)     │
│ Pin 2: GND     │───────▶│ GND          │
│ Pin 3: RS485-A │───────▶│ A (485+)     │
│ Pin 4: RS485-B │───────▶│ B (485-)     │
└────────────────┘        └──────────────┘
```

- **Wire**: Max 0.5mm² (spring terminal limit), keep < 3m
- **Power**: 5V from Marstek (no external PSU needed)

## Configuration

**Access**: `http://192.168.0.7` • Login: `admin` / `admin`  
**Tool**: [USR-M0 V2.2.6.1.exe](https://www.pusr.com/support/downloads/usr-dr134-downloads.html) or Web UI

### Required Settings

**Serial Port (RS485)**
```
BaudRate    = 115200
DataBit     = 8
StopBit     = 1
Parity      = None
WorkMode    = Modbus RTU to TCP
```

**Network**
```
IP Address  = [Your IP, e.g. 10.0.0.150]
SubnetMask  = 255.255.255.0
Gateway     = [Router IP]
DHCP        = Disable (static recommended)
```

**Modbus TCP**
```
Protocol    = Modbus Gateway
LocalPort   = 502
Timeout     = 5000
FramerType  = RTU  (Important! See troubleshooting)
```

## Home Assistant Setup

**Settings** → **Devices & Services** → **Add Integration** → **Marstek Venus Modbus**

```
Host:           10.0.0.150  (USR-DR134 IP)
Port:           502
Unit ID:        1
Device version: v1/v2 or v3
```

## Testing

Use **Modbus Poll**, **OpenModScan**, or **QModMaster** to test:

- Register `32104` (Battery SOC), Function `03`, Type `uint16`, Unit `1`
- Expected: 0-100 (battery percentage)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No response from Unit ID"** / timeout | **Set WorkMode = "Modbus RTU to TCP"** in serial settings (critical!) |
| "Extra data" / unexpected data errors | DR134 sending RTU frames - verify RTU framing mode enabled |
| Module not found | Marstek powered on? Try `192.168.0.7`, check PC subnet `192.168.0.x` |
| No Modbus connection | Check A/B wiring not swapped, baud rate 115200, Unit ID = 1 |
| No data | Enable RS485 Control Mode in Marstek, firmware v1.48+, test register 32104 |

## Resources

- [USR-DR134 Product Page](https://www.pusr.com/) (search "DR134" on PUSR website)
- [PV Forum Setup Guide](https://www.photovoltaikforum.com/thread/247095-marstek-venus-e-hat-jetzt-einen-lan-anschluss-von-mir-bekommen/) (German)
- [Duravolt Modbus Manual](https://duravolt.nl/wp-content/uploads/Duravolt-Plug-in-Battery-Modbus.pdf)
- [GitHub Issues](https://github.com/ViperRNMC/marstek_venus_modbus/issues)

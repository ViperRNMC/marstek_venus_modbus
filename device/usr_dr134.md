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
WorkMode    = Modbus TCP 
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
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No response from Unit ID"** / timeout | Verify **WorkMode = "Modbus TCP"** (NOT "RTU to TCP") in serial settings |
| "Extra data" / unexpected data errors | Wrong WorkMode - must be "Modbus TCP", not "Modbus RTU to TCP" |
| Module not found | Marstek powered on? Try `192.168.0.7`, check PC subnet `192.168.0.x` |
| No Modbus connection | Check A/B wiring not swapped, baud rate 115200, Unit ID = 1 |
| Connection works with other tools but not HA | Other tool may auto-detect RTU framing - DR134 must use "Modbus TCP" mode for this integration |

## Resources

- [USR-DR134 Product Page](https://www.pusr.com/) (search "DR134" on PUSR website)
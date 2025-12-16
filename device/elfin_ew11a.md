# Elfin EW11A WiFi to RS485

**WiFi to RS485** • Powered by Marstek (5V) or external • [AliExpress](https://nl.aliexpress.com/item/1005006939991800.html)

⚠️ Order **Wide Range Voltage Version** (5-36V DC input)

## Wiring

```
Marstek RS485              Elfin EW11A
┌────────────────┐        ┌──────────────┐
│ Pin 1: +5V     │───────▶│ VIN (5-36V)  │
│ Pin 2: GND     │───────▶│ GND          │
│ Pin 3: RS485-A │───────▶│ A+ (485+)    │
│ Pin 4: RS485-B │───────▶│ B- (485-)    │
└────────────────┘        └──────────────┘
                                │
                                └─ WiFi/Ethernet
```

- **Wire**: Keep < 3m for reliable communication
- **Power**: 5V from Marstek or external 5-36V DC

## Configuration

**Access**: WiFi AP mode (SSID: `HF-A11-xxxx`) or `http://[device-ip]`  
**Tool**: Web UI or Elfin Config Tool (check product manual)

### Required Settings

**Serial Port**
```ini
BaudRate    = 115200
DataBit     = 8
StopBit     = 1
Parity      = None
BufferSize  = 512
GapTime     = 50
FlowControl = HalfDuplex
Protocol    = Modbus
```

**Communication**
```ini
Protocol    = TcpServer
LocalPort   = 502
BufferSize  = 512
KeepAlive   = 60
Timeout     = 300
MaxAccept   = 3
Route       = Uart
```

**Network** (Optional - for WiFi)
```ini
WorkMode    = STA (Station mode)
SSID        = [Your WiFi]
Password    = [Your WiFi password]
DHCP        = Enable (or set static IP)
```

## Home Assistant Setup

**Settings** → **Devices & Services** → **Add Integration** → **Marstek Venus Modbus**

```
Host:           [EW11A IP]
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
| Cannot connect to WiFi AP | Reset device (hold button 5s), connect to `HF-A11-xxxx` |
| No Modbus connection | Check A/B wiring not swapped, baud rate 115200, FlowControl = HalfDuplex |
| Unstable connection | Reduce GapTime to 20ms, check WiFi signal strength |
| No data | Enable RS485 Control Mode in Marstek, firmware v1.48+, test register 32104 |

## Resources

- [Elfin EW11A on AliExpress](https://nl.aliexpress.com/item/1005006939991800.html)
- [Duravolt Modbus Manual](https://duravolt.nl/wp-content/uploads/Duravolt-Plug-in-Battery-Modbus.pdf)
- [GitHub Issues](https://github.com/ViperRNMC/marstek_venus_modbus/issues)

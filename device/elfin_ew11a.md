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

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cannot connect to WiFi AP | Reset device (hold button 5s), connect to `HF-A11-xxxx` |
| No Modbus connection | Check A/B wiring not swapped, baud rate 115200, FlowControl = HalfDuplex |
| Unstable connection | Reduce GapTime to 20ms, check WiFi signal strength |

## Resources

- [Elfin EW11A on AliExpress](https://nl.aliexpress.com/item/1005006939991800.html)
- [Duravolt Modbus Manual](https://duravolt.nl/wp-content/uploads/Duravolt-Plug-in-Battery-Modbus.pdf)
- [GitHub Issues](https://github.com/ViperRNMC/marstek_venus_modbus/issues)

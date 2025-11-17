# Elfin EW11B Modbus TCP Configuration (Wide Range Voltage Version)

Use this configuration for the Elfin EW11B as a Modbus TCP server:

```ini
[Serial Port]
BaudRate=115200
DataBit=8
StopBit=1
Parity=None
BufferSize=512
GapTime=50
FlowControl=HalfDuplex
Cli=Disable
Protocol=Modbus

[Communication]
Protocol=TcpServer
LocalPort=502
BufferSize=512
KeepAlive=60
Timeout=300
MaxAccept=3
Security=Disable
Route=Uart
```

Refer to the Elfin EW11B documentation for upload instructions and further details.
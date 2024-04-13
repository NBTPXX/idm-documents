```
[mcu idm]
serial:
#canbus_uuid:

[probe_eddy_current eddy]
sensor_type: ldc1612
i2c_mcu: idm
i2c_bus: i2c1
x_offset: 0
y_offset: 21.1
speed:40
lift_speed: 15.

[thermistor ntc47k]
temperature1:25.
resistance1:47000
beta:4010

[probe_drift_adjust]
sensor_type:ntc47k
sensor_pin:idm:PA4
pullup_resistor:10000
```

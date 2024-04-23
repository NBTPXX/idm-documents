### 固件
更新到[最新固件](https://gitee.com/NBTP/idm-documents/tree/master/IDM%E5%9B%BA%E4%BB%B6(Main%20firmware))
### 配置
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
###  操作说明
首先`SET_KINEMATIC_POSITION z=80`  
然后控制打印头到热床中央2cm高的位置,执行`LDC_CALIBRATE_DRIVE_CURRENT CHIP=eddy`和`PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy`  
此时校准步骤完成。  
整床扫描使用`BED_MESH_CALIBRATE METHOD=scan SCAN_MODE=rapid`  

### QGL使用扫描模式
```
[gcode_macro QUAD_GANTRY_LEVEL]   #随着龙门高低差降低降低探测高度
rename_existing: _QUAD_GANTRY_LEVEL
gcode:
    SAVE_GCODE_STATE NAME=STATE_QGL
    BED_MESH_CLEAR
    {% if not printer.quad_gantry_level.applied %}
      _QUAD_GANTRY_LEVEL horizontal_move_z=10 retry_tolerance=1
    {% endif %}
    _QUAD_GANTRY_LEVEL horizontal_move_z=2 METHOD=scan
    # G28 Z
    RESTORE_GCODE_STATE NAME=STATE_QGL
```
### z_tilt使用扫描模式
```
[gcode_macro Z_TILT_ADJUST]
rename_existing: _Z_TILT_ADJUST
gcode:
    SAVE_GCODE_STATE NAME=STATE_Z_TILT
    BED_MESH_CLEAR
    {% if not printer.z_tilt.applied %}
      _Z_TILT_ADJUST horizontal_move_z=10 retry_tolerance=1
    {% endif %}
    _Z_TILT_ADJUST horizontal_move_z=2 METHOD=scan
    # G28 Z
    RESTORE_GCODE_STATE NAME=STATE_Z_TILT
```
### 温补校准
PROBE_DRIFT_CALIBRATE COUNT=6 AUTOSTEP=7
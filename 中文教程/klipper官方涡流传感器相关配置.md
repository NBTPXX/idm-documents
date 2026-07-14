# Klipper 官方涡流传感器配置

> **不推荐使用此方案。** IDM 自有脚本提供了更丰富的功能和更好的兼容性，建议优先使用主教程中的 `[scanner]` 配置方案。

## 一、固件要求

更新到最新固件（见 `IDM固件(Main firmware)` 目录）。

## 二、配置

将以下配置添加到 `printer.cfg`：

```ini
[mcu idm]
serial:
#canbus_uuid:

[probe_eddy_current eddy]
sensor_type: ldc1612
i2c_mcu: idm
i2c_bus: i2c1
x_offset: 0
y_offset: 21.1
speed: 40
lift_speed: 15.

[thermistor ntc47k]
temperature1: 25.
resistance1: 47000
beta: 4010

[probe_drift_adjust]
sensor_type: ntc47k
sensor_pin: idm:PA4
pullup_resistor: 10000
```

### 参数调整

- `x_offset` 和 `y_offset` 需要根据你的安装位置修改
- `serial` 或 `canbus_uuid` 按实际情况填写

## 三、校准步骤

1. 执行 `SET_KINEMATIC_POSITION z=80`
2. 将打印头移动到热床中央约 2cm 高度
3. 执行驱动电流校准：

```gcode
LDC_CALIBRATE_DRIVE_CURRENT CHIP=eddy
```

4. 执行传感器校准：

```gcode
PROBE_EDDY_CURRENT_CALIBRATE CHIP=eddy
```

此时校准步骤完成。

## 四、整床扫描

```gcode
BED_MESH_CALIBRATE METHOD=scan SCAN_MODE=rapid
```

## 五、QGL 使用扫描模式

```ini
[gcode_macro QUAD_GANTRY_LEVEL]
rename_existing: _QUAD_GANTRY_LEVEL
gcode:
    SAVE_GCODE_STATE NAME=STATE_QGL
    BED_MESH_CLEAR
    {% if not printer.quad_gantry_level.applied %}
      _QUAD_GANTRY_LEVEL horizontal_move_z=10 retry_tolerance=1
    {% endif %}
    _QUAD_GANTRY_LEVEL horizontal_move_z=2 METHOD=scan
    RESTORE_GCODE_STATE NAME=STATE_QGL
```

## 六、Z_TILT 使用扫描模式

```ini
[gcode_macro Z_TILT_ADJUST]
rename_existing: _Z_TILT_ADJUST
gcode:
    SAVE_GCODE_STATE NAME=STATE_Z_TILT
    BED_MESH_CLEAR
    {% if not printer.z_tilt.applied %}
      _Z_TILT_ADJUST horizontal_move_z=10 retry_tolerance=1
    {% endif %}
    _Z_TILT_ADJUST horizontal_move_z=2 METHOD=scan
    RESTORE_GCODE_STATE NAME=STATE_Z_TILT
```

## 七、温补校准

```gcode
PROBE_DRIFT_CALIBRATE COUNT=6 AUTOSTEP=7
```

## 注意事项

- 使用此方案时，Klipper 控制 IDM 的功能将受到限制
- 如需 Touch 模式、多模型管理等 IDM 特有功能，请使用 IDM 自有脚本方案
- 此方案的 Z 偏移管理方式和 IDM 自有方案不同，切换方案时需要重新校准

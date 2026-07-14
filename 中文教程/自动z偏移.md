# 自动 Z 偏移教程（Touch 以外的方案）

本文介绍使用 Touch 以外的触发方式实现自动 Z 偏移校准，适用于 TAP 或普通限位开关。

## 适用场景

- 使用 Voron TAP 作为 Z 探针
- 使用普通限位开关作为 Z 触发
- 不想使用 IDM Touch 的热端戳床方式

## 一、配置

在 `[scanner]` 配置段中添加以下内容：

```ini
calibration_method: second_probe
# 使用第二探针模式

z_offset: 0
# 触发高度相对于喷嘴的偏移。使用 TAP 时请自行测量实际值

probe_speed: 10
# 校准时 Z 轴移动速度

probe_pin:
# TAP 或其他限位的引脚配置
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `calibration_method` | 设为 `second_probe`，启用第二探针触发模式 |
| `z_offset` | 第二探针的触发高度与喷嘴之间的固定偏移量 |
| `probe_speed` | Z 轴在校准过程中的移动速度，建议不超过 15 |
| `probe_pin` | 第二探针的限位引脚（如 TAP 的触发引脚） |

## 二、执行校准

配置完成后，执行以下命令触发自动校准：

```gcode
IDM_TOUCH CALIBRATE=1
```

此时 IDM 将使用第二探针进行 Z 归零，然后自动开始校准。

## 三、Z 偏移校准

对 Z 偏移进行校准：

```gcode
PROBE_CALIBRATE METHOD=AUTO
```

## 四、固定 Z 偏移补偿

由于 TAP 等触发方式在自动 Z 偏移过程中可能产生挤压偏差，需要自行测定固定 Z 偏移值：

1. 在网页界面上使用偏移按钮微调 Z 偏移
2. 调至合适位置后，使用以下命令保存：

```gcode
SAVE_TOUCH_OFFSET
```

此命令将当前偏移量保存为自动 Z 偏移的固定补偿值。

## 注意事项

- 确保第二探针（TAP 或限位）已在 Klipper 中正确配置且工作正常
- `z_offset` 参数需要在首次使用时手动测量并填入
- 更换喷嘴或热端组件后建议重新测定固定 Z 偏移

# IDM Touch 使用教程

本文介绍 IDM Touch 模式（热端戳床）的使用方法，包括校准、阈值设置和自动 Z 偏移。

## 一、bed_mesh 配置

在 `[bed_mesh]` 配置段中添加 `zero_reference_position`（必须配置，否则会报错）：

```ini
[bed_mesh]
zero_reference_position: 125, 125
# 设置为热床正中心坐标，自动 Z 偏移时喷嘴将在此位置戳床
```

## 二、指令参考

| 命令 | 用途 |
|------|------|
| `IDM_TOUCH METHOD=MANUAL` | 手动进行 IDM 模型校准（通常在初次使用或未校准 Touch 时） |
| `IDM_TOUCH CALIBRATE=1` | 自动进行 IDM 模型校准（通常在 Touch 完成校准后使用） |
| `IDM_THRESHOLD_SCAN MIN=500` | 对 Touch 进行阈值校准（需先归零） |
| `PROBE_CALIBRATE METHOD=AUTO` | 自动测算 Z 偏移 |
| `SAVE_TOUCH_OFFSET` | 保存自动 Z 偏移所用的固定偏移量 |

## 三、操作步骤

### 步骤 1：初次手动校准

```gcode
IDM_TOUCH METHOD=MANUAL
```

在弹出的偏移控制框中，将喷头降到喷嘴贴热床，然后点击 -0.1 偏移并确认，校准将自动进行。

### 步骤 2：归零

完成初次校准后执行归零：

```gcode
G28
```

### 步骤 3：Touch 阈值校准

确保 Z 轴完成归零后执行：

```gcode
IDM_THRESHOLD_SCAN MIN=500
```

此步骤将校准喷嘴接触热床时的力度阈值，确保 Touch 触发准确。

### 步骤 4：固定 Z 偏移补偿

由于 Touch 戳床过程中可能产生挤压偏差，需要手动测定固定偏移：

1. 在网页界面上使用偏移按钮微调 Z 偏移
2. 调至合适位置后执行：

```gcode
SAVE_TOUCH_OFFSET
```

### 步骤 5：自动 Z 偏移测量

```gcode
PROBE_CALIBRATE METHOD=AUTO
```

### 步骤 6：开始打印时加入自动校准

在打印起始 G-code 中添加以下命令，每次打印前自动进行 Touch 校准和 Z 偏移：

```gcode
IDM_TOUCH CALIBRATE=1
PROBE_CALIBRATE METHOD=AUTO
```

## 四、日常使用流程

完成初次配置后，日常使用的推荐流程：

1. 执行 `G28` 归零
2. 执行 `IDM_TOUCH CALIBRATE=1` 自动校准
3. 执行 `PROBE_CALIBRATE METHOD=AUTO` 自动 Z 偏移
4. 开始打印

也可以在打印起始 G-code 中集成以上命令，实现全自动校准。

## 五、注意事项

- 执行 `IDM_THRESHOLD_SCAN` 前务必确保 Z 轴已归零
- Touch 模式要求喷嘴能下降到指定温度（`scanner_touch_max_temp`），确保热端配置正确
- 更换 PEI 板或喷嘴后建议重新执行 `IDM_THRESHOLD_SCAN`

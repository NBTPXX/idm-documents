# 双 CAN UUID 查询需求

## 术语

- **Katapult UUID**：处于 Katapult 引导程序的 CAN 设备标识，用于刷写。
- **Klipper MCU UUID**：运行 Klipper 主固件的 CAN MCU 标识，用于 `canbus_uuid` 配置。

## 需求

### 需求 1：双通道查询

**用户故事：** 作为打印机用户，我希望同时查看两类 CAN UUID，并选择任一查询结果用于刷写。

1. WHEN 用户查询 CAN 设备，刷写页面 SHALL 返回 Katapult UUID 和 Klipper MCU UUID 两个分组。
2. WHEN 存在 Katapult UUID，刷写页面 SHALL 将第一个 Katapult UUID 填入刷写输入框。
3. WHEN 查询结果包含 Katapult UUID 或 Klipper MCU UUID，刷写页面 SHALL 为每个 UUID 提供选择控件。
4. WHEN 用户选择任一 UUID，刷写页面 SHALL 将该 UUID 填入刷写输入框。
5. IF 任一分组查询失败，刷写页面 SHALL 展示另一分组的可用结果和原始命令输出。

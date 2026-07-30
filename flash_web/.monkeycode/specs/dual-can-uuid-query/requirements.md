# 双 CAN UUID 查询需求

## 术语

- **Katapult UUID**：处于 Katapult 引导程序的 CAN 设备标识，用于刷写。
- **Klipper MCU UUID**：运行 Klipper 主固件的 CAN MCU 标识，用于 `canbus_uuid` 配置。

## 需求

### 需求 1：双通道查询

**用户故事：** 作为打印机用户，我希望通过 Moonraker 查看 CAN 节点与 Klipper MCU 配置，并选择查询到的 UUID 用于刷写。

1. WHEN 用户查询 CAN 设备，刷写页面 SHALL 调用 Moonraker CAN 接口并显示每个未分配节点的 UUID 与 application。
2. WHEN 用户查询 CAN 设备，刷写页面 SHALL 读取 Klipper `configfile` 对象并显示每个 MCU 配置的 UUID。
3. WHEN Moonraker 提供 MCU 状态常量，刷写页面 SHALL 显示 MCU 型号。
4. WHEN Moonraker 提供 MCU 固件版本，刷写页面 SHALL 显示 MCU 固件版本。
5. WHEN 查询结果包含 UUID，刷写页面 SHALL 为该 UUID 提供选择控件。
6. WHEN 用户选择任一 UUID，刷写页面 SHALL 将该 UUID 填入刷写输入框。
7. IF Moonraker 查询失败，刷写页面 SHALL 显示查询错误。
8. WHEN 查询结果包含 UUID，刷写页面 SHALL 在同一选择控件中显示对应 MCU 情报。
9. WHEN 用户选择 UUID，刷写页面 SHALL 使用高亮样式标识当前选择。
10. WHEN Klipper 注册名为 `abc` 的 MCU 对象，刷写页面 SHALL 按 `[mcu abc]`、`[abc]` 顺序查找 `canbus_uuid` 补充该 MCU 对象。
11. WHEN 刷写页面显示 UUID 选择控件，刷写页面 SHALL 显示名称、应用、使用中状态、型号和固件版本。
12. WHEN 未分配节点与已注册 MCU 具有相同 UUID，刷写页面 SHALL 保留未分配节点记录并使用已注册 MCU 状态补充设备情报。
13. WHEN 未分配 Katapult 节点缺少已注册 MCU 情报，刷写页面 SHALL 发送 Katapult 状态请求并显示返回的型号和软件版本。
14. IF Moonraker 无法查询未分配 CAN 节点，刷写页面 SHALL 继续显示已注册 MCU 的查询结果并记录 CAN 查询错误。

# 双 CAN UUID 查询设计

Feature Name: dual-can-uuid-query
Updated: 2026-07-30

## 描述

CAN 查询接口通过 Moonraker 聚合未分配 CAN 节点、Klipper MCU 配置与 MCU 状态。

## 组件与接口

- `server.py`：调用 `/machine/peripherals/canbus`、`/printer/objects/query?configfile`、`/printer/objects/list` 与 MCU 状态接口。
- `GET /api/devices/can`：返回 `can_devices`；每项包含 UUID、application、MCU 名称、MCU 型号、固件版本和来源。
- `templates/index.html`：使用全宽设备卡片展示 UUID 与元数据；当前选中卡片使用主题强调色高亮。

## 错误处理

CAN 接口不可用时返回 Moonraker 错误。配置与 MCU 状态缺失时保留可用的 CAN 节点结果，并将缺失的元数据显示为未知。

已注册 MCU 使用运行时状态记录，并按 `[mcu 名称]`、`[名称]` 顺序从配置段补充 `canbus_uuid`。

相同 UUID 的未分配节点与已注册 MCU 记录合并为一个未分配节点记录，并从已注册 MCU 状态填充名称、型号和固件版本。

未匹配已注册 MCU 的 Katapult 节点使用 `flashtool.py -u <uuid> -s` 获取引导器返回的 MCU 类型和软件版本。

Moonraker 无法绑定 CAN 接口时，接口保留已注册 MCU 查询结果，并将 CAN 查询错误写入原始输出。

已注册 MCU 仅在 Moonraker 状态包含 `mcu_constants` 或 `mcu_version` 时显示，确保页面仅列出已连接设备。

## 测试策略

使用模拟 Moonraker 响应验证未分配节点、配置 MCU、型号提取和兼容 UUID 数组；验证页面选择按钮与四种语言键。

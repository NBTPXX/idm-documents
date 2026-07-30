# 双 CAN UUID 查询设计

Feature Name: dual-can-uuid-query
Updated: 2026-07-30

## 描述

CAN 查询接口执行 Katapult 与 Klipper 两条受控查询命令，并将结果按用途分组返回。

## 组件与接口

- `server.py`：执行 `flashtool.py -q` 获取 Katapult UUID；执行 `canbus_query.py` 获取运行中 Klipper MCU UUID。
- `GET /api/devices/can`：返回 `katapult_uuids`、`klipper_uuids`、兼容字段 `devices` 及命令输出。
- `templates/index.html`：分组显示两类 UUID，仅自动填充 Katapult UUID。

## 错误处理

Klipper 查询失败时保留 Katapult 查询结果，并将失败信息附加到原始输出。

## 测试策略

验证接口返回两类数组；验证页面仅将 Katapult UUID 写入刷写输入框；验证翻译键覆盖四种语言。

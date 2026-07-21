# Moonraker 集成

IDM Flash Web 可以与 Klipper 生态系统的 Moonraker API 服务器集成，实现在 Fluiid/Mainsail 中管理服务。

## 自动配置

运行 `install.sh` 后会自动配置两项：

### update_manager

在 `moonraker.conf` 中添加：

```ini
[update_manager idm_flash_web]
type: git_repo
channel: dev
path: ~/idm-documents
origin: https://gitee.com/NBTP/idm-documents.git
is_system_service: False
managed_services: idm_flash_web
info_tags:
    desc=IDM Flash Web Tool
```

### moonraker.asvc

在 `~/printer_data/moonraker.asvc` 中添加 `idm_flash_web`，允许 Moonraker 管理该服务。

## 功能

- **在线更新**：在 Fluiid/Mainsail 的 Update Manager 中一键更新 Flash Web
- **服务管理**：在 Services 面板中查看、启停 `idm_flash_web` 服务
- **状态查看**：通过 Moonraker API 获取打印机连接状态

## 浏览器集成

通过 Moonraker 的 `/printer/info` 端点获取打印机信息，在前端显示 Moonraker 连接状态。

## 手动配置

如果自动配置失败，可以手动添加上述配置到 `moonraker.conf`，以及将 `idm_flash_web` 添加到 `~/printer_data/moonraker.asvc`。

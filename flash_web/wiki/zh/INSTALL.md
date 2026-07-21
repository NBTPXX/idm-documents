# 安装指南

## 环境要求

- 运行 Klipper 的上位机（树莓派、香橙派等，Debian/Ubuntu 系统）
- Python 3.7+
- pyserial（通过 pip 安装或随 Klipper 安装）

## 一键安装

```bash
cd ~/idm-documents/flash_web
./install.sh
```

安装脚本会自动完成：

1. 设置可执行权限
2. 配置 Moonraker `update_manager`（支持在线更新）
3. 安装 systemd 服务并设为开机自启
4. 启动 Web 服务（端口 8888）

## 手动启动

```bash
cd ~/idm-documents/flash_web
python3 server.py
```

## 验证安装

```bash
curl http://localhost:8888/api/env
```

应返回 JSON 格式的环境信息，包含 CAN/USB/DFU 可用性检测结果。

## 访问 Web 界面

浏览器打开：`http://<打印机IP>:8888`

如需嵌入 Mainsail/Fluidd，可使用 iframe：

```html
<iframe src="http://localhost:8888" style="width:100%;height:100vh"></iframe>
```

## 卸载

```bash
cd ~/idm-documents/flash_web
./uninstall.sh
```

卸载脚本会：
1. 停止并移除 systemd 服务
2. 从 `moonraker.asvc` 中移除条目
3. 从 `moonraker.conf` 中移除 `[update_manager]` 配置

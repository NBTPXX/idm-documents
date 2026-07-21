# USB 模式刷写

USB 模式通过串口与设备通信，适用于使用 USB 串口连接的 IDM 传感器。

## 选择 USB 模式

在 Web 界面顶部点击 **USB 模式** 选项卡。

## 串口选择

- **串口端口**：选择设备的常规串口（如 `/dev/serial/by-id/usb-IDM_*`）
- **Bootloader 串口**：设备进入 bootloader 后的串口。如果设备已在 bootloader 模式，可直接填写此字段，无需填写常规串口

设备列表自动过滤，仅显示包含 "IDM" 的设备。

## 固件选择

USB 模式下会显示所有可用固件文件，不做频率筛选。

## 进出 Bootloader

- **Enter BL (进入 BL)**：通过 Katapult 串口协议发送 `KLIPPER_REBOOT_CMD`，使设备进入 bootloader 模式
- **Exit BL (退出 BL)**：使用 Katapult 协议的 `prime + CONNECT + COMPLETE` 序列退出 bootloader，此实现不依赖 DTR 切换

## 自动检测 Bootloader

点击「检测 BL」按钮自动扫描 bootloader 设备：
- 如果当前端口已是 bootloader 设备（名称含 `katapult` 或 `canboot`），直接确认
- 否则扫描 `/dev/serial/by-id/*` 和 `/dev/ttyUSB*`、`/dev/ttyACM*`

若设备已在 bootloader 模式，填写 `boot-serial` 字段即可跳过检测步骤，直接刷写。

## 刷写流程

1. 选择 USB 模式
2. 选择串口（或填写 bootloader 串口）
3. 选择固件类型、版本和文件
4. 若非 bootloader 模式，点击「Enter BL」
5. 点击「开始刷写」
6. 观察控制台输出，等待刷写完成

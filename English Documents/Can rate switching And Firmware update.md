## CAN Frequency Switching

> **Version Compatibility Note:** Newer Klipper has replaced `CanBoot` with `Katapult`. The flash tool path and usage differ. If your Klipper uses Katapult, refer to the **Katapult (new)** commands below; if still using legacy CanBoot, use the **CanBoot (legacy)** commands. To check which version you have:
>
> ```bash
> test -f ~/klipper/lib/katapult/flashtool.py && echo "Katapult (new)" || echo "CanBoot (legacy)"
> ```

First, connect to the host computer.

Recompile the firmware for the CAN communication device (U2C or Can Bridge) directly connected to the host computer and set the frequency to 1M to communicate with IDM.

Use the following command to query IDM's UUID:

**CanBoot (legacy):**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -q
```

**Katapult (new):**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -q
```

Download the required frequency IDM firmware and bootloader overlay firmware from the cloud drive.

Execute the following command:

**CanBoot (legacy):**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <path to canboot update firmware> -u <UUID obtained>
```

**Katapult (new):**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -f <path to katapult update firmware> -u <UUID obtained>
```

For example, `<path to canboot update firmware>` could be ~/Canboot 1M.bin. Fill in your data and remember to remove the `< >` brackets.

Wait for the execution to complete, then enter:

**CanBoot (legacy):**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <path to new frequency IDM firmware> -u <UUID obtained>
```

**Katapult (new):**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -f <path to new frequency IDM firmware> -u <UUID obtained>
```
For example, `<path to new frequency IDM firmware>` could be ~/IDM_CAN_8kib_offset_1M.bin. Fill in your data and remember to remove the `< >` brackets.

If you want to switch to USB communication, you can flash firmware with the USB label using the same method and solder the mode-setting jumper on the back of IDM to the side with USB.

## If you are currently using USB firmware and want to update or switch to CAN mode:

```bash
cd ~/klipper/scripts 
~/klippy-env/bin/python -c 'import flash_usb as u; u.enter_bootloader("<your device serial port address>")'
cd ~
```

**CanBoot (legacy):**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <firmware path> -d <your device serial port address>
```

**Katapult (new):**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -d <your device serial port address> -f <firmware path>
```

The device serial port address refers to the address in the format /dev/serial/by-id/****. Please note that the serial port number for the second time should be different. Re-query it.

Fill in your data and remember to remove the `< >` brackets.
#### via DFU
if you managed to get your idm into dfu mode,
you can use the command below to upload bootloader,  
please note that this method is only applicable to bootloader with usb communication.  
if you are trying to upload bootloader for CAN version, please use the second one (the command for main Firmware).  
```
sudo dfu-util -d ,0483:df11 -R -a 0 -s 0x8000000:leave -D <Where The Firmware Is>  
```
and the command below to upload main firmware
```
sudo dfu-util -d ,0483:df11 -R -a 0 -s 0x8002000:leave -D <Where The Firmware Is>
```
Fill in your data and remember to remove the `< >` brackets.Please note that these two commands are different
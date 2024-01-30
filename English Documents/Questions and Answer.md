**Q1: I encountered an "Internal error during connect: IDM model convergence" error. What does it mean, and how can I resolve it?**

**A:** If you encounter this error, it indicates that the Z-offset value is too large. Please set the `model_offset` in the configuration file to 0 and readjust the Z-offset. If you are unable to control the Z-offset to within 1mm, redo the `idm_calibrate` calibration process.

**Q2: I received an error message at the bottom with content similar to the image below. What should I do?**

![error1](/imgs/error1.png)

**A:** If you see this error, it suggests that you need to update the IDM firmware to the latest version available on the provided cloud storage.
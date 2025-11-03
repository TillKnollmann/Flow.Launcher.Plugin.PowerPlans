# Lenovo Legion Power LED Support

This plugin includes experimental support for controlling the power LED on Lenovo Legion laptops when switching power plans.

## How It Works

On Lenovo Legion devices, the power LED changes color based on the active power plan:
- **Power Saver**: White/Blue LED
- **Balanced**: White LED  
- **High Performance**: Red LED

This plugin attempts to replicate this behavior when switching power plans through Flow Launcher.

## Requirements

### For Lenovo Legion LED Support

1. **Lenovo Legion Laptop**: This feature only works on Lenovo Legion series laptops
2. **Windows Operating System**: LED control uses Windows-specific APIs
3. **Python WMI Library**: Required for LED control via Windows Management Instrumentation

To install the WMI library:
```bash
pip install wmi pywin32
```

## Enabling Lenovo Legion LED Support

The feature is **disabled by default** to avoid impacting non-Legion devices.

To enable it:

1. Navigate to the plugin's cache directory:
   ```
   %APPDATA%\FlowLauncher\Plugins\Power Plans-{version}\.cache\
   ```

2. Open `settings.json` in a text editor

3. Change `lenovo_legion_led_enabled` from `false` to `true`:
   ```json
   {
     "lenovo_legion_led_enabled": true
   }
   ```

4. Restart Flow Launcher

## How LED Control Works

The implementation uses multiple methods to control the LED:

1. **WMI (Primary Method)**: Uses Windows Management Instrumentation to communicate with Lenovo's hardware control interfaces
   - Attempts to use `LENOVO_LIGHTING_METHOD` WMI class
   - Falls back to `LENOVO_GAMEZONE_DATA` if available
   
2. **Fallback Methods**: Additional methods may be attempted if WMI fails

## Device Detection

When enabled, the plugin:
1. Checks if the manufacturer is "Lenovo"
2. Checks if the model contains "Legion"
3. Only activates LED control if both conditions are met

This ensures the feature doesn't interfere with non-Legion devices.

## Troubleshooting

### LED doesn't change color

1. **Verify you have a Lenovo Legion laptop**: Run `wmic computersystem get manufacturer,model` in Command Prompt
2. **Install WMI library**: Run `pip install wmi pywin32`
3. **Check settings**: Ensure `lenovo_legion_led_enabled` is set to `true` in `settings.json`
4. **Restart Flow Launcher**: Changes to settings require a restart

### LED control conflicts with Lenovo Vantage/Legion Toolkit

If you have Lenovo Vantage or third-party tools like Legion Toolkit installed, they may override the LED settings. In this case:
- The plugin will still attempt to set the LED, but the other software may immediately change it back
- Consider disabling LED control in the other software, or disable this feature in the plugin

## Technical Details

### Implementation

The LED control is implemented in `lenovo_legion_led.py` and is:
- **Weakly coupled**: Failures don't affect core power plan switching
- **Silent**: Errors are caught and ignored to prevent disruption
- **Efficient**: Device detection is cached to minimize overhead
- **Opt-in**: Must be explicitly enabled to activate

### Color Mapping

The plugin maps Windows default power plan GUIDs to LED colors:
- `a1841308-3541-4fab-bc81-f71556f20b4a` (Power Saver) → White
- `381b4222-f694-41f0-9685-ff5bb260df2e` (Balanced) → White
- `8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c` (High Performance) → Red

Custom power plans default to White LED.

## References

This implementation is based on:
- [Lenovo Legion Toolkit](https://github.com/BartoszCichecki/LenovoLegionToolkit) - Community reverse engineering project
- [Lenovo WMI Interface Documentation](https://download.lenovo.com/pccbbs/mobiles_pdf/wmi_interface.pdf)
- [Lenovo Legion Linux Support](https://github.com/SmokelessCPU/Lenovo_Legion_Linux) - Linux kernel module with WMI details

## Disclaimer

This feature is **experimental** and based on reverse engineering. It may not work on all Lenovo Legion models due to:
- Different WMI implementations across models
- BIOS/firmware differences
- Regional variations

If the feature doesn't work on your device, please open an issue with:
- Your exact Legion model
- BIOS version
- Windows version
- Any error logs (check Flow Launcher logs)

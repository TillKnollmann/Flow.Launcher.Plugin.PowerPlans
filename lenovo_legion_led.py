# -*- coding: utf-8 -*-

"""
Lenovo Legion Power LED Controller

This module provides support for controlling the power LED on Lenovo Legion laptops
when switching power plans. The LED color changes based on the active power plan:
- Power Saver: White/Blue LED
- Balanced: White LED  
- High Performance: Red LED

Implementation Notes:
- Uses WMI (Windows Management Instrumentation) for LED control
- Only activates on Lenovo Legion devices when explicitly enabled
- Weakly coupled to the main plugin - failures are silent and don't affect core functionality
- Based on reverse engineering of Lenovo Vantage/Legion Toolkit behavior

References:
- Lenovo Legion Toolkit: https://github.com/BartoszCichecki/LenovoLegionToolkit
- Lenovo WMI documentation: https://download.lenovo.com/pccbbs/mobiles_pdf/wmi_interface.pdf
- Community findings: https://github.com/SmokelessCPU/Lenovo_Legion_Linux
"""

import subprocess
import json
import os
import platform

# Try to import WMI at module level for better performance
try:
    import wmi
    _WMI_MODULE = wmi
except ImportError:
    _WMI_MODULE = None


class LenovoLegionLED:
    """Manages Lenovo Legion power LED based on power plan changes."""
    
    # LED color codes based on power plan GUIDs
    # These mappings are based on default Lenovo behavior
    POWER_PLAN_LED_COLORS = {
        "a1841308-3541-4fab-bc81-f71556f20b4a": "white",      # Power saver
        "381b4222-f694-41f0-9685-ff5bb260df2e": "white",      # Balanced
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "red",        # High performance
    }
    
    # WMI color code mapping
    WMI_COLOR_CODES = {
        "white": 1,
        "red": 2,
        "blue": 3,
    }
    
    # WMI LED control constants
    WMI_LED_ZONE_POWER = 0
    WMI_LED_BRIGHTNESS_MAX = 100
    
    def __init__(self, settings_file_path):
        """
        Initialize the Lenovo Legion LED controller.
        
        Args:
            settings_file_path: Path to the settings JSON file
        """
        self._settings_file_path = settings_file_path
        self._enabled = False
        self._is_legion_device = False
        self._wmi_available = False
        self._initialize()
    
    def _initialize(self):
        """Initialize settings and check if device is Lenovo Legion."""
        self._load_settings()
        if self._enabled:
            self._check_device()
            self._check_wmi_availability()
    
    def _load_settings(self):
        """Load settings from the settings file."""
        try:
            if os.path.exists(self._settings_file_path):
                with open(self._settings_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._enabled = data.get('lenovo_legion_led_enabled', False)
        except Exception:
            # Silently ignore - defaults to disabled
            self._enabled = False
    
    def _check_device(self):
        """Check if the current device is a Lenovo Legion laptop."""
        try:
            # Check system manufacturer using WMIC
            output = subprocess.check_output(
                ["wmic", "computersystem", "get", "manufacturer"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore').lower()
            
            is_lenovo = "lenovo" in output
            
            if not is_lenovo:
                return
            
            # Check if it's a Legion model
            model_output = subprocess.check_output(
                ["wmic", "computersystem", "get", "model"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore').lower()
            
            self._is_legion_device = "legion" in model_output
            
        except Exception:
            # If detection fails, assume not a Legion device
            self._is_legion_device = False
    
    def _check_wmi_availability(self):
        """Check if WMI Python library is available."""
        # WMI module is imported at the top level, just check if it's available
        self._wmi_available = _WMI_MODULE is not None
    
    def is_supported(self):
        """
        Check if Lenovo Legion LED control is supported on this device.
        
        Returns:
            bool: True if enabled, device is Legion, and on Windows
        """
        return (self._enabled and 
                self._is_legion_device and 
                platform.system() == "Windows")
    
    def set_led_for_power_plan(self, power_plan_guid):
        """
        Set the LED color based on the power plan GUID.
        
        Args:
            power_plan_guid: The GUID of the power plan being activated
        """
        if not self.is_supported():
            return
        
        color = self._get_led_color_for_plan(power_plan_guid)
        if color:
            self._set_led_color(color)
    
    def _get_led_color_for_plan(self, power_plan_guid):
        """
        Determine the LED color for a given power plan GUID.
        
        Args:
            power_plan_guid: The power plan GUID
            
        Returns:
            str: LED color ("red", "white", "blue") or None
        """
        # Normalize GUID
        guid_lower = power_plan_guid.lower()
        
        # Check if it's a known default power plan
        if guid_lower in self.POWER_PLAN_LED_COLORS:
            return self.POWER_PLAN_LED_COLORS[guid_lower]
        
        # For custom plans, we could try to infer from the name,
        # but for now, default to white for unknown plans
        return "white"
    
    def _set_led_color(self, color):
        """
        Set the LED color using the available method.
        
        Args:
            color: LED color to set ("red", "white", "blue")
        """
        # Try WMI method first (most reliable)
        if self._wmi_available:
            if self._set_led_via_wmi(color):
                return
        
        # Fallback to PowerShell/registry method
        self._set_led_via_powershell(color)
    
    def _set_led_via_wmi(self, color):
        """
        Set LED color using WMI.
        
        Args:
            color: LED color to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        if _WMI_MODULE is None:
            return False
            
        try:
            # Connect to WMI
            c = _WMI_MODULE.WMI(namespace="root\\WMI")
            
            # Try to find Lenovo lighting control
            # Different Legion models use different WMI classes
            # Common ones: LENOVO_LIGHTING_METHOD, LENOVO_GAMEZONE_DATA
            
            # Color codes vary by model, but commonly:
            # 0 or 1 = White, 2 = Red, 3 = Blue
            color_code = self._get_wmi_color_code(color)
            
            # Attempt method 1: LENOVO_LIGHTING_METHOD
            try:
                lighting_methods = c.LENOVO_LIGHTING_METHOD()
                for method in lighting_methods:
                    # Set lighting method - parameters vary by model
                    # Common signature: SetLighting(zone, color, brightness)
                    method.SetLighting(
                        self.WMI_LED_ZONE_POWER,
                        color_code,
                        self.WMI_LED_BRIGHTNESS_MAX
                    )
                    return True
            except Exception:
                pass
            
            # Attempt method 2: LENOVO_GAMEZONE_DATA  
            try:
                gamezone_data = c.LENOVO_GAMEZONE_DATA()
                for data in gamezone_data:
                    # Try setting the power LED
                    # Format: "PowerLED:<color_code>"
                    data.SetData(f"PowerLED:{color_code}")
                    return True
            except Exception:
                pass
            
            # If we get here, WMI methods didn't work
            return False
            
        except Exception:
            # WMI operation failed
            return False
    
    def _get_wmi_color_code(self, color):
        """
        Convert color name to WMI color code.
        
        Args:
            color: Color name string
            
        Returns:
            int: WMI color code
        """
        return self.WMI_COLOR_CODES.get(color.lower(), 1)  # Default to white
    
    def _set_led_via_powershell(self, color):
        """
        Placeholder for PowerShell/registry-based LED control.
        
        This method is not currently implemented because:
        1. Registry key locations vary significantly between Legion models
        2. Requires administrator rights to modify registry
        3. WMI method (primary approach) is more reliable and portable
        
        Future implementation could attempt registry manipulation as a fallback
        when WMI is not available, but this is left for future enhancement.
        
        Args:
            color: LED color to set (unused in current implementation)
        """
        # Placeholder - not implemented
        # If you wish to contribute a registry-based implementation,
        # please refer to Lenovo Legion Toolkit for guidance:
        # https://github.com/BartoszCichecki/LenovoLegionToolkit
        pass


def create_default_settings_file(settings_file_path):
    """
    Create a default settings file with Lenovo Legion LED support disabled.
    
    Args:
        settings_file_path: Path where the settings file should be created
    """
    default_settings = {
        "lenovo_legion_led_enabled": False,
        "lenovo_legion_led_info": """Set to true to enable Lenovo Legion power LED control. \
This feature is only available on Lenovo Legion laptops. \
Requires the 'wmi' Python package: pip install wmi pywin32"""
    }
    
    try:
        with open(settings_file_path, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)
    except Exception:
        # Silently ignore if we can't create the file
        pass

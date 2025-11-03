# -*- coding: utf-8 -*-

"""
Power plan activation observer interface and Lenovo-specific implementation.

This module provides an extensible pattern for executing actions when power plans are activated.
"""

import subprocess
import json
import os

# Try to import WMI at module level
try:
    import wmi
    _WMI_MODULE = wmi
except ImportError:
    _WMI_MODULE = None


class PowerPlanActivationObserver:
    """Interface for observing power plan activations."""
    
    def on_power_plan_activated(self, power_plan_guid):
        """
        Called when a power plan is activated.
        
        Args:
            power_plan_guid: The GUID of the activated power plan
        """
        pass


class LenovoLegionLEDObserver(PowerPlanActivationObserver):
    """
    Observer that controls Lenovo Legion power LED when specific power plans are activated.
    
    Lenovo Legion laptops have specific power plans with corresponding LED colors:
    - Lenovo Quiet Mode (Power Saver): White LED
    - Lenovo Balanced Mode: White LED
    - Lenovo Performance Mode: Red LED
    
    The observer only activates when one of these Lenovo-specific power plans is selected.
    System detection is cached to avoid repeated checks.
    """
    
    # Lenovo power plan GUIDs and their LED colors
    # Based on Lenovo Legion Toolkit: https://github.com/BartoszCichecki/LenovoLegionToolkit
    LENOVO_POWER_PLANS = {
        "a1841308-3541-4fab-bc81-f71556f20b4a": 1,  # Power Saver -> White
        "381b4222-f694-41f0-9685-ff5bb260df2e": 1,  # Balanced -> White
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": 2,  # High Performance -> Red
    }
    
    def __init__(self, cache_dir):
        """
        Initialize the Lenovo LED observer.
        
        Args:
            cache_dir: Directory to store cached system detection result
        """
        self._cache_file = os.path.join(cache_dir, "is_lenovo_system.json")
        self._is_lenovo_system = None
    
    def on_power_plan_activated(self, power_plan_guid):
        """Handle power plan activation for Lenovo systems."""
        guid_lower = power_plan_guid.lower()
        
        # Only proceed if this is a Lenovo power plan
        if guid_lower not in self.LENOVO_POWER_PLANS:
            return
        
        # Determine if system is Lenovo (cached)
        if self._is_lenovo_system is None:
            self._is_lenovo_system = self._detect_lenovo_system()
        
        if not self._is_lenovo_system:
            return
        
        # Set LED color for this power plan
        led_color_code = self.LENOVO_POWER_PLANS[guid_lower]
        self._set_led_color(led_color_code)
    
    def _detect_lenovo_system(self):
        """
        Detect if the current system is a supported Lenovo system.
        
        Detection is based on:
        1. Manufacturer must be "Lenovo"
        2. Model must contain "Legion"
        
        Result is cached in .cache/is_lenovo_system.json
        
        Returns:
            bool: True if system is Lenovo Legion, False otherwise
        """
        # Try to load from cache first
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, 'r') as f:
                    data = json.load(f)
                    return data.get('is_lenovo_system', False)
            except Exception:
                pass
        
        # Detect system
        is_lenovo = False
        try:
            # Check manufacturer
            manufacturer = subprocess.check_output(
                ["wmic", "computersystem", "get", "manufacturer"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore').lower()
            
            if "lenovo" not in manufacturer:
                self._save_cache(False)
                return False
            
            # Check model for "Legion"
            model = subprocess.check_output(
                ["wmic", "computersystem", "get", "model"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stderr=subprocess.DEVNULL
            ).decode('utf-8', errors='ignore').lower()
            
            is_lenovo = "legion" in model
        except Exception:
            is_lenovo = False
        
        self._save_cache(is_lenovo)
        return is_lenovo
    
    def _save_cache(self, is_lenovo):
        """Save detection result to cache."""
        try:
            with open(self._cache_file, 'w') as f:
                json.dump({'is_lenovo_system': is_lenovo}, f)
        except Exception:
            pass
    
    def _set_led_color(self, color_code):
        """
        Set LED color using WMI.
        
        Args:
            color_code: 1 for white, 2 for red
        """
        if _WMI_MODULE is None:
            return
        
        try:
            c = _WMI_MODULE.WMI(namespace="root\\WMI")
            
            # Try LENOVO_LIGHTING_METHOD
            try:
                for method in c.LENOVO_LIGHTING_METHOD():
                    method.SetLighting(0, color_code, 100)
                    return
            except Exception:
                pass
            
            # Try LENOVO_GAMEZONE_DATA
            try:
                for data in c.LENOVO_GAMEZONE_DATA():
                    data.SetData(f"PowerLED:{color_code}")
                    return
            except Exception:
                pass
        except Exception:
            pass

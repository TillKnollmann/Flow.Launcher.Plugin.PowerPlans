# -*- coding: utf-8 -*-

import json
import os
import subprocess

import wmi


class PowerPlanActivationObserver:
    """Interface for observing power plan activations."""

    def on_power_plan_activated(self, power_plan_guid):
        pass


class LenovoLegionLEDObserver(PowerPlanActivationObserver):
    """Controls Lenovo Legion power LED when specific power plans are activated."""

    # GUID to LED color code mapping (1=white, 2=red)
    LENOVO_POWER_PLANS = {
        "a1841308-3541-4fab-bc81-f71556f20b4a": 1,  # Power Saver
        "381b4222-f694-41f0-9685-ff5bb260df2e": 1,  # Balanced
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": 2,  # High Performance
    }

    def __init__(self, cache_dir):
        self._cache_file = os.path.join(cache_dir, "lenovo.json")
        self._is_lenovo_system = None

    def on_power_plan_activated(self, power_plan_guid):
        guid_lower = power_plan_guid.lower()

        if guid_lower not in self.LENOVO_POWER_PLANS:
            return

        if self._is_lenovo_system is None:
            self._is_lenovo_system = self._detect_lenovo_system()

        if not self._is_lenovo_system:
            return

        led_color_code = self.LENOVO_POWER_PLANS[guid_lower]
        self._set_led_color(led_color_code)

    def _detect_lenovo_system(self):
        """Detect if system is Lenovo Legion. Cached in .cache/lenovo.json"""
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, "r") as f:
                    data = json.load(f)
                    return data.get("is_lenovo_system", False)
            except Exception:
                pass  # Ignore cache read errors

        is_lenovo = False
        try:
            manufacturer = (
                subprocess.check_output(
                    ["wmic", "computersystem", "get", "manufacturer"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stderr=subprocess.DEVNULL,
                )
                .decode("utf-8", errors="ignore")
                .lower()
            )

            if "lenovo" not in manufacturer:
                self._save_cache(False)
                return False

            model = (
                subprocess.check_output(
                    ["wmic", "computersystem", "get", "model"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stderr=subprocess.DEVNULL,
                )
                .decode("utf-8", errors="ignore")
                .lower()
            )

            is_lenovo = "legion" in model
        except Exception:
            is_lenovo = False

        self._save_cache(is_lenovo)
        return is_lenovo

    def _save_cache(self, is_lenovo):
        try:
            with open(self._cache_file, "w") as f:
                json.dump({"is_lenovo_system": is_lenovo}, f)
        except Exception:
            pass  # Ignore cache write errors

    def _set_led_color(self, color_code):
        """Set LED via WMI. Tries LENOVO_LIGHTING_METHOD then LENOVO_GAMEZONE_DATA."""

        try:
            c = wmi.WMI(namespace="root\\WMI")

            try:
                for method in c.LENOVO_LIGHTING_METHOD():
                    method.SetLighting(0, color_code, 100)
                    return
            except Exception:
                pass  # Ignore errors and try next method

            try:
                for data in c.LENOVO_GAMEZONE_DATA():
                    data.SetData(f"PowerLED:{color_code}")
                    return
            except Exception:
                pass  # Ignore errors
        except Exception:
            pass  # Ignore WMI connection errors

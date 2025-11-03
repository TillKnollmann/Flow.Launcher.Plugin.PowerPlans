# -*- coding: utf-8 -*-

import json
import os
import subprocess


class PowerPlanActivationObserver:
    """Interface for observing power plan activations."""

    def on_power_plan_activated(self, power_plan_guid):
        pass


class LenovoLegionLEDObserver(PowerPlanActivationObserver):
    """Controls Lenovo Legion power LED when specific power plans are activated."""

    LENOVO_POWER_PLANS = {
        "16edbccd-dee9-4ec4-ace5-2f0b5f2a8975": 0,  # Quiet -> blue
        "85d583c5-cf2e-4197-80fd-3789a227a72c": 1,  # Balanced -> white
        "52521609-efc9-4268-b9ba-67dea73f18b2": 2,  # Performance -> red
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
        """Set LED via PowerShell WMI calls."""
        # WMI class name from reverse engineering - may vary by Legion model
        self._try_wmi_method(
            "LENOVO_LIGHTING_METHOD", "SetLighting", [0, color_code, 100]
        )
        # Alternative WMI class - fallback for different Legion models
        self._try_wmi_method(
            "LENOVO_GAMEZONE_DATA", "SetData", [f"PowerLED:{color_code}"]
        )

    def _try_wmi_method(self, wmi_class, method_name, params):
        """Invoke WMI method via PowerShell subprocess."""
        try:
            # Build PowerShell command to invoke WMI method
            # Parameters: zone (0=power LED, uncertain), color, brightness
            params_str = ", ".join(
                str(p) if isinstance(p, int) else f'"{p}"' for p in params
            )

            ps_command = (
                f"Get-WmiObject -Namespace root\\WMI -Class {wmi_class} | "
                f"ForEach-Object {{ $_.{method_name}({params_str}) }}"
            )

            subprocess.run(
                ["powershell", "-Command", ps_command],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                timeout=2,
            )
        except Exception:
            pass  # Ignore errors - WMI class may not exist on this model

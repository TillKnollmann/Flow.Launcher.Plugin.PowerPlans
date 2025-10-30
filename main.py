# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys

parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, "lib"))
sys.path.append(os.path.join(parent_folder_path, "plugin"))

from flowlauncher import FlowLauncher
from system_encoding import SystemEncoding
from default_power_plans import DefaultPowerPlans

class Result:
    """Represents a result entry for Flow Launcher."""

    def __init__(self, title, subtitle, ico_path, json_rpc_action=None, score=0):
        self.title = title
        self.subtitle = subtitle
        self.ico_path = ico_path
        self.json_rpc_action = json_rpc_action
        self.score = score

    def to_json(self):
        return {
            "title": self.title,
            "subTitle": self.subtitle,
            "icoPath": self.ico_path,
            "jsonRPCAction": (
                self.json_rpc_action.to_json() if self.json_rpc_action else None
            ),
            "score": self.score,
        }


class JsonRPCAction:
    """Defines a JSON RPC action for executing commands through Flow Launcher."""

    def __init__(self, method, parameters):
        self.method = method
        self.parameters = parameters

    def to_json(self):
        return {"method": self.method, "parameters": self.parameters}


class PowerPlan:
    """Defines a windows power plan"""

    def __init__(self, identifier, name, icon_path):
        self.identifier = identifier
        self.name = name
        self.icon_path = icon_path

    def switch_to(self):
        PowerPlanManager.switch_to_plan(self.identifier)


class PowerPlanManager:
    """Manages power plans using SystemEncoding and DefaultPowerPlans."""

    DEFAULT_APP_ICON = "Images/app.png"
    UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def __init__(self, system_encoding, default_plans):
        """
        Initializes the PowerPlanManager.

        Args:
            system_encoding: SystemEncoding instance
            default_plans: DefaultPowerPlans instance
        """
        self.system_encoding = system_encoding
        self.default_plans = default_plans

    def get_all_system_plans(self):
        """Retrieves all power plans available on the system using powercfg."""
        plans = []
        found_guids = set()

        try:
            output_bytes = subprocess.check_output(
                ["powercfg", "/list"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = self.system_encoding.decode_output(output_bytes)

            for line in output.split('\n'):
                # search for GUID and name
                match = re.search(
                    r'(' + self.UUID_REGEX + r')\s+\(([^)]+)\)',
                    line,
                    re.IGNORECASE
                )
                if match:
                    guid = match.group(1).lower()
                    name = match.group(2).strip()
                    found_guids.add(guid)

                    if self.default_plans.is_default_plan(guid):
                        # use cached localized name and icon for default plans
                        plan_info = self.default_plans.get_plan(guid)
                        if plan_info:
                            plans.append(PowerPlan(guid, plan_info["name"], plan_info["icon"]))
                        else:
                            # fallback: use system name with default icon
                            plans.append(PowerPlan(guid, name, self.DEFAULT_APP_ICON))
                    else:
                        # custom power plan - use default icon
                        plans.append(PowerPlan(guid, name, self.DEFAULT_APP_ICON))

            # add missing default plans
            for guid in self.default_plans.get_all_guids():
                if guid not in found_guids:
                    plan_info = self.default_plans.get_plan(guid)
                    if plan_info:
                        plans.append(PowerPlan(guid, plan_info["name"], plan_info["icon"]))

        except Exception:
            # fallback: use default plans
            for guid in self.default_plans.get_all_guids():
                plan_info = self.default_plans.get_plan(guid)
                if plan_info:
                    plans.append(PowerPlan(guid, plan_info["name"], plan_info["icon"]))

        return sorted(plans, key=lambda plan: plan.name)

    @staticmethod
    def switch_to_plan(identifier):
        """Switches to the specified power plan."""
        subprocess.call(
            ["powercfg", "/s", identifier],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

    def get_active_plan(self):
        """Returns the GUID of the currently active power plan."""
        try:
            output_bytes = subprocess.check_output(
                ["powercfg", "/GETACTIVESCHEME"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = self.system_encoding.decode_output(output_bytes)

            match = re.search(PowerPlanManager.UUID_REGEX, output, re.IGNORECASE)
            if match:
                return match.group(0)
            else:
                return None
        except Exception:
            return None # silently ignore errors


class PowerPlanSwitcherPlugin(FlowLauncher):
    """Handles user queries and manages results."""

    def __init__(self):
        """Initialize the plugin with encoding and default plans."""

        cache_dir = os.path.join(parent_folder_path, ".cache")
        os.makedirs(cache_dir, exist_ok=True)

        encoding_cache_path = os.path.join(cache_dir, "system_encoding.json")
        self.system_encoding = SystemEncoding(encoding_cache_path)

        plans_cache_path = os.path.join(cache_dir, "default_plans.json")
        self.default_plans = DefaultPowerPlans(self.system_encoding, plans_cache_path)

        self.power_plan_manager = PowerPlanManager(self.system_encoding, self.default_plans)

        super().__init__()

    def query(self, query_text):
        results = []

        power_plans = self.power_plan_manager.get_all_system_plans()
        active_plan = self.power_plan_manager.get_active_plan()
        filtered_power_plans = (
            [p for p in power_plans if query_text.lower() in p.name.lower()]
            if query_text
            else power_plans
        )

        if not filtered_power_plans:
            subtitle = f"No power plan matches '{query_text}'."
            results.append(
                Result(
                    "No matching power plan found",
                    subtitle,
                    PowerPlanManager.DEFAULT_APP_ICON,
                ).to_json()
            )
        else:
            for power_plan in filtered_power_plans:
                name = (
                    power_plan.name + " (active)"
                    if power_plan.identifier == active_plan
                    else power_plan.name
                )
                results.append(
                    Result(
                        title=name,
                        subtitle=f"Switch to '{power_plan.name}'",
                        ico_path=power_plan.icon_path,
                        json_rpc_action=JsonRPCAction(
                            "switch_to", [power_plan.identifier]
                        ),
                    ).to_json()
                )

        return results

    def switch_to(self, power_plan_identifier):
        PowerPlanManager.switch_to_plan(power_plan_identifier)


if __name__ == "__main__":
    PowerPlanSwitcherPlugin()

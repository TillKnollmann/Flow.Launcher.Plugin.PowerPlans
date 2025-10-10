# -*- coding: utf-8 -*-

import sys, os, subprocess, re

parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, "lib"))
sys.path.append(os.path.join(parent_folder_path, "plugin"))

from flowlauncher import FlowLauncher


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
    """Manages power plans"""

    POWER_PLANS_BY_ID = {
        "a1841308-3541-4fab-bc81-f71556f20b4a": PowerPlan(
            "a1841308-3541-4fab-bc81-f71556f20b4a",
            "Power saver",
            "Images/power-saver.png",
        ),
        "381b4222-f694-41f0-9685-ff5bb260df2e": PowerPlan(
            "381b4222-f694-41f0-9685-ff5bb260df2e",
            "Balanced",
            "Images/balanced.png",
        ),
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": PowerPlan(
            "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            "High performance",
            "Images/high-performance.png",
        ),
    }
    UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    @staticmethod
    def switch_to_plan(identifier):
        subprocess.call(
            f"powercfg /s {identifier}", creationflags=subprocess.CREATE_NO_WINDOW
        )

    @staticmethod
    def get_plans():
        return PowerPlanManager.POWER_PLANS_BY_ID.values()

    @staticmethod
    def get_active():
        output = str(
            subprocess.check_output(
                f"powercfg /GETACTIVESCHEME", creationflags=subprocess.CREATE_NO_WINDOW
            )
        )
        return re.search(PowerPlanManager.UUID_REGEX, output, re.IGNORECASE).group(0)


class PowerPlanSwitcherPlugin(FlowLauncher):
    """Handles user queries and manages results."""

    def query(self, query_text):
        results = []

        power_plans = PowerPlanManager.get_plans()
        active_plan = PowerPlanManager.get_active()
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
                        subtitle=f"Switch to {power_plan.name.lower()} power plan",
                        ico_path=power_plan.icon_path,
                        json_rpc_action=JsonRPCAction(
                            "switch_to", [power_plan.identifier]
                        ),
                    ).to_json()
                )

        return results

    def switch_to(self, power_plan_identifier):
        PowerPlanManager.POWER_PLANS_BY_ID.get(power_plan_identifier).switch_to()


if __name__ == "__main__":
    PowerPlanSwitcherPlugin()

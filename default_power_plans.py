# -*- coding: utf-8 -*-

import os
import re
import subprocess
import json


class DefaultPowerPlans:
    """Manages default Windows power plans with localized names and caching."""

    DEFAULT_PLANS_METADATA = {
        "a1841308-3541-4fab-bc81-f71556f20b4a": {
            "name": "Power saver",
            "icon": "Images/power-saver.png",
        },
        "381b4222-f694-41f0-9685-ff5bb260df2e": {
            "name": "Balanced",
            "icon": "Images/balanced.png",
        },
        "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": {
            "name": "High performance",
            "icon": "Images/high-performance.png",
        },
    }

    UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def __init__(self, system_encoding, cache_file_path):
        """
        Initializes the DefaultPowerPlans manager.

        Args:
            system_encoding: SystemEncoding instance for decoding powercfg output
            cache_file_path: Path to the JSON file for caching the localized plan names
        """
        self._system_encoding = system_encoding
        self._cache_file_path = cache_file_path
        self._localized_plans = {}
        self._initialize()

    def _initialize(self):
        """Initializes the localized plans by loading from cache or querying system."""
        cached_plans = self._load_from_cache()
        if cached_plans:
            self._localized_plans = cached_plans
            return

        self._build_localized_plans()
        self._save_to_cache(self._localized_plans)

    def _load_from_cache(self):
        """Loads the cached localized plan names from file."""
        try:
            if os.path.exists(self._cache_file_path):
                with open(self._cache_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('plans')
        except Exception:
            pass
        return None

    def _save_to_cache(self, plans):
        """Saves the localized plan names to cache file."""
        try:
            with open(self._cache_file_path, 'w', encoding='utf-8') as f:
                json.dump({'plans': plans}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _build_localized_plans(self):
        """Builds the localized plans dictionary by querying powercfg."""
        for guid, metadata in self.DEFAULT_PLANS_METADATA.items():
            localized_name = self._get_localized_plan_name(guid)
            self._localized_plans[guid] = {
                "name": localized_name if localized_name else metadata["name"],
                "icon": metadata["icon"]
            }

    def _get_localized_plan_name(self, guid):
        """
        Retrieves the localized name for a power plan using powercfg /query.

        Args:
            guid: The GUID of the power plan

        Returns:
            Localized name string or None if not found
        """
        try:
            output_bytes = subprocess.check_output(
                f"powercfg /query {guid}",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            output = self._system_encoding.decode_output(output_bytes)

            # Parse GUID and localized name
            for line in output.split('\n'):
                match = re.search(
                    r'(' + self.UUID_REGEX + r')\s+\(([^)]+)\)',
                    line,
                    re.IGNORECASE
                )
                if match and match.group(1).lower() == guid.lower():
                    return match.group(2).strip()
        except Exception:
            pass
        return None

    def get_plan(self, guid):
        """Returns the localized plan information for a given GUID."""
        return self._localized_plans.get(guid)

    def is_default_plan(self, guid):
        """Checks if a GUID corresponds to a default Windows power plan."""
        return guid in self.DEFAULT_PLANS_METADATA

    def get_all_guids(self):
        """Returns a set of all default plan GUIDs."""
        return set(self.DEFAULT_PLANS_METADATA.keys())

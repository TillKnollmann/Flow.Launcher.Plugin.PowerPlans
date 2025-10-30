# -*- coding: utf-8 -*-

import os
import re
import subprocess
import json


class SystemEncoding:
    """Manages system console encoding detection and caching."""

    def __init__(self, cache_file_path):
        """
        Initializes the SystemEncoding manager.

        Args:
            cache_file_path: Path to the JSON file for caching the encoding
        """
        self._cache_file_path = cache_file_path
        self._encoding = None
        self._initialize()

    def _initialize(self):
        """Initializes the encoding by loading from cache or detecting it."""
        cached_encoding = self._load_from_cache()
        if cached_encoding:
            self._encoding = cached_encoding
            return

        self._encoding = self._detect_encoding()
        self._save_to_cache(self._encoding)

    def _load_from_cache(self):
        """Loads the cached encoding from file."""
        try:
            if os.path.exists(self._cache_file_path):
                with open(self._cache_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('encoding')
        except Exception:
            pass # silently ignore cache load errors
        return None

    def _save_to_cache(self, encoding):
        """Saves the encoding to cache file."""
        try:
            with open(self._cache_file_path, 'w', encoding='utf-8') as f:
                json.dump({'encoding': encoding}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass # silently ignore cache save errors

    def _detect_encoding(self):
        """Detects the current system console encoding by running chcp."""
        try:
            chcp_output = subprocess.check_output(
                ["chcp"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                shell=True # needed for chcp on Windows
            )
            # parse output to find any number (the codepage)
            match = re.search(r'(\d+)', chcp_output.decode('ascii', errors='ignore'))
            if match:
                codepage = match.group(1)
                return f'cp{codepage}'
        except Exception:
            pass # silently ignore detection errors

        return 'cp850'

    def get_encoding(self):
        """Returns the system encoding."""
        return self._encoding

    def decode_output(self, output_bytes):
        """Decodes subprocess output bytes using system encoding."""
        return output_bytes.decode(self._encoding, errors='replace')

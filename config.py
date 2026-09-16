"""
API TEST CLI - Configuration & Profile Persistence Manager
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

CONFIG_DIR = Path.home() / ".api_test_cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_PRESETS = [
    {
        "name": "OpenAI Official",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "default_model": "gpt-4o-mini",
    },
    {
        "name": "Groq Cloud (Fast)",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": "",
        "default_model": "llama-3.3-70b-versatile",
    },
    {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
    },
    {
        "name": "Ollama (Localhost)",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "default_model": "llama3.2",
    },
    {
        "name": "vLLM / Local Server",
        "base_url": "http://localhost:8000/v1",
        "api_key": "",
        "default_model": "",
    },
    {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "api_key": "",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    },
    {
        "name": "DeepSeek Official",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "default_model": "deepseek-chat",
    }
]


def sanitize_base_url(url: str) -> str:
    """
    Cleans and normalizes base URL.
    Strips accidental trailing sub-endpoints (/models, /chat/completions).
    Ensures http:// or https:// protocol.
    """
    url = url.strip().rstrip("/")
    if not url:
        return ""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    suffixes = [
        "/chat/completions",
        "/completions",
        "/models",
        "/embeddings",
        "/v1/models",
        "/v1/chat/completions",
    ]
    for s in suffixes:
        if url.endswith(s):
            if s.startswith("/v1/"):
                url = url[:-len(s)] + "/v1"
            else:
                url = url[:-len(s)]
            break

    return url.rstrip("/")


class ConfigManager:
    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self._ensure_config_dir()
        self.data = self._load()

    def _ensure_config_dir(self):
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self.config_file.exists():
            default_config = {
                "active_profile": None,
                "profiles": {},
                "history": [],
            }
            self._save_raw(default_config)
            return default_config

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "active_profile": None,
                "profiles": {},
                "history": [],
            }

    def _save_raw(self, data: Dict[str, Any]):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def save(self):
        self._save_raw(self.data)

    def get_active_profile(self) -> Optional[Dict[str, Any]]:
        active_name = self.data.get("active_profile")
        profiles = self.data.get("profiles", {})
        if active_name and active_name in profiles:
            return profiles[active_name]
        if profiles:
            first_name = next(iter(profiles.keys()))
            self.data["active_profile"] = first_name
            return profiles[first_name]
        return None

    def set_active_profile(self, name: str) -> bool:
        if name in self.data.get("profiles", {}):
            self.data["active_profile"] = name
            self.save()
            return True
        return False

    def save_profile(self, name: str, base_url: str, api_key: str = "", default_model: str = "", timeout: float = 30.0):
        clean_url = sanitize_base_url(base_url)

        if "profiles" not in self.data or not isinstance(self.data["profiles"], dict):
            self.data["profiles"] = {}

        self.data["profiles"][name] = {
            "name": name,
            "base_url": clean_url,
            "api_key": api_key.strip(),
            "default_model": default_model.strip(),
            "timeout": timeout,
        }
        self.data["active_profile"] = name
        self.save()

    def delete_profile(self, name: str) -> bool:
        profiles = self.data.get("profiles", {})
        if name in profiles:
            del profiles[name]
            if self.data.get("active_profile") == name:
                self.data["active_profile"] = next(iter(profiles.keys())) if profiles else None
            self.save()
            return True
        return False

    def list_profiles(self) -> List[Dict[str, Any]]:
        profiles = self.data.get("profiles", {})
        if isinstance(profiles, dict):
            return list(profiles.values())
        return []

    def has_configured_profile(self) -> bool:
        profile = self.get_active_profile()
        return bool(profile and profile.get("base_url"))

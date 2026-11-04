from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).resolve().parent
PROFILE_STORE = BASE_DIR / "profiles.json"

DEFAULT_PROFILES: Dict[str, int] = {
    "low": 20,
    "medium": 10,
    "strict": 3,
}


def _normalize_profiles(data: Dict[str, int]) -> Dict[str, int]:
    normalized: Dict[str, int] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        if not isinstance(value, int):
            raise ValueError(f"Risk threshold for {key!r} must be an integer")
        if value < 0:
            raise ValueError(f"Risk threshold for {key!r} must be non-negative")
        normalized[key] = value
    return normalized


def load_profiles() -> Dict[str, int]:
    profiles = dict(DEFAULT_PROFILES)
    if PROFILE_STORE.exists():
        raw = json.loads(PROFILE_STORE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("profiles.json must contain an object")
        profiles.update(_normalize_profiles(raw))
    return profiles


def save_profiles(profiles: Dict[str, int]) -> None:
    PROFILE_STORE.write_text(json.dumps(_normalize_profiles(profiles), indent=2), encoding="utf-8")


def get_threshold(profile_name: str) -> int:
    profiles = load_profiles()
    try:
        return profiles[profile_name]
    except KeyError as exc:
        raise ValueError(f"Unknown risk profile: {profile_name}") from exc


def list_profiles() -> list[str]:
    return sorted(load_profiles().keys())


def set_profile(profile_name: str, threshold: int) -> Dict[str, int]:
    if not isinstance(threshold, int):
        raise ValueError("Threshold must be an integer")
    if threshold < 0:
        raise ValueError("Threshold must be non-negative")
    profiles = load_profiles()
    profiles[profile_name] = threshold
    save_profiles(profiles)
    return profiles


def delete_profile(profile_name: str) -> Dict[str, int]:
    if profile_name in DEFAULT_PROFILES:
        raise ValueError(f"Cannot delete built-in profile: {profile_name}")
    profiles = load_profiles()
    if profile_name not in profiles:
        raise ValueError(f"Unknown risk profile: {profile_name}")
    del profiles[profile_name]
    save_profiles(profiles)
    return profiles

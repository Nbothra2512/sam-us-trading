# Copyright (c) 2026 Smart Touch Infotech Private Limited. All rights reserved.
# SAM (Smart Analyst for Markets) — Proprietary Software

"""Server-side user data storage — chat history, preferences, P&L snapshots.
Persists to /app/data/user_data.json on Railway volume.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "user_data.json")


def _load() -> dict:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception:
            return _default()
    return _default()


def _default() -> dict:
    return {
        "chat_tabs": [{"id": "general", "name": "General"}],
        "chat_history": {},
        "preferences": {"theme": "dark"},
        "pnl_snapshots": [],
    }


def _save(data: dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ─── Chat History ─────────────────────────────────────────────────

def get_chat_tabs() -> list:
    return _load().get("chat_tabs", [{"id": "general", "name": "General"}])


def save_chat_tabs(tabs: list):
    data = _load()
    data["chat_tabs"] = tabs
    _save(data)


def get_chat_history(tab_id: str) -> list:
    return _load().get("chat_history", {}).get(tab_id, [])


def save_chat_history(tab_id: str, messages: list):
    data = _load()
    if "chat_history" not in data:
        data["chat_history"] = {}
    # Keep last 200 messages per tab
    data["chat_history"][tab_id] = messages[-200:]
    _save(data)


def delete_chat_history(tab_id: str):
    data = _load()
    data.get("chat_history", {}).pop(tab_id, None)
    _save(data)


def get_all_chat_data() -> dict:
    """Get tabs + all history in one call."""
    data = _load()
    return {
        "tabs": data.get("chat_tabs", [{"id": "general", "name": "General"}]),
        "history": data.get("chat_history", {}),
    }


def save_all_chat_data(tabs: list, history: dict):
    """Save tabs + all history in one call."""
    data = _load()
    data["chat_tabs"] = tabs
    data["chat_history"] = history
    _save(data)


# ─── Preferences ──────────────────────────────────────────────────

def get_preferences() -> dict:
    return _load().get("preferences", {"theme": "dark"})


def save_preferences(prefs: dict):
    data = _load()
    data["preferences"] = prefs
    _save(data)


# ─── P&L Snapshots ───────────────────────────────────────────────

def get_pnl_snapshots() -> list:
    return _load().get("pnl_snapshots", [])


def save_pnl_snapshot(snapshot: dict):
    """Append a snapshot, keep max 200."""
    data = _load()
    snapshots = data.get("pnl_snapshots", [])
    snapshots.append(snapshot)
    if len(snapshots) > 200:
        snapshots = snapshots[-200:]
    data["pnl_snapshots"] = snapshots
    _save(data)


def save_pnl_snapshots(snapshots: list):
    """Replace all snapshots."""
    data = _load()
    data["pnl_snapshots"] = snapshots[-200:]
    _save(data)

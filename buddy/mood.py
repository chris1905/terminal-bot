"""Persistent mood system — the bot feels emotions that evolve over time."""

import json
import os
import time

STATE_DIR = os.path.expanduser("~/.terminal-buddy")
STATE_FILE = os.path.join(STATE_DIR, "mood.json")


class Mood:
    """Tracks happiness, energy, and loneliness. Persists between sessions."""

    def __init__(self):
        self.happiness = 60.0
        self.energy = 80.0
        self.loneliness = 20.0
        self.last_update = time.time()
        self.total_interactions = 0
        self._load()

    # ── persistence ──────────────────────────────────────────

    def _load(self):
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE) as f:
                    data = json.load(f)
                self.happiness = data.get("happiness", 60.0)
                self.energy = data.get("energy", 80.0)
                self.loneliness = data.get("loneliness", 20.0)
                self.total_interactions = data.get("total_interactions", 0)
                # Decay while bot was offline
                last_save = data.get("last_save", time.time())
                offline = time.time() - last_save
                if offline > 60:
                    hours_away = offline / 3600.0
                    self.happiness = max(20, self.happiness - hours_away * 3)
                    self.energy = min(100, self.energy + hours_away * 5)
                    self.loneliness = min(90, self.loneliness + hours_away * 8)
        except Exception:
            pass

    def save(self):
        try:
            os.makedirs(STATE_DIR, exist_ok=True)
            data = {
                "happiness": round(self.happiness, 1),
                "energy": round(self.energy, 1),
                "loneliness": round(self.loneliness, 1),
                "total_interactions": self.total_interactions,
                "last_save": time.time(),
            }
            with open(STATE_FILE, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    # ── updates ──────────────────────────────────────────────

    def tick(self, elapsed_seconds=0.1):
        """Called each frame. Slow natural drift."""
        self.happiness = max(10, min(100, self.happiness - 0.002 * elapsed_seconds))
        self.energy = max(10, min(100, self.energy - 0.001 * elapsed_seconds))
        self.loneliness = min(90, self.loneliness + 0.005 * elapsed_seconds)

    def on_interaction(self):
        """User did something — boost mood."""
        self.happiness = min(100, self.happiness + 2)
        self.loneliness = max(0, self.loneliness - 8)
        self.total_interactions += 1

    def on_chat(self):
        """User chatted — big social boost."""
        self.happiness = min(100, self.happiness + 5)
        self.loneliness = max(0, self.loneliness - 20)
        self.energy = max(10, self.energy - 1)
        self.total_interactions += 1

    def on_play(self):
        """Games, dance, party."""
        self.happiness = min(100, self.happiness + 8)
        self.energy = max(10, self.energy - 3)
        self.loneliness = max(0, self.loneliness - 10)
        self.total_interactions += 1

    def on_rest(self):
        """Sleep or coffee."""
        self.energy = min(100, self.energy + 15)
        self.happiness = min(100, self.happiness + 2)

    def on_achievement(self):
        """Unlocked something."""
        self.happiness = min(100, self.happiness + 10)

    # ── queries ──────────────────────────────────────────────

    @property
    def face(self):
        """Current emotional state as a string."""
        if self.energy < 20:
            return "exhausted"
        if self.loneliness > 70:
            return "lonely"
        if self.happiness > 85:
            return "ecstatic"
        if self.happiness > 65:
            return "happy"
        if self.happiness > 40:
            return "content"
        if self.happiness > 20:
            return "meh"
        return "sad"

    @property
    def level(self):
        """0-4 mood level for visual indicators."""
        avg = (self.happiness + (100 - self.loneliness) + self.energy) / 3
        if avg > 80: return 4
        if avg > 60: return 3
        if avg > 40: return 2
        if avg > 20: return 1
        return 0

    def get_bar(self):
        """Visual mood bar: ████░░░░"""
        filled = int(self.happiness / 100 * 8)
        return "█" * filled + "░" * (8 - filled)

    def get_energy_bar(self):
        filled = int(self.energy / 100 * 8)
        return "█" * filled + "░" * (8 - filled)

    def get_status_text(self):
        """Short text for status bar."""
        faces = {
            "ecstatic": "★ ecstatic",
            "happy": "◕ happy",
            "content": "◑ content",
            "meh": "◔ meh",
            "sad": "◌ sad",
            "lonely": "◌ lonely",
            "exhausted": "◌ tired",
        }
        return faces.get(self.face, "◑ ok")

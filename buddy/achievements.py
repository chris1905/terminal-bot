"""Achievement tracker with JSON persistence."""

import json
import os
import time

from buddy.data import ACHIEVEMENTS

SAVE_DIR = os.path.expanduser("~/.terminal-buddy")
SAVE_FILE = os.path.join(SAVE_DIR, "achievements.json")

# Counter thresholds that auto-unlock achievements
THRESHOLDS = {
    "chat_count": [(1, "first_chat"), (10, "ten_chats")],
    "joke_count": [(1, "first_joke"), (10, "ten_jokes")],
    "motivate_count": [(1, "first_motivate"), (10, "ten_motivates")],
    "trivia_correct_count": [(1, "trivia_correct"), (5, "five_trivia_correct")],
    "pomodoro_count": [(1, "pomodoro_complete"), (5, "five_pomodoros")],
    "party_count": [(5, "party_animal")],
    "skin_changes": [(3, "skin_changer")],
}


class AchievementTracker:
    def __init__(self, save_path=None):
        self.save_path = save_path or SAVE_FILE
        self.unlocked = {}       # {achievement_id: timestamp}
        self.counters = {}       # {counter_name: int}
        self.pending = []        # Newly unlocked, not yet shown
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.save_path):
                with open(self.save_path, "r") as f:
                    data = json.load(f)
                self.unlocked = data.get("unlocked", {})
                self.counters = data.get("counters", {})
        except (json.JSONDecodeError, OSError):
            self.unlocked = {}
            self.counters = {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            tmp = self.save_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"unlocked": self.unlocked, "counters": self.counters}, f, indent=2)
            os.replace(tmp, self.save_path)
        except OSError:
            pass

    def unlock(self, achievement_id):
        """Unlock an achievement. Returns True if newly unlocked."""
        if achievement_id in self.unlocked:
            return False
        if achievement_id not in ACHIEVEMENTS:
            return False
        self.unlocked[achievement_id] = time.time()
        info = ACHIEVEMENTS[achievement_id]
        self.pending.append(f"{info['icon']} {info['name']}: {info['desc']}")
        self._save()
        return True

    def increment(self, counter_name):
        """Increment counter, auto-check thresholds."""
        self.counters[counter_name] = self.counters.get(counter_name, 0) + 1
        val = self.counters[counter_name]
        if counter_name in THRESHOLDS:
            for threshold, ach_id in THRESHOLDS[counter_name]:
                if val >= threshold:
                    self.unlock(ach_id)
        self._save()
        return val

    def is_unlocked(self, achievement_id):
        return achievement_id in self.unlocked

    def get_notification(self):
        """Pop the next pending notification, or None."""
        if self.pending:
            return self.pending.pop(0)
        return None

    def get_display(self):
        """Format all achievements for display."""
        lines = []
        total = len(ACHIEVEMENTS)
        unlocked = len(self.unlocked)
        for aid, info in ACHIEVEMENTS.items():
            if aid in self.unlocked:
                lines.append(f"  {info['icon']} {info['name']} - {info['desc']}")
            else:
                lines.append(f"  [ ] {info['name']} - ???")
        return lines

    def get_summary(self):
        return f"{len(self.unlocked)}/{len(ACHIEVEMENTS)}"

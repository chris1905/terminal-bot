"""Games: typing race, trivia, pomodoro timer."""

import time
import random

from buddy.data import TYPING_SNIPPETS, TRIVIA
from buddy.ansi import fg, RESET, BOLD, DIM


class TypingRace:
    """Typing speed challenge."""

    def __init__(self):
        self.active = False
        self.target = ""
        self.user_input = ""
        self.start_time = 0.0
        self.finished = False

    def start(self):
        """Start a new race. Returns target text."""
        self.target = random.choice(TYPING_SNIPPETS)
        self.user_input = ""
        self.start_time = time.time()
        self.active = True
        self.finished = False
        return self.target

    def handle_char(self, ch):
        """Process a keystroke. Returns result dict when done, else None."""
        if not self.active:
            return None

        if ch == '\b' or ch == '\x7f':
            if self.user_input:
                self.user_input = self.user_input[:-1]
            return None

        self.user_input += ch

        # Check if complete
        if len(self.user_input) >= len(self.target):
            self.finished = True
            self.active = False
            return self._calculate_result()

        return None

    def _calculate_result(self):
        elapsed = time.time() - self.start_time
        if elapsed < 0.1:
            elapsed = 0.1

        # WPM: words = chars / 5, per minute
        wpm = (len(self.target) / 5.0) / (elapsed / 60.0)

        # Accuracy
        correct = sum(1 for a, b in zip(self.user_input, self.target) if a == b)
        accuracy = (correct / len(self.target)) * 100 if self.target else 0

        return {
            "wpm": wpm,
            "accuracy": accuracy,
            "time": elapsed,
            "correct": self.user_input == self.target,
        }

    def cancel(self):
        self.active = False
        self.finished = False

    def get_display(self):
        """Returns formatted display lines for the race."""
        lines = []
        lines.append("TYPE THIS:")
        lines.append(f"  {self.target}")
        lines.append("")

        # Color-coded user input
        colored = ""
        for i, ch in enumerate(self.user_input):
            if i < len(self.target):
                if ch == self.target[i]:
                    colored += ch  # correct
                else:
                    colored += ch  # wrong (will show in bubble)
            else:
                colored += ch

        lines.append(f"YOU: {self.user_input}")

        remaining = len(self.target) - len(self.user_input)
        if remaining > 0:
            elapsed = time.time() - self.start_time
            lines.append(f"  {remaining} chars left | {elapsed:.1f}s elapsed")

        return "\n".join(lines)


class TriviaGame:
    """Programming trivia questions."""

    def __init__(self):
        self.active = False
        self.current = None
        self.asked = set()

    def start(self):
        """Pick a question. Returns question dict or None if all asked."""
        available = [i for i in range(len(TRIVIA)) if i not in self.asked]
        if not available:
            self.asked.clear()
            available = list(range(len(TRIVIA)))

        idx = random.choice(available)
        self.asked.add(idx)
        self.current = TRIVIA[idx]
        self.active = True
        return self.current

    def handle_answer(self, ch):
        """Process answer (a/b/c/d). Returns (correct, fact)."""
        if not self.active or not self.current:
            return False, ""
        self.active = False
        correct = ch.lower() == self.current["answer"].lower()
        return correct, self.current["fact"]

    def get_display(self):
        """Format question for speech bubble."""
        if not self.current:
            return "No question loaded!"
        lines = [self.current["q"], ""]
        for choice in self.current["choices"]:
            lines.append(f"  {choice}")
        lines.append("")
        lines.append("Press a, b, c, or d to answer!")
        return "\n".join(lines)

    def cancel(self):
        self.active = False


class PomodoroTimer:
    """Pomodoro work/break timer."""

    WORK_SECS = 25 * 60    # 25 minutes
    BREAK_SECS = 5 * 60    # 5 minutes

    def __init__(self):
        self.active = False
        self.phase = "work"  # "work" or "break"
        self.start_time = 0.0
        self.paused = False
        self.pause_elapsed = 0.0
        self.completed = 0

    def start(self):
        """Start a work session."""
        self.active = True
        self.phase = "work"
        self.start_time = time.time()
        self.paused = False
        self.pause_elapsed = 0.0

    def start_break(self):
        """Start a break session."""
        self.phase = "break"
        self.start_time = time.time()
        self.pause_elapsed = 0.0

    def tick(self):
        """Check timer. Returns 'work_done', 'break_done', or None."""
        if not self.active or self.paused:
            return None

        elapsed = time.time() - self.start_time - self.pause_elapsed
        duration = self.WORK_SECS if self.phase == "work" else self.BREAK_SECS

        if elapsed >= duration:
            if self.phase == "work":
                self.completed += 1
                return "work_done"
            else:
                return "break_done"
        return None

    def remaining(self):
        """Formatted remaining time."""
        if not self.active:
            return "00:00"
        elapsed = time.time() - self.start_time - self.pause_elapsed
        duration = self.WORK_SECS if self.phase == "work" else self.BREAK_SECS
        left = max(0, duration - elapsed)
        mins = int(left) // 60
        secs = int(left) % 60
        return f"{mins:02d}:{secs:02d}"

    def cancel(self):
        self.active = False
        self.phase = "work"

    def toggle_pause(self):
        if not self.active:
            return
        if self.paused:
            self.paused = False
            # Adjust start time to account for pause
            self.pause_elapsed += time.time() - self._pause_start
        else:
            self.paused = True
            self._pause_start = time.time()

"""AI-powered features: code roast, commit poet, non-repeating pools."""

import subprocess
import random

from buddy.data import MOTIVATIONAL, JOKES

# ─── Local fallback roasts ───────────────────────────────────────────────────

LOCAL_ROASTS = [
    "I've seen spaghetti with better structure than this code.",
    "This diff has more changes than my therapist recommends in one sitting.",
    "Bold move, pushing code like this on a weekday.",
    "Your variable names tell a story. Unfortunately, it's a horror story.",
    "This code has character. And by character, I mean characters everywhere.",
    "I see you went with the 'job security through obscurity' pattern.",
    "If this code were a building, it would be up to code... building code violations.",
    "You're not writing bugs, you're writing surprise features. So many features.",
    "This looks like it was written with confidence. Misplaced confidence, but confidence.",
    "The good news: it probably works. The bad news: nobody knows why.",
    "I've seen better indentation in a ransom note.",
    "This diff is proof that not all heroes wear capes. Some just press commit.",
]

LOCAL_COMMIT_MSGS = [
    "Lo, the developer hath wrought changes most magnificent upon {n} files",
    "Witness! {n} files transformed by hands both skilled and caffeinated",
    "In the quiet hours, {n} files were blessed with modifications divine",
    "Hark! A commit of great import: {n} files, reborn from the ashes of TODO",
    "And on this day, the code was changed, and it was... probably fine",
    "The sacred {n} files have been anointed with fresh logic and zero tests",
    "Behold: {n} files, lovingly mangled, ready for production",
    "From the depths of the terminal, {n} files emerge, changed forevermore",
]


def get_git_diff_for_roast():
    """Get git diff for roasting. Returns diff string or None."""
    # Try unstaged first, then last commit
    for cmd in [["git", "diff"], ["git", "diff", "HEAD~1"]]:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                diff = result.stdout[:3000]
                if len(result.stdout) > 3000:
                    diff += "\n... (truncated)"
                return diff
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return None


def build_roast_prompt(diff):
    """Build API prompt for a loving code roast."""
    return (
        f"You are a code roaster. Lovingly roast this git diff. Be funny, "
        f"specific about the actual code changes, and end with genuine encouragement. "
        f"Keep it to 3-4 sentences max. Here's the diff:\n\n{diff}"
    )


def get_local_roast():
    """Return a random local roast."""
    return random.choice(LOCAL_ROASTS)


def get_staged_diff():
    """Get staged changes for commit poet. Returns diff string or None."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout[:2000]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def build_commit_poet_prompt(diff):
    """Build API prompt for a dramatic commit message."""
    return (
        f"Write a single dramatic, funny, over-the-top git commit message for these "
        f"staged changes. Make it sound like an epic poem or movie trailer narration. "
        f"One line only, max 72 chars. Here are the changes:\n\n{diff}"
    )


def get_local_commit_msg():
    """Generate a local funny commit message."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat", "--shortstat"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            # Count files from shortstat line
            n = "some"
            for line in lines:
                if "file" in line:
                    parts = line.strip().split()
                    if parts and parts[0].isdigit():
                        n = parts[0]
                    break
            return random.choice(LOCAL_COMMIT_MSGS).format(n=n)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return random.choice(LOCAL_COMMIT_MSGS).format(n="some")


class NonRepeatingPool:
    """Picks items without repeating until all have been seen."""

    def __init__(self, items):
        self.items = list(items)
        self.remaining = list(items)
        random.shuffle(self.remaining)

    def pick(self):
        if not self.remaining:
            self.remaining = list(self.items)
            random.shuffle(self.remaining)
        return self.remaining.pop()

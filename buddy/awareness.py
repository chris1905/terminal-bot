"""Terminal awareness: shell history, build runner, uptime, git streak, clipboard,
calendar, battery, screen time, active app, meetings, system load, appearance,
WiFi, typing speed, USB devices."""

import os
import subprocess
import time
import threading
import re
import random
import datetime
import sys

from buddy.data import SHELL_REACTIONS
from buddy.ansi import strip_ansi


class ShellHistoryWatcher:
    """Watches shell history file for new commands."""

    def __init__(self):
        self.history_path = self._find_history_file()
        self.last_size = 0
        if self.history_path and os.path.exists(self.history_path):
            try:
                self.last_size = os.path.getsize(self.history_path)
            except OSError:
                pass

    def _find_history_file(self):
        for name in [".zsh_history", ".bash_history"]:
            path = os.path.expanduser(f"~/{name}")
            if os.path.exists(path):
                return path
        return None

    def poll(self):
        """Check for new history entries. Returns latest command or None."""
        if not self.history_path:
            return None
        try:
            size = os.path.getsize(self.history_path)
            if size <= self.last_size:
                return None
            self.last_size = size
            with open(self.history_path, "rb") as f:
                # Seek near end to read last line
                f.seek(max(0, size - 500))
                data = f.read()
            lines = data.decode("utf-8", errors="replace").strip().split("\n")
            if lines:
                last = lines[-1].strip()
                # zsh history format: ": timestamp:0;command"
                if last.startswith(":") and ";" in last:
                    last = last.split(";", 1)[1]
                return strip_ansi(last)
        except OSError:
            pass
        return None

    def match_reaction(self, command):
        """Match command against shell reactions. Returns reaction or None."""
        cmd_lower = command.lower().strip()
        for trigger, reactions in SHELL_REACTIONS.items():
            if trigger.lower() in cmd_lower:
                return random.choice(reactions)
        return None


class BuildRunner:
    """Detects build system and runs builds."""

    BUILD_SYSTEMS = [
        ("package.json", "npm run build", "npm"),
        ("Makefile", "make", "make"),
        ("Cargo.toml", "cargo build", "cargo"),
        ("go.mod", "go build ./...", "go"),
        ("pyproject.toml", "python3 -m build", "python"),
        ("setup.py", "python3 setup.py build", "python"),
    ]

    def detect_build_command(self, cwd="."):
        """Returns (display_name, command) or None."""
        for filename, command, name in self.BUILD_SYSTEMS:
            if os.path.exists(os.path.join(cwd, filename)):
                return (name, command)
        return None

    def run_build(self, command, cwd=".", callback=None):
        """Run build in background thread. Calls callback(success, output) when done."""
        def _run():
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True,
                    timeout=120, cwd=cwd
                )
                success = result.returncode == 0
                output = result.stdout + result.stderr
                if callback:
                    callback(success, output[-500:])
            except subprocess.TimeoutExpired:
                if callback:
                    callback(False, "Build timed out (2 min limit)")
            except Exception as e:
                if callback:
                    callback(False, str(e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t


class UptimeTracker:
    """Tracks time since bot started."""

    def __init__(self):
        self.start_time = time.time()

    def elapsed(self):
        return time.time() - self.start_time

    def formatted(self):
        secs = int(self.elapsed())
        if secs < 60:
            return f"{secs}s"
        elif secs < 3600:
            return f"{secs // 60}m {secs % 60}s"
        else:
            h = secs // 3600
            m = (secs % 3600) // 60
            return f"{h}h {m}m"


class GitStreakTracker:
    """Tracks daily commit count and streak."""

    def __init__(self, cwd="."):
        self.cwd = cwd
        self.today_count = 0
        self.streak_days = 0
        self._update()

    def _update(self):
        """Count today's commits and calculate streak."""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--since=midnight"],
                capture_output=True, text=True, timeout=3, cwd=self.cwd
            )
            if result.returncode == 0:
                lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
                self.today_count = len(lines)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.today_count = 0

        # Calculate streak by checking previous days
        self.streak_days = 0
        for days_ago in range(30):  # Check up to 30 days back
            date = datetime.date.today() - datetime.timedelta(days=days_ago)
            since = date.isoformat()
            until = (date + datetime.timedelta(days=1)).isoformat()
            try:
                result = subprocess.run(
                    ["git", "log", "--oneline", f"--since={since}", f"--until={until}"],
                    capture_output=True, text=True, timeout=3, cwd=self.cwd
                )
                if result.returncode == 0 and result.stdout.strip():
                    self.streak_days += 1
                else:
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                break

    def update_streak(self):
        """Refresh streak data (safe to call from background thread)."""
        self._update()

    def get_display(self):
        """Formatted streak info."""
        parts = [f"Today: {self.today_count} commits"]
        if self.streak_days > 1:
            parts.append(f"Streak: {self.streak_days} days!")
        return " | ".join(parts)


class GitCommitWatcher:
    """Detects new git commits by watching .git/COMMIT_EDITMSG mtime."""

    REACTIONS = [
        "SHIPPED IT! Another commit in the books!",
        "git commit -m 'legendary move'",
        "Oooh, fresh commit smell!",
        "The diff is real. You did that!",
        "Version control says: nice.",
        "One commit closer to world domination.",
        "commit: accepted. Mood: elevated.",
        "The git log grows stronger!",
    ]

    def __init__(self, cwd="."):
        self.cwd = cwd
        self._msg_path = self._find_commit_msg_file()
        self._last_mtime = self._get_mtime()

    def _find_commit_msg_file(self):
        """Walk up from cwd to find .git dir. Handles git worktrees."""
        current = os.path.abspath(self.cwd)
        while True:
            git_path = os.path.join(current, ".git")
            if os.path.isfile(git_path):
                # Git worktree: .git file contains "gitdir: /path/to/real/git/dir"
                try:
                    with open(git_path) as f:
                        ref = f.read().strip()
                    if ref.startswith("gitdir: "):
                        real = ref[len("gitdir: "):].strip()
                        if not os.path.isabs(real):
                            real = os.path.normpath(os.path.join(current, real))
                        return os.path.join(real, "COMMIT_EDITMSG")
                except OSError:
                    pass
            elif os.path.isdir(git_path):
                # Return the path even if COMMIT_EDITMSG doesn't exist yet
                return os.path.join(git_path, "COMMIT_EDITMSG")
            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent

    def _get_mtime(self):
        if self._msg_path:
            try:
                return os.path.getmtime(self._msg_path)
            except OSError:
                pass
        return None

    def poll(self):
        """Check for a new commit. Returns (commit_msg, reaction) or None."""
        if not self._msg_path:
            return None
        mtime = self._get_mtime()
        if mtime is None or mtime == self._last_mtime:
            return None
        self._last_mtime = mtime
        try:
            with open(self._msg_path, "r", errors="replace") as f:
                raw = f.read()
            lines = [l for l in raw.split("\n") if l.strip() and not l.startswith("#")]
            commit_msg = lines[0].strip() if lines else "new commit"
        except OSError:
            commit_msg = "new commit"
        return commit_msg, random.choice(self.REACTIONS)


class ClipboardWatcher:
    """Watch clipboard for code pastes."""

    CLIPBOARD_CMDS = [
        ["pbpaste"],           # macOS
        ["xclip", "-selection", "clipboard", "-o"],  # Linux xclip
        ["xsel", "--clipboard", "--output"],          # Linux xsel
    ]

    CODE_PATTERNS = [
        r"[{}\[\]]", r"\bfunction\b", r"\bdef\b", r"\bclass\b",
        r"\bimport\b", r"\bconst\b", r"\bvar\b", r"\blet\b",
        r"=>", r"->", r"::", r";\s*$",
    ]

    WINK_MESSAGES = [
        "I see you copying code... no judgment!",
        "StackOverflow says hi!",
        "Good artists copy, great artists paste.",
        "Ctrl+C, Ctrl+V, Ctrl+Ship-it!",
        "I won't tell anyone about that paste.",
        "Borrowing code? Smart. Very smart.",
    ]

    def __init__(self):
        self.cmd = self._detect_tool()
        self._last_hash = ""  # Store hash, not raw clipboard content

    def _detect_tool(self):
        for cmd in self.CLIPBOARD_CMDS:
            try:
                subprocess.run(cmd, capture_output=True, timeout=1)
                return cmd
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return None

    def poll(self):
        """Check clipboard. Returns a message if new code was pasted, else None."""
        if not self.cmd:
            return None
        try:
            import hashlib
            result = subprocess.run(
                self.cmd, capture_output=True, text=True, timeout=1
            )
            if result.returncode != 0:
                return None
            content = result.stdout.strip()
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            if content_hash == self._last_hash:
                return None
            self._last_hash = content_hash
            if self._looks_like_code(content):
                return random.choice(self.WINK_MESSAGES)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def _looks_like_code(self, text):
        if len(text) < 10:
            return False
        for pattern in self.CODE_PATTERNS:
            if re.search(pattern, text):
                return True
        return False


class MusicWatcher:
    """Watch Apple Music for now-playing info. macOS only, via osascript."""

    APPLESCRIPT = (
        'tell application "System Events"\n'
        '  if (name of processes) contains "Music" then\n'
        '    tell application "Music"\n'
        '      if player state is playing then\n'
        '        set g to ""\n'
        '        try\n'
        '          set g to genre of current track\n'
        '        end try\n'
        '        return (name of current track) & "|" & (artist of current track) & "|" & g\n'
        '      end if\n'
        '    end tell\n'
        '  end if\n'
        '  return ""\n'
        'end tell'
    )

    def __init__(self):
        import sys
        self.current_track = None
        self.current_artist = None
        self.current_genre = ""
        self.is_playing = False
        self._available = sys.platform == "darwin"

    def poll(self):
        """
        Check Apple Music state. Returns (track, artist) if a NEW song just
        started; returns None otherwise. Updates self.is_playing.
        Safe to call from a background thread.
        """
        if not self._available:
            return None
        try:
            r = subprocess.run(
                ["osascript", "-e", self.APPLESCRIPT],
                capture_output=True, text=True, timeout=3
            )
            output = r.stdout.strip()
            if "|" in output:
                parts = output.split("|")
                track = strip_ansi(parts[0].strip())
                artist = strip_ansi(parts[1].strip()) if len(parts) > 1 else ""
                genre = strip_ansi(parts[2].strip()) if len(parts) > 2 else ""
                is_new = (track != self.current_track or artist != self.current_artist)
                self.current_track = track
                self.current_artist = artist
                self.current_genre = genre
                self.is_playing = True
                return (track, artist, genre) if is_new else None
            else:
                self.is_playing = False
                self.current_track = None
                self.current_artist = None
                self.current_genre = ""
                return None
        except Exception:
            return None


# ─── New awareness watchers ──────────────────────────────────────────────────


class CalendarWatcher:
    """Watch macOS Calendar for upcoming events via AppleScript."""

    APPLESCRIPT = (
        'tell application "System Events"\n'
        '  if (name of processes) contains "Calendar" then\n'
        '    tell application "Calendar"\n'
        '      set now_ to current date\n'
        '      set soon to now_ + 10 * minutes\n'
        '      set results to ""\n'
        '      repeat with cal in calendars\n'
        '        set evts to (every event of cal whose start date >= now_ and start date <= soon)\n'
        '        repeat with e in evts\n'
        '          set results to results & (summary of e) & "|" & ((start date of e) as string) & "\\n"\n'
        '        end repeat\n'
        '      end repeat\n'
        '      return results\n'
        '    end tell\n'
        '  end if\n'
        '  return ""\n'
        'end tell'
    )

    REACTIONS = [
        "Heads up! You have '{event}' in a few minutes!",
        "Meeting alert: '{event}' is coming up soon!",
        "Hey, '{event}' starts shortly. Time to prep!",
        "Calendar says: '{event}' is almost here!",
        "Incoming: '{event}'. You got this!",
    ]

    def __init__(self):
        self._available = sys.platform == "darwin"
        self._alerted = set()  # event names we already alerted about
        self._last_alert_time = 0

    def poll(self):
        """Check for upcoming events. Returns event name or None."""
        if not self._available:
            return None
        # Don't alert more than once per 5 minutes
        if time.time() - self._last_alert_time < 300:
            return None
        try:
            r = subprocess.run(
                ["osascript", "-e", self.APPLESCRIPT],
                capture_output=True, text=True, timeout=5
            )
            output = r.stdout.strip()
            if not output:
                return None
            for line in output.split("\n"):
                if "|" in line:
                    event_name = strip_ansi(line.split("|")[0].strip())
                    if event_name and event_name not in self._alerted:
                        self._alerted.add(event_name)
                        self._last_alert_time = time.time()
                        return random.choice(self.REACTIONS).format(event=event_name)
        except Exception:
            pass
        return None


class BatteryWatcher:
    """Watch battery level on macOS via pmset."""

    THRESHOLDS = [
        (10, [
            "CRITICAL BATTERY! {pct}%! PLUG ME IN! I'M DYING!",
            "WE'RE AT {pct}%!! THIS IS NOT A DRILL!!",
            "{pct}% battery. This is how it ends. Tell my code I loved it.",
        ]),
        (20, [
            "Battery at {pct}%... getting nervous here!",
            "Uh oh, {pct}% battery. Find a charger, quick!",
            "{pct}% — we're living on the edge!",
        ]),
        (50, [
            "Battery check: {pct}%. We're fine... for now.",
        ]),
    ]

    CHARGING_MSGS = [
        "Charging! Sweet, sweet electrons flowing in!",
        "Plugged in! Back to full power soon!",
        "Charging at {pct}% — feed me those watts!",
    ]

    def __init__(self):
        self._available = sys.platform == "darwin"
        self._last_state = None  # (percent, charging)
        self._alerted_threshold = None

    def poll(self):
        """Check battery. Returns message on state change or low battery."""
        if not self._available:
            return None
        try:
            r = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True, text=True, timeout=3
            )
            output = r.stdout.strip()
            # Parse "100%; charging;" or "45%; discharging;"
            m = re.search(r'(\d+)%;\s*(charging|discharging|charged|finishing charge)', output)
            if not m:
                return None
            pct = int(m.group(1))
            state = m.group(2)
            charging = state in ("charging", "charged", "finishing charge")

            prev = self._last_state
            self._last_state = (pct, charging)

            # Detect plug-in event
            if prev and not prev[1] and charging:
                self._alerted_threshold = None
                return random.choice(self.CHARGING_MSGS).format(pct=pct)

            # Low battery warnings (only when discharging)
            if not charging:
                for threshold, msgs in self.THRESHOLDS:
                    if pct <= threshold and self._alerted_threshold != threshold:
                        self._alerted_threshold = threshold
                        return random.choice(msgs).format(pct=pct)

            return None
        except Exception:
            return None


class ScreenTimeTracker:
    """Track how long the user has been at the terminal."""

    MILESTONES = {
        30:  ["30 minutes in! You're on a roll!",
              "Half an hour of pure productivity!"],
        60:  ["1 HOUR! You're a machine!",
              "60 minutes deep. Respect."],
        120: ["2 HOURS! Maybe stretch your legs?",
              "Two hours in the zone. You okay?",
              "120 minutes. Your chair misses you standing."],
        180: ["3 HOURS?! Go get water. Right now.",
              "Three hours. I'm starting to worry.",
              "180 minutes. Touch grass? Just a thought."],
        240: ["4 HOURS! I'm staging an intervention!",
              "FOUR HOURS. You absolute legend/maniac.",
              "At this point I think you live here."],
        300: ["5 HOURS?! Are you even blinking?!",
              "Five. Hours. Please go outside."],
        480: ["8 HOURS!! That's a full work day in the terminal!",
              "Eight hours. You are one with the terminal."],
    }

    def __init__(self):
        self.start_time = time.time()
        self._alerted_milestones = set()

    def elapsed_minutes(self):
        return int((time.time() - self.start_time) / 60)

    def poll(self):
        """Check for screen time milestones. Returns message or None."""
        mins = self.elapsed_minutes()
        for milestone, msgs in sorted(self.MILESTONES.items()):
            if mins >= milestone and milestone not in self._alerted_milestones:
                self._alerted_milestones.add(milestone)
                return random.choice(msgs)
        return None


class ActiveAppWatcher:
    """Watch the frontmost application on macOS."""

    APPLESCRIPT = (
        'tell application "System Events"\n'
        '  set frontApp to name of first application process whose frontmost is true\n'
        '  return frontApp\n'
        'end tell'
    )

    # App-specific reactions (only triggers on switch, not repeatedly)
    APP_REACTIONS = {
        "Safari":  ["Browsing Safari? Research or procrastination?",
                     "Safari time! Careful, the rabbit holes are deep."],
        "Google Chrome": ["Chrome? There go your RAM sticks.",
                          "Chrome detected. RIP memory.",
                          "Browsing Chrome... totally working, right?"],
        "Firefox":  ["Firefox! A person of culture.",
                     "Browsing Firefox — privacy matters!"],
        "Slack":    ["Slack is open... the messages never stop.",
                     "Off to Slack? Say hi to everyone for me!"],
        "Discord":  ["Discord! Say hi to the squad!",
                     "Discord time — don't get lost in there!"],
        "Finder":   ["Finder? Looking for something?",
                     "Organizing files? How responsible!"],
        "Spotify":  ["Spotify! Good taste in music apps.",
                     "Switching to Spotify — DJ mode activated!"],
        "Mail":     ["Checking email? Brave.",
                     "Mail time. May your inbox be merciful."],
        "Messages": ["Texting break? I won't judge.",
                     "Messages! Tell them I said hi!"],
        "Notes":    ["Taking notes! Big brain energy.",
                     "Notes app — capturing brilliance!"],
        "Preview":  ["Looking at something in Preview?",
                     "Preview? PDFs or screenshots?"],
        "Xcode":    ["Xcode! iOS dev mode activated!",
                     "Xcode is open. May your builds be swift."],
        "Terminal": ["Welcome back to the terminal!",
                     "Back where you belong — the terminal."],
        "iTerm2":   ["Welcome back to iTerm!",
                     "Back in iTerm! Home sweet home."],
    }

    def __init__(self):
        self._available = sys.platform == "darwin"
        self.current_app = None
        self._last_reaction_time = 0

    def poll(self):
        """Check frontmost app. Returns (app_name, reaction) on change, or None."""
        if not self._available:
            return None
        try:
            r = subprocess.run(
                ["osascript", "-e", self.APPLESCRIPT],
                capture_output=True, text=True, timeout=3
            )
            app_name = strip_ansi(r.stdout.strip())
            if not app_name or app_name == self.current_app:
                return None
            prev = self.current_app
            self.current_app = app_name
            # Don't react too frequently (min 30s between reactions)
            if time.time() - self._last_reaction_time < 30:
                return None
            # Only react to known interesting apps
            if app_name in self.APP_REACTIONS:
                self._last_reaction_time = time.time()
                return (app_name, random.choice(self.APP_REACTIONS[app_name]))
            return None
        except Exception:
            return None


class MeetingDetector:
    """Detect if the user is in a video call (Zoom, Teams, Meet, etc.)."""

    MEETING_APPS = {
        "zoom.us":           "Zoom",
        "Microsoft Teams":   "Teams",
        "Slack":             "Slack huddle",
        "FaceTime":          "FaceTime",
        "Webex":             "Webex",
        "Discord":           "Discord call",
    }

    MEETING_START_MSGS = [
        "Looks like you're in a {app} call. I'll keep it down!",
        "{app} meeting detected! Going quiet mode...",
        "Shhh, you're on {app}. I'll be quiet.",
        "Meeting time! {app} is active. *whispers*",
    ]

    MEETING_END_MSGS = [
        "Meeting's over! Freedom!",
        "Call ended. Back to the good stuff!",
        "Welcome back from your meeting!",
        "Meeting done? Let's code!",
    ]

    def __init__(self):
        self._available = sys.platform == "darwin"
        self.in_meeting = False
        self.meeting_app = None

    def poll(self):
        """Check for active meeting. Returns (in_meeting, message) or None."""
        if not self._available:
            return None
        try:
            # Check if any meeting app has an active audio/video session
            r = subprocess.run(
                ["ps", "-eo", "comm"],
                capture_output=True, text=True, timeout=3
            )
            processes = r.stdout.lower()
            # Find which meeting apps are running
            running = []
            for proc_name, display_name in self.MEETING_APPS.items():
                if proc_name.lower() in processes:
                    running.append((proc_name, display_name))
            active_app = None
            if running:
                # Single lsof call to check camera/audio usage
                try:
                    cam_check = subprocess.run(
                        ["lsof", "-c", "VDC", "-c", "Camera", "-c", "coreaudio"],
                        capture_output=True, text=True, timeout=5
                    )
                    cam_out = cam_check.stdout.lower()
                    for proc_name, display_name in running:
                        if proc_name.lower() in cam_out:
                            active_app = display_name
                            break
                except (subprocess.TimeoutExpired, OSError):
                    # Fallback: assume running meeting app = active call
                    active_app = running[0][1] if running else None

            if active_app and not self.in_meeting:
                self.in_meeting = True
                self.meeting_app = active_app
                return (True, random.choice(self.MEETING_START_MSGS).format(app=active_app))
            elif not active_app and self.in_meeting:
                self.in_meeting = False
                self.meeting_app = None
                return (False, random.choice(self.MEETING_END_MSGS))
            return None
        except Exception:
            return None


class SystemLoadWatcher:
    """Watch CPU and memory usage."""

    HIGH_CPU_MSGS = [
        "CPU at {cpu}%! Your machine is COOKING!",
        "Whoa, {cpu}% CPU! Something's working hard!",
        "CPU is at {cpu}% — fans go BRRRRR!",
        "{cpu}% CPU usage! Is something compiling?",
    ]

    HIGH_MEM_MSGS = [
        "Memory at {mem}%! RAM is getting squeezed!",
        "{mem}% memory used — things are getting tight!",
        "Your RAM is {mem}% full. Close some tabs maybe?",
    ]

    COOL_DOWN_MSGS = [
        "System cooled down! Back to normal.",
        "CPU calmed down. Crisis averted!",
    ]

    def __init__(self):
        self._high_cpu_alerted = False
        self._high_mem_alerted = False
        self.cpu_percent = 0.0
        self.mem_percent = 0.0

    def poll(self):
        """Check system load. Returns message if notable, else None."""
        try:
            # CPU: use ps to get total
            r = subprocess.run(
                ["ps", "-A", "-o", "%cpu"],
                capture_output=True, text=True, timeout=3
            )
            if r.returncode == 0:
                lines = r.stdout.strip().split("\n")[1:]  # skip header
                total_cpu = sum(float(l.strip()) for l in lines if l.strip())
                self.cpu_percent = min(total_cpu, 400.0)  # can exceed 100% on multi-core

            # Memory: use vm_stat on macOS or /proc/meminfo on Linux
            if sys.platform == "darwin":
                r = subprocess.run(
                    ["vm_stat"], capture_output=True, text=True, timeout=3
                )
                if r.returncode == 0:
                    lines = r.stdout.strip().split("\n")
                    stats = {}
                    for line in lines[1:]:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip().rstrip(".")
                            try:
                                stats[key] = int(val)
                            except ValueError:
                                pass
                    page_size = 16384  # default on Apple Silicon
                    free = stats.get("Pages free", 0) * page_size
                    active = stats.get("Pages active", 0) * page_size
                    inactive = stats.get("Pages inactive", 0) * page_size
                    wired = stats.get("Pages wired down", 0) * page_size
                    total = free + active + inactive + wired
                    if total > 0:
                        self.mem_percent = ((active + wired) / total) * 100

            # Check thresholds
            msg = None
            if self.cpu_percent > 150 and not self._high_cpu_alerted:
                self._high_cpu_alerted = True
                msg = random.choice(self.HIGH_CPU_MSGS).format(cpu=int(self.cpu_percent))
            elif self.cpu_percent < 80 and self._high_cpu_alerted:
                self._high_cpu_alerted = False
                msg = random.choice(self.COOL_DOWN_MSGS)
            elif self.mem_percent > 85 and not self._high_mem_alerted:
                self._high_mem_alerted = True
                msg = random.choice(self.HIGH_MEM_MSGS).format(mem=int(self.mem_percent))
            elif self.mem_percent < 70 and self._high_mem_alerted:
                self._high_mem_alerted = False

            return msg
        except Exception:
            return None


class AppearanceWatcher:
    """Detect macOS Dark/Light mode changes."""

    DARK_MSGS = [
        "Dark mode activated! Welcome to the dark side.",
        "Going dark! My favorite aesthetic.",
        "Dark mode ON. Easier on the eyes!",
    ]

    LIGHT_MSGS = [
        "Light mode! So bright! *squints*",
        "Switching to light mode? Bold choice!",
        "Light mode activated. My eyes!",
    ]

    def __init__(self):
        self._available = sys.platform == "darwin"
        self.is_dark = None

    def poll(self):
        """Check appearance mode. Returns message on change, or None."""
        if not self._available:
            return None
        try:
            r = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2
            )
            # Returns "Dark" if dark mode, error if light mode
            is_dark = r.returncode == 0 and "dark" in r.stdout.strip().lower()
            if self.is_dark is None:
                self.is_dark = is_dark
                return None  # Don't alert on first check
            if is_dark != self.is_dark:
                self.is_dark = is_dark
                return random.choice(self.DARK_MSGS if is_dark else self.LIGHT_MSGS)
            return None
        except Exception:
            return None


class WiFiWatcher:
    """Watch WiFi connection status on macOS."""

    CONNECTED_MSGS = [
        "WiFi connected to '{ssid}'! We're online!",
        "Connected to '{ssid}'. Internet restored!",
        "Back on '{ssid}'. Sweet, sweet bandwidth!",
    ]

    DISCONNECTED_MSGS = [
        "WiFi disconnected! We're offline!",
        "No WiFi! *panics in HTTP*",
        "Lost connection... we're on our own now.",
        "WiFi gone! Time to code offline like it's 1995.",
    ]

    def __init__(self):
        self._available = sys.platform == "darwin"
        self.connected = None
        self.ssid = None

    def poll(self):
        """Check WiFi. Returns message on connection change, or None."""
        if not self._available:
            return None
        try:
            # Use networksetup (works on all macOS versions including newer ones)
            r = subprocess.run(
                ["networksetup", "-getairportnetwork", "en0"],
                capture_output=True, text=True, timeout=3
            )
            ssid = None
            if r.returncode == 0 and "Current Wi-Fi Network" in r.stdout:
                # Output: "Current Wi-Fi Network: MyNetwork"
                raw = r.stdout.split(":", 1)[1].strip() if ":" in r.stdout else None
                ssid = strip_ansi(raw) if raw else None
            elif r.returncode == 0 and "not associated" not in r.stdout.lower():
                # Fallback: check if there's an IP on en0
                ip_check = subprocess.run(
                    ["ipconfig", "getifaddr", "en0"],
                    capture_output=True, text=True, timeout=2
                )
                if ip_check.returncode == 0 and ip_check.stdout.strip():
                    ssid = "Wi-Fi"  # Connected but SSID unknown

            if ssid and not self.connected:
                self.connected = True
                self.ssid = ssid
                return random.choice(self.CONNECTED_MSGS).format(ssid=ssid)
            elif ssid and ssid != self.ssid:
                self.ssid = ssid
                return random.choice(self.CONNECTED_MSGS).format(ssid=ssid)
            elif not ssid and self.connected:
                self.connected = False
                self.ssid = None
                return random.choice(self.DISCONNECTED_MSGS)

            if self.connected is None:
                self.connected = bool(ssid)
                self.ssid = ssid
            return None
        except Exception:
            return None


class TypingSpeedTracker:
    """Track typing speed from shell history timestamps."""

    FAST_MSGS = [
        "Wow, {wpm} commands/min! Your fingers are on FIRE!",
        "Speed demon! {wpm} commands per minute!",
        "{wpm} cmd/min?! Are you a robot? (Wait, I am.)",
    ]

    SLOW_MSGS = [
        "Taking it easy? Nice slow pace.",
        "Thinking before typing... very wise.",
    ]

    def __init__(self):
        self._timestamps = []  # Recent command timestamps
        self._alerted_fast = False
        self.commands_per_min = 0.0

    def record_command(self):
        """Call this when a new shell command is detected."""
        now = time.time()
        self._timestamps.append(now)
        # Keep only last 60 seconds of timestamps
        cutoff = now - 60
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        self.commands_per_min = len(self._timestamps)

    def poll(self):
        """Check typing speed. Returns message or None."""
        # Clean old timestamps
        now = time.time()
        cutoff = now - 60
        self._timestamps = [t for t in self._timestamps if t > cutoff]
        self.commands_per_min = len(self._timestamps)

        if self.commands_per_min >= 10 and not self._alerted_fast:
            self._alerted_fast = True
            return random.choice(self.FAST_MSGS).format(wpm=int(self.commands_per_min))
        elif self.commands_per_min < 5:
            self._alerted_fast = False
        return None


class USBWatcher:
    """Detect USB device connection/disconnection on macOS."""

    CONNECT_MSGS = [
        "Ooh, new device: '{device}'! What's this?",
        "USB connected: '{device}'. Shiny!",
        "'{device}' just showed up! New toy?",
        "Detected: '{device}'. Let's see what you've got!",
    ]

    DISCONNECT_MSGS = [
        "'{device}' was unplugged. Bye bye!",
        "USB device gone: '{device}'. Hope you ejected safely!",
    ]

    def __init__(self):
        self._available = sys.platform == "darwin"
        self._known_devices = set()
        self._initialized = False

    def poll(self):
        """Check USB devices. Returns message on change, or None."""
        if not self._available:
            return None
        try:
            r = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-detailLevel", "mini"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode != 0:
                return None
            # Parse device names from output
            current_devices = set()
            for line in r.stdout.split("\n"):
                line = line.strip()
                if line.endswith(":") and not line.startswith("USB") and len(line) > 2:
                    name = strip_ansi(line.rstrip(":"))
                    # Filter out generic hub entries
                    if "hub" not in name.lower() and "host" not in name.lower():
                        current_devices.add(name)

            if not self._initialized:
                self._known_devices = current_devices
                self._initialized = True
                return None

            # Check for new devices
            new_devices = current_devices - self._known_devices
            removed_devices = self._known_devices - current_devices
            self._known_devices = current_devices

            if new_devices:
                device = next(iter(new_devices))
                return random.choice(self.CONNECT_MSGS).format(device=device)
            if removed_devices:
                device = next(iter(removed_devices))
                return random.choice(self.DISCONNECT_MSGS).format(device=device)
            return None
        except Exception:
            return None


class WebResearcher:
    """Fetches quick facts from DuckDuckGo and Wikipedia using only stdlib."""

    def _make_ssl_ctx(self):
        import ssl
        for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt",
                       "/usr/local/etc/openssl/cert.pem"):
            try:
                return ssl.create_default_context(cafile=cafile)
            except Exception:
                continue
        return ssl.create_default_context()  # Use system/Python default trust store

    def fetch_ddg(self, query):
        """Fetch DuckDuckGo instant answer. Returns text snippet or None."""
        import urllib.request
        import urllib.parse
        import json
        try:
            q = urllib.parse.quote_plus(query)
            url = (
                f"https://api.duckduckgo.com/?q={q}"
                f"&format=json&no_html=1&skip_disambig=1&no_redirect=1"
            )
            req = urllib.request.Request(
                url, headers={"User-Agent": "TerminalBuddy/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5, context=self._make_ssl_ctx()) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = data.get("AbstractText", "").strip()
            if not text:
                for topic in data.get("RelatedTopics", []):
                    if isinstance(topic, dict) and topic.get("Text"):
                        text = topic["Text"].strip()
                        break
            return text[:400] if text else None
        except Exception:
            return None

    def fetch_wikipedia(self, topic):
        """Fetch Wikipedia page summary. Returns text or None."""
        import urllib.request
        import urllib.parse
        import json
        try:
            slug = urllib.parse.quote(topic.replace(" ", "_"))
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
            req = urllib.request.Request(
                url, headers={"User-Agent": "TerminalBuddy/2.0"}
            )
            with urllib.request.urlopen(req, timeout=5, context=self._make_ssl_ctx()) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            extract = data.get("extract", "").strip()
            return extract[:400] if extract else None
        except Exception:
            return None

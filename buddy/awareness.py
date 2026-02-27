"""Terminal awareness: shell history, build runner, uptime, git streak, clipboard."""

import os
import subprocess
import time
import threading
import re
import random
import datetime

from buddy.data import SHELL_REACTIONS


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
                return last
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
        self.last_content = ""

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
            result = subprocess.run(
                self.cmd, capture_output=True, text=True, timeout=1
            )
            if result.returncode != 0:
                return None
            content = result.stdout.strip()
            if content == self.last_content:
                return None
            self.last_content = content
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
        '        return (name of current track) & "|" & (artist of current track)\n'
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
                track, artist = output.split("|", 1)
                track = track.strip()
                artist = artist.strip()
                is_new = (track != self.current_track or artist != self.current_artist)
                self.current_track = track
                self.current_artist = artist
                self.is_playing = True
                return (track, artist) if is_new else None
            else:
                self.is_playing = False
                self.current_track = None
                self.current_artist = None
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

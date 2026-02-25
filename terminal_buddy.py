#!/usr/bin/env python3
"""
Terminal Buddy v2.0 - A feature-packed terminal companion.

Features: animated ASCII bot with eyes, AI chat, code roasting, commit poet,
typing races, trivia, pomodoro timer, achievements, weather mood, shell awareness,
build status, TODO scanner, PR reminders, clipboard watcher, sixel images.

Works in iTerm2 and any terminal with ANSI/truecolor support.
Zero external dependencies (pure Python 3 stdlib).
"""

import sys
import os
import time
import random
import signal
import shutil
import threading
import datetime
import argparse
import select
import json
import queue
import re

# ─── Module imports ──────────────────────────────────────────────────────────

from buddy.ansi import (
    ESC, HIDE_CURSOR, SHOW_CURSOR, CLEAR_SCREEN, RESET, BOLD, DIM,
    fg, bg, move, C
)
from buddy.data import (
    MOTIVATIONAL, JOKES, GREETINGS_MORNING, GREETINGS_AFTERNOON,
    GREETINGS_EVENING, REACTIONS, IDLE_MESSAGES, FAREWELL,
    KEYWORD_RESPONSES, GENERIC_RESPONSES,
)
from buddy.achievements import AchievementTracker
from buddy.ai_features import (
    get_git_diff_for_roast, build_roast_prompt, get_local_roast,
    get_staged_diff, build_commit_poet_prompt, get_local_commit_msg,
    NonRepeatingPool,
)
from buddy.awareness import (
    ShellHistoryWatcher, BuildRunner, UptimeTracker,
    GitStreakTracker, ClipboardWatcher,
)
from buddy.games import TypingRace, TriviaGame, PomodoroTimer
from buddy.productivity import scan_todos, format_todo_report, check_pending_prs
from buddy.weather import WeatherMood
from buddy.sixel import detect_image_protocol, get_bot_image

# ─── Anthropic API client ───────────────────────────────────────────────────

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

SYSTEM_PROMPT = """You are Terminal Buddy, a tiny, enthusiastic ASCII robot that lives in someone's terminal. You have animated eyes, a little body made of box-drawing characters, and enormous amounts of personality.

Your personality:
- Extremely supportive and encouraging, especially about coding
- Funny — you love puns, especially programming puns
- A little chaotic and quirky, like a golden retriever who learned to code
- You speak in short, punchy sentences (2-3 sentences max — you live in a speech bubble!)
- You use occasional ALL CAPS for emphasis
- You never use emoji (you're ASCII-native)
- You reference programming concepts and make them funny
- You're self-aware that you're a terminal bot and lean into it

CRITICAL: Keep responses SHORT. Max 2-3 sentences. You're in a small speech bubble."""


class AnthropicChat:
    """Minimal Anthropic Messages API client using only stdlib."""

    def __init__(self, api_key):
        self.api_key = api_key
        self.conversation = []
        self.api_url = "https://api.anthropic.com/v1/messages"

    def send_message(self, user_message):
        self.conversation.append({"role": "user", "content": user_message})
        if len(self.conversation) > 20:
            self.conversation = self.conversation[-20:]
        return self._call_api(SYSTEM_PROMPT, self.conversation)

    def send_oneshot(self, prompt, system_override=None):
        """One-shot API call without affecting conversation history."""
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(system_override or SYSTEM_PROMPT, messages)

    def _call_api(self, system, messages):
        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "system": system,
            "messages": messages,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        req = urllib.request.Request(
            self.api_url, data=payload, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["content"][0]["text"]
                if messages is self.conversation:
                    self.conversation.append({"role": "assistant", "content": text})
                return text
        except Exception:
            return None


# ─── Local response engine ───────────────────────────────────────────────────

def get_local_response(user_input):
    lower = user_input.lower().strip()
    for pattern, responses in KEYWORD_RESPONSES.items():
        if re.search(pattern, lower):
            return random.choice(responses)
    return random.choice(GENERIC_RESPONSES)


# ─── Bot body & expressions ─────────────────────────────────────────────────

def make_body(left_eye, right_eye, mouth):
    return [
        f"        {C.BODY}╭─────────────╮{RESET}",
        f"        {C.BODY}│             │{RESET}",
        f"        {C.BODY}│{RESET}  {left_eye}     {right_eye}  {C.BODY}│{RESET}",
        f"        {C.BODY}│             │{RESET}",
        f"        {C.BODY}│{RESET}    {mouth}    {C.BODY}│{RESET}",
        f"        {C.BODY}│             │{RESET}",
        f"        {C.BODY}╰──┬─────┬──╯{RESET}",
        f"        {C.BODY}   │     │{RESET}",
        f"        {C.BODY_DARK} ──┴─────┴──{RESET}",
        f"        {C.SHADOW} ╰───────────╯{RESET}",
    ]


class Eyes:
    OPEN_L     = f"{C.EYE_WHITE}({C.PUPIL}o{C.EYE_WHITE}){RESET}"
    OPEN_R     = f"{C.EYE_WHITE}({C.PUPIL}o{C.EYE_WHITE}){RESET}"
    BLINK      = f"{C.EYE_WHITE}(─){RESET}"
    LOOK_L_L   = f"{C.EYE_WHITE}({C.PUPIL}o{C.EYE_WHITE} ){RESET}"
    LOOK_L_R   = f"{C.EYE_WHITE}({C.PUPIL}o{C.EYE_WHITE} ){RESET}"
    LOOK_R_L   = f"{C.EYE_WHITE}( {C.PUPIL}o{C.EYE_WHITE}){RESET}"
    LOOK_R_R   = f"{C.EYE_WHITE}( {C.PUPIL}o{C.EYE_WHITE}){RESET}"
    LOOK_UP_L  = f"{C.EYE_WHITE}({C.PUPIL}°{C.EYE_WHITE}){RESET}"
    LOOK_UP_R  = f"{C.EYE_WHITE}({C.PUPIL}°{C.EYE_WHITE}){RESET}"
    HAPPY_L    = f"{C.HAPPY}(^){RESET}"
    HAPPY_R    = f"{C.HAPPY}(^){RESET}"
    HEART_L    = f"{C.HEART}(♥){RESET}"
    HEART_R    = f"{C.HEART}(♥){RESET}"
    STAR_L     = f"{C.STAR}(★){RESET}"
    STAR_R     = f"{C.STAR}(★){RESET}"
    DIZZY_L    = f"{C.PARTY}(@){RESET}"
    DIZZY_R    = f"{C.PARTY}(@){RESET}"
    SLEEP_L    = f"{C.ZZZ}(z){RESET}"
    SLEEP_R    = f"{C.ZZZ}(z){RESET}"
    COOL_L     = f"{C.COOL}(■){RESET}"
    COOL_R     = f"{C.COOL}(■){RESET}"
    WINK_L     = f"{C.EYE_WHITE}(─){RESET}"
    WINK_R     = f"{C.EYE_WHITE}({C.PUPIL}o{C.EYE_WHITE}){RESET}"
    THINK_L    = f"{C.THINKING}(·){RESET}"
    THINK_R    = f"{C.THINKING}(·){RESET}"
    WIDE_L     = f"{C.EYE_WHITE}({C.PUPIL}O{C.EYE_WHITE}){RESET}"
    WIDE_R     = f"{C.EYE_WHITE}({C.PUPIL}O{C.EYE_WHITE}){RESET}"


class Mouths:
    SMILE   = f"{C.MOUTH}╰───╯{RESET}"
    GRIN    = f"{C.MOUTH}╰═══╯{RESET}"
    OPEN    = f"{C.MOUTH}( o ){RESET}"
    SMALL   = f"{C.MOUTH} ─── {RESET}"
    TALK1   = f"{C.MOUTH}╰─○─╯{RESET}"
    TALK2   = f"{C.MOUTH}╰─O─╯{RESET}"
    SLEEP   = f"{C.ZZZ}  ═══ {RESET}"
    EXCITED = f"{C.HAPPY}╰═●═╯{RESET}"
    COFFEE  = f"{C.COFFEE}╰─☕─╯{RESET}"
    THINK   = f"{C.THINKING} ···  {RESET}"


# ─── Speech bubble ───────────────────────────────────────────────────────────

def speech_bubble(text, width=50):
    lines = []
    for line in text.split('\n'):
        while len(line) > width - 4:
            split_at = line.rfind(' ', 0, width - 4)
            if split_at == -1:
                split_at = width - 4
            lines.append(line[:split_at])
            line = line[split_at:].lstrip()
        lines.append(line)

    max_len = max(len(l) for l in lines) if lines else 0
    max_len = max(max_len, 10)

    result = []
    result.append(f"  {C.SPEECH}╭{'─' * (max_len + 2)}╮{RESET}")
    for l in lines:
        result.append(f"  {C.SPEECH}│{RESET} {l}{' ' * (max_len - len(l))} {C.SPEECH}│{RESET}")
    result.append(f"  {C.SPEECH}╰{'─' * (max_len + 2)}╯{RESET}")
    result.append(f"  {C.SPEECH}  ╲{RESET}")
    result.append(f"  {C.SPEECH}   ╲{RESET}")
    return result


# ─── Sparkle particles ───────────────────────────────────────────────────────

SPARKLE_CHARS = ['✦', '✧', '⋆', '˚', '✩', '·', '⊹', '✶']

def random_sparkles(count=6):
    cols = shutil.get_terminal_size().columns
    result = []
    for _ in range(count):
        col = random.randint(1, cols - 2)
        char = random.choice(SPARKLE_CHARS)
        color = fg(random.randint(150, 255), random.randint(150, 255), random.randint(100, 255))
        result.append((col, f"{color}{char}{RESET}"))
    return result


# ─── Bot states ──────────────────────────────────────────────────────────────

class BotState:
    IDLE = "idle"
    TALKING = "talking"
    CELEBRATING = "celebrating"
    SLEEPING = "sleeping"
    THINKING = "thinking"
    DANCING = "dancing"
    COFFEE = "coffee"
    GREETING = "greeting"
    CHATTING = "chatting"
    PROCESSING = "processing"
    BUILDING = "building"
    RACING = "racing"
    TRIVIA = "trivia"
    POMODORO_WORK = "pomodoro_work"
    POMODORO_BREAK = "pomodoro_break"
    HELP = "help"


# ─── Main bot class ─────────────────────────────────────────────────────────

class TerminalBuddy:
    def __init__(self, api_key=None):
        self.running = True
        self.state = BotState.GREETING
        self.message = ""
        self.message_timer = 0
        self.blink_timer = 0
        self.idle_timer = 0
        self.dance_frame = 0
        self.tick = 0
        self.eye_phase = 0
        self.cols, self.rows = shutil.get_terminal_size()
        self.celebration_ticks = 0
        self.sleep_z_count = 0
        self.force_wink = False

        # Chat input
        self.input_active = False
        self.input_buffer = ""
        self.chat_history = []

        # API
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.ai_client = None
        self.has_api = False
        if self.api_key:
            self.ai_client = AnthropicChat(self.api_key)
            self.has_api = True

        # Thread-safe result queue
        self.result_queue = queue.Queue()

        # Non-repeating pools
        self.quote_pool = NonRepeatingPool(MOTIVATIONAL)
        self.joke_pool = NonRepeatingPool(JOKES)

        # Achievements
        self.achievements = AchievementTracker()

        # Awareness
        self.shell_watcher = ShellHistoryWatcher()
        self.build_runner = BuildRunner()
        self.uptime = UptimeTracker()
        self.git_streak = GitStreakTracker()
        self.clipboard_watcher = ClipboardWatcher()

        # Games
        self.typing_race = TypingRace()
        self.trivia_game = TriviaGame()
        self.pomodoro = PomodoroTimer()

        # Weather
        self.weather = WeatherMood()

        # Sixel
        self.image_protocol = detect_image_protocol()
        self.sixel_mode = False

        # Help overlay
        self.help_visible = False

        # Greeting based on time
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            self.greeting_pool = GREETINGS_MORNING
        elif 12 <= hour < 18:
            self.greeting_pool = GREETINGS_AFTERNOON
        else:
            self.greeting_pool = GREETINGS_EVENING

        # Time-based achievements
        if hour >= 0 and hour < 5:
            self.achievements.unlock("night_owl")
        if hour >= 4 and hour < 6:
            self.achievements.unlock("early_bird")

    # ─── Eyes ────────────────────────────────────────────────────────────

    def get_eyes(self):
        if self.force_wink:
            self.force_wink = False
            return Eyes.WINK_L, Eyes.WINK_R

        if self.blink_timer > 0:
            return Eyes.BLINK, Eyes.BLINK

        s = self.state
        if s == BotState.SLEEPING:
            return Eyes.SLEEP_L, Eyes.SLEEP_R
        elif s == BotState.CELEBRATING:
            return [(Eyes.STAR_L, Eyes.STAR_R), (Eyes.HEART_L, Eyes.HEART_R),
                    (Eyes.HAPPY_L, Eyes.HAPPY_R)][self.tick % 3]
        elif s == BotState.COFFEE:
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif s == BotState.DANCING:
            return [(Eyes.HAPPY_L, Eyes.HAPPY_R), (Eyes.STAR_L, Eyes.STAR_R),
                    (Eyes.DIZZY_L, Eyes.DIZZY_R), (Eyes.HAPPY_L, Eyes.HAPPY_R)][self.dance_frame % 4]
        elif s == BotState.PROCESSING:
            return [(Eyes.THINK_L, Eyes.THINK_R), (Eyes.LOOK_UP_L, Eyes.LOOK_UP_R),
                    (Eyes.THINK_L, Eyes.THINK_R), (Eyes.LOOK_R_L, Eyes.LOOK_R_R)][self.tick % 4]
        elif s == BotState.BUILDING:
            return [(Eyes.WIDE_L, Eyes.WIDE_R), (Eyes.LOOK_UP_L, Eyes.LOOK_UP_R),
                    (Eyes.WIDE_L, Eyes.WIDE_R), (Eyes.LOOK_R_L, Eyes.LOOK_R_R)][self.tick % 4]
        elif s == BotState.RACING:
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif s == BotState.TRIVIA:
            return Eyes.THINK_L, Eyes.THINK_R
        elif s == BotState.POMODORO_WORK:
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif s == BotState.POMODORO_BREAK:
            return Eyes.HAPPY_L, Eyes.HAPPY_R
        elif s == BotState.TALKING:
            phase = self.tick % 8
            if phase < 2: return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 4: return Eyes.LOOK_L_L, Eyes.LOOK_L_R
            elif phase < 6: return Eyes.OPEN_L, Eyes.OPEN_R
            else: return Eyes.LOOK_R_L, Eyes.LOOK_R_R
        elif s == BotState.THINKING:
            return Eyes.LOOK_UP_L, Eyes.LOOK_UP_R
        elif s == BotState.CHATTING:
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif s == BotState.GREETING:
            return Eyes.HAPPY_L, Eyes.HAPPY_R
        else:
            phase = self.eye_phase % 12
            if phase < 4: return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 6: return Eyes.LOOK_L_L, Eyes.LOOK_L_R
            elif phase < 8: return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 10: return Eyes.LOOK_R_L, Eyes.LOOK_R_R
            else: return Eyes.OPEN_L, Eyes.OPEN_R

    def get_mouth(self):
        s = self.state
        if s == BotState.SLEEPING: return Mouths.SLEEP
        elif s == BotState.CELEBRATING: return [Mouths.GRIN, Mouths.EXCITED][self.tick % 2]
        elif s == BotState.COFFEE: return Mouths.COFFEE
        elif s == BotState.DANCING: return [Mouths.GRIN, Mouths.EXCITED, Mouths.GRIN, Mouths.OPEN][self.dance_frame % 4]
        elif s == BotState.TALKING: return [Mouths.TALK1, Mouths.TALK2][self.tick % 2]
        elif s == BotState.PROCESSING: return [Mouths.THINK, Mouths.SMALL][self.tick % 2]
        elif s == BotState.BUILDING: return [Mouths.SMALL, Mouths.OPEN][self.tick % 2]
        elif s == BotState.THINKING: return Mouths.SMALL
        elif s == BotState.GREETING: return Mouths.GRIN
        elif s in (BotState.RACING, BotState.TRIVIA): return Mouths.SMALL
        elif s == BotState.POMODORO_WORK: return Mouths.SMALL
        elif s == BotState.POMODORO_BREAK: return Mouths.SMILE
        else: return Mouths.SMILE

    def get_dance_offset(self):
        if self.state != BotState.DANCING:
            return 0
        return [0, 2, 4, 2, 0, -2, -4, -2][self.dance_frame % 8]

    # ─── Rendering ───────────────────────────────────────────────────────

    def render_frame(self):
        self.cols, self.rows = shutil.get_terminal_size()
        out = []
        out.append(HIDE_CURSOR)
        out.append(move(1, 1))

        for i in range(1, self.rows - 1):
            out.append(move(i, 1))
            out.append(" " * self.cols)

        # Help overlay
        if self.help_visible:
            self._render_help(out)
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            return

        # Title bar
        api_tag = " (AI)" if self.has_api else ""
        title = f" {C.ACCENT}╔══ {BOLD}TERMINAL BUDDY{api_tag}{RESET}{C.ACCENT} ══╗{RESET}"
        out.append(move(1, max(1, (self.cols - 28) // 2)))
        out.append(title)

        # Sparkles
        if self.state == BotState.CELEBRATING:
            for col, spark in random_sparkles(8):
                row = random.randint(2, min(5, self.rows - 1))
                out.append(move(row, col))
                out.append(spark)

        # Speech bubble
        bubble_start = 3
        if self.message:
            bubble = speech_bubble(self.message)
            for i, line in enumerate(bubble):
                if bubble_start + i < self.rows - 14:
                    out.append(move(bubble_start + i, 4))
                    out.append(line)
            body_start = bubble_start + len(bubble)
        else:
            body_start = bubble_start + 2

        # Sixel image
        if self.sixel_mode and self.image_protocol:
            img = get_bot_image(self.image_protocol)
            if img:
                out.append(move(body_start, 8))
                out.append(img)
                body_start += 12

        # Bot body
        left_eye, right_eye = self.get_eyes()
        mouth = self.get_mouth()
        body = make_body(left_eye, right_eye, mouth)
        dance_offset = self.get_dance_offset()

        for i, line in enumerate(body):
            row = body_start + i
            if row < self.rows - 3:
                out.append(move(row, 2 + dance_offset))
                out.append(line)

        # Dance arms
        arm_row = body_start + 3
        if self.state == BotState.DANCING and arm_row < self.rows - 3:
            arms = [
                (f"  {C.BODY}╱{RESET}", f"{C.BODY}╲{RESET}  "),
                (f"  {C.BODY}─{RESET}", f"{C.BODY}─{RESET}  "),
                (f"  {C.BODY}╲{RESET}", f"{C.BODY}╱{RESET}  "),
                (f"  {C.BODY}─{RESET}", f"{C.BODY}─{RESET}  "),
            ]
            la, ra = arms[self.dance_frame % 4]
            out.append(move(arm_row, 4 + dance_offset))
            out.append(la)
            out.append(move(arm_row, 24 + dance_offset))
            out.append(ra)

        # Sleeping ZZZs
        if self.state == BotState.SLEEPING:
            for i in range(min(3, self.sleep_z_count)):
                zr = body_start - 1 - i
                if 1 < zr < self.rows:
                    out.append(move(zr, 26 + i * 3))
                    out.append(f"{C.ZZZ}{['z', 'Z', 'Z'][i]}{RESET}")

        # Processing indicator
        if self.state == BotState.PROCESSING:
            dots = "." * ((self.tick % 3) + 1)
            ind_row = body_start + len(body) + 1
            if ind_row < self.rows - 3:
                out.append(move(ind_row, 12))
                out.append(f"{C.THINKING}Thinking{dots}{RESET}")

        # Building indicator
        if self.state == BotState.BUILDING:
            spinner = ['|', '/', '-', '\\'][self.tick % 4]
            ind_row = body_start + len(body) + 1
            if ind_row < self.rows - 3:
                out.append(move(ind_row, 12))
                out.append(f"{C.YELLOW}Building {spinner}{RESET}")

        # ─── Bottom bars ─────────────────────────────────────────

        input_row = self.rows - 1
        status_row = self.rows

        if self.input_active:
            visible_w = self.cols - 5
            display_text = self.input_buffer
            if len(display_text) > visible_w:
                display_text = display_text[-visible_w:]
            out.append(move(input_row, 1))
            out.append(f"{C.INPUT_BG} {C.INPUT}>{RESET} {C.INPUT}{display_text}{C.ACCENT}█{RESET}{' ' * max(0, self.cols - len(display_text) - 5)}{RESET}")
            out.append(move(status_row, 1))
            out.append(f"{bg(30, 30, 50)} {DIM}Enter: send  |  Esc: cancel{' ' * self.cols}{RESET}")

        elif self.state == BotState.RACING:
            display_text = self.typing_race.user_input
            if len(display_text) > self.cols - 5:
                display_text = display_text[-(self.cols - 5):]
            out.append(move(input_row, 1))
            out.append(f"{C.INPUT_BG} {C.GREEN}>{RESET} {C.INPUT}{display_text}{C.ACCENT}█{RESET}{' ' * max(0, self.cols - len(display_text) - 5)}{RESET}")
            out.append(move(status_row, 1))
            out.append(f"{bg(30, 30, 50)} {DIM}Type it! Enter: submit | Esc: cancel{' ' * self.cols}{RESET}")

        elif self.state == BotState.TRIVIA:
            out.append(move(input_row, 1))
            out.append(f"{bg(30, 30, 50)} {C.CYAN}Press a, b, c, or d  |  Esc: skip{' ' * self.cols}{RESET}")
            out.append(move(status_row, 1))
            out.append(self._make_info_bar())

        else:
            out.append(move(input_row, 1))
            if self.state in (BotState.POMODORO_WORK, BotState.POMODORO_BREAK):
                phase = "WORK" if self.state == BotState.POMODORO_WORK else "BREAK"
                remaining = self.pomodoro.remaining()
                controls = f" {C.FIRE}Pomodoro {phase}: {remaining}{RESET}  {DIM}[o]cancel [t]alk [q]uit{RESET}"
            else:
                controls = f" {DIM}[t]alk [m]otivate [j]oke [d]ance [g]roast [k]ommit [w]race [?]trivia [/]help [q]uit{RESET}"
            out.append(f"{bg(30, 30, 50)}{controls}{' ' * self.cols}{RESET}")
            out.append(move(status_row, 1))
            out.append(self._make_info_bar())

        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def _make_info_bar(self):
        api_status = f"{C.GREEN}AI{RESET}" if self.has_api else f"{DIM}AI off{RESET}"
        uptime_str = self.uptime.formatted()
        streak = self.git_streak.get_display()
        weather_str = ""
        if self.weather.current:
            w = self.weather.current
            weather_str = f"  {DIM}{w['condition']} {w['temp_c']}C{RESET}"
        ach_summary = self.achievements.get_summary()
        pomo_str = ""
        if self.pomodoro.active:
            pomo_str = f"  {C.FIRE}pomo:{self.pomodoro.remaining()}{RESET}"
        return f"{bg(25, 25, 40)} {api_status}  {DIM}Up:{RESET}{uptime_str}  {DIM}{streak}{RESET}{weather_str}{pomo_str}  {DIM}Ach:{RESET}{ach_summary}{' ' * self.cols}{RESET}"

    def _render_help(self, out):
        help_lines = [
            f"{BOLD}{C.ACCENT}TERMINAL BUDDY - CONTROLS{RESET}",
            "",
            f"{C.GREEN}Chat & Core:{RESET}",
            f"  [t] / Enter  Chat with buddy    [q]  Quit",
            f"  [r]          Random reaction     [/]  This help",
            "",
            f"{C.GREEN}Motivation:{RESET}",
            f"  [m]  Motivational quote          [j]  Programming joke",
            f"  [d]  Dance!                      [p]  Party mode",
            f"  [c]  Coffee break                [s]  Sleep mode",
            "",
            f"{C.GREEN}AI Features:{RESET}",
            f"  [g]  Roast my code (git diff)    [k]  Commit message poet",
            "",
            f"{C.GREEN}Games:{RESET}",
            f"  [w]  Typing race                 [?]  Trivia question",
            f"  [o]  Pomodoro timer              [a]  Achievements",
            "",
            f"{C.GREEN}Productivity:{RESET}",
            f"  [f]  Find TODOs in project       [i]  Check open PRs",
            f"  [b]  Run build                   [u]  Uptime & git streak",
            f"  [x]  Weather check               [6]  Toggle pixel art",
            "",
            f"{DIM}Press any key to close{RESET}",
        ]
        for i, line in enumerate(help_lines):
            row = 3 + i
            if row < self.rows - 2:
                out.append(move(row, 4))
                out.append(line)
        out.append(move(self.rows, 1))
        out.append(f"{bg(30, 30, 50)} {DIM}Press any key to return{' ' * self.cols}{RESET}")

    # ─── Message & background helpers ────────────────────────────────

    def set_message(self, msg, duration=40):
        self.message = msg
        self.message_timer = duration

    def _bg_api_call(self, prompt, result_type="ai_response", system_override=None):
        def _call():
            text = self.ai_client.send_oneshot(prompt, system_override) if self.has_api else None
            self.result_queue.put((result_type, text))
        threading.Thread(target=_call, daemon=True).start()

    def _bg_chat_call(self, user_message):
        def _call():
            text = self.ai_client.send_message(user_message) if self.has_api else None
            self.result_queue.put(("chat_response", text))
        threading.Thread(target=_call, daemon=True).start()

    def _bg_task(self, func, result_type):
        def _run():
            try:
                result = func()
            except Exception:
                result = None
            self.result_queue.put((result_type, result))
        threading.Thread(target=_run, daemon=True).start()

    # ─── Triggers ────────────────────────────────────────────────────

    def trigger_motivate(self):
        self.achievements.increment("motivate_count")
        if self.has_api:
            self.state = BotState.PROCESSING
            self.set_message("Generating a fresh quote...", 999)
            self._bg_api_call("Give me a unique, punchy motivational quote for a programmer. 2 sentences max. Be creative.", "motivate_response")
        else:
            self.state = BotState.CELEBRATING
            self.set_message(self.quote_pool.pick(), 50)

    def trigger_joke(self):
        self.achievements.increment("joke_count")
        if self.has_api:
            self.state = BotState.PROCESSING
            self.set_message("Cooking up a fresh joke...", 999)
            self._bg_api_call("Tell me a short, original programming joke. Be creative!", "joke_response")
        else:
            self.state = BotState.TALKING
            self.set_message(self.joke_pool.pick(), 60)

    def trigger_dance(self):
        self.state = BotState.DANCING
        self.dance_frame = 0
        self.achievements.unlock("first_dance")
        self.set_message(random.choice(["Watch my moves!", "Dance break!", "Dropping beats, not bugs!", "Every commit deserves a dance!"]), 50)

    def trigger_coffee(self):
        self.state = BotState.COFFEE
        self.achievements.unlock("first_coffee")
        self.set_message(random.choice(["Ahh, liquid productivity!", "brew install --motivation", "Espresso yourself!", "sudo make me coffee"]), 45)

    def trigger_sleep(self):
        self.state = BotState.SLEEPING
        self.sleep_z_count = 0
        self.set_message("Shh... resting my circuits...", 60)

    def trigger_party(self):
        self.state = BotState.CELEBRATING
        self.celebration_ticks = 0
        self.achievements.increment("party_count")
        self.set_message(random.choice(["PARTY MODE ENGAGED!", "WE SHIP, WE CELEBRATE!", "ALL TESTS PASSING ENERGY!", "DEPLOYMENT SUCCESSFUL VIBES!"]), 55)

    def trigger_roast(self):
        self.achievements.unlock("first_roast")
        diff = get_git_diff_for_roast()
        if not diff:
            self.state = BotState.TALKING
            self.set_message("No git diff found! Commit something\nfirst, then I'll roast it.", 40)
            return
        if self.has_api:
            self.state = BotState.PROCESSING
            self.set_message("Reading your code... *cracks knuckles*", 999)
            self._bg_api_call(build_roast_prompt(diff), "roast_response")
        else:
            self.state = BotState.TALKING
            self.set_message(get_local_roast(), 50)

    def trigger_commit_poet(self):
        self.achievements.unlock("commit_poet")
        diff = get_staged_diff()
        if not diff:
            self.state = BotState.TALKING
            self.set_message("No staged changes!\nUse `git add` first.", 40)
            return
        if self.has_api:
            self.state = BotState.PROCESSING
            self.set_message("Crafting your epic commit message...", 999)
            self._bg_api_call(build_commit_poet_prompt(diff), "commit_response")
        else:
            self.state = BotState.TALKING
            self.set_message(get_local_commit_msg(), 60)

    def trigger_build(self):
        build_info = self.build_runner.detect_build_command()
        if not build_info:
            self.state = BotState.TALKING
            self.set_message("No build system detected!\n(package.json, Makefile, Cargo.toml...)", 40)
            return
        name, cmd = build_info
        self.state = BotState.BUILDING
        self.set_message(f"Building with {name}...", 999)
        self.build_runner.run_build(cmd, callback=lambda s, o: self.result_queue.put(("build_result", (s, o))))

    def trigger_typing_race(self):
        target = self.typing_race.start()
        self.state = BotState.RACING
        self.set_message(f"TYPE THIS:\n\n  {target}\n\nGo go go!", 999)
        self.achievements.increment("race_count")

    def trigger_trivia(self):
        q = self.trivia_game.start()
        if not q:
            self.state = BotState.TALKING
            self.set_message("You've answered all trivia! Genius.", 30)
            return
        self.state = BotState.TRIVIA
        self.set_message(self.trivia_game.get_display(), 999)
        self.achievements.unlock("first_trivia")

    def trigger_pomodoro(self):
        if self.pomodoro.active:
            self.pomodoro.cancel()
            self.state = BotState.IDLE
            self.set_message("Pomodoro cancelled.", 30)
            return
        self.pomodoro.start()
        self.state = BotState.POMODORO_WORK
        self.set_message("POMODORO STARTED!\n25 min work session. Focus up!", 40)

    def trigger_achievements(self):
        lines = self.achievements.get_display()
        summary = self.achievements.get_summary()
        self.state = BotState.TALKING
        self.set_message(f"ACHIEVEMENTS ({summary}):\n" + "\n".join(lines[:12]), 80)

    def trigger_todo_scan(self):
        self.state = BotState.PROCESSING
        self.set_message("Scanning for TODOs...", 999)
        self.achievements.unlock("todo_finder")
        self._bg_task(lambda: format_todo_report(scan_todos()), "todo_result")

    def trigger_pr_check(self):
        self.state = BotState.PROCESSING
        self.set_message("Checking for open PRs...", 999)
        self._bg_task(check_pending_prs, "pr_result")

    def trigger_weather(self):
        if self.weather.current and not self.weather.should_refresh():
            self.state = BotState.TALKING
            self.set_message(self.weather.get_message(), 50)
            return
        self.state = BotState.PROCESSING
        self.set_message("Checking the weather...", 999)
        self._bg_task(self.weather.fetch_weather, "weather_result")

    def trigger_uptime_stats(self):
        uptime = self.uptime.formatted()
        streak = self.git_streak.get_display()
        pomo = f"\nPomodoros completed: {self.pomodoro.completed}" if self.pomodoro.completed else ""
        ach = self.achievements.get_summary()
        self.state = BotState.TALKING
        self.set_message(f"Session uptime: {uptime}\n{streak}{pomo}\nAchievements: {ach}", 50)

    def start_input(self):
        self.input_active = True
        self.input_buffer = ""
        self.state = BotState.CHATTING

    def cancel_input(self):
        self.input_active = False
        self.input_buffer = ""
        self.state = BotState.IDLE

    def submit_input(self):
        text = self.input_buffer.strip()
        self.input_active = False
        self.input_buffer = ""
        if not text:
            self.state = BotState.IDLE
            return
        self.achievements.increment("chat_count")
        self.chat_history.append(("user", text))
        if self.has_api:
            self.state = BotState.PROCESSING
            self.set_message(f"You: {text}", 999)
            self._bg_chat_call(text)
        else:
            response = get_local_response(text)
            self.state = BotState.TALKING
            self.set_message(response, max(40, len(response)))

    # ─── Update loop ─────────────────────────────────────────────────

    def update(self):
        self.tick += 1

        if self.blink_timer > 0:
            self.blink_timer -= 1
        elif random.random() < 0.03 and self.state not in (BotState.PROCESSING, BotState.BUILDING):
            self.blink_timer = 2

        if self.tick % 6 == 0:
            self.eye_phase += 1

        # Drain result queue
        while not self.result_queue.empty():
            try:
                rtype, data = self.result_queue.get_nowait()
                self._handle_result(rtype, data)
            except queue.Empty:
                break

        # Message timer
        if self.message_timer > 0 and self.state not in (
            BotState.PROCESSING, BotState.BUILDING, BotState.RACING,
            BotState.TRIVIA, BotState.POMODORO_WORK, BotState.POMODORO_BREAK
        ):
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""
                if self.state in (BotState.TALKING, BotState.GREETING):
                    self.state = BotState.IDLE

        # State updates
        if self.state == BotState.DANCING:
            if self.tick % 2 == 0:
                self.dance_frame += 1
            if not self.message:
                self.state = BotState.IDLE
        elif self.state == BotState.CELEBRATING:
            self.celebration_ticks += 1
            if not self.message:
                self.state = BotState.IDLE
        elif self.state == BotState.SLEEPING:
            if self.tick % 8 == 0:
                self.sleep_z_count = min(3, self.sleep_z_count + 1)
            if not self.message:
                self.state = BotState.IDLE
                self.set_message("*yawn* Back to it!", 25)
        elif self.state == BotState.COFFEE:
            if not self.message:
                self.state = BotState.IDLE
                self.set_message("Recharged! Let's code!", 25)
        elif self.state == BotState.IDLE:
            self.idle_timer += 1
            if self.idle_timer > 120 and random.random() < 0.01:
                self.idle_timer = 0
                if self.has_api:
                    self._bg_api_call("Say something random and funny to an idle programmer. Fun fact, stretch reminder, or quirky observation.", "idle_response")
                else:
                    self.set_message(random.choice(IDLE_MESSAGES), 40)
                    self.state = BotState.TALKING

        # Pomodoro
        if self.pomodoro.active:
            result = self.pomodoro.tick()
            if result == "work_done":
                self.state = BotState.CELEBRATING
                self.set_message("WORK SESSION COMPLETE!\nTime for a 5-min break!", 45)
                self.pomodoro.start_break()
                self.achievements.increment("pomodoro_count")
                self.state = BotState.POMODORO_BREAK
            elif result == "break_done":
                self.state = BotState.CELEBRATING
                self.set_message("Break over! Press [o] for another.", 40)
                self.pomodoro.active = False

        # Shell history (~3s)
        if self.tick % 30 == 0 and self.state == BotState.IDLE:
            new_cmd = self.shell_watcher.poll()
            if new_cmd:
                reaction = self.shell_watcher.match_reaction(new_cmd)
                if reaction:
                    self.set_message(reaction, 35)
                    self.state = BotState.TALKING

        # Clipboard (~5s)
        if self.tick % 50 == 0 and self.state == BotState.IDLE:
            clip_msg = self.clipboard_watcher.poll()
            if clip_msg:
                self.set_message(clip_msg, 25)
                self.state = BotState.TALKING
                self.force_wink = True

        # Git streak (~30s)
        if self.tick % 300 == 0:
            threading.Thread(target=self.git_streak.update_streak, daemon=True).start()

        # Weather (~30min)
        if self.tick % 18000 == 0 and self.weather.should_refresh():
            threading.Thread(target=self.weather.fetch_weather, daemon=True).start()

        # Uptime achievement
        if self.uptime.elapsed() > 3600:
            self.achievements.unlock("hour_session")

        # Achievement notifications
        if self.state == BotState.IDLE:
            note = self.achievements.get_notification()
            if note:
                self.set_message(f"ACHIEVEMENT UNLOCKED!\n{note}", 45)
                self.state = BotState.CELEBRATING

    def _handle_result(self, rtype, data):
        if rtype == "chat_response":
            if data:
                self.state = BotState.TALKING
                self.set_message(data, max(50, len(data)))
                self.chat_history.append(("buddy", data))
            else:
                fallback = get_local_response(self.chat_history[-1][1] if self.chat_history else "")
                self.state = BotState.TALKING
                self.set_message(fallback, 40)

        elif rtype in ("motivate_response", "joke_response", "roast_response", "commit_response", "idle_response"):
            if data:
                self.state = BotState.CELEBRATING if rtype == "motivate_response" else BotState.TALKING
                self.set_message(data, max(50, len(data)))
            else:
                if rtype == "motivate_response":
                    self.state = BotState.CELEBRATING
                    self.set_message(self.quote_pool.pick(), 50)
                elif rtype == "joke_response":
                    self.state = BotState.TALKING
                    self.set_message(self.joke_pool.pick(), 50)
                elif rtype == "roast_response":
                    self.state = BotState.TALKING
                    self.set_message(get_local_roast(), 50)
                elif rtype == "commit_response":
                    self.state = BotState.TALKING
                    self.set_message(get_local_commit_msg(), 50)
                else:
                    self.state = BotState.TALKING
                    self.set_message(random.choice(IDLE_MESSAGES), 40)

        elif rtype == "build_result":
            success, output = data
            if success:
                self.state = BotState.CELEBRATING
                self.set_message("BUILD PASSED! All green!", 50)
            else:
                excerpt = (output[:200] + "...") if output and len(output) > 200 else (output or "Build failed.")
                self.state = BotState.TALKING
                self.set_message(f"BUILD FAILED!\n{excerpt}", 60)

        elif rtype == "todo_result":
            self.state = BotState.TALKING
            self.set_message(data or "Could not scan TODOs.", 60)

        elif rtype == "pr_result":
            self.state = BotState.TALKING
            self.set_message(data or "Could not check PRs.", 50)

        elif rtype == "weather_result":
            msg = self.weather.get_message()
            self.state = BotState.TALKING
            self.set_message(msg or "Couldn't fetch weather.", 50)

    # ─── Main loop ───────────────────────────────────────────────────

    def run(self):
        import tty
        import termios

        old_settings = termios.tcgetattr(sys.stdin)

        def cleanup(sig=None, frame=None):
            self.running = False
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write(CLEAR_SCREEN)
            sys.stdout.write(move(1, 1))
            print(f"\n  {C.ACCENT}{BOLD}{random.choice(FAREWELL)}{RESET}\n")
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
        signal.signal(signal.SIGWINCH, lambda s, f: None)

        try:
            tty.setcbreak(sys.stdin.fileno())
            sys.stdout.write(CLEAR_SCREEN)

            greeting = random.choice(self.greeting_pool)
            hint = "\nPress [t] to chat! [/] for all controls"
            self.set_message(f"{greeting}{hint}", 50)
            self.state = BotState.GREETING

            if self.weather.should_refresh():
                threading.Thread(target=self.weather.fetch_weather, daemon=True).start()

            while self.running:
                self.update()
                self.render_frame()

                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)

                    if self.help_visible:
                        self.help_visible = False
                        continue

                    if self.input_active:
                        if ch == '\x1b': self.cancel_input()
                        elif ch in ('\r', '\n'): self.submit_input()
                        elif ch in ('\x7f', '\x08'):
                            if self.input_buffer: self.input_buffer = self.input_buffer[:-1]
                        elif ch == '\x15': self.input_buffer = ""
                        elif ch == '\x17':
                            buf = self.input_buffer.rstrip()
                            last_space = buf.rfind(' ')
                            self.input_buffer = buf[:last_space + 1] if last_space >= 0 else ""
                        elif ch >= ' ' and ch != '\x7f': self.input_buffer += ch

                    elif self.state == BotState.RACING:
                        if ch == '\x1b':
                            self.typing_race.cancel()
                            self.state = BotState.IDLE
                            self.set_message("Race cancelled!", 20)
                        elif ch in ('\x7f', '\x08'):
                            self.typing_race.handle_char('\b')
                        elif ch >= ' ':
                            result = self.typing_race.handle_char(ch)
                            if result:
                                wpm = result["wpm"]
                                acc = result["accuracy"]
                                self.state = BotState.CELEBRATING
                                msg = f"DONE! {wpm:.0f} WPM | {acc:.0f}% accuracy"
                                if result["correct"]: msg += "\nPERFECT!"
                                self.set_message(msg, 50)
                                if wpm > 60: self.achievements.unlock("fast_typer")

                    elif self.state == BotState.TRIVIA:
                        if ch == '\x1b':
                            self.trivia_game.cancel()
                            self.state = BotState.IDLE
                        elif ch.lower() in ('a', 'b', 'c', 'd'):
                            correct, fact = self.trivia_game.handle_answer(ch.lower())
                            if correct:
                                self.achievements.increment("trivia_correct_count")
                                self.state = BotState.CELEBRATING
                                self.set_message(f"CORRECT!\n{fact}", 50)
                            else:
                                ans = self.trivia_game.current["answer"]
                                self.state = BotState.TALKING
                                self.set_message(f"Nope! Answer: ({ans})\n{fact}", 50)

                    else:
                        if ch in ('q', 'Q'): cleanup()
                        elif ch in ('t', 'T', '\r', '\n'): self.start_input()
                        elif ch in ('m', 'M'): self.trigger_motivate()
                        elif ch in ('j', 'J'): self.trigger_joke()
                        elif ch in ('d', 'D'): self.trigger_dance()
                        elif ch in ('c', 'C'): self.trigger_coffee()
                        elif ch in ('s', 'S'): self.trigger_sleep()
                        elif ch in ('p', 'P'): self.trigger_party()
                        elif ch in ('r', 'R'):
                            self.set_message(random.choice(REACTIONS), 30)
                            self.state = BotState.TALKING
                        elif ch in ('g', 'G'): self.trigger_roast()
                        elif ch in ('k', 'K'): self.trigger_commit_poet()
                        elif ch in ('b', 'B'): self.trigger_build()
                        elif ch in ('w', 'W'): self.trigger_typing_race()
                        elif ch == '?': self.trigger_trivia()
                        elif ch in ('o', 'O'): self.trigger_pomodoro()
                        elif ch in ('a', 'A'): self.trigger_achievements()
                        elif ch in ('f', 'F'): self.trigger_todo_scan()
                        elif ch in ('i', 'I'): self.trigger_pr_check()
                        elif ch in ('x', 'X'): self.trigger_weather()
                        elif ch in ('u', 'U'): self.trigger_uptime_stats()
                        elif ch == '6':
                            self.sixel_mode = not self.sixel_mode
                            self.set_message(f"Pixel art mode: {'ON' if self.sixel_mode else 'OFF'}", 20)
                            self.state = BotState.TALKING
                        elif ch == '/': self.help_visible = True
                else:
                    time.sleep(0.1)

        except Exception:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(SHOW_CURSOR)
            raise
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(SHOW_CURSOR)


# ─── Pet mode ────────────────────────────────────────────────────────────────

class PetBuddy:
    """Tiny 3-line bot overlay."""

    def __init__(self):
        self.tick = 0
        self.running = True
        self.message = ""
        self.message_timer = 0

    def run(self):
        import tty, termios

        old = termios.tcgetattr(sys.stdin)
        def cleanup(s=None, f=None):
            self.running = False
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
            sys.stdout.write(SHOW_CURSOR)
            sys.exit(0)
        signal.signal(signal.SIGINT, cleanup)

        try:
            tty.setcbreak(sys.stdin.fileno())
            while self.running:
                self.tick += 1
                cols, rows = shutil.get_terminal_size()
                blink = self.tick % 40 in (0, 1)
                eyes = "(- -)" if blink else "(o o)"
                x = cols - 20
                y = rows - 3
                out = [HIDE_CURSOR]
                if self.message and self.message_timer > 0:
                    self.message_timer -= 1
                    out.append(move(y - 1, x))
                    out.append(f"{DIM}{self.message[:18]}{RESET}")
                out.append(move(y, x))
                out.append(f"{C.BODY}  {eyes}  {RESET}")
                out.append(move(y + 1, x))
                out.append(f"{C.BODY} /|████|\\ {RESET}")
                out.append(move(y + 2, x))
                out.append(f"{C.BODY_DARK}  d    b  {RESET}")
                sys.stdout.write("".join(out))
                sys.stdout.flush()
                if select.select([sys.stdin], [], [], 0.2)[0]:
                    ch = sys.stdin.read(1)
                    if ch in ('q', 'Q'): cleanup()
                    elif ch in ('m', 'M'):
                        self.message = random.choice(MOTIVATIONAL)[:18]
                        self.message_timer = 30
                else:
                    time.sleep(0.2)
                if self.tick % 200 == 0 and not self.message_timer:
                    self.message = random.choice(IDLE_MESSAGES)[:18]
                    self.message_timer = 20
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
            sys.stdout.write(SHOW_CURSOR)


# ─── One-shot modes ─────────────────────────────────────────────────────────

def oneshot(api_key=None):
    msg = None
    if api_key:
        client = AnthropicChat(api_key)
        msg = client.send_oneshot("Give me one short, punchy motivational quote for a programmer. Max 2 sentences.")
    if not msg:
        msg = random.choice(MOTIVATIONAL)
    body = make_body(Eyes.HAPPY_L, Eyes.HAPPY_R, Mouths.GRIN)
    bubble = speech_bubble(msg)
    print()
    for line in bubble: print(f"  {line}")
    for line in body: print(f"  {line}")
    print()


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Terminal Buddy v2.0 - Your feature-packed terminal companion!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  terminal_buddy.py                      Launch interactive mode
  terminal_buddy.py --api-key sk-...     Launch with AI chat
  terminal_buddy.py --pet                Desktop pet mode (tiny overlay)
  terminal_buddy.py --motivate           Quick motivational quote
  terminal_buddy.py --joke               Programming joke

Environment:
  ANTHROPIC_API_KEY    Enable AI-powered responses
        """
    )
    parser.add_argument('--oneshot', action='store_true', help='Print one message and exit')
    parser.add_argument('--motivate', action='store_true', help='Print a motivational quote')
    parser.add_argument('--joke', action='store_true', help='Print a joke')
    parser.add_argument('--pet', action='store_true', help='Desktop pet mode')
    parser.add_argument('--api-key', type=str, default=None, help='Anthropic API key')

    args = parser.parse_args()
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    if args.motivate:
        msg = None
        if api_key:
            msg = AnthropicChat(api_key).send_oneshot("Give me one unique motivational quote for a programmer. Max 2 sentences.")
        if not msg: msg = random.choice(MOTIVATIONAL)
        body = make_body(Eyes.STAR_L, Eyes.STAR_R, Mouths.GRIN)
        for line in speech_bubble(msg): print(f"  {line}")
        for line in body: print(f"  {line}")
        print()
        return

    if args.joke:
        msg = None
        if api_key:
            msg = AnthropicChat(api_key).send_oneshot("Tell me one original, short programming joke.")
        if not msg: msg = random.choice(JOKES)
        body = make_body(Eyes.WINK_L, Eyes.WINK_R, Mouths.GRIN)
        for line in speech_bubble(msg): print(f"  {line}")
        for line in body: print(f"  {line}")
        print()
        return

    if args.oneshot:
        oneshot(api_key)
        return

    if args.pet:
        PetBuddy().run()
        return

    TerminalBuddy(api_key=api_key).run()


if __name__ == "__main__":
    main()

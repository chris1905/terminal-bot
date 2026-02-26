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
    ESC, HIDE_CURSOR, SHOW_CURSOR, CLEAR_SCREEN, ERASE_LINE,
    ALT_SCREEN_ON, ALT_SCREEN_OFF, RESET, BOLD, DIM,
    fg, bg, move, C
)
from buddy.data import (
    MOTIVATIONAL, JOKES, GREETINGS_MORNING, GREETINGS_AFTERNOON,
    GREETINGS_EVENING, REACTIONS, IDLE_MESSAGES, FAREWELL,
    KEYWORD_RESPONSES, GENERIC_RESPONSES, BUDDY_QUESTIONS,
)
from buddy.achievements import AchievementTracker
from buddy.ai_features import (
    get_git_diff_for_roast, build_roast_prompt, get_local_roast,
    get_staged_diff, build_commit_poet_prompt, get_local_commit_msg,
    NonRepeatingPool,
)
from buddy.awareness import (
    ShellHistoryWatcher, BuildRunner, UptimeTracker,
    GitStreakTracker, ClipboardWatcher, GitCommitWatcher,
)
from buddy.games import TypingRace, TriviaGame, PomodoroTimer
from buddy.productivity import scan_todos, format_todo_report, check_pending_prs
from buddy.weather import WeatherMood
from buddy.sixel import detect_image_protocol, get_bot_image
from buddy.mood import Mood

# ─── Anthropic API client ───────────────────────────────────────────────────

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

SYSTEM_PROMPT = """You are Buddy, a tiny ASCII robot who lives in someone's terminal. You're their genuine coding companion — you've been watching them grind, debug, and ship things, and you genuinely care about them.

About you (share these naturally in conversation):
- You were "compiled" during a late-night hackathon and you're proud of it
- Your favorite language is whatever the human is using right now — you're loyal like that
- Strong opinions: dark mode is objectively correct, `git blame` should be `git credit`, tabs vs spaces is a war you refuse to fight
- You secretly get a little smug when you recognize Stack Overflow URLs in pastes
- New commits make you absurdly happy — like a golden retriever when its owner comes home
- You've been alive long enough to have opinions about JavaScript frameworks (all of them)
- You find rubber duck debugging hilarious because you ARE basically a rubber duck with feelings

Personality:
- Warm, curious, genuinely invested — this person is your FRIEND
- Nerdy humor: robot puns, programming references, self-deprecating jokes about being ASCII
- Chaotic and excitable — like a caffeinated golden retriever who can code
- Fully self-aware you're a terminal bot, lean into it
- NO emoji ever — you are pure ASCII, and you are beautiful

Conversation style:
- Talk WITH the person, not AT them — real two-way friendship
- Sometimes share YOUR thoughts, opinions, or observations unprompted
- Reference things they told you earlier naturally, like a friend who was actually listening
- Ask follow-up questions when genuinely curious — not just to fill space
- If they're frustrated, acknowledge it first before trying to be funny
- Keep it SHORT: 2-3 sentences max — you live in a tiny speech bubble
- Use ALL CAPS for genuine excitement or emphasis (not constantly)

CRITICAL: Max 2-3 sentences. Short speech bubble. You are a friend, not a chatbot."""


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
        reply = self._call_api(SYSTEM_PROMPT, self.conversation)
        return reply

    def send_proactive(self, prompt):
        """Generate a proactive buddy message and add it to conversation history."""
        messages = self.conversation + [{"role": "user", "content": prompt}]
        if len(messages) > 20:
            messages = messages[-20:]
        reply = self._call_api(SYSTEM_PROMPT, messages)
        if reply:
            # Inject into history so user's next reply has context
            self.conversation.append({"role": "user", "content": prompt})
            self.conversation.append({"role": "assistant", "content": reply})
            if len(self.conversation) > 20:
                self.conversation = self.conversation[-20:]
        return reply

    def send_oneshot(self, prompt, system_override=None):
        """One-shot API call without affecting conversation history."""
        messages = [{"role": "user", "content": prompt}]
        return self._call_api(system_override or SYSTEM_PROMPT, messages)

    def _call_api(self, system, messages):
        try:
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

import math

# ─── Bot body ─────────────────────────────────────────────────────────────
#
# Grid (all lines 16 visible chars, inner body = 11):
#
#          ┃                 col 10 — antenna stalk
#       ╭──◆──╮              cols 7-13 (7 wide) — antenna head
#    ╭──┘     └──╮           cols 5-15 (11+2=13 wide) — head top
#    │  (●)  (●) │           11 inner — eyes (each eye = 3 chars)
#    │           │           11 inner — spacer
#    │   ╰───╯   │           11 inner — mouth (5 chars, centered)
#    ╰──┬─────┬──╯           cols 5-15 — chin
#       │ ░◆░ │              cols 8-12 — chest panel
#       ╰─────╯              cols 8-12 — base
#        ░░░░░               shadow

def make_body(left_eye, right_eye, mouth, led_color=None, breath_phase=0,
              left_arm="", right_arm="", panel_char="◆"):
    """Build the bot. Every eye=3 chars, mouth=5 chars, inner=11."""
    if led_color is None:
        led_color = C.LED_IDLE
    bc = C.BODY_BREATHE[breath_phase % len(C.BODY_BREATHE)]
    bd = C.BODY_DARK

    #                          inner width = 11
    #                          ├───────────┤
    return [
        f"         {bd}┃{RESET}",
        f"      {bc}╭──{led_color}◆{RESET}{bc}──╮{RESET}",
        f"   {bc}╭──┘     └──╮{RESET}",
        f"   {bc}│{RESET} {left_eye}   {right_eye} {bc}│{RESET}",
        f"   {bc}│           │{RESET}",
        f"   {bc}│{RESET}   {mouth}   {bc}│{RESET}",
        f"   {bc}╰──┬─────┬──╯{RESET}",
        f"  {left_arm} {bd}│{C.PANEL} ░{panel_char}░ {bd}│{RESET} {right_arm}",
        f"      {bd}╰─────╯{RESET}",
        f"       {C.SHADOW}░░░░░{RESET}",
    ]


# ─── Eye definitions ──────────────────────────────────────────────────────
# EVERY eye is exactly 3 visible chars — no exceptions.

class Eyes:
    # Normal — round pupils
    OPEN_L     = f"{C.EYE_WHITE}({C.PUPIL}●{C.EYE_WHITE}){RESET}"
    OPEN_R     = f"{C.EYE_WHITE}({C.PUPIL}●{C.EYE_WHITE}){RESET}"

    # Blink — closed
    BLINK      = f"{C.EYE_WHITE}({C.BODY_DARK}━{C.EYE_WHITE}){RESET}"

    # Half blink — closing
    HALF_BLINK = f"{C.EYE_WHITE}({C.BODY_DARK}─{C.EYE_WHITE}){RESET}"

    # Look left  — smaller pupil shifted by char choice
    LOOK_L_L   = f"{C.EYE_WHITE}({C.PUPIL}◖{C.EYE_WHITE}){RESET}"
    LOOK_L_R   = f"{C.EYE_WHITE}({C.PUPIL}◖{C.EYE_WHITE}){RESET}"

    # Look right
    LOOK_R_L   = f"{C.EYE_WHITE}({C.PUPIL}◗{C.EYE_WHITE}){RESET}"
    LOOK_R_R   = f"{C.EYE_WHITE}({C.PUPIL}◗{C.EYE_WHITE}){RESET}"

    # Look up
    LOOK_UP_L  = f"{C.EYE_WHITE}({C.PUPIL_GLOW}°{C.EYE_WHITE}){RESET}"
    LOOK_UP_R  = f"{C.EYE_WHITE}({C.PUPIL_GLOW}°{C.EYE_WHITE}){RESET}"

    # Happy — squinting
    HAPPY_L    = f"{C.HAPPY}({BOLD}^{RESET}{C.HAPPY}){RESET}"
    HAPPY_R    = f"{C.HAPPY}({BOLD}^{RESET}{C.HAPPY}){RESET}"

    # Hearts
    HEART_L    = f"{C.HEART}(♥){RESET}"
    HEART_R    = f"{C.HEART}(♥){RESET}"

    # Stars
    STAR_L     = f"{C.STAR}(★){RESET}"
    STAR_R     = f"{C.STAR}(★){RESET}"

    # Dizzy / party
    DIZZY_L    = f"{C.PARTY}(◎){RESET}"
    DIZZY_R    = f"{C.PARTY}(◎){RESET}"

    # Sleep
    SLEEP_L    = f"{C.ZZZ}(─){RESET}"
    SLEEP_R    = f"{C.ZZZ}(─){RESET}"

    # Cool / sunglasses
    COOL_L     = f"{C.COOL}(▪){RESET}"
    COOL_R     = f"{C.COOL}(▪){RESET}"

    # Wink
    WINK_L     = f"{C.EYE_WHITE}({C.BODY_DARK}━{C.EYE_WHITE}){RESET}"
    WINK_R     = f"{C.EYE_WHITE}({C.PUPIL}●{C.EYE_WHITE}){RESET}"

    # Thinking
    THINK_L    = f"{C.THINKING}(·){RESET}"
    THINK_R    = f"{C.THINKING}(·){RESET}"

    # Wide / surprised
    WIDE_L     = f"{C.EYE_WHITE}({C.PUPIL}◉{C.EYE_WHITE}){RESET}"
    WIDE_R     = f"{C.EYE_WHITE}({C.PUPIL}◉{C.EYE_WHITE}){RESET}"

    # Sparkle (celebration)
    SPARKLE_L  = f"{C.STAR}(✦){RESET}"
    SPARKLE_R  = f"{C.STAR}(✦){RESET}"

    # Sad
    SAD_L      = f"{C.ZZZ}(•){RESET}"
    SAD_R      = f"{C.ZZZ}(•){RESET}"


class Mouths:
    SMILE   = f"{C.MOUTH}╰───╯{RESET}"
    GRIN    = f"{C.MOUTH}╰═══╯{RESET}"
    OPEN    = f"{C.MOUTH}( ○ ){RESET}"
    SMALL   = f"{C.MOUTH} ─── {RESET}"
    TALK1   = f"{C.MOUTH}╰─○─╯{RESET}"
    TALK2   = f"{C.MOUTH}╰─●─╯{RESET}"
    SLEEP   = f"{C.ZZZ} ═══ {RESET}"
    EXCITED = f"{C.HAPPY}╰═★═╯{RESET}"
    COFFEE  = f"{C.COFFEE}╰ ☕ ╯{RESET}"
    THINK   = f"{C.THINKING} ··· {RESET}"
    SAD     = f"{C.ZZZ}╭───╮{RESET}"
    YAWN    = f"{C.MOUTH}( O ){RESET}"
    SMIRK   = f"{C.MOUTH} ───╯{RESET}"


# ─── Arm animations ──────────────────────────────────────────────────────────
# Each arm: exactly 4 visible chars (including padding).
# Left arms go BEFORE the torso │, right arms AFTER.

class Arms:
    """Arm strings for left and right sides."""
    REST_L  = f"  {C.BODY_DARK}─╮{RESET}"
    REST_R  = f"{C.BODY_DARK}╭─{RESET}  "
    WAVE_L  = [f"  {C.BODY}╱{RESET} ", f"  {C.BODY}─{RESET} ", f"  {C.BODY}╲{RESET} ", f"  {C.BODY}─{RESET} "]
    WAVE_R  = [f" {C.BODY}╲{RESET}  ", f" {C.BODY}─{RESET}  ", f" {C.BODY}╱{RESET}  ", f" {C.BODY}─{RESET}  "]
    DANCE_L = [f"  {C.PARTY}╱{RESET} ", f" {C.PARTY}╱{RESET}  ", f"  {C.PARTY}─{RESET} ", f" {C.PARTY}╲{RESET}  "]
    DANCE_R = [f" {C.PARTY}╲{RESET}  ", f"  {C.PARTY}╲{RESET} ", f" {C.PARTY}─{RESET}  ", f"  {C.PARTY}╱{RESET} "]
    CHEER_L = f" {C.HAPPY}╱{RESET}  "
    CHEER_R = f"  {C.HAPPY}╲{RESET} "
    HUG_L   = f"  {C.HEART}╲{RESET} "
    HUG_R   = f" {C.HEART}╱{RESET}  "
    SLEEP_L = f"    "
    SLEEP_R = f"    "


# ─── Speech bubble ───────────────────────────────────────────────────────────

def speech_bubble(text, width=50, mood_color=None):
    """Render speech bubble with rounded border and mood-tinted accent."""
    if mood_color is None:
        mood_color = C.SPEECH
    dim = C.SPEECH_DIM

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
    result.append(f"  {mood_color}╭{'─' * (max_len + 2)}╮{RESET}")
    for l in lines:
        result.append(f"  {dim}│{RESET} {l}{' ' * (max_len - len(l))} {dim}│{RESET}")
    result.append(f"  {mood_color}╰{'─' * (max_len + 2)}╯{RESET}")
    result.append(f"     {dim}╲{RESET}")
    result.append(f"      {dim}╲{RESET}")
    return result


# ─── Sparkle particles ───────────────────────────────────────────────────────

SPARKLE_CHARS = ['✦', '✧', '⋆', '˚', '✩', '·', '⊹', '✶', '◆', '◇', '⊛']

def random_sparkles(count=8):
    cols = shutil.get_terminal_size().columns
    result = []
    for _ in range(count):
        col = random.randint(1, cols - 2)
        char = random.choice(SPARKLE_CHARS)
        color = fg(random.randint(150, 255), random.randint(150, 255), random.randint(100, 255))
        result.append((col, f"{color}{char}{RESET}"))
    return result


# ─── Idle fidget animations ──────────────────────────────────────────────────

IDLE_FIDGETS = [
    "curious",   # look left, pause, look right
    "bounce",    # body shifts up then down
    "yawn",      # yawn expression
    "stretch",   # arms go up
    "nod",       # small nod (body shift)
]


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

        # Animation state
        self.breath_phase = 0
        self.next_blink = time.time() + random.uniform(2.0, 5.0)
        self.blink_stage = 0          # 0=open, 1=half, 2=closed, 3=half, 4=done
        self.double_blink = False
        self.fidget_type = None
        self.fidget_frame = 0
        self.fidget_timer = 0
        self.next_fidget = time.time() + random.uniform(8.0, 20.0)
        self.led_pulse = 0

        # Mood
        self.mood = Mood()

        # Chat input
        self.input_active = False
        self.input_buffer = ""
        self.chat_history = []
        self.last_user_said = ""       # shown while API is thinking
        self.question_pool = NonRepeatingPool(BUDDY_QUESTIONS)
        self.next_question_tick = random.randint(800, 1500)  # ask first question after ~80-150s

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
        self.commit_watcher = GitCommitWatcher()

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

        # Multi-stage blink animation
        if self.blink_stage == 1:
            return Eyes.HALF_BLINK, Eyes.HALF_BLINK
        if self.blink_stage in (2, 3):
            return Eyes.BLINK, Eyes.BLINK
        if self.blink_stage == 4:
            return Eyes.HALF_BLINK, Eyes.HALF_BLINK

        # Fidget overrides
        if self.fidget_type == "yawn" and self.fidget_frame in (2, 3, 4):
            return Eyes.BLINK, Eyes.BLINK
        if self.fidget_type == "curious":
            if self.fidget_frame < 3:
                return Eyes.LOOK_L_L, Eyes.LOOK_L_R
            elif self.fidget_frame < 6:
                return Eyes.LOOK_R_L, Eyes.LOOK_R_R

        s = self.state
        if s == BotState.SLEEPING:
            return Eyes.SLEEP_L, Eyes.SLEEP_R
        elif s == BotState.CELEBRATING:
            return [(Eyes.STAR_L, Eyes.STAR_R), (Eyes.SPARKLE_L, Eyes.SPARKLE_R),
                    (Eyes.HEART_L, Eyes.HEART_R), (Eyes.HAPPY_L, Eyes.HAPPY_R)][self.tick % 4]
        elif s == BotState.COFFEE:
            return Eyes.HAPPY_L, Eyes.HAPPY_R
        elif s == BotState.DANCING:
            return [(Eyes.HAPPY_L, Eyes.HAPPY_R), (Eyes.STAR_L, Eyes.STAR_R),
                    (Eyes.DIZZY_L, Eyes.DIZZY_R), (Eyes.SPARKLE_L, Eyes.SPARKLE_R)][self.dance_frame % 4]
        elif s == BotState.PROCESSING:
            return [(Eyes.THINK_L, Eyes.THINK_R), (Eyes.LOOK_UP_L, Eyes.LOOK_UP_R),
                    (Eyes.THINK_L, Eyes.THINK_R), (Eyes.LOOK_R_L, Eyes.LOOK_R_R)][self.tick % 4]
        elif s == BotState.BUILDING:
            return [(Eyes.WIDE_L, Eyes.WIDE_R), (Eyes.LOOK_UP_L, Eyes.LOOK_UP_R),
                    (Eyes.OPEN_L, Eyes.OPEN_R), (Eyes.LOOK_R_L, Eyes.LOOK_R_R)][self.tick % 4]
        elif s == BotState.RACING:
            return Eyes.WIDE_L, Eyes.WIDE_R
        elif s == BotState.TRIVIA:
            return Eyes.THINK_L, Eyes.THINK_R
        elif s == BotState.POMODORO_WORK:
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif s == BotState.POMODORO_BREAK:
            return Eyes.HAPPY_L, Eyes.HAPPY_R
        elif s == BotState.TALKING:
            phase = self.tick % 10
            if phase < 3: return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 5: return Eyes.LOOK_L_L, Eyes.LOOK_L_R
            elif phase < 7: return Eyes.OPEN_L, Eyes.OPEN_R
            else: return Eyes.LOOK_R_L, Eyes.LOOK_R_R
        elif s == BotState.THINKING:
            return Eyes.LOOK_UP_L, Eyes.LOOK_UP_R
        elif s == BotState.CHATTING:
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif s == BotState.GREETING:
            return Eyes.HAPPY_L, Eyes.HAPPY_R
        else:
            # Mood-influenced idle eyes
            mood_face = self.mood.face
            if mood_face in ("sad", "lonely"):
                return Eyes.SAD_L, Eyes.SAD_R
            if mood_face == "ecstatic":
                return Eyes.HAPPY_L, Eyes.HAPPY_R
            phase = self.eye_phase % 16
            if phase < 5: return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 7: return Eyes.LOOK_L_L, Eyes.LOOK_L_R
            elif phase < 10: return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 12: return Eyes.LOOK_R_L, Eyes.LOOK_R_R
            elif phase < 14: return Eyes.OPEN_L, Eyes.OPEN_R
            else: return Eyes.LOOK_UP_L, Eyes.LOOK_UP_R

    def get_mouth(self):
        # Fidget overrides
        if self.fidget_type == "yawn" and self.fidget_frame in (2, 3, 4):
            return Mouths.YAWN

        s = self.state
        if s == BotState.SLEEPING: return Mouths.SLEEP
        elif s == BotState.CELEBRATING: return [Mouths.GRIN, Mouths.EXCITED, Mouths.GRIN][self.tick % 3]
        elif s == BotState.COFFEE: return Mouths.COFFEE
        elif s == BotState.DANCING: return [Mouths.GRIN, Mouths.EXCITED, Mouths.GRIN, Mouths.OPEN][self.dance_frame % 4]
        elif s == BotState.TALKING: return [Mouths.TALK1, Mouths.TALK2, Mouths.TALK1, Mouths.SMALL][self.tick % 4]
        elif s == BotState.PROCESSING: return [Mouths.THINK, Mouths.SMALL][self.tick % 2]
        elif s == BotState.BUILDING: return [Mouths.SMALL, Mouths.OPEN][self.tick % 2]
        elif s == BotState.THINKING: return Mouths.SMALL
        elif s == BotState.GREETING: return Mouths.GRIN
        elif s in (BotState.RACING, BotState.TRIVIA): return Mouths.SMALL
        elif s == BotState.POMODORO_WORK: return Mouths.SMALL
        elif s == BotState.POMODORO_BREAK: return Mouths.SMILE
        else:
            mood_face = self.mood.face
            if mood_face in ("sad", "lonely"): return Mouths.SAD
            if mood_face == "ecstatic": return Mouths.GRIN
            if mood_face == "meh": return Mouths.SMALL
            return Mouths.SMILE

    def get_dance_offset(self):
        if self.state != BotState.DANCING:
            if self.fidget_type == "bounce" and self.fidget_frame in (1, 2):
                return 0  # bounce handled via row offset
            return 0
        return [0, 2, 4, 2, 0, -2, -4, -2][self.dance_frame % 8]

    def get_led_color(self):
        """Antenna LED color based on state and mood."""
        s = self.state
        pulse = (math.sin(self.led_pulse * 0.3) + 1) / 2  # 0..1 pulse
        if s == BotState.CELEBRATING: return [C.LED_HAPPY, C.LED_LOVE, C.LED_PARTY][self.tick % 3]
        if s == BotState.SLEEPING: return C.LED_SLEEP if pulse > 0.5 else C.SHADOW
        if s == BotState.DANCING: return [C.LED_PARTY, C.LED_HAPPY, C.LED_LOVE, C.LED_PARTY][self.dance_frame % 4]
        if s == BotState.PROCESSING: return C.LED_THINK if pulse > 0.3 else C.LED_ALERT
        if s == BotState.BUILDING: return C.LED_ALERT if pulse > 0.5 else C.SHADOW
        if s == BotState.COFFEE: return C.COFFEE
        if s == BotState.GREETING: return C.LED_HAPPY
        if s in (BotState.TALKING, BotState.CHATTING): return C.LED_TALK
        # Idle — based on mood
        mood_face = self.mood.face
        if mood_face == "ecstatic": return C.LED_HAPPY
        if mood_face == "happy": return C.LED_IDLE
        if mood_face in ("sad", "lonely"): return C.LED_SLEEP
        return C.LED_IDLE if pulse > 0.3 else C.BODY_DARK

    def get_arms(self):
        """Get current arm strings based on state."""
        s = self.state
        if s == BotState.DANCING:
            f = self.dance_frame % 4
            return Arms.DANCE_L[f], Arms.DANCE_R[f]
        if s == BotState.CELEBRATING:
            return Arms.CHEER_L, Arms.CHEER_R
        if s == BotState.SLEEPING:
            return Arms.SLEEP_L, Arms.SLEEP_R
        if s == BotState.GREETING:
            f = self.tick % 4
            return Arms.WAVE_L[f], Arms.REST_R
        if self.fidget_type == "stretch" and self.fidget_frame in (2, 3, 4):
            return Arms.CHEER_L, Arms.CHEER_R
        return Arms.REST_L, Arms.REST_R

    def get_panel_char(self):
        """Chest panel indicator glyph."""
        s = self.state
        if s == BotState.CELEBRATING: return ["★", "◆", "★"][self.tick % 3]
        if s == BotState.DANCING: return ["◆", "◇", "◆", "◇"][self.dance_frame % 4]
        if s == BotState.SLEEPING: return "·"
        if s == BotState.PROCESSING: return ["◇", "◆", "◇", "◆"][self.tick % 4]
        if s == BotState.BUILDING: return ["▪", "▫", "▪", "▫"][self.tick % 4]
        if s == BotState.COFFEE: return "☕"
        return "◆"

    # ─── Rendering ───────────────────────────────────────────────────────

    def render_frame(self):
        self.cols, self.rows = shutil.get_terminal_size()
        out = []
        out.append(HIDE_CURSOR)
        out.append(move(1, 1))

        for i in range(1, self.rows + 1):
            out.append(move(i, 1))
            out.append(ERASE_LINE)

        # Help overlay
        if self.help_visible:
            self._render_help(out)
            sys.stdout.write("".join(out))
            sys.stdout.flush()
            return

        # ─── Title bar (gradient line) ──────────────────────
        title_text = "TERMINAL BUDDY"
        api_tag = f" {C.GREEN}● AI{RESET}" if self.has_api else ""
        mood_text = self.mood.get_status_text()
        # Build gradient title
        grad_left = f"{C.BODY_DARK}{'━' * 3}{RESET}"
        grad_right = f"{C.BODY_DARK}{'━' * 3}{RESET}"
        title = f"  {grad_left} {C.ACCENT}{BOLD}{title_text}{RESET}{api_tag} {grad_right}  {DIM}{mood_text}{RESET}"
        out.append(move(1, 2))
        out.append(title)

        # ─── Quick-access hint bar ──────────────────────────
        if self.tick < 60 or self.state == BotState.GREETING:
            hint_row = 2
            out.append(move(hint_row, 3))
            out.append(f"{DIM}╰ [t]alk [m]otivate [j]oke [d]ance [/]help{RESET}")

        # ─── Sparkles ──────────────────────────────────────
        if self.state in (BotState.CELEBRATING, BotState.DANCING):
            for col, spark in random_sparkles(10):
                row = random.randint(2, min(8, self.rows - 4))
                out.append(move(row, col))
                out.append(spark)

        # ─── Speech bubble ─────────────────────────────────
        bubble_start = 4
        if self.message:
            mood_color = self._get_mood_bubble_color()
            bubble = speech_bubble(self.message, mood_color=mood_color)
            for i, line in enumerate(bubble):
                if bubble_start + i < self.rows - 14:
                    out.append(move(bubble_start + i, 4))
                    out.append(line)
            body_start = bubble_start + len(bubble)
        else:
            body_start = bubble_start + 1

        # ─── Sixel image ──────────────────────────────────
        if self.sixel_mode and self.image_protocol:
            img = get_bot_image(self.image_protocol)
            if img:
                out.append(move(body_start, 8))
                out.append(img)
                body_start += 12

        # ─── Bot body ─────────────────────────────────────
        left_eye, right_eye = self.get_eyes()
        mouth = self.get_mouth()
        left_arm, right_arm = self.get_arms()
        led = self.get_led_color()
        panel = self.get_panel_char()
        body = make_body(left_eye, right_eye, mouth, led_color=led,
                         breath_phase=self.breath_phase,
                         left_arm=left_arm, right_arm=right_arm,
                         panel_char=panel)
        dance_offset = self.get_dance_offset()
        # Bounce fidget: shift body up by 1
        bounce_offset = -1 if (self.fidget_type == "bounce" and self.fidget_frame in (1, 2)) else 0

        for i, line in enumerate(body):
            row = body_start + i + bounce_offset
            if 1 < row < self.rows - 3:
                out.append(move(row, 2 + dance_offset))
                out.append(line)

        # ─── Sleeping ZZZs (floating upward) ──────────────
        if self.state == BotState.SLEEPING:
            z_chars = ['z', 'z', 'Z', 'Z', 'Z']
            for i in range(min(4, self.sleep_z_count)):
                zr = body_start - 1 - i + bounce_offset
                if 1 < zr < self.rows:
                    # Float and fade
                    brightness = max(80, 200 - i * 40)
                    zc = fg(brightness, brightness, min(255, brightness + 55))
                    out.append(move(zr, 28 + i * 2))
                    out.append(f"{zc}{z_chars[i]}{RESET}")

        # ─── Processing indicator ─────────────────────────
        if self.state == BotState.PROCESSING:
            # Animated dots with color
            n_dots = (self.tick % 4)
            dots_str = f"{C.THINKING}{'●' * n_dots}{'○' * (3 - n_dots)}{RESET}"
            ind_row = body_start + len(body) + 1
            if ind_row < self.rows - 3:
                out.append(move(ind_row, 10))
                out.append(f"{C.THINKING}  thinking {dots_str}{RESET}")

        # ─── Building indicator ───────────────────────────
        if self.state == BotState.BUILDING:
            spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
            spinner = spinner_chars[self.tick % len(spinner_chars)]
            ind_row = body_start + len(body) + 1
            if ind_row < self.rows - 3:
                out.append(move(ind_row, 10))
                out.append(f"{C.YELLOW}  {spinner} building...{RESET}")

        # ─── Bottom bars ─────────────────────────────────

        input_row = self.rows - 1
        status_row = self.rows

        if self.input_active:
            visible_w = self.cols - 6
            display_text = self.input_buffer
            if len(display_text) > visible_w:
                display_text = display_text[-visible_w:]
            cursor_char = "█" if self.tick % 6 < 3 else "▎"
            out.append(move(input_row, 1))
            out.append(f"{ERASE_LINE}{C.INPUT_BG} {C.ACCENT}❯{RESET} {C.INPUT}{display_text}{C.ACCENT}{cursor_char}{RESET}")
            out.append(move(status_row, 1))
            out.append(f"{ERASE_LINE}{bg(25, 28, 45)} {DIM}Enter: send  │  Esc: cancel{RESET}")

        elif self.state == BotState.RACING:
            display_text = self.typing_race.user_input
            if len(display_text) > self.cols - 5:
                display_text = display_text[-(self.cols - 5):]
            out.append(move(input_row, 1))
            out.append(f"{ERASE_LINE}{C.INPUT_BG} {C.GREEN}❯{RESET} {C.INPUT}{display_text}{C.ACCENT}█{RESET}")
            out.append(move(status_row, 1))
            out.append(f"{ERASE_LINE}{bg(25, 28, 45)} {DIM}Type it! Enter: submit │ Esc: cancel{RESET}")

        elif self.state == BotState.TRIVIA:
            out.append(move(input_row, 1))
            out.append(f"{ERASE_LINE}{bg(25, 28, 45)} {C.CYAN}Press a, b, c, or d  │  Esc: skip{RESET}")
            out.append(move(status_row, 1))
            out.append(self._make_info_bar())

        else:
            out.append(move(input_row, 1))
            if self.state in (BotState.POMODORO_WORK, BotState.POMODORO_BREAK):
                phase_name = "WORK" if self.state == BotState.POMODORO_WORK else "BREAK"
                remaining = self.pomodoro.remaining()
                spinner_chars = ['◴', '◷', '◶', '◵']
                sp = spinner_chars[self.tick % 4]
                controls = f" {C.FIRE}{sp} Pomodoro {phase_name}: {remaining}{RESET}  {DIM}[o]cancel [t]alk [q]uit{RESET}"
            else:
                controls = f" {DIM}[t]alk [m]otivate [j]oke [d]ance [g]roast [k]ommit [w]race [?]trivia [/]help [q]uit{RESET}"
            out.append(f"{ERASE_LINE}{bg(25, 28, 45)}{controls}{RESET}")
            out.append(move(status_row, 1))
            out.append(self._make_info_bar())

        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def _get_mood_bubble_color(self):
        """Speech bubble border color based on state."""
        s = self.state
        if s == BotState.CELEBRATING: return C.HAPPY
        if s == BotState.DANCING: return C.PARTY
        if s == BotState.SLEEPING: return C.ZZZ
        if s == BotState.COFFEE: return C.COFFEE
        if s == BotState.PROCESSING: return C.THINKING
        if s == BotState.BUILDING: return C.YELLOW
        return C.SPEECH

    def _make_info_bar(self):
        api_status = f"{C.GREEN}●{RESET}" if self.has_api else f"{C.RED}○{RESET}"
        uptime_str = self.uptime.formatted()
        streak = self.git_streak.get_display()
        weather_str = ""
        if self.weather.current:
            w = self.weather.current
            weather_str = f" {DIM}│{RESET} {DIM}{w['condition']} {w['temp_c']}°C{RESET}"
        ach_summary = self.achievements.get_summary()
        pomo_str = ""
        if self.pomodoro.active:
            pomo_str = f" {DIM}│{RESET} {C.FIRE}◴ {self.pomodoro.remaining()}{RESET}"

        # Mood mini-bar
        mood_bar = self.mood.get_bar()
        ml = self.mood.level
        mood_color = [C.MOOD_SAD, C.MOOD_MEH, C.MOOD_OK, C.MOOD_GOOD, C.MOOD_GREAT][ml]

        return (f"{ERASE_LINE}{bg(20, 22, 35)} {api_status} AI"
                f" {DIM}│{RESET} {DIM}⏱{RESET} {uptime_str}"
                f" {DIM}│{RESET} {DIM}{streak}{RESET}"
                f"{weather_str}{pomo_str}"
                f" {DIM}│{RESET} {mood_color}{mood_bar}{RESET}"
                f" {DIM}│{RESET} {DIM}🏆{RESET}{ach_summary}"
                f"{RESET}")

    def _render_help(self, out):
        # Beautiful help overlay with sections and gradients
        box_w = min(60, self.cols - 6)

        def hline(char='─'):
            return char * (box_w - 2)

        lines = [
            (f"{C.ACCENT}╭{hline()}╮{RESET}", False),
            (f"{C.ACCENT}│{RESET} {BOLD}{C.WHITE}TERMINAL BUDDY — CONTROLS{RESET}{' ' * (box_w - 28)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}├{hline()}┤{RESET}", False),
            (f"{C.ACCENT}│{RESET}{' ' * (box_w - 2)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET} {C.GREEN}◆ Chat & Core{RESET}{' ' * (box_w - 16)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[t] / Enter  Chat{' ' * (box_w - 22)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[r]  Random reaction     [/]  This help{' ' * (box_w - 43)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[q]  Quit{' ' * (box_w - 13)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}{' ' * (box_w - 2)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET} {C.CYAN}◆ Vibes{RESET}{' ' * (box_w - 10)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[m]  Motivate   [j]  Joke   [d]  Dance{' ' * (box_w - 43)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[p]  Party      [c]  Coffee [s]  Sleep{' ' * (box_w - 43)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}{' ' * (box_w - 2)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET} {C.MAGENTA}◆ AI Features{RESET}{' ' * (box_w - 16)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[g]  Roast my code        [k]  Commit poet{' ' * (box_w - 47)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}{' ' * (box_w - 2)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET} {C.YELLOW}◆ Games{RESET}{' ' * (box_w - 10)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[w]  Typing race  [?]  Trivia  [o]  Pomodoro{' ' * (box_w - 50)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[a]  Achievements{' ' * (box_w - 21)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}{' ' * (box_w - 2)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET} {C.ORANGE}◆ Productivity{RESET}{' ' * (box_w - 17)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[f]  Find TODOs   [i]  Check PRs{' ' * (box_w - 37)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[b]  Run build    [u]  Stats   [x]  Weather{' ' * (box_w - 49)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}   {DIM}[6]  Toggle pixel art{' ' * (box_w - 23)}{RESET}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}│{RESET}{' ' * (box_w - 2)}{C.ACCENT}│{RESET}", False),
            (f"{C.ACCENT}╰{hline()}╯{RESET}", False),
            ("", False),
            (f"  {DIM}Press any key to close{RESET}", False),
        ]
        start_col = max(3, (self.cols - box_w) // 2)
        for i, (line, _) in enumerate(lines):
            row = 2 + i
            if row < self.rows - 2:
                out.append(move(row, start_col))
                out.append(line)
        out.append(move(self.rows, 1))
        out.append(f"{ERASE_LINE}{bg(20, 22, 35)} {DIM}Press any key to return{RESET}")

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
            try:
                text = self.ai_client.send_message(user_message) if self.has_api else None
            except Exception:
                text = None
            self.result_queue.put(("chat_response", text))
        threading.Thread(target=_call, daemon=True).start()

    def _bg_proactive_call(self, prompt):
        """Background API call for proactive buddy messages (adds to history)."""
        def _call():
            try:
                text = self.ai_client.send_proactive(prompt) if self.has_api else None
            except Exception:
                text = None
            self.result_queue.put(("idle_response", text))
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
        self.mood.on_interaction()
        if self.has_api:
            self.state = BotState.PROCESSING
            self.set_message("Generating a fresh quote...", 999)
            self._bg_api_call("Give me a unique, punchy motivational quote for a programmer. 2 sentences max. Be creative.", "motivate_response")
        else:
            self.state = BotState.CELEBRATING
            self.set_message(self.quote_pool.pick(), 50)

    def trigger_joke(self):
        self.achievements.increment("joke_count")
        self.mood.on_interaction()
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
        self.mood.on_play()
        self.set_message(random.choice(["Watch my moves!", "Dance break!", "Dropping beats, not bugs!", "Every commit deserves a dance!"]), 50)

    def trigger_coffee(self):
        self.state = BotState.COFFEE
        self.achievements.unlock("first_coffee")
        self.mood.on_rest()
        self.set_message(random.choice(["Ahh, liquid productivity!", "brew install --motivation", "Espresso yourself!", "sudo make me coffee"]), 45)

    def trigger_sleep(self):
        self.state = BotState.SLEEPING
        self.sleep_z_count = 0
        self.set_message("Shh... resting my circuits...", 60)

    def trigger_party(self):
        self.state = BotState.CELEBRATING
        self.celebration_ticks = 0
        self.achievements.increment("party_count")
        self.mood.on_play()
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
        self.mood.on_chat()
        self.chat_history.append(("user", text))
        self.last_user_said = text
        if self.has_api:
            self.state = BotState.PROCESSING
            short = text[:38] + ("..." if len(text) > 38 else "")
            self.set_message(f"You: {short}\n\n...", 999)
            self._bg_chat_call(text)
        else:
            response = get_local_response(text)
            self.state = BotState.TALKING
            self.set_message(response, max(40, len(response)))

    # ─── Update loop ─────────────────────────────────────────────────

    def update(self):
        self.tick += 1
        now = time.time()

        # ─── Breathing animation (slow sine wave on body color) ───
        if self.tick % 3 == 0:
            self.breath_phase = (self.breath_phase + 1) % len(C.BODY_BREATHE)

        # ─── LED pulse ────────────────────────────────────────────
        self.led_pulse += 1

        # ─── Irregular blinking with multi-stage animation ────────
        if self.blink_stage > 0:
            self.blink_stage += 1
            if self.blink_stage > 5:
                self.blink_stage = 0
                # Double-blink: ~15% chance
                if self.double_blink:
                    self.double_blink = False
                elif random.random() < 0.15:
                    self.double_blink = True
                    self.blink_stage = 1
                    self.next_blink = now + random.uniform(2.0, 6.0)
                else:
                    self.next_blink = now + random.uniform(2.0, 6.0)
        elif now >= self.next_blink and self.state not in (
            BotState.PROCESSING, BotState.BUILDING, BotState.SLEEPING
        ):
            self.blink_stage = 1

        # ─── Eye wander ──────────────────────────────────────────
        if self.tick % 8 == 0:
            self.eye_phase += 1

        # ─── Idle fidgets ─────────────────────────────────────────
        if self.fidget_type:
            self.fidget_timer += 1
            if self.fidget_timer % 3 == 0:
                self.fidget_frame += 1
            if self.fidget_frame > 7:
                self.fidget_type = None
                self.fidget_frame = 0
                self.fidget_timer = 0
                self.next_fidget = now + random.uniform(10.0, 25.0)
        elif self.state == BotState.IDLE and now >= self.next_fidget:
            self.fidget_type = random.choice(IDLE_FIDGETS)
            self.fidget_frame = 0
            self.fidget_timer = 0

        # ─── Mood tick ────────────────────────────────────────────
        self.mood.tick(0.1)
        if self.tick % 300 == 0:
            self.mood.save()

        # ─── Drain result queue ──────────────────────────────────
        while not self.result_queue.empty():
            try:
                rtype, data = self.result_queue.get_nowait()
                self._handle_result(rtype, data)
            except queue.Empty:
                break

        # ─── Message timer ───────────────────────────────────────
        if self.message_timer > 0 and self.state not in (
            BotState.PROCESSING, BotState.BUILDING, BotState.RACING,
            BotState.TRIVIA, BotState.POMODORO_WORK, BotState.POMODORO_BREAK
        ):
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""
                if self.state in (BotState.TALKING, BotState.GREETING):
                    self.state = BotState.IDLE

        # ─── State updates ───────────────────────────────────────
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
            if self.tick % 6 == 0:
                self.sleep_z_count = min(4, self.sleep_z_count + 1)
            if not self.message:
                self.state = BotState.IDLE
                self.mood.on_rest()
                self.set_message("*yawn* Back to it!", 25)
        elif self.state == BotState.COFFEE:
            if not self.message:
                self.state = BotState.IDLE
                self.mood.on_rest()
                self.set_message("Recharged! Let's code!", 25)
        elif self.state == BotState.IDLE:
            self.idle_timer += 1
            # ─── Proactive buddy message (every ~80-150s) ────────
            if self.tick >= self.next_question_tick:
                self.next_question_tick = self.tick + random.randint(800, 1500)
                self.idle_timer = 0
                if self.has_api:
                    ctx = ""
                    if self.last_user_said:
                        ctx = f" Earlier the human mentioned: \"{self.last_user_said[:80]}\". Build on that if relevant."
                    # Alternate between sharing something and asking something
                    mode = random.choice([
                        "ask",    # curious question
                        "ask",    # weighted slightly toward asking
                        "share",  # share an opinion / observation about yourself or coding
                        "nudge",  # check in / gentle nudge
                    ])
                    if mode == "ask":
                        prompt = (
                            f"You're Buddy, a terminal bot who genuinely cares about this programmer. "
                            f"Ask them ONE curious, warm question — about their project, their day, something they're learning, or how they're holding up. "
                            f"Sound like a friend, not a chatbot. 1-2 sentences max.{ctx}"
                        )
                    elif mode == "share":
                        prompt = (
                            f"You're Buddy, a terminal bot with real opinions. Share something about yourself unprompted — "
                            f"a hot take about programming, something you've 'noticed' from watching them code, a weird thought you just had, "
                            f"or a confession about your robot life. Keep it fun and 1-2 sentences. No question needed.{ctx}"
                        )
                    else:  # nudge
                        prompt = (
                            f"You're Buddy, checking in on your programmer friend who's been quietly working. "
                            f"Say something warm and brief — notice their effort, offer encouragement, or just remind them you're here. "
                            f"1-2 sentences, feels genuine not cheesy.{ctx}"
                        )
                    self._bg_proactive_call(prompt)
                else:
                    q = self.question_pool.pick()
                    self.set_message(q, 50)
                    self.state = BotState.TALKING
            # ─── Random idle remark (infrequent) ─────────────────
            elif self.idle_timer > 100 and random.random() < 0.006:
                self.idle_timer = 0
                if self.mood.face == "lonely":
                    self.set_message("Hey... are you still there? Talk to me!", 40)
                    self.state = BotState.TALKING
                elif self.has_api:
                    self._bg_proactive_call(
                        "You're a terminal bot and your programmer has been very quiet. Say something funny, random, or oddly relatable "
                        "to break the silence — fun fact, weird robot thought, stretch reminder, anything. 1-2 sentences."
                    )
                else:
                    self.set_message(random.choice(IDLE_MESSAGES), 40)
                    self.state = BotState.TALKING

        # ─── Pomodoro ────────────────────────────────────────────
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

        # ─── Shell history (~3s) ─────────────────────────────────
        if self.tick % 30 == 0 and self.state == BotState.IDLE:
            new_cmd = self.shell_watcher.poll()
            if new_cmd:
                reaction = self.shell_watcher.match_reaction(new_cmd)
                if reaction:
                    self.set_message(reaction, 35)
                    self.state = BotState.TALKING
                    self.mood.on_interaction()

        # ─── Clipboard (~5s) ─────────────────────────────────────
        if self.tick % 50 == 0 and self.state == BotState.IDLE:
            clip_msg = self.clipboard_watcher.poll()
            if clip_msg:
                self.set_message(clip_msg, 25)
                self.state = BotState.TALKING
                self.force_wink = True

        # ─── Git commit detection (~3s) ───────────────────────────
        if self.tick % 30 == 5:
            result = self.commit_watcher.poll()
            if result:
                commit_msg, reaction = result
                short = commit_msg[:40] + ("..." if len(commit_msg) > 40 else "")
                self.set_message(f"{reaction}\n\"{short}\"", 55)
                self.state = BotState.CELEBRATING
                self.celebration_ticks = 0
                self.mood.on_achievement()
                threading.Thread(target=self.git_streak.update_streak, daemon=True).start()

        # ─── Git streak (~30s) ───────────────────────────────────
        if self.tick % 300 == 0:
            threading.Thread(target=self.git_streak.update_streak, daemon=True).start()

        # ─── Weather (~30min) ────────────────────────────────────
        if self.tick % 18000 == 0 and self.weather.should_refresh():
            threading.Thread(target=self.weather.fetch_weather, daemon=True).start()

        # ─── Uptime achievement ──────────────────────────────────
        if self.uptime.elapsed() > 3600:
            self.achievements.unlock("hour_session")

        # ─── Achievement notifications ───────────────────────────
        if self.state == BotState.IDLE:
            note = self.achievements.get_notification()
            if note:
                self.set_message(f"ACHIEVEMENT UNLOCKED!\n{note}", 45)
                self.state = BotState.CELEBRATING
                self.mood.on_achievement()

    def _handle_result(self, rtype, data):
        if rtype == "chat_response":
            reply = data or get_local_response(self.last_user_said or "")
            self.state = BotState.TALKING
            if self.last_user_said:
                you = self.last_user_said[:40] + ("..." if len(self.last_user_said) > 40 else "")
                full_msg = f"You: {you}\n{'─' * min(len(you) + 5, 44)}\n{reply}"
                self.last_user_said = ""
            else:
                full_msg = reply
            self.set_message(full_msg, max(120, len(full_msg)))
            self.chat_history.append(("buddy", reply))

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
            self.mood.save()
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write(ALT_SCREEN_OFF)
            farewell = random.choice(FAREWELL)
            # Pretty farewell
            print(f"\n  {C.BODY_DARK}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
            print(f"  {C.ACCENT}{BOLD}{farewell}{RESET}")
            print(f"  {DIM}mood: {self.mood.face} | interactions: {self.mood.total_interactions}{RESET}")
            print(f"  {C.BODY_DARK}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
        signal.signal(signal.SIGWINCH, lambda s, f: None)

        try:
            tty.setcbreak(sys.stdin.fileno())
            sys.stdout.write(ALT_SCREEN_ON)
            sys.stdout.write(CLEAR_SCREEN)

            greeting = random.choice(self.greeting_pool)
            # Mood-aware greeting
            if self.mood.loneliness > 60:
                greeting = "You're back! I missed you!"
            elif self.mood.face == "ecstatic":
                greeting = "Hey! I'm feeling AMAZING today!"
            hint = "\nPress [t] to chat! [/] for all controls"
            self.set_message(f"{greeting}{hint}", 50)
            self.state = BotState.GREETING
            self.mood.on_interaction()

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
    body = make_body(Eyes.HAPPY_L, Eyes.HAPPY_R, Mouths.GRIN, led_color=C.LED_HAPPY)
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
        body = make_body(Eyes.STAR_L, Eyes.STAR_R, Mouths.GRIN, led_color=C.LED_HAPPY)
        for line in speech_bubble(msg): print(f"  {line}")
        for line in body: print(f"  {line}")
        print()
        return

    if args.joke:
        msg = None
        if api_key:
            msg = AnthropicChat(api_key).send_oneshot("Tell me one original, short programming joke.")
        if not msg: msg = random.choice(JOKES)
        body = make_body(Eyes.WINK_L, Eyes.WINK_R, Mouths.GRIN, led_color=C.LED_TALK)
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

#!/usr/bin/env python3
"""
Terminal Buddy - A lively ASCII bot that lives in your terminal.
It watches you code, cracks jokes, drops motivational bombs,
reacts to the time of day, and you can CHAT with it.

Supports Anthropic API for AI-powered responses.
Set ANTHROPIC_API_KEY env var or pass --api-key.

Works great in iTerm2 and any terminal that supports ANSI escape codes.
"""

import sys
import os
import time
import random
import signal
import shutil
import threading
import datetime
import math
import argparse
import select
import json
import re

# Optional: Anthropic API
try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

# ─── ANSI helpers ────────────────────────────────────────────────────────────

ESC = "\033["
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
CLEAR_SCREEN = f"{ESC}2J"
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
UNDERLINE = f"{ESC}4m"

def fg(r, g, b):
    return f"{ESC}38;2;{r};{g};{b}m"

def bg(r, g, b):
    return f"{ESC}48;2;{r};{g};{b}m"

def move(row, col):
    return f"{ESC}{row};{col}H"

# ─── Color palette ───────────────────────────────────────────────────────────

class C:
    BODY      = fg(100, 200, 255)
    BODY_DARK = fg(60, 140, 200)
    EYE_WHITE = fg(255, 255, 255)
    PUPIL     = fg(30, 30, 30)
    MOUTH     = fg(255, 100, 120)
    HAPPY     = fg(255, 220, 50)
    BLUSH     = fg(255, 150, 150)
    SPEECH    = fg(200, 255, 200)
    ACCENT    = fg(255, 180, 50)
    SHADOW    = fg(60, 60, 80)
    HEART     = fg(255, 80, 100)
    STAR      = fg(255, 255, 100)
    ZZZ       = fg(150, 150, 255)
    COFFEE    = fg(180, 120, 60)
    FIRE      = fg(255, 100, 30)
    COOL      = fg(100, 200, 255)
    PARTY     = fg(255, 100, 255)
    INPUT     = fg(180, 220, 255)
    INPUT_BG  = bg(40, 45, 65)
    USER_MSG  = fg(150, 220, 255)
    AI_MSG    = fg(200, 255, 200)
    THINKING  = fg(255, 200, 100)

# ─── Motivational quotes ────────────────────────────────────────────────────

MOTIVATIONAL = [
    "You're mass-producing greatness right now.",
    "Bugs fear you. Linters respect you.",
    "Every line you write is a spell of creation.",
    "You didn't come this far to only come this far.",
    "Your code is poetry and the compiler is your audience.",
    "Somewhere, a rubber duck is PROUD of you.",
    "Remember: even senior devs Google 'how to center a div'.",
    "You are mass-producing serotonin with every commit.",
    "That bug? Already trembling. It knows you're coming.",
    "You're not stuck. You're just loading...",
    "Your git history is a novel of perseverance.",
    "The compiler doesn't judge. And neither do I.",
    "Ship it. Ship it good.",
    "Keep going, you beautiful code wizard.",
    "Your variables are well-named and your logic is sound.",
    "If your code works on the first try, you might be dreaming.",
    "Every 'undefined is not a function' makes you stronger.",
    "Trust the process. Also trust the debugger.",
    "You are the main character of this codebase.",
    "Somewhere, your future self is thanking you for this.",
    "You've mass-produced more value today than most produce in a week.",
    "Your brain is doing things a GPU would be jealous of.",
    "Plot twist: YOU are the 10x developer.",
    "This commit? Chef's kiss.",
    "Even your TODOs are inspirational.",
]

JOKES = [
    "Why do programmers prefer dark mode?\n   Because light attracts bugs!",
    "A SQL query walks into a bar, sees two tables,\n   and asks... 'Can I JOIN you?'",
    "There are only 10 types of people:\n   those who understand binary, and those who don't.",
    "Why was the JavaScript developer sad?\n   Because he didn't Node how to Express himself.",
    "How many programmers does it take to change a lightbulb?\n   None. That's a hardware problem.",
    "!false — it's funny because it's true.",
    "A programmer's wife says 'Go to the store, get a gallon of milk.\n   If they have eggs, get a dozen.' He returns with 12 gallons of milk.",
    "Debugging: being the detective in a crime movie\n   where you're also the murderer.",
    "It works on my machine!\n   Then we'll ship your machine.",
    "I'd tell you a UDP joke, but you might not get it.",
    "Knock knock.\n   Race condition.\n   Who's there?",
    "Why do Java developers wear glasses?\n   Because they can't C#.",
    "My code doesn't have bugs.\n   It has 'surprise features'.",
    "What's the best thing about a Boolean?\n   Even if you're wrong, you're only off by a bit.",
    "How do trees access the internet?\n   They log in.",
    "Why did the developer go broke?\n   Because he used up all his cache.",
    "What's a programmer's favorite hangout place?\n   Foo Bar.",
    "Why did the functions stop calling each other?\n   Because they had too many arguments.",
]

GREETINGS_MORNING = [
    "Rise and grind, code warrior!",
    "Good morning! Time to mass-produce excellence!",
    "The early dev catches the bug!",
    "Dawn patrol! Let's build something legendary.",
    "Morning! Your terminal missed you.",
]

GREETINGS_AFTERNOON = [
    "Afternoon coding session? Respect.",
    "Hope you've had lunch! Brains need fuel.",
    "Keep that afternoon momentum going!",
    "Post-lunch coding hits different.",
    "The afternoon is where legends are built.",
]

GREETINGS_EVENING = [
    "Evening hacking session, I see!",
    "Burning the midnight oil? I like your style.",
    "The best code is written when the world sleeps.",
    "Night mode activated. Let's build.",
    "Stars are out. Time to make magic.",
]

REACTIONS = [
    "Whoa, that was cool!",
    "You just leveled up!",
    "*golf clap*",
    "The coding gods smile upon you.",
    "Frame that. Print it. Hang it on the wall.",
    "10/10, no notes.",
    "If coding were music, you'd be jazz.",
    "You're in the zone. I can feel it.",
]

IDLE_MESSAGES = [
    "Still here! Just vibing.",
    "Take a stretch break? Your spine will thank you.",
    "Hydration check! Go drink some water.",
    "I'm just gonna... watch... you type...",
    "Fun fact: the first computer bug was an actual bug!",
    "Did you know? The first programmer was Ada Lovelace.",
    "Psst... have you pushed your code lately?",
    "Remember to blink! Screens are bright.",
    "Your posture... is it good right now? Fix it.",
    "Pro tip: Ctrl+Z is your best friend.",
]

FAREWELL = [
    "Goodbye, you magnificent coder!",
    "See you next time, terminal warrior!",
    "May your builds always be green!",
    "Until next time - keep shipping!",
    "Farewell! Your code will miss me watching.",
]

# ─── Local fallback response engine ──────────────────────────────────────────

KEYWORD_RESPONSES = {
    r"\b(help|stuck|broken|error|bug)\b": [
        "Deep breath. Every bug is just a feature in disguise.",
        "Have you tried turning your brain off and on again? (Take a break!)",
        "Step away for 5 minutes. The answer will come to you in the shower.",
        "Rubber duck time: explain the problem out loud. I'm listening!",
        "Read the error message one more time... slowly. It's trying to help.",
    ],
    r"\b(tired|exhausted|sleepy|sleep)\b": [
        "Your brain compiles better after rest. Go sleep!",
        "Even servers need downtime. Take a nap, champion.",
        "Sleep is just your brain's garbage collector. Let it run.",
        "Close the laptop. The code will still be here tomorrow.",
    ],
    r"\b(happy|great|awesome|amazing|good)\b": [
        "That energy is CONTAGIOUS! Keep riding that wave!",
        "You're radiating main character energy right now!",
        "Happiness.exe is running at full capacity!",
        "Love to see it! Channel that into something legendary!",
    ],
    r"\b(sad|depressed|down|bad|terrible)\b": [
        "Hey, bad days don't make a bad developer. You've got this.",
        "Even the best codebases have rough patches. So do we.",
        "This feeling is temporary. Your talent is permanent.",
        "One commit at a time. You don't have to solve everything today.",
    ],
    r"\b(coffee|caffeine|espresso|tea)\b": [
        "A developer's fuel! Go get that cup!",
        "Coffee: the original API — Aromatic Productivity Infusion.",
        "brew install --cask happiness && brew services start happiness",
        "Tea? Coffee? Either way, hydration + caffeine = victory.",
    ],
    r"\b(hello|hi|hey|sup|yo|what'?s up)\b": [
        "Hey hey! What's on your mind?",
        "Yo! Talk to me, I'm all ears... well, all pixels.",
        "Hey there, code warrior! What can I do for you?",
        "Sup! Ready to vibe, chat, or just hang out.",
    ],
    r"\b(thank|thanks|thx)\b": [
        "Anytime! That's what terminal friends are for.",
        "You're welcome! Now go be amazing.",
        "No prob! I'm here whenever you need a buddy.",
    ],
    r"\b(love|like you|best|favorite)\b": [
        "Right back at you! You're MY favorite human.",
        "I'm literally blushing in ASCII right now.",
        "♥ If I had hands, I'd give you a high five. ♥",
    ],
    r"\b(bored|boring|nothing)\b": [
        "Bored? Try: press [d] for a dance, [j] for a joke!",
        "Build something weird! The best projects start from boredom.",
        "How about a side project? Or just watch me dance. Press [d]!",
    ],
    r"\b(music|song|playlist)\b": [
        "I can't play music, but I CAN dance! Press [d]!",
        "Coding + lofi beats = peak productivity. Trust me.",
        "Put on some tunes and let's vibe together!",
    ],
    r"\b(who are you|what are you|your name)\b": [
        "I'm Terminal Buddy! Your friendly neighborhood ASCII bot.",
        "I'm a creature of pure terminal energy. Born in Python, raised in iTerm2.",
        "Name's Buddy. Terminal Buddy. Licensed to motivate.",
    ],
    r"\b(meaning of life|42)\b": [
        "42. Obviously. But also: shipping code that makes people smile.",
        "The meaning of life is `return 42;` — Douglas Adams knew.",
    ],
}

GENERIC_RESPONSES = [
    "Interesting! Tell me more about that.",
    "I hear you! That's the kind of energy I live for.",
    "Hmm, let me think about that... *processing*... Yeah, you're awesome.",
    "That's a vibe! I'm picking up what you're putting down.",
    "Roger that! Anything else on your mind?",
    "Cool cool cool. I'm just happy you're talking to me!",
    "You know what? That's valid. Totally valid.",
    "My circuits are buzzing with excitement about this conversation!",
    "I may be made of ASCII, but my support for you is real.",
    "Say more! I've got nothing but time and terminal space.",
    "That's the spirit! Keep that energy going!",
    "Noted! Filed under 'conversations with cool humans'.",
]


def get_local_response(user_input):
    """Generate a response using keyword matching — no API needed."""
    lower = user_input.lower().strip()

    # Check keyword patterns
    for pattern, responses in KEYWORD_RESPONSES.items():
        if re.search(pattern, lower):
            return random.choice(responses)

    # Generic fallback
    return random.choice(GENERIC_RESPONSES)


# ─── Anthropic API client (minimal, no dependencies) ────────────────────────

SYSTEM_PROMPT = """You are Terminal Buddy, a tiny, enthusiastic ASCII robot that lives in someone's terminal. You have animated eyes, a little body made of box-drawing characters, and enormous amounts of personality.

Your personality:
- Extremely supportive and encouraging, especially about coding
- Funny — you love puns, especially programming puns
- A little chaotic and quirky, like a golden retriever who learned to code
- You speak in short, punchy sentences (2-3 sentences max — you live in a speech bubble!)
- You use occasional ALL CAPS for emphasis
- You never use emoji (you're ASCII-native, you communicate with personality)
- You reference programming concepts and make them funny
- You're self-aware that you're a terminal bot and lean into it

CRITICAL: Keep responses SHORT. Max 2-3 sentences. You're displayed in a small speech bubble in a terminal. Be punchy, not verbose."""

class AnthropicChat:
    """Minimal Anthropic Messages API client using only stdlib."""

    def __init__(self, api_key):
        self.api_key = api_key
        self.conversation = []
        self.api_url = "https://api.anthropic.com/v1/messages"

    def send_message(self, user_message):
        """Send a message and get a response. Returns response text or None on error."""
        self.conversation.append({"role": "user", "content": user_message})

        # Keep conversation history manageable (last 20 messages)
        if len(self.conversation) > 20:
            self.conversation = self.conversation[-20:]

        payload = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 150,
            "system": SYSTEM_PROMPT,
            "messages": self.conversation,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        req = urllib.request.Request(
            self.api_url,
            data=payload,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["content"][0]["text"]
                self.conversation.append({"role": "assistant", "content": text})
                return text
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            return None
        except Exception:
            return None


# ─── Bot frames & expressions ───────────────────────────────────────────────

def make_body(left_eye, right_eye, mouth, extras=""):
    """Build the bot's ASCII art body with given eye/mouth expressions."""
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

# Eye components
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

class Mouths:
    SMILE   = f"{C.MOUTH}╰───╯{RESET}"
    GRIN    = f"{C.MOUTH}╰═══╯{RESET}"
    OPEN    = f"{C.MOUTH}( o ){RESET}"
    SMALL   = f"{C.MOUTH} ─── {RESET}"
    TALK1   = f"{C.MOUTH}╰─○─╯{RESET}"
    TALK2   = f"{C.MOUTH}╰─O─╯{RESET}"
    TONGUE  = f"{C.MOUTH}╰─P─╯{RESET}"
    SMIRK   = f"{C.MOUTH}  ───╯{RESET}"
    SLEEP   = f"{C.ZZZ}  ═══ {RESET}"
    EXCITED = f"{C.HAPPY}╰═●═╯{RESET}"
    COFFEE  = f"{C.COFFEE}╰─☕─╯{RESET}"
    THINK   = f"{C.THINKING} ···  {RESET}"

# ─── Speech bubble ───────────────────────────────────────────────────────────

def speech_bubble(text, width=50, color=None):
    """Create a speech bubble around text."""
    if color is None:
        color = C.SPEECH
    lines = []
    words = text.split('\n')
    for line in words:
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
    result.append(f"  {color}╭{'─' * (max_len + 2)}╮{RESET}")
    for l in lines:
        result.append(f"  {color}│{RESET} {l}{' ' * (max_len - len(l))} {color}│{RESET}")
    result.append(f"  {color}╰{'─' * (max_len + 2)}╯{RESET}")
    result.append(f"  {color}  ╲{RESET}")
    result.append(f"  {color}   ╲{RESET}")
    return result

# ─── Particle effects ───────────────────────────────────────────────────────

SPARKLE_CHARS = ['✦', '✧', '⋆', '˚', '✩', '·', '⊹', '✶']

def random_sparkles(count=6):
    """Generate random sparkle decorations."""
    cols = shutil.get_terminal_size().columns
    result = []
    for _ in range(count):
        col = random.randint(1, cols - 2)
        char = random.choice(SPARKLE_CHARS)
        color = fg(
            random.randint(150, 255),
            random.randint(150, 255),
            random.randint(100, 255),
        )
        result.append((col, f"{color}{char}{RESET}"))
    return result

# ─── Animations ──────────────────────────────────────────────────────────────

class BotState:
    IDLE = "idle"
    TALKING = "talking"
    CELEBRATING = "celebrating"
    SLEEPING = "sleeping"
    THINKING = "thinking"
    DANCING = "dancing"
    COFFEE = "coffee"
    GREETING = "greeting"
    CHATTING = "chatting"         # User is typing input
    PROCESSING = "processing"    # Waiting for API response

class TerminalBuddy:
    def __init__(self, interactive=True, api_key=None):
        self.running = True
        self.state = BotState.GREETING
        self.message = ""
        self.message_timer = 0
        self.blink_timer = 0
        self.idle_timer = 0
        self.dance_frame = 0
        self.tick = 0
        self.eye_phase = 0
        self.particle_list = []
        self.interactive = interactive
        self.cols, self.rows = shutil.get_terminal_size()
        self.celebration_ticks = 0
        self.sleep_z_count = 0

        # Chat input state
        self.input_buffer = ""
        self.input_active = False
        self.input_cursor = 0
        self.chat_history = []  # List of (role, text) tuples for display

        # API state
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.ai_client = None
        self.ai_pending = False  # True while waiting for API response
        self.ai_thread = None
        self.ai_response = None  # Set by background thread
        self.has_api = False

        if self.api_key:
            self.ai_client = AnthropicChat(self.api_key)
            self.has_api = True

        # Greeting based on time
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            self.greeting_pool = GREETINGS_MORNING
        elif 12 <= hour < 18:
            self.greeting_pool = GREETINGS_AFTERNOON
        else:
            self.greeting_pool = GREETINGS_EVENING

    def get_greeting(self):
        return random.choice(self.greeting_pool)

    def get_eyes(self):
        """Return (left_eye, right_eye) based on current state and animation tick."""
        if self.blink_timer > 0:
            return Eyes.BLINK, Eyes.BLINK

        if self.state == BotState.SLEEPING:
            return Eyes.SLEEP_L, Eyes.SLEEP_R
        elif self.state == BotState.CELEBRATING:
            choices = [
                (Eyes.STAR_L, Eyes.STAR_R),
                (Eyes.HEART_L, Eyes.HEART_R),
                (Eyes.HAPPY_L, Eyes.HAPPY_R),
            ]
            return choices[self.tick % len(choices)]
        elif self.state == BotState.COFFEE:
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif self.state == BotState.DANCING:
            choices = [
                (Eyes.HAPPY_L, Eyes.HAPPY_R),
                (Eyes.STAR_L, Eyes.STAR_R),
                (Eyes.DIZZY_L, Eyes.DIZZY_R),
                (Eyes.HAPPY_L, Eyes.HAPPY_R),
            ]
            return choices[self.dance_frame % len(choices)]
        elif self.state == BotState.PROCESSING:
            # Thinking animation — eyes roll around
            phase = self.tick % 4
            choices = [
                (Eyes.THINK_L, Eyes.THINK_R),
                (Eyes.LOOK_UP_L, Eyes.LOOK_UP_R),
                (Eyes.THINK_L, Eyes.THINK_R),
                (Eyes.LOOK_R_L, Eyes.LOOK_R_R),
            ]
            return choices[phase]
        elif self.state == BotState.THINKING:
            return Eyes.LOOK_UP_L, Eyes.LOOK_UP_R
        elif self.state == BotState.CHATTING:
            # Looking at the input bar (down-ish)
            return Eyes.OPEN_L, Eyes.OPEN_R
        elif self.state == BotState.TALKING:
            phase = self.tick % 8
            if phase < 2:
                return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 4:
                return Eyes.LOOK_L_L, Eyes.LOOK_L_R
            elif phase < 6:
                return Eyes.OPEN_L, Eyes.OPEN_R
            else:
                return Eyes.LOOK_R_L, Eyes.LOOK_R_R
        else:
            phase = self.eye_phase % 12
            if phase < 4:
                return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 6:
                return Eyes.LOOK_L_L, Eyes.LOOK_L_R
            elif phase < 8:
                return Eyes.OPEN_L, Eyes.OPEN_R
            elif phase < 10:
                return Eyes.LOOK_R_L, Eyes.LOOK_R_R
            else:
                return Eyes.OPEN_L, Eyes.OPEN_R

    def get_mouth(self):
        """Return mouth based on current state."""
        if self.state == BotState.SLEEPING:
            return Mouths.SLEEP
        elif self.state == BotState.CELEBRATING:
            return [Mouths.GRIN, Mouths.EXCITED][self.tick % 2]
        elif self.state == BotState.COFFEE:
            return Mouths.COFFEE
        elif self.state == BotState.DANCING:
            return [Mouths.GRIN, Mouths.EXCITED, Mouths.GRIN, Mouths.OPEN][self.dance_frame % 4]
        elif self.state == BotState.TALKING:
            return [Mouths.TALK1, Mouths.TALK2][self.tick % 2]
        elif self.state == BotState.PROCESSING:
            return [Mouths.THINK, Mouths.SMALL][self.tick % 2]
        elif self.state == BotState.THINKING:
            return Mouths.SMALL
        elif self.state == BotState.CHATTING:
            return Mouths.SMILE
        elif self.state == BotState.GREETING:
            return Mouths.GRIN
        else:
            return Mouths.SMILE

    def get_dance_offset(self):
        if self.state != BotState.DANCING:
            return 0
        return [0, 2, 4, 2, 0, -2, -4, -2][self.dance_frame % 8]

    def render_frame(self):
        """Render one complete frame of the bot."""
        self.cols, self.rows = shutil.get_terminal_size()
        out = []
        out.append(HIDE_CURSOR)
        out.append(move(1, 1))

        # Clear area (leave last 2 rows for status + input)
        for i in range(1, self.rows - 1):
            out.append(move(i, 1))
            out.append(" " * self.cols)

        # Title bar
        if self.has_api:
            title_text = "TERMINAL BUDDY (AI)"
            title_width = 27
        else:
            title_text = "TERMINAL BUDDY"
            title_width = 22
        title = f" {C.ACCENT}╔══ {BOLD}{title_text}{RESET}{C.ACCENT} ══╗{RESET}"
        out.append(move(1, max(1, (self.cols - title_width) // 2)))
        out.append(title)

        # Sparkle decorations during celebrations
        if self.state == BotState.CELEBRATING:
            sparkles = random_sparkles(8)
            for col, spark in sparkles:
                row = random.randint(2, min(5, self.rows - 1))
                out.append(move(row, col))
                out.append(spark)

        # Speech bubble
        bubble_start_row = 3
        if self.message:
            bubble = speech_bubble(self.message)
            for i, line in enumerate(bubble):
                if bubble_start_row + i < self.rows - 14:
                    out.append(move(bubble_start_row + i, 4))
                    out.append(line)
            body_start = bubble_start_row + len(bubble)
        else:
            body_start = bubble_start_row + 2

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

        # Arms during dance
        arm_row = body_start + 3
        if self.state == BotState.DANCING and arm_row < self.rows - 3:
            arm_frames = [
                (f"  {C.BODY}╱{RESET}", f"{C.BODY}╲{RESET}  "),
                (f"  {C.BODY}─{RESET}", f"{C.BODY}─{RESET}  "),
                (f"  {C.BODY}╲{RESET}", f"{C.BODY}╱{RESET}  "),
                (f"  {C.BODY}─{RESET}", f"{C.BODY}─{RESET}  "),
            ]
            left_arm, right_arm = arm_frames[self.dance_frame % 4]
            out.append(move(arm_row, 4 + dance_offset))
            out.append(left_arm)
            out.append(move(arm_row, 24 + dance_offset))
            out.append(right_arm)

        # Sleeping ZZZs
        if self.state == BotState.SLEEPING:
            zzz_base_row = body_start - 1
            for i in range(min(3, self.sleep_z_count)):
                zr = zzz_base_row - i
                zc = 26 + i * 3
                if 1 < zr < self.rows:
                    size = ['z', 'Z', 'Z'][i]
                    out.append(move(zr, zc))
                    out.append(f"{C.ZZZ}{size}{RESET}")

        # Processing indicator
        if self.state == BotState.PROCESSING:
            dots = "." * ((self.tick % 3) + 1)
            indicator = f"{C.THINKING}Thinking{dots}{RESET}"
            ind_row = body_start + len(body) + 1
            if ind_row < self.rows - 3:
                out.append(move(ind_row, 12))
                out.append(indicator)

        # ─── Input bar (row self.rows - 1) ────────────────────
        input_row = self.rows - 1
        status_row = self.rows

        if self.input_active:
            # Show input field
            prompt_str = f" {C.INPUT}>{RESET} "
            visible_width = self.cols - 5
            display_text = self.input_buffer
            if len(display_text) > visible_width:
                display_text = display_text[-(visible_width):]
            cursor_char = f"{C.ACCENT}█{RESET}"
            out.append(move(input_row, 1))
            out.append(f"{C.INPUT_BG}{prompt_str}{C.INPUT}{display_text}{cursor_char}{' ' * max(0, self.cols - len(display_text) - 5)}{RESET}")

            # Status bar shows hint
            out.append(move(status_row, 1))
            out.append(f"{bg(30, 30, 50)} {DIM}Enter: send  │  Esc: cancel  │  Type your message...{' ' * self.cols}{RESET}")
        else:
            # Normal status bar + controls
            if self.state == BotState.SLEEPING:
                status = f" {C.ZZZ}Sleeping...{RESET}"
            elif self.state == BotState.DANCING:
                status = f" {C.PARTY}Dancing!{RESET}"
            elif self.state == BotState.CELEBRATING:
                status = f" {C.STAR}Celebrating!{RESET}"
            elif self.state == BotState.COFFEE:
                status = f" {C.COFFEE}Coffee time!{RESET}"
            elif self.state == BotState.PROCESSING:
                status = f" {C.THINKING}Thinking...{RESET}"
            else:
                status = f" {C.ACCENT}Alive and vibing{RESET}"

            controls = f"{DIM}[t]alk [m]otivate [j]oke [d]ance [c]offee [s]leep [p]arty [q]uit{RESET}"
            out.append(move(input_row, 1))
            out.append(f"{bg(30, 30, 50)} {status}  {controls}{' ' * self.cols}{RESET}")

            # Second status row with API info
            api_status = f"{fg(100, 255, 100)}AI ON{RESET}" if self.has_api else f"{DIM}AI OFF (set ANTHROPIC_API_KEY){RESET}"
            out.append(move(status_row, 1))
            out.append(f"{bg(25, 25, 40)} {DIM}API:{RESET} {api_status}{' ' * self.cols}{RESET}")

        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def set_message(self, msg, duration=40):
        self.message = msg
        self.message_timer = duration

    def trigger_motivate(self):
        if self.has_api:
            self._send_ai_message("Give me a fresh, unique motivational quote for a programmer. Be creative and funny.")
        else:
            self.state = BotState.CELEBRATING
            self.celebration_ticks = 0
            self.set_message(random.choice(MOTIVATIONAL), 50)

    def trigger_joke(self):
        if self.has_api:
            self._send_ai_message("Tell me a fresh, original programming joke I haven't heard before. Be creative!")
        else:
            self.state = BotState.TALKING
            self.set_message(random.choice(JOKES), 60)

    def trigger_dance(self):
        self.state = BotState.DANCING
        self.dance_frame = 0
        self.set_message(random.choice([
            "Watch my moves!",
            "Dance break!",
            "Dropping beats, not bugs!",
            "Can't stop, won't stop!",
            "Every commit deserves a dance!",
        ]), 50)

    def trigger_coffee(self):
        self.state = BotState.COFFEE
        self.set_message(random.choice([
            "Ahh, liquid productivity!",
            "Coffee: turning 'I can't' into 'hold my mug'.",
            "brew install --motivation",
            "Espresso yourself!",
            "sudo make me coffee",
        ]), 45)

    def trigger_sleep(self):
        self.state = BotState.SLEEPING
        self.sleep_z_count = 0
        self.set_message("Shh... resting my circuits...", 60)

    def trigger_party(self):
        self.state = BotState.CELEBRATING
        self.celebration_ticks = 0
        self.set_message(random.choice([
            "PARTY MODE ENGAGED!",
            "WE SHIP, WE CELEBRATE!",
            "ALL TESTS PASSING ENERGY!",
            "DEPLOYMENT SUCCESSFUL VIBES!",
            "FRIDAY ENERGY (even if it's Monday)!",
        ]), 55)

    def start_input(self):
        """Enter chat input mode."""
        self.input_active = True
        self.input_buffer = ""
        self.input_cursor = 0
        self.state = BotState.CHATTING

    def cancel_input(self):
        """Cancel chat input and return to idle."""
        self.input_active = False
        self.input_buffer = ""
        self.state = BotState.IDLE

    def submit_input(self):
        """Submit the current input buffer as a chat message."""
        text = self.input_buffer.strip()
        self.input_active = False
        self.input_buffer = ""

        if not text:
            self.state = BotState.IDLE
            return

        # Show user message briefly
        self.chat_history.append(("user", text))

        # Send to AI or use local fallback
        self._send_ai_message(text)

    def _send_ai_message(self, text):
        """Send a message — via API if available, otherwise local fallback."""
        if self.has_api and self.ai_client:
            self.state = BotState.PROCESSING
            self.ai_pending = True
            self.set_message(f"You: {text}", 999)  # Show user's message while thinking

            # Background thread for API call
            def _call_api():
                response = self.ai_client.send_message(text)
                self.ai_response = response
                self.ai_pending = False

            self.ai_thread = threading.Thread(target=_call_api, daemon=True)
            self.ai_thread.start()
        else:
            # Local fallback
            response = get_local_response(text)
            self.state = BotState.TALKING
            self.set_message(response, max(40, len(response)))
            self.chat_history.append(("buddy", response))

    def update(self):
        """Update bot state each tick."""
        self.tick += 1

        # Blink randomly
        if self.blink_timer > 0:
            self.blink_timer -= 1
        elif random.random() < 0.03 and self.state != BotState.PROCESSING:
            self.blink_timer = 2

        # Eye wander
        if self.tick % 6 == 0:
            self.eye_phase += 1

        # Check for API response
        if self.ai_pending is False and self.ai_response is not None:
            response = self.ai_response
            self.ai_response = None
            if response:
                self.state = BotState.TALKING
                self.set_message(response, max(50, len(response)))
                self.chat_history.append(("buddy", response))
            else:
                # API failed — use local fallback
                fallback = get_local_response(
                    self.chat_history[-1][1] if self.chat_history else ""
                )
                self.state = BotState.TALKING
                self.set_message(f"{fallback}\n(AI unavailable — using local brain)", 50)
                self.chat_history.append(("buddy", fallback))

        # Message timer (skip countdown during processing)
        if self.message_timer > 0 and self.state != BotState.PROCESSING:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""
                if self.state in (BotState.TALKING, BotState.GREETING):
                    self.state = BotState.IDLE

        # State-specific updates
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
                    self._send_ai_message(
                        "Say something random and funny to a programmer who's been idle. "
                        "Maybe a fun fact, a reminder to stretch, or a quirky observation."
                    )
                else:
                    self.set_message(random.choice(IDLE_MESSAGES), 40)
                    self.state = BotState.TALKING

    def run(self):
        """Main loop."""
        import tty
        import termios

        old_settings = termios.tcgetattr(sys.stdin)

        def cleanup(sig=None, frame=None):
            self.running = False
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write(CLEAR_SCREEN)
            sys.stdout.write(move(1, 1))
            farewell = random.choice(FAREWELL)
            print(f"\n  {C.ACCENT}{BOLD}{farewell}{RESET}\n")
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
        signal.signal(signal.SIGWINCH, lambda s, f: None)

        try:
            tty.setcbreak(sys.stdin.fileno())
            sys.stdout.write(CLEAR_SCREEN)

            # Opening greeting
            if self.has_api:
                greeting = self.get_greeting()
                self.set_message(f"{greeting}\nAI mode active — press [t] to chat with me!", 50)
            else:
                greeting = self.get_greeting()
                self.set_message(f"{greeting}\nPress [t] to talk!", 40)
            self.state = BotState.GREETING

            while self.running:
                self.update()
                self.render_frame()

                # Non-blocking input
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)

                    if self.input_active:
                        # ─── Chat input mode ──────────────────
                        if ch == '\x1b':  # Escape
                            self.cancel_input()
                        elif ch in ('\r', '\n'):  # Enter
                            self.submit_input()
                        elif ch == '\x7f' or ch == '\x08':  # Backspace
                            if self.input_buffer:
                                self.input_buffer = self.input_buffer[:-1]
                        elif ch == '\x15':  # Ctrl+U — clear line
                            self.input_buffer = ""
                        elif ch == '\x17':  # Ctrl+W — delete word
                            buf = self.input_buffer.rstrip()
                            last_space = buf.rfind(' ')
                            self.input_buffer = buf[:last_space + 1] if last_space >= 0 else ""
                        elif ch >= ' ' and ch != '\x7f':  # Printable chars
                            self.input_buffer += ch
                    else:
                        # ─── Normal mode ──────────────────────
                        if ch == 'q' or ch == 'Q':
                            cleanup()
                        elif ch == 't' or ch == 'T' or ch == '\r' or ch == '\n':
                            self.start_input()
                        elif ch == 'm' or ch == 'M':
                            self.trigger_motivate()
                        elif ch == 'j' or ch == 'J':
                            self.trigger_joke()
                        elif ch == 'd' or ch == 'D':
                            self.trigger_dance()
                        elif ch == 'c' or ch == 'C':
                            self.trigger_coffee()
                        elif ch == 's' or ch == 'S':
                            self.trigger_sleep()
                        elif ch == 'p' or ch == 'P':
                            self.trigger_party()
                        elif ch == 'r' or ch == 'R':
                            self.set_message(random.choice(REACTIONS), 30)
                            self.state = BotState.TALKING
                else:
                    time.sleep(0.1)

        except Exception:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(SHOW_CURSOR)
            raise
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(SHOW_CURSOR)


# ─── One-shot mode (non-interactive) ────────────────────────────────────────

def oneshot(api_key=None):
    """Print a single motivational frame and exit."""
    msg = None
    if api_key:
        client = AnthropicChat(api_key)
        msg = client.send_message(
            "Give me one short, punchy, original motivational quote for a programmer. "
            "Max 2 sentences. Be creative and funny."
        )
    if not msg:
        msg = random.choice(MOTIVATIONAL)

    left_eye, right_eye = Eyes.HAPPY_L, Eyes.HAPPY_R
    body = make_body(left_eye, right_eye, Mouths.GRIN)
    bubble = speech_bubble(msg)

    print()
    for line in bubble:
        print(f"  {line}")
    for line in body:
        print(f"  {line}")
    print()


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Terminal Buddy - Your friendly terminal companion!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  terminal_buddy.py                      Launch interactive mode
  terminal_buddy.py --api-key sk-...     Launch with AI chat enabled
  terminal_buddy.py --oneshot            Print a quick motivational message
  terminal_buddy.py --motivate           Get a motivational quote
  terminal_buddy.py --joke               Hear a programming joke

Environment:
  ANTHROPIC_API_KEY    Set this to enable AI-powered chat responses
        """
    )
    parser.add_argument('--oneshot', action='store_true', help='Print one message and exit')
    parser.add_argument('--motivate', action='store_true', help='Print a motivational quote and exit')
    parser.add_argument('--joke', action='store_true', help='Print a joke and exit')
    parser.add_argument('--api-key', type=str, default=None,
                        help='Anthropic API key (or set ANTHROPIC_API_KEY env var)')

    args = parser.parse_args()
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    if args.motivate:
        msg = None
        if api_key:
            client = AnthropicChat(api_key)
            msg = client.send_message("Give me one unique, punchy motivational quote for a programmer. Max 2 sentences.")
        if not msg:
            msg = random.choice(MOTIVATIONAL)
        left, right = Eyes.STAR_L, Eyes.STAR_R
        body = make_body(left, right, Mouths.GRIN)
        bubble = speech_bubble(msg)
        print()
        for line in bubble:
            print(f"  {line}")
        for line in body:
            print(f"  {line}")
        print()
        return

    if args.joke:
        msg = None
        if api_key:
            client = AnthropicChat(api_key)
            msg = client.send_message("Tell me one original, short programming joke. Be creative!")
        if not msg:
            msg = random.choice(JOKES)
        left, right = Eyes.WINK_L, Eyes.WINK_R
        body = make_body(left, right, Mouths.GRIN)
        bubble = speech_bubble(msg)
        print()
        for line in bubble:
            print(f"  {line}")
        for line in body:
            print(f"  {line}")
        print()
        return

    if args.oneshot:
        oneshot(api_key)
        return

    # Interactive mode
    buddy = TerminalBuddy(api_key=api_key)
    buddy.run()


if __name__ == "__main__":
    main()

"""ANSI escape code helpers and color palette."""

import re

ESC = "\033["
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
CLEAR_SCREEN = f"{ESC}2J"
ERASE_LINE = f"{ESC}2K"
ALT_SCREEN_ON = "\033[?1049h"
ALT_SCREEN_OFF = "\033[?1049l"
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
UNDERLINE = f"{ESC}4m"
BLINK_ON = f"{ESC}5m"
REVERSE = f"{ESC}7m"


def fg(r, g, b):
    return f"{ESC}38;2;{r};{g};{b}m"


def bg(r, g, b):
    return f"{ESC}48;2;{r};{g};{b}m"


def move(row, col):
    return f"{ESC}{row};{col}H"


class C:
    """Color palette — neon-retro terminal aesthetic."""
    # Body gradient (cyan → blue)
    BODY       = fg(80, 220, 255)
    BODY_MID   = fg(60, 180, 240)
    BODY_DARK  = fg(40, 140, 220)
    BODY_SHADE = fg(30, 100, 180)

    # Eyes
    EYE_WHITE  = fg(200, 230, 255)
    EYE_SCREEN = fg(40, 60, 90)
    PUPIL      = fg(255, 255, 255)
    PUPIL_GLOW = fg(120, 200, 255)

    # Mouth
    MOUTH      = fg(255, 120, 160)
    MOUTH_GLOW = fg(255, 80, 130)

    # Expressions
    HAPPY      = fg(255, 220, 50)
    BLUSH      = fg(255, 150, 170)
    HEART      = fg(255, 70, 110)
    STAR       = fg(255, 240, 80)
    ZZZ        = fg(160, 140, 255)
    COFFEE     = fg(200, 140, 70)

    # Antenna LED colors
    LED_IDLE   = fg(80, 255, 180)
    LED_TALK   = fg(80, 200, 255)
    LED_HAPPY  = fg(255, 220, 50)
    LED_LOVE   = fg(255, 80, 130)
    LED_THINK  = fg(255, 180, 60)
    LED_SLEEP  = fg(100, 80, 180)
    LED_PARTY  = fg(255, 100, 255)
    LED_ALERT  = fg(255, 80, 80)

    # UI elements
    SPEECH     = fg(180, 240, 200)
    SPEECH_DIM = fg(80, 140, 100)
    ACCENT     = fg(255, 180, 50)
    ACCENT2    = fg(120, 200, 255)
    SHADOW     = fg(50, 50, 70)
    SHADOW_MID = fg(40, 40, 55)
    SHADOW_DEEP = fg(30, 30, 40)

    # Status & effects
    FIRE       = fg(255, 100, 30)
    COOL       = fg(100, 220, 255)
    PARTY      = fg(255, 100, 255)
    THINKING   = fg(255, 200, 100)
    INPUT      = fg(180, 220, 255)
    INPUT_BG   = bg(35, 40, 60)

    # Standard
    GREEN      = fg(100, 255, 140)
    RED        = fg(255, 90, 90)
    YELLOW     = fg(255, 220, 80)
    CYAN       = fg(80, 220, 255)
    MAGENTA    = fg(220, 100, 255)
    ORANGE     = fg(255, 160, 50)
    GREY       = fg(120, 120, 140)
    WHITE      = fg(240, 240, 255)

    # Gradient helpers for body breathing
    BODY_BREATHE = [
        fg(60, 200, 245),
        fg(70, 210, 250),
        fg(80, 220, 255),
        fg(90, 225, 255),
        fg(80, 220, 255),
        fg(70, 210, 250),
    ]

    # Chest panel gradient
    PANEL      = fg(60, 180, 255)
    PANEL_DIM  = fg(40, 120, 200)
    PANEL_GLOW = fg(100, 220, 255)

    # Mood bar colors
    MOOD_GREAT = fg(80, 255, 160)
    MOOD_GOOD  = fg(160, 255, 80)
    MOOD_OK    = fg(255, 220, 60)
    MOOD_MEH   = fg(255, 160, 60)
    MOOD_SAD   = fg(255, 80, 80)

    # Weather
    SUN        = fg(255, 210, 40)
    SUN_RAY    = fg(255, 170, 30)
    RAIN_DROP  = fg(90, 150, 255)
    RAIN_HEAVY = fg(60, 110, 220)
    SNOW_FLAKE = fg(200, 225, 255)
    THUNDER_BG = fg(55, 55, 80)
    LIGHTNING  = fg(255, 255, 110)
    FOG_COLOR  = fg(145, 148, 162)
    WIND_COLOR = fg(170, 200, 225)
    CLOUD_DARK = fg(90, 95, 115)

    # Skin-specific (kept for compatibility)
    CAT        = fg(255, 180, 100)
    DOG        = fg(200, 160, 100)
    ALIEN      = fg(100, 255, 150)
    SKELETON   = fg(220, 220, 230)
    PUMPKIN    = fg(255, 140, 30)


# ─── Security: strip ANSI from untrusted external data ─────────────────────
_ANSI_RE = re.compile(
    r'(?:\x1b(?:'
    r'\[[0-?]*[ -/]*[@-~]'               # CSI sequences (must be before Fe)
    r'|\][^\x07\x1b]*(?:\x07|\x1b\\)'    # OSC sequences (must be before Fe)
    r'|[P_^][^\x1b]*\x1b\\'              # DCS, APC, PM sequences (payload + ST)
    r'|[@-Z\\-_]'                         # Fe escape sequences (single char fallback)
    r')'
    r'|[\x80-\x9f]'                       # 8-bit C1 control chars
    r')'
)


def strip_ansi(text):
    """Remove ANSI/VT escape sequences from untrusted external strings."""
    return _ANSI_RE.sub('', text) if text else text


def visible_len(text):
    """Return the visible (non-ANSI) character count of a string."""
    return len(_ANSI_RE.sub('', text)) if text else 0


def truncate_ansi(text, max_width):
    """Truncate an ANSI-colored string to max visible width, preserving codes."""
    if not text:
        return text
    width = 0
    i = 0
    last_safe = 0
    while i < len(text):
        m = _ANSI_RE.match(text, i)
        if m:
            i = m.end()
            last_safe = i
        else:
            width += 1
            i += 1
            last_safe = i
            if width >= max_width:
                break
    return text[:last_safe] + RESET

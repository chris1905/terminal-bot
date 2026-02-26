"""ANSI escape code helpers and color palette."""

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

    # Skin-specific (kept for compatibility)
    CAT        = fg(255, 180, 100)
    DOG        = fg(200, 160, 100)
    ALIEN      = fg(100, 255, 150)
    SKELETON   = fg(220, 220, 230)
    PUMPKIN    = fg(255, 140, 30)

"""ANSI escape code helpers and color palette."""

ESC = "\033["
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"
CLEAR_SCREEN = f"{ESC}2J"
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
    """Color palette."""
    BODY       = fg(100, 200, 255)
    BODY_DARK  = fg(60, 140, 200)
    EYE_WHITE  = fg(255, 255, 255)
    PUPIL      = fg(30, 30, 30)
    MOUTH      = fg(255, 100, 120)
    HAPPY      = fg(255, 220, 50)
    BLUSH      = fg(255, 150, 150)
    SPEECH     = fg(200, 255, 200)
    ACCENT     = fg(255, 180, 50)
    SHADOW     = fg(60, 60, 80)
    HEART      = fg(255, 80, 100)
    STAR       = fg(255, 255, 100)
    ZZZ        = fg(150, 150, 255)
    COFFEE     = fg(180, 120, 60)
    FIRE       = fg(255, 100, 30)
    COOL       = fg(100, 200, 255)
    PARTY      = fg(255, 100, 255)
    INPUT      = fg(180, 220, 255)
    INPUT_BG   = bg(40, 45, 65)
    THINKING   = fg(255, 200, 100)
    GREEN      = fg(100, 255, 100)
    RED        = fg(255, 80, 80)
    YELLOW     = fg(255, 220, 80)
    CYAN       = fg(80, 220, 255)
    MAGENTA    = fg(220, 100, 255)
    ORANGE     = fg(255, 160, 50)
    GREY       = fg(140, 140, 140)
    WHITE      = fg(255, 255, 255)
    # Skin-specific
    CAT        = fg(255, 180, 100)
    DOG        = fg(200, 160, 100)
    ALIEN      = fg(100, 255, 150)
    SKELETON   = fg(220, 220, 230)
    PUMPKIN    = fg(255, 140, 30)

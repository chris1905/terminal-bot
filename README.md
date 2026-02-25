# Terminal Buddy 🤖

A lively ASCII bot that lives in your terminal. It has animated eyes, tells programming jokes, drops motivational quotes, dances, drinks coffee, and keeps you company while you code.

Built for iTerm2 (and any terminal with ANSI/truecolor support).

```
  ╭──────────────────────────────────────────────╮
  │ You're mass-producing greatness right now.    │
  ╰──────────────────────────────────────────────╯
    ╲
     ╲
        ╭─────────────╮
        │             │
        │  (★)   (★)  │
        │             │
        │    ╰═══╯    │
        │             │
        ╰──┬─────┬──╯
           │     │
         ──┴─────┴──
         ╰───────────╯
```

## Quick Start

```bash
# Run directly (no dependencies needed - pure Python 3)
python3 terminal_buddy.py

# Or install system-wide
chmod +x setup.sh && ./setup.sh
```

## Usage

### Interactive Mode (full screen)
```bash
python3 terminal_buddy.py
```

**Controls:**
| Key | Action |
|-----|--------|
| `m` | Motivational quote |
| `j` | Programming joke |
| `d` | Dance! |
| `c` | Coffee break |
| `s` | Sleep mode |
| `p` | Party mode |
| `r` | Random reaction |
| `q` | Quit |

### One-shot Modes

```bash
# Quick motivational boost
python3 terminal_buddy.py --motivate

# Programming joke
python3 terminal_buddy.py --joke

# Random one-shot message
python3 terminal_buddy.py --oneshot
```

### Shell Aliases (after install)

```bash
buddy              # Launch interactive mode
buddy-motivate     # Quick motivation
buddy-joke         # Quick joke
```

## iTerm2 Integration

For the full iTerm2 experience with status bar and periodic motivational alerts:

```bash
chmod +x setup_iterm2.sh && ./setup_iterm2.sh
```

This adds:
- **Status bar component** - Shows buddy's face and a rotating motivational message
- **Periodic alerts** - A motivational popup every 30 minutes

To enable the status bar: iTerm2 → Profiles → Session → Configure Status Bar → drag "Terminal Buddy" in.

## Features

- **Animated eyes** - Blink, wander, look around, react to actions
- **Multiple expressions** - Happy, excited, sleepy, cool shades, hearts, stars, dizzy
- **Speech bubbles** - Dynamic word-wrapped message display
- **Dancing** - Full body animation with arm movements
- **Time-aware greetings** - Different greetings for morning, afternoon, and evening
- **Idle chatter** - Random helpful reminders (hydrate, stretch, push your code)
- **Particle effects** - Sparkles during celebrations
- **Zero dependencies** - Pure Python 3 standard library
- **Truecolor** - Beautiful 24-bit color palette (works in iTerm2, kitty, Alacritty, etc.)

## Requirements

- Python 3.6+
- A terminal with truecolor support (iTerm2, kitty, Alacritty, Windows Terminal, etc.)
- For iTerm2 integration: `pip3 install iterm2`

## Add Buddy to Your Shell Startup

Want a quick motivational hit every time you open a terminal?

```bash
# Add to your ~/.zshrc or ~/.bashrc:
python3 ~/.terminal-buddy/terminal_buddy.py --motivate
```

## File Structure

```
terminal-bot/
├── terminal_buddy.py      # Main bot (interactive + one-shot modes)
├── iterm2_trigger.py       # iTerm2 Python API integration
├── setup.sh                # System-wide installer
├── setup_iterm2.sh         # iTerm2-specific setup
└── README.md               # You are here
```

## License

MIT - Do whatever you want with your new terminal friend.

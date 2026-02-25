# Terminal Buddy 🤖

A lively ASCII bot that lives in your terminal. It has animated eyes, tells programming jokes, drops motivational quotes, dances, drinks coffee, and **you can chat with it** — powered by the Anthropic API for fresh, AI-generated responses every time.

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

# With AI chat enabled (fresh jokes, quotes, and conversations)
export ANTHROPIC_API_KEY="sk-ant-..."
python3 terminal_buddy.py

# Or pass the key directly
python3 terminal_buddy.py --api-key "sk-ant-..."

# Install system-wide
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
| `t` / `Enter` | Open chat input — talk to the bot! |
| `m` | Motivational quote (AI-generated if API key set) |
| `j` | Programming joke (AI-generated if API key set) |
| `d` | Dance! |
| `c` | Coffee break |
| `s` | Sleep mode |
| `p` | Party mode |
| `r` | Random reaction |
| `q` | Quit |

**While typing (chat mode):**
| Key | Action |
|-----|--------|
| `Enter` | Send your message |
| `Escape` | Cancel input |
| `Ctrl+U` | Clear the line |
| `Ctrl+W` | Delete last word |
| `Backspace` | Delete character |

### Chat / AI Mode

Press `t` or `Enter` to open the input bar at the bottom of the screen, type your message, and hit Enter. The bot will:

1. Show your message in a speech bubble
2. Go into "thinking" mode (eyes spin, mouth goes `···`)
3. Respond with an AI-generated reply from Claude

**Without an API key**, the bot uses a smart keyword-matching local brain that recognizes topics like:
- Greetings, mood (happy/sad/tired), coding help, coffee, boredom, existential questions
- Falls back to a pool of fun generic responses

**With an API key**, everything becomes dynamic:
- `[m]` generates a **fresh, unique** motivational quote each time
- `[j]` generates a **brand new** programming joke each time
- Idle chatter becomes AI-generated observations
- Full conversational chat with memory (last 20 messages)

### One-shot Modes

```bash
# Quick motivational boost (AI-generated if key set)
python3 terminal_buddy.py --motivate

# Programming joke (AI-generated if key set)
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

## API Setup

Terminal Buddy uses the **Anthropic Messages API** with `claude-haiku-4-5` for fast, cheap responses. No pip packages needed — it uses Python's built-in `urllib`.

```bash
# Option 1: Environment variable (recommended)
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Option 2: Command line flag
python3 terminal_buddy.py --api-key "sk-ant-api03-..."
```

The bot works perfectly fine without an API key — it just uses its built-in local responses instead.

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

- **Chat input** - Press `t` to type messages, bot responds with AI or local brain
- **Anthropic API integration** - Fresh AI-generated jokes, quotes, and conversations
- **Smart local fallback** - Keyword-matching responses when offline / no API key
- **Animated eyes** - Blink, wander, look around, react to actions, spin while thinking
- **Multiple expressions** - Happy, excited, sleepy, cool shades, hearts, stars, dizzy, thinking
- **Speech bubbles** - Dynamic word-wrapped message display
- **Dancing** - Full body animation with arm movements
- **Time-aware greetings** - Different greetings for morning, afternoon, and evening
- **Idle chatter** - Random helpful reminders (AI-generated or from built-in pool)
- **Particle effects** - Sparkles during celebrations
- **Conversation memory** - AI remembers last 20 messages in a session
- **Zero required dependencies** - Pure Python 3 standard library
- **Truecolor** - Beautiful 24-bit color palette (works in iTerm2, kitty, Alacritty, etc.)

## Requirements

- Python 3.6+
- A terminal with truecolor support (iTerm2, kitty, Alacritty, Windows Terminal, etc.)
- **Optional:** `ANTHROPIC_API_KEY` for AI-powered responses
- For iTerm2 integration: `pip3 install iterm2`

## Add Buddy to Your Shell Startup

Want a quick motivational hit every time you open a terminal?

```bash
# Add to your ~/.zshrc or ~/.bashrc:
export ANTHROPIC_API_KEY="sk-ant-..."
python3 ~/.terminal-buddy/terminal_buddy.py --motivate
```

## File Structure

```
terminal-bot/
├── terminal_buddy.py      # Main bot (interactive + chat + AI + one-shot modes)
├── iterm2_trigger.py       # iTerm2 Python API integration
├── setup.sh                # System-wide installer
├── setup_iterm2.sh         # iTerm2-specific setup
└── README.md               # You are here
```

## License

MIT - Do whatever you want with your new terminal friend.

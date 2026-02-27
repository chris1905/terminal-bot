# Terminal Buddy v2.0

A lively ASCII bot that lives in your terminal. Animated eyes, AI-powered chat, code roasting, typing races, trivia, weather moods, Apple Music sync, achievement system, pomodoro timer, and much more. Pure Python 3 — zero external dependencies.

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

# One-shot modes
python3 terminal_buddy.py --motivate    # Quick motivation
python3 terminal_buddy.py --joke        # Quick joke
python3 terminal_buddy.py --oneshot     # Random message

# Desktop pet mode (minimal 3-line overlay)
python3 terminal_buddy.py --pet

# Install system-wide
chmod +x setup.sh && ./setup.sh
```

## Controls

### Normal Mode

| Key | Action |
|-----|--------|
| `t` / `Enter` | Open chat — talk to the bot |
| `m` | Motivational quote (AI or local) |
| `j` | Programming joke (AI or local) |
| `d` | Dance |
| `c` | Coffee break |
| `s` | Sleep mode |
| `p` | Party / celebrate |
| `r` | Random reaction |
| `g` | Roast my code (reads git diff) |
| `k` | Commit message poet (reads staged changes) |
| `b` | Run build (auto-detects npm/make/cargo/go/python) |
| `u` | Show uptime & git streak |
| `w` | Typing race |
| `?` | Trivia question |
| `o` | Pomodoro timer (start/toggle) |
| `a` | Show achievements |
| `f` | TODO/FIXME finder |
| `i` | Open PR reminders (via `gh` CLI) |
| `x` | Weather mood check |
| `6` | Toggle sixel/iTerm2 image mode |
| `/` | Show help overlay |
| `q` | Quit |
| `1` / `2` | Answer Buddy's curiosity prompt (appears automatically when he finds something interesting) |

### Chat Mode (after pressing `t` or `Enter`)

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Escape` | Cancel input |
| `Ctrl+U` | Clear the line |
| `Ctrl+W` | Delete last word |
| `Backspace` | Delete character |

### Typing Race Mode (after pressing `w`)

Type the displayed code snippet as fast as you can. Your WPM and accuracy are tracked.

| Key | Action |
|-----|--------|
| Type normally | Match the snippet |
| `Escape` | Quit race |

### Trivia Mode (after pressing `?`)

| Key | Action |
|-----|--------|
| `a` `b` `c` `d` | Answer the question |
| `Escape` | Skip question |

## Features

### AI-Powered Content (Claude Haiku 4.5 via Anthropic API)
- **Buddy chat** — Conversational AI that remembers your session. Press `t` to type. Shows "You: ..." while Buddy thinks.
- **Proactive messages** — Every ~2 minutes Buddy spontaneously asks questions, shares opinions, checks in on you, or goes into curiosity mode.
- **Web curiosity** — Buddy autonomously picks an interesting tech topic, looks it up (DuckDuckGo / Wikipedia), and surfaces it: `[1] Tell me!  [2] Skip`. Press `1` and he'll excitedly explain what he found. Fully automatic — fires as part of the idle proactive cycle.
- **Personalized commit reactions** — When you commit, Buddy reads the actual commit message and reacts to *what you did specifically*, not a generic canned line.
- **Fresh quotes & jokes** — AI-generated, never-repeating within a session.
- **Code roasting** — Reads your `git diff` and lovingly roasts your code. Falls back to a pool of generic roasts without API.
- **Commit message poet** — Reads staged changes and generates dramatic, over-the-top commit messages.
- **Smart local fallback** — Keyword-matching brain when offline: recognizes greetings, coding topics, mood, existential questions, and more.

### Terminal Awareness
- **Shell history reactions** — Watches `~/.zsh_history` or `~/.bash_history` and reacts to commands like `rm -rf`, `git push --force`, `sudo`, `npm install`, etc.
- **Git commit detection** — Watches `.git/COMMIT_EDITMSG` for new commits and celebrates with a personalized AI reaction referencing your actual commit message. Works with git worktrees too.
- **Build runner** — Auto-detects your build system (npm, make, cargo, go, python) and runs builds in the background. Shows success/failure.
- **Uptime & git streak** — Track how long you've been coding and your daily commit streak.
- **Clipboard watcher** — Detects code pastes from clipboard and makes cheeky comments.
- **Apple Music sync** — Detects what's playing via AppleScript (macOS). Bot sings along: happy/star eyes, `♪`/`♫` mouth animation, dancing arms, musical notes on the chest panel, rhythmic body bob, `♪` in the title bar and status line. With API enabled, Buddy reacts to the specific song/artist by name.

### Games & Timer
- **Typing race** — Code snippet typing challenge with WPM and accuracy scoring.
- **Programming trivia** — 15 questions about languages, tools, and CS history. Tracks which you've answered.
- **Pomodoro timer** — 25-min work / 5-min break cycles with pause support.

### Achievement System
24 unlockable achievements with JSON persistence (`~/.terminal-buddy/achievements.json`):
- `first_chat` — Send your first message
- `ten_jokes` — Hear 10 jokes
- `speed_demon` — Get 60+ WPM in typing race
- `trivia_master` — Answer 10 trivia questions correctly
- `night_owl` — Use buddy after midnight
- `marathon` — Run buddy for over an hour
- ...and 18 more

### Productivity
- **TODO finder** — Scans your project for TODO, FIXME, HACK, and XXX comments across 18 file types.
- **PR reminders** — Shows open pull requests via `gh` CLI.

### Weather Mood
- Fetches weather from `wttr.in` (free, no API key needed).
- Maps conditions to bot moods: sunny = happy, rainy = cozy, thunderstorm = intense, foggy = mysterious.
- Affects the bot's eye expression, and pulls out the umbrella on rainy/snowy days.

### Visual
- **Animated eyes** — Blink, wander, react to actions, spin while thinking.
- **Multiple expressions** — Happy, sleepy, cool shades, hearts, stars, dizzy, thinking.
- **Sixel/iTerm2 image protocol** — Toggle pixel-art rendering with `6`.
- **Truecolor** — 24-bit color palette throughout.
- **Particle effects** — Sparkles during celebrations.

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

```bash
chmod +x setup_iterm2.sh && ./setup_iterm2.sh
```

This adds a status bar component and periodic motivational alerts. Enable via: iTerm2 → Profiles → Session → Configure Status Bar → drag "Terminal Buddy" in.

## Shell Aliases (after install)

```bash
buddy              # Launch interactive mode
buddy-motivate     # Quick motivation
buddy-joke         # Quick joke
```

## Add Buddy to Your Shell Startup

```bash
# Add to your ~/.zshrc or ~/.bashrc:
export ANTHROPIC_API_KEY="sk-ant-..."
python3 ~/.terminal-buddy/terminal_buddy.py --motivate
```

## File Structure

```
terminal-bot/
├── terminal_buddy.py      # Main bot — state machine, rendering, input handling
├── buddy/
│   ├── __init__.py        # Package init (v2.0.0)
│   ├── ansi.py            # ANSI escape codes, colors, cursor control
│   ├── data.py            # All static data: quotes, jokes, trivia, achievements, reactions
│   ├── ai_features.py     # Code roast, commit poet, non-repeating pools
│   ├── awareness.py       # Shell history watcher, build runner, uptime, git streak, clipboard, commit watcher, web researcher, music watcher
│   ├── games.py           # Typing race, trivia, pomodoro timer
│   ├── achievements.py    # Achievement tracker with JSON persistence
│   ├── productivity.py    # TODO scanner, PR checker
│   ├── weather.py         # Weather mood via wttr.in
│   └── sixel.py           # Sixel/iTerm2 inline image protocol
├── iterm2_trigger.py      # iTerm2 Python API integration
├── setup.sh               # System-wide installer
├── setup_iterm2.sh        # iTerm2-specific setup
└── README.md
```

## Requirements

- Python 3.6+
- A terminal with truecolor support (iTerm2, kitty, Alacritty, Windows Terminal, etc.)
- **Optional:** `ANTHROPIC_API_KEY` for AI-powered responses
- **Optional:** `gh` CLI for PR checking
- **Optional:** `xclip` or `xsel` (Linux) for clipboard watching
- **Optional:** Apple Music (macOS) for music sync — no setup needed, uses built-in AppleScript

## License

MIT — Do whatever you want with your new terminal friend.

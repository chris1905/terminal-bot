#!/usr/bin/env python3
"""
iTerm2 Integration for Terminal Buddy

This script uses iTerm2's Python API to add Terminal Buddy features
directly into your iTerm2 experience:
  - Status bar component showing buddy's current mood
  - Trigger to launch buddy via a keyboard shortcut
  - Random motivational popups via iTerm2 alerts

Setup:
  1. In iTerm2: Scripts > Manage > Install Python Runtime
  2. Copy this file to: ~/Library/Application Support/iTerm2/Scripts/AutoLaunch/
  3. Restart iTerm2

Alternatively, use the setup_iterm2.sh script.
"""

import sys
import os

try:
    import iterm2
    HAS_ITERM2 = True
except ImportError:
    HAS_ITERM2 = False

import random
import asyncio

MOTIVATIONAL = [
    "You're mass-producing greatness!",
    "Bugs fear you. Linters respect you.",
    "Ship it. Ship it good.",
    "Your code is poetry.",
    "Trust the process.",
    "You're in the zone!",
    "Keep going, code wizard!",
    "Plot twist: YOU are the 10x dev.",
    "This commit? Chef's kiss.",
    "Your future self thanks you.",
]

FACES = [
    "(o_o) ",
    "(^_^) ",
    "(★_★) ",
    "(♥_♥) ",
    "(◕‿◕) ",
    "(⌐■_■)",
]


async def main(connection):
    """Main iTerm2 integration."""

    # ── Status Bar Component ──────────────────────────────────
    component = iterm2.StatusBarComponent(
        short_description="Terminal Buddy",
        detailed_description="Your friendly terminal companion",
        knobs=[],
        exemplar=f"🤖 (^_^) Vibing!",
        update_cadence=30,
        identifier="com.terminal-buddy.statusbar"
    )

    @iterm2.StatusBarRPC
    async def buddy_status_bar(knobs):
        face = random.choice(FACES)
        msg = random.choice(MOTIVATIONAL)
        return f"🤖 {face} {msg}"

    await component.async_register(connection, buddy_status_bar)

    # ── Periodic Motivational Alerts ──────────────────────────
    app = await iterm2.async_get_app(connection)

    async def periodic_motivation():
        """Send a motivational alert every ~30 minutes."""
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            face = random.choice(FACES)
            msg = random.choice(MOTIVATIONAL)
            alert = iterm2.Alert(
                "Terminal Buddy Says:",
                f"{face}\n\n{msg}",
            )
            alert.add_button("Thanks, buddy!")
            try:
                window = app.current_terminal_window
                if window:
                    tab = window.current_tab
                    if tab:
                        session = tab.current_session
                        if session:
                            await alert.async_run(connection)
            except Exception:
                pass

    asyncio.ensure_future(periodic_motivation())

    # Keep running
    await connection.async_dispatch_until_future(asyncio.Future())


if __name__ == "__main__":
    if HAS_ITERM2:
        iterm2.run_forever(main)
    else:
        print("This script requires the iterm2 Python package.")
        print("Install it with: pip3 install iterm2")
        print("")
        print("Then set up iTerm2's Python API:")
        print("  1. In iTerm2: Scripts > Manage > Install Python Runtime")
        print("  2. Copy this script to ~/Library/Application Support/iTerm2/Scripts/AutoLaunch/")
        sys.exit(1)

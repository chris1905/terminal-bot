#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Terminal Buddy - iTerm2 Integration Setup
#  Installs the iTerm2 status bar component & auto-launch script
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ITERM2_SCRIPTS_DIR="$HOME/Library/Application Support/iTerm2/Scripts/AutoLaunch"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║  🤖 Terminal Buddy - iTerm2 Setup 🤖 ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# Check if iTerm2 scripts directory exists
if [ ! -d "$HOME/Library/Application Support/iTerm2" ]; then
    echo "  ✗ iTerm2 does not appear to be installed."
    echo "    Download it from: https://iterm2.com"
    exit 1
fi

# Check for iterm2 Python package
if python3 -c "import iterm2" 2>/dev/null; then
    echo "  ✓ iterm2 Python package found"
else
    echo "  Installing iterm2 Python package..."
    pip3 install iterm2
    echo "  ✓ Installed iterm2 Python package"
fi

# Create AutoLaunch directory
mkdir -p "$ITERM2_SCRIPTS_DIR"
echo "  ✓ AutoLaunch directory ready"

# Copy integration script
cp "$SCRIPT_DIR/iterm2_trigger.py" "$ITERM2_SCRIPTS_DIR/terminal_buddy.py"
chmod +x "$ITERM2_SCRIPTS_DIR/terminal_buddy.py"
echo "  ✓ Installed iTerm2 integration script"

echo ""
echo "  ═══════════════════════════════════════"
echo "  iTerm2 Setup Complete!"
echo ""
echo "  Features enabled:"
echo "    • Status bar component (add via Profiles > Session > Status Bar)"
echo "    • Periodic motivational alerts (every 30 min)"
echo ""
echo "  Please restart iTerm2 to activate."
echo "  ═══════════════════════════════════════"
echo ""

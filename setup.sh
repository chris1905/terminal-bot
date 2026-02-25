#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  Terminal Buddy - Installer
#  Sets up your friendly terminal companion
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.terminal-buddy"
BUDDY_SCRIPT="terminal_buddy.py"

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║   🤖 Terminal Buddy Installer 🤖     ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# Check Python version
if command -v python3 &>/dev/null; then
    PY=$(command -v python3)
    echo "  ✓ Found Python: $($PY --version)"
else
    echo "  ✗ Python 3 is required but not found."
    echo "    Install it with: brew install python3"
    exit 1
fi

# Create install directory
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/$BUDDY_SCRIPT" "$INSTALL_DIR/$BUDDY_SCRIPT"
chmod +x "$INSTALL_DIR/$BUDDY_SCRIPT"

echo "  ✓ Installed to $INSTALL_DIR"

# Create launcher symlink
LINK_PATH="/usr/local/bin/terminal-buddy"
if [ -w "/usr/local/bin" ]; then
    ln -sf "$INSTALL_DIR/$BUDDY_SCRIPT" "$LINK_PATH"
    echo "  ✓ Symlinked to $LINK_PATH"
else
    # Try with user local bin
    mkdir -p "$HOME/.local/bin"
    ln -sf "$INSTALL_DIR/$BUDDY_SCRIPT" "$HOME/.local/bin/terminal-buddy"
    echo "  ✓ Symlinked to $HOME/.local/bin/terminal-buddy"
    echo "    Make sure $HOME/.local/bin is in your PATH"
fi

# Create shell alias
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "terminal-buddy" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Terminal Buddy - your friendly terminal companion" >> "$SHELL_RC"
        echo "alias buddy='python3 $INSTALL_DIR/$BUDDY_SCRIPT'" >> "$SHELL_RC"
        echo "alias buddy-motivate='python3 $INSTALL_DIR/$BUDDY_SCRIPT --motivate'" >> "$SHELL_RC"
        echo "alias buddy-joke='python3 $INSTALL_DIR/$BUDDY_SCRIPT --joke'" >> "$SHELL_RC"
        echo "  ✓ Added aliases to $SHELL_RC"
    else
        echo "  ✓ Aliases already exist in $SHELL_RC"
    fi
fi

echo ""
echo "  ═══════════════════════════════════════"
echo "  Installation complete!"
echo ""
echo "  Usage:"
echo "    buddy              Launch interactive mode"
echo "    buddy-motivate     Quick motivational quote"
echo "    buddy-joke         Quick programming joke"
echo ""
echo "  Or run directly:"
echo "    python3 $INSTALL_DIR/$BUDDY_SCRIPT"
echo ""
echo "  Restart your shell or run: source $SHELL_RC"
echo "  ═══════════════════════════════════════"
echo ""

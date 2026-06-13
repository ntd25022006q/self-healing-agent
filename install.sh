#!/usr/bin/env bash

# Self-Healing Agent installer script for macOS / Linux
# Mimics Aider's installer to set up isolated virtual environments and create shell shortcuts

set -e

echo "=== Self-Healing Agent Installer ==="

# 1. Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[Error] Python 3 is not installed. Please install Python 3.9+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[Info] Found Python version: $PYTHON_VERSION"

# 2. Setup isolated env
INSTALL_DIR="$HOME/.self-healing-agent"
echo "[Info] Setting up isolated environment in $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# Download repository files using git if available, or fetch zip
if command -v git &> /dev/null; then
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "[Info] Updating existing repository..."
        git -C "$INSTALL_DIR" pull
    else
        echo "[Info] Cloning repository..."
        git clone https://github.com/ntd25022006q/self-healing-agent.git "$INSTALL_DIR"
    fi
else
    echo "[Warning] Git is not installed. Downloading repository zip archive..."
    curl -L https://github.com/ntd25022006q/self-healing-agent/archive/refs/heads/main.zip -o "$INSTALL_DIR/archive.zip"
    unzip -q -o "$INSTALL_DIR/archive.zip" -d "$INSTALL_DIR"
    mv "$INSTALL_DIR/self-healing-agent-main/"* "$INSTALL_DIR/"
    rm -rf "$INSTALL_DIR/self-healing-agent-main" "$INSTALL_DIR/archive.zip"
fi

# 3. Create virtual environment
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
"$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR"

# 4. Create global command shortcut in ~/.local/bin
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

# Create symlink or launch wrapper script
cat <<EOF > "$BIN_DIR/heal"
#!/usr/bin/env bash
exec "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/main.py" "\$@"
EOF

chmod +x "$BIN_DIR/heal"

# Also link shc
ln -sf "$BIN_DIR/heal" "$BIN_DIR/shc"

echo "=================================================="
echo "SUCCESS! Self-Healing Agent installed successfully."
echo "Commands created in: $BIN_DIR"
echo ""
echo "Please ensure $BIN_DIR is in your system PATH."
echo "Test the installation by running:"
echo "  heal --help"
echo "=================================================="

#!/usr/bin/env bash
# Amber - One-Line Local Installation Script

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "Installing Amber from ${REPO_DIR}..."

# 1. Check Python version
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required."
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo "Error: Python 3.11+ is required (found ${PY_VER})."
    exit 1
fi

# 2. Setup Virtual Environment
cd "${REPO_DIR}"
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    if command -v uv &>/dev/null; then
        uv venv .venv
    else
        python3 -m venv .venv
    fi
fi

# 3. Install Package & Dependencies
echo "Installing dependencies..."
if command -v uv &>/dev/null; then
    uv pip install -e .
else
    .venv/bin/pip install -e .
fi

# 4. Link Executables to ~/.local/bin
mkdir -p "${BIN_DIR}"
ln -sf "${REPO_DIR}/.venv/bin/amber" "${BIN_DIR}/amber"
ln -sf "${REPO_DIR}/.venv/bin/amber-server" "${BIN_DIR}/amber-server"
ln -sf "${REPO_DIR}/cli/amber-popup" "${BIN_DIR}/amber-popup"

# 5. Setup Systemd Service
if command -v systemctl &>/dev/null; then
    echo "Configuring background systemd service..."
    mkdir -p "${SYSTEMD_USER_DIR}"
    
    # Generate service file with exact paths
    cat << EOF > "${SYSTEMD_USER_DIR}/amber.service"
[Unit]
Description=Amber - Personal Memory, Command & Knowledge Retrieval Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=${REPO_DIR}
ExecStart=${REPO_DIR}/.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 7474
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=AMBER_PORT=7474

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable --now amber
    echo "Amber background daemon enabled and started via systemd."
fi

echo ""
echo "Amber installed successfully!"
echo "• CLI binary: ${BIN_DIR}/amber"
echo "• Desktop popup: ${BIN_DIR}/amber-popup"
echo "• Web UI: http://127.0.0.1:7474"
echo ""
echo "Try running: amber 'venv'"

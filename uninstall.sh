#!/usr/bin/env bash
# Amber - Uninstaller Script

set -e

BIN_DIR="${HOME}/.local/bin"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "Uninstalling Amber..."

# Stop and disable systemd service
if command -v systemctl &>/dev/null; then
    systemctl --user stop amber 2>/dev/null || true
    systemctl --user disable amber 2>/dev/null || true
    rm -f "${SYSTEMD_USER_DIR}/amber.service"
    systemctl --user daemon-reload 2>/dev/null || true
    echo "Removed systemd service."
fi

# Remove binary symlinks
rm -f "${BIN_DIR}/amber"
rm -f "${BIN_DIR}/amber-server"
rm -f "${BIN_DIR}/amber-popup"
echo "Removed binary links from ${BIN_DIR}."

echo ""
echo "Amber uninstalled successfully."
echo "Note: Your saved memory database (~/.local/share/amber/db.sqlite) was preserved."

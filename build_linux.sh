#!/usr/bin/env bash
# =========================================================================
#  build_linux.sh — Build TraceMax executable for Linux
#
#  Usage:
#      ./build_linux.sh           (build using tracemax.spec)
#      ./build_linux.sh clean     (remove previous build artifacts first)
# =========================================================================

set -e

echo ""
echo "===================================="
echo "  TraceMax — Linux Build Script"
echo "===================================="
echo ""

# --- Optional clean step ---
if [ "${1}" = "clean" ]; then
    echo "[1/4] Cleaning previous builds..."
    rm -rf dist/ build/
    echo "       Done."
else
    echo "[1/4] Skipping clean (pass 'clean' to remove previous artifacts)"
fi

# --- Generate icon ---
echo "[2/4] Generating icon files..."
python3 generate_icon.py

# --- Build ---
echo "[3/4] Running PyInstaller..."
pyinstaller --noconfirm tracemax.spec

# --- Summary ---
echo "[4/4] Build complete!"
echo ""
echo "  Output directory: dist/TraceMax/"
echo "  Executable:       dist/TraceMax/TraceMax"
echo ""
echo "To run:"
echo "  ./dist/TraceMax/TraceMax"
echo ""

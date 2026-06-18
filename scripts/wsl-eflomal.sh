#!/usr/bin/env bash
# Provision the Linux toolchain + run eflomal word alignment for the eBible pairs.
# Idempotent. Runnable as root (no sudo) or as a sudo-capable user. Invoked by
# scripts/wsl-eflomal-setup-run.ps1, or directly:  wsl -d Ubuntu -u root -e bash <this>
set -euo pipefail

SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"

# Repo path on the Windows drive (override with $REPO).
REPO="${REPO:-/mnt/c/Users/johnm/Documents/repos/linguistic-assistant}"
RESEARCH="$REPO/research"

echo "== [1/4] apt build deps =="
export DEBIAN_FRONTEND=noninteractive  # NB: an env-assignment can't follow an (empty) $SUDO — bash would treat it as the command
$SUDO apt-get update -y
$SUDO apt-get install -y build-essential python3-dev python3-venv curl git

echo "== [2/4] uv =="
if ! command -v uv >/dev/null 2>&1; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi
export PATH="$HOME/.local/bin:$PATH"
uv --version

echo "== [3/4] uv sync --extra align (builds sil-thot + eflomal) =="
cd "$RESEARCH"
uv sync --extra align

PAIRS="${*:-tur hun}"  # pairs may be passed as args; default tur hun
echo "== [4/4] eflomal alignment build ($PAIRS) =="
PYTHONUTF8=1 uv run python datasets/ebible/build.py --pair $PAIRS --backend eflomal
echo "== done: outputs under research/golden/_sources/ebible/ =="

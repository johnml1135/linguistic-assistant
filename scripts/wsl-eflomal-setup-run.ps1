<#
.SYNOPSIS
  Provision WSL (Ubuntu) and run eflomal word alignment for the eBible golden pairs.

.DESCRIPTION
  eflomal is Linux-only (CPU, no GPU). This script sets up a Linux toolchain under WSL, installs the
  `align` extra (sil-machine[thot] + eflomal) with uv, and runs the alignment build for the chosen
  pairs at eflomal quality — replacing the deterministic co-occurrence fallback used on Windows.

  Steps:
    1. Ensure WSL + a distro are installed (needs Admin + a reboot the FIRST time only).
    2. Inside WSL: apt build deps (gcc/make/python3-dev), install uv.
    3. `uv sync --extra align` in research/ (builds eflomal), then run build.py --backend eflomal.

.PARAMETER Distro
  WSL distro name. Default: Ubuntu.

.PARAMETER Pairs
  Target keys to build. Default: tur hun.

.EXAMPLE
  # first time (installs WSL — run from an elevated PowerShell, then reboot and re-run):
  powershell -ExecutionPolicy Bypass -File scripts/wsl-eflomal-setup-run.ps1

.NOTES
  If WSL is not yet installed this script prints the one-time elevated command and exits — it does
  not silently trigger a reboot.
#>
[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu",
    [string[]]$Pairs = @("tur", "hun")
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Test-WslInstalled {
    try { wsl.exe -l -q 2>$null | Out-Null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

# 1. WSL presence ---------------------------------------------------------------
if (-not (Test-WslInstalled)) {
    Write-Warning "WSL is not installed on this machine."
    Write-Host    "Run this ONCE from an elevated (Administrator) PowerShell, then reboot:" -ForegroundColor Yellow
    Write-Host    "    wsl --install -d $Distro" -ForegroundColor Cyan
    Write-Host    "After the reboot and first-run user setup, re-run this script (no elevation needed)."
    exit 1
}

# Translate the Windows repo path to a WSL /mnt path.
$wslRepo = "/mnt/" + ($repoRoot.Substring(0,1).ToLower()) + ($repoRoot.Substring(2) -replace '\\','/')
$research = "$wslRepo/research"
Write-Host "WSL repo path: $research" -ForegroundColor Green

# 2 + 3. Provision the distro and run -------------------------------------------
# Delegate to the single-source provisioner scripts/wsl-eflomal.sh (idempotent: toolchain -> uv ->
# uv sync --extra align -> build). Run as root (no sudo prompt). `tr -d '\r'` tolerates a CRLF checkout.
# REPO + pair args are passed through; the .sh is the one place this logic lives.
$shPath   = "$wslRepo/scripts/wsl-eflomal.sh"
$pairArgs = ($Pairs -join " ")
Write-Host "Launching WSL eflomal build via $shPath (root; several minutes — apt + uv build + align)..." -ForegroundColor Green
wsl.exe -d $Distro -u root bash -lc "tr -d '\r' < '$shPath' | REPO='$wslRepo' bash -s -- $pairArgs"
if ($LASTEXITCODE -ne 0) { Write-Error "WSL run failed (exit $LASTEXITCODE)."; exit $LASTEXITCODE }
Write-Host "eflomal alignment complete. Outputs updated under research/golden/_sources/ebible/." -ForegroundColor Green

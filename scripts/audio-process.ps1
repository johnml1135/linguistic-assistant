<#
.SYNOPSIS
  Normalize downloaded NT audio to 16 kHz mono WAV and stage it for the audio add-on.

.DESCRIPTION
  Converts cached audio under research/.cache/audio/<target-id>/ to 16 kHz mono WAV via ffmpeg when
  present (the format the add-on's preview/recognition path expects), then prints the next command.
  Skips gracefully when no approved source has been downloaded yet or when ffmpeg is unavailable.

.PARAMETER Python
  Python executable (reserved for future catalog generation). Default: python.

.EXAMPLE
  pwsh -File scripts/audio-process.ps1
#>
[CmdletBinding()]
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$research = Join-Path $repoRoot "research"
$cacheRoot = Join-Path $research ".cache/audio"

if (-not (Test-Path $cacheRoot)) {
    Write-Host "No cached audio yet. Run scripts/audio-download.ps1 -Execute first." -ForegroundColor Yellow
    return
}

$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Warning "ffmpeg not found on PATH; cannot transcode to WAV. Install ffmpeg, then re-run."
}

$dirs = Get-ChildItem $cacheRoot -Directory -ErrorAction SilentlyContinue
if (-not $dirs) {
    Write-Host "Cache is empty. Nothing to process." -ForegroundColor Yellow
    return
}

foreach ($d in $dirs) {
    $targetDir = $d.FullName
    $wavDir = Join-Path $targetDir "wav"
    New-Item -ItemType Directory -Force -Path $wavDir | Out-Null
    if ($ffmpeg) {
        Get-ChildItem $targetDir -File |
            Where-Object { $_.Extension -in '.mp3', '.m4a', '.ogg', '.flac', '.wav', '.audio' } |
            ForEach-Object {
                $wav = Join-Path $wavDir ($_.BaseName + ".wav")
                & ffmpeg -y -loglevel error -i $_.FullName -ac 1 -ar 16000 $wav
                if ($LASTEXITCODE -eq 0) { Write-Host ("wav: {0}" -f $wav) -ForegroundColor Green }
            }
    }
    Write-Host ("processed: {0}" -f $d.Name) -ForegroundColor Cyan
}

Write-Host "`nNext: build a catalog.json pointing at the wav files, then run:" -ForegroundColor Yellow
Write-Host "  python -m audio.candidates locate --pair-dir <pair> --target <key> --samples <samples.json> --catalog <catalog.json> --phone-cues"

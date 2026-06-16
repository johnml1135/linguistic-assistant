<#
.SYNOPSIS
  Clone and build ik_llama.cpp (CUDA) on Windows, producing llama-server.exe.

.DESCRIPTION
  Shared dev-box tooling for serving local GGUF models (e.g. Gemma 4 / Qwen 3.6) behind
  an OpenAI-compatible endpoint. Callable from the Python research harness or from C#.

  ik_llama.cpp is a llama.cpp fork with SOTA quantization types (IQ*_K / trellis IQ*_KT)
  — directly useful for the quantization sweep. It ships llama-server with an
  OpenAI-compatible /v1/chat/completions endpoint, so the existing harness adapter talks
  to it with no code changes.

  Requires on PATH: git, cmake, a C++ toolchain (Visual Studio Build Tools / MSVC), and —
  for a CUDA build — the NVIDIA CUDA Toolkit (nvcc). Targets NVIDIA Turing or newer
  (RTX 3090 = Ampere, supported).

.PARAMETER RepoDir
  Where to clone/build. Default: serving/.cache/ik_llama.cpp (gitignored).

.PARAMETER Ref
  Git branch/tag to build. Default: main.

.PARAMETER NoCuda
  Build a CPU-only binary (skips the nvcc requirement).

.PARAMETER Target
  CMake target to build. Default: llama-server. Pass an empty string to build everything
  if the target name ever changes upstream.

.PARAMETER Jobs
  Parallel build jobs. 0 = let CMake decide.

.EXAMPLE
  ./serving/install-ik-llama.ps1

.EXAMPLE
  ./serving/install-ik-llama.ps1 -RepoDir D:\src\ik_llama.cpp -Jobs 12
#>
[CmdletBinding()]
param(
    [string]$RepoDir = (Join-Path $PSScriptRoot '.cache/ik_llama.cpp'),
    [string]$Ref = 'main',
    [switch]$NoCuda,
    [string]$Target = 'llama-server',
    [int]$Jobs = 0
)

$ErrorActionPreference = 'Stop'

function Assert-Tool([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required tool '$Name' not found on PATH. $Hint"
    }
}

Assert-Tool git   'Install Git for Windows.'
Assert-Tool cmake 'Install CMake and add it to PATH.'
if (-not $NoCuda) {
    Assert-Tool nvcc 'Install the NVIDIA CUDA Toolkit (nvcc must be on PATH), or pass -NoCuda.'
}

# --- Clone or update ----------------------------------------------------------
if (Test-Path (Join-Path $RepoDir '.git')) {
    Write-Host "Updating existing checkout: $RepoDir"
    git -C $RepoDir fetch --depth 1 origin $Ref;  if ($LASTEXITCODE -ne 0) { throw 'git fetch failed' }
    git -C $RepoDir checkout $Ref;                 if ($LASTEXITCODE -ne 0) { throw 'git checkout failed' }
    git -C $RepoDir reset --hard "origin/$Ref";    if ($LASTEXITCODE -ne 0) { throw 'git reset failed' }
}
else {
    $parent = Split-Path $RepoDir -Parent
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Write-Host "Cloning ik_llama.cpp ($Ref) into: $RepoDir"
    git clone --depth 1 --branch $Ref https://github.com/ikawrakow/ik_llama.cpp.git $RepoDir
    if ($LASTEXITCODE -ne 0) { throw 'git clone failed' }
}

$buildDir = Join-Path $RepoDir 'build'

# --- Configure ----------------------------------------------------------------
$cuda = if ($NoCuda) { 'OFF' } else { 'ON' }
Write-Host "Configuring (GGML_CUDA=$cuda) ..."
cmake -B $buildDir -S $RepoDir -DGGML_NATIVE=ON -DGGML_CUDA=$cuda -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) { throw 'cmake configure failed' }

# --- Build --------------------------------------------------------------------
$buildArgs = @('--build', $buildDir, '--config', 'Release')
if ($Target) { $buildArgs += @('--target', $Target) }
if ($Jobs -gt 0) { $buildArgs += @('-j', "$Jobs") }
Write-Host "Building ..."
cmake @buildArgs
if ($LASTEXITCODE -ne 0) { throw "cmake build failed (if the target name changed upstream, re-run with -Target '')" }

# --- Locate the server binary -------------------------------------------------
$server = Get-ChildItem -Path $buildDir -Recurse -Filter 'llama-server.exe' -ErrorAction SilentlyContinue |
          Select-Object -First 1
if (-not $server) { throw "Build finished but llama-server.exe was not found under $buildDir" }

$marker = Join-Path $PSScriptRoot '.ik_llama_server_path.txt'
Set-Content -Path $marker -Value $server.FullName -Encoding utf8
Write-Host ""
Write-Host "Built:    $($server.FullName)"
Write-Host "Recorded: $marker  (run-ik-llama-server.ps1 reads this)"

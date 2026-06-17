<#
.SYNOPSIS
  Clone and build mainline llama.cpp (CUDA) on Windows, producing llama-server.exe.

.DESCRIPTION
  Mainline (ggml-org/llama.cpp) is built ALONGSIDE ik_llama.cpp. Use mainline for fast
  iteration: it supports Multi-Token Prediction (MTP) speculative decoding (~1.4-2.2x on
  Gemma 4 / Qwen 3.6) and is first to support new model architectures. Keep ik_llama for
  its SOTA IQ_K quants when benchmarking the quantization frontier.

  Both serve the same OpenAI-compatible /v1 endpoint, so the harness is unchanged — only
  the served binary differs (run-ik-llama-server.ps1 -ServerExe <this build's llama-server>).

  Requires on PATH: git, cmake, MSVC (VS Build Tools), and CUDA Toolkit (nvcc).

.EXAMPLE
  ./serving/install-llamacpp.ps1 -CudaArch 86
#>
[CmdletBinding()]
param(
    [string]$RepoDir = 'C:\llamacpp',
    [string]$Ref = 'master',
    [switch]$NoCuda,
    [string]$CudaArch = '',          # '86' for RTX 3090
    [string]$Target = 'llama-server',
    [int]$Jobs = 0
)

$ErrorActionPreference = 'Stop'

function Assert-Tool([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { throw "Required tool '$Name' not found on PATH. $Hint" }
}
Assert-Tool git 'Install Git for Windows.'
Assert-Tool cmake 'Install CMake.'
if (-not $NoCuda) { Assert-Tool nvcc 'Install the NVIDIA CUDA Toolkit (nvcc), or pass -NoCuda.' }

if (Test-Path (Join-Path $RepoDir '.git')) {
    Write-Host "Updating: $RepoDir"
    git -C $RepoDir -c core.longpaths=true fetch --depth 1 origin $Ref; if ($LASTEXITCODE -ne 0) { throw 'git fetch failed' }
    git -C $RepoDir -c core.longpaths=true checkout $Ref;               if ($LASTEXITCODE -ne 0) { throw 'git checkout failed' }
    git -C $RepoDir -c core.longpaths=true reset --hard "origin/$Ref";  if ($LASTEXITCODE -ne 0) { throw 'git reset failed' }
}
else {
    $parent = Split-Path $RepoDir -Parent
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Write-Host "Cloning mainline llama.cpp ($Ref) into: $RepoDir"
    git -c core.longpaths=true clone --depth 1 --branch $Ref https://github.com/ggml-org/llama.cpp.git $RepoDir
    if ($LASTEXITCODE -ne 0) { throw 'git clone failed' }
}

$buildDir = Join-Path $RepoDir 'build'
$cuda = if ($NoCuda) { 'OFF' } else { 'ON' }
$cfg = @('-B', $buildDir, '-S', $RepoDir, '-DGGML_NATIVE=ON', "-DGGML_CUDA=$cuda", '-DCMAKE_BUILD_TYPE=Release')
if ($CudaArch -and -not $NoCuda) { $cfg += "-DCMAKE_CUDA_ARCHITECTURES=$CudaArch" }
Write-Host "Configuring (GGML_CUDA=$cuda, arch=$CudaArch) ..."
cmake @cfg; if ($LASTEXITCODE -ne 0) { throw 'cmake configure failed' }

$bargs = @('--build', $buildDir, '--config', 'Release')
if ($Target) { $bargs += @('--target', $Target) }
if ($Jobs -gt 0) { $bargs += @('-j', "$Jobs") }
Write-Host "Building ..."
cmake @bargs; if ($LASTEXITCODE -ne 0) { throw "cmake build failed (try -Target '')" }

$server = Get-ChildItem -Path $buildDir -Recurse -Filter 'llama-server.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $server) { throw "llama-server.exe not found under $buildDir" }
$marker = Join-Path $PSScriptRoot '.llamacpp_server_path.txt'
Set-Content -Path $marker -Value $server.FullName -Encoding utf8
Write-Host "`nBuilt:    $($server.FullName)"
Write-Host "Recorded: $marker"

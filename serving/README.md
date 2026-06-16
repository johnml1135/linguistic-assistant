# serving/

Shared dev-box tooling for serving local GGUF models behind an **OpenAI-compatible
endpoint**, using [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp). Used by the
Python research harness now and callable from C# later — the integration is the *server*
(no Ollama, no Python bindings), so any caller just talks HTTP to `/v1`.

Why ik_llama.cpp: it's a llama.cpp fork (MIT, CUDA for Turing+) with SOTA quant types
(`IQ*_K`, trellis `IQ*_KT`) that get better quality-per-bit — directly relevant to the
"does Q4 dent morphology reasoning?" sweep. It ships `llama-server` with
`/v1/chat/completions`, so the existing `harness/openai_compat.py` adapter drives it
unchanged.

## Scripts

| Script | Does |
|---|---|
| `install-ik-llama.ps1` | Clone + CUDA-build ik_llama.cpp → `llama-server.exe`; records its path. |
| `run-ik-llama-server.ps1` | Launch the server for a given `.gguf` model on a port. |

Prerequisites (Windows): **git, cmake, Visual Studio Build Tools (MSVC), CUDA Toolkit
(nvcc)**. Pass `-NoCuda` to the installer for a CPU-only build.

## Use

```powershell
# 1. Build once
./serving/install-ik-llama.ps1                      # → serving/.cache/ik_llama.cpp, records exe path

# 2. Serve a model (foreground; Ctrl-C to stop)
./serving/run-ik-llama-server.ps1 -Model D:\gguf\gemma-4-27b-IQ4_K.gguf -CtxSize 16384

# 3. Point the harness at it
python research/scripts/smoke_test.py --endpoint ik_llama --prompt "Gloss 'ninakupenda'."
```

The `ik_llama` endpoint (`http://127.0.0.1:8080/v1`) is pre-registered in
`research/harness/config.py`.

## Calling from code

**Python** — launch as a child process, poll `/health`, tear down when done:

```python
import subprocess, httpx, time
p = subprocess.Popen([
    "pwsh", "-File", "serving/run-ik-llama-server.ps1",
    "-Model", r"D:\gguf\gemma-4-27b-IQ4_K.gguf", "-CtxSize", "16384",
])
# wait for readiness
for _ in range(360):
    try:
        if httpx.get("http://127.0.0.1:8080/health", timeout=2).status_code == 200:
            break
    except Exception:
        time.sleep(0.5)
# ... run the benchmark against the openai_compat 'ik_llama' endpoint ...
p.terminate()
```

**C#** — same shape with `System.Diagnostics.Process.Start("pwsh", "-File serving/run-ik-llama-server.ps1 ...")`, poll `/health` with `HttpClient`, `Kill()` when done.

(Or run `-WaitForReady`, which backgrounds the server, waits, prints the PID, and returns — then manage that PID yourself.)

## Notes

- The server is the contract. To swap to mainline llama.cpp or vLLM, just start that
  server and point a config endpoint at its port — no harness change.
- `serving/.cache/` (the build tree) and `.ik_llama_server_path.txt` are gitignored.
- GGUF model files are large — keep them outside the repo and pass absolute `-Model` paths.

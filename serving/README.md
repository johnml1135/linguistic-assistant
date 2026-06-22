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

## Reasoning / "thinking" models (Gemma 4, Qwen 3.6)

ik_llama.cpp's jinja path is **broken for Gemma-4 thinking**: with `-Jinja` it leaves the response
`content` empty and dumps the whole answer into `reasoning_content` (a known Gemma-4 26b-a4b chat-template
bug). **Use a mainline [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server` build
for the thinking path** — it splits the chain-of-thought into `reasoning_content` and the final answer
into `content` correctly.

```powershell
# thinking ON, mainline build (pass its exe via -ServerExe; -Think adds --reasoning on)
./serving/run-ik-llama-server.ps1 -ServerExe C:\llamacpp\build\bin\Release\llama-server.exe `
  -Model C:\path\gemma-4-26B-A4B-it-qat-UD-Q4_K_XL.gguf -CtxSize 8192 -Jinja -Think -WaitForReady
# thinking OFF (either build): -NoThink  → --reasoning off
```

The harness `openai_compat` adapter surfaces the final answer as `CompletionResult.text` and the
chain-of-thought as `CompletionResult.reasoning`; its default `max_tokens` is 2048 so reasoning + answer
both fit (a small budget gets eaten by thinking and the answer never lands). Measured effect on the
deferral resolve/defer eval: thinking raised Gemma's resolve-rate 0.75 → 0.92 at unchanged 1.0 precision.

## Notes

- The server is the contract. To swap to mainline llama.cpp or vLLM, just start that
  server and point a config endpoint at its port — no harness change.
- `serving/.cache/` (the build tree) and `.ik_llama_server_path.txt` are gitignored.
- GGUF model files are large — keep them outside the repo and pass absolute `-Model` paths.

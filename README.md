# DeBruyneCopilot

Hinge auto-sender via WebDriverAgent (USB). Prompts/replies live in the repo; **personal filter values stay on your machine**.

## Quick start

```bash
git clone https://github.com/cristofersalinas/DeBruyneCopilot.git
cd DeBruyneCopilot
pip3 install -r requirements.txt
cp prefs.example.yaml prefs.local.yaml
```

Open the project in Cursor (or similar) and ask the AI to set up environment + filters. See [AGENTS.md](AGENTS.md) — it will guide Xcode, WDA, Python, and filters **1:1**, always offering **"I'll edit from the code"**.

```bash
python3 hinge_wda.py
```

**F8** pause/resume · **F9** quit

## What is public vs local

| Public | Local only (gitignored) |
|--------|-------------------------|
| Engine (`hinge_wda.py`), prompts/replies | `prefs.local.yaml` (your filter values — edit by hand) |
| `prefs.example.yaml` (max 2 examples per list) | `errores/`, logs, Instagram/resumen files |
| `AGENTS.md` + `.cursor/rules/` | |

`prefs.local.yaml` is intentionally **human-readable** (section order like the original filters). Toggle `*_activo`, add/remove list lines — no AI required after setup.

## Para contribuidores

Añadir capacidades (visión, nuevos filtros como *features*, fiabilidad) en el motor. No subir listas personales — documentar claves nuevas en `prefs.example.yaml` con ≤2 ejemplos.

**Runtime must stay code-only** (no cloud LLM / token APIs in the like loop). AI is for install/setup and development help only — see `.cursor/rules/` and [AGENTS.md](AGENTS.md).

## Requirements (high level)

- macOS + Xcode (for WebDriverAgent)
- Python 3 + packages in `requirements.txt`
- iPhone unlocked over USB, developer trust enabled
- WebDriverAgent project (default `~/WebDriverAgent`)

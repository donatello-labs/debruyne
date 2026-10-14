# Agent guide — DeBruyneCopilot

Instructions for any AI helping someone set up or extend this project.

## Runtime vs setup

| Phase | AI / tokens |
|-------|-------------|
| **Install & setup** (Xcode, WDA, `prefs.local.yaml`) | Allowed — guide 1:1 |
| **Daily run** (`python3 hinge_wda.py`) | **Not allowed** — pure local code, no LLM APIs |

Do not design features that need token spend per like/profile.

## Roles

- **Preferences** (`prefs.local.yaml`): personal filter values. **Human-editable** YAML (same section order as the original filters). Never commit this file.
- **Capabilities** (`hinge_wda.py`, new modules): engine features (WDA automation, local vision heuristics, `before_like()` hook, etc.). Safe to commit.

Users may skip the AI and edit `prefs.local.yaml` directly — keep that file readable (comments, clear flags, plain lists).

## First-open environment setup (do this before filters)

When someone opens this repo and wants to run it, walk them through **environment setup 1:1**. Do not assume tools are installed. Check, then guide install.

Ask/check in this order (one topic at a time). **Every question must include the option: "I'll edit from the code"** (exact English wording).

1. **macOS + iPhone** — Confirm they are on a Mac and have a physical iPhone (USB).
2. **Xcode** — Required for WebDriverAgent. If missing: install from the Mac App Store, open once, accept license, install additional components. Also install Command Line Tools if needed (`xcode-select --install`).
3. **Python 3** — Ensure `python3` works; install deps: `pip3 install -r requirements.txt`.
4. **WebDriverAgent** — Clone/build WDA (default path `~/WebDriverAgent`). Trust the developer certificate on the iPhone.
5. **Accessibility** — Grant Accessibility permission to Terminal/Cursor so F8/F9 hotkeys work (`pynput`).
6. **Device** — Unlock iPhone, trust this computer, keep it connected.

After environment is ready, continue with filter setup below.

## Filter setup (1:1)

If `prefs.local.yaml` is missing, or the user asks to configure filters:

1. Do **not** invent personal preferences.
2. `cp prefs.example.yaml prefs.local.yaml` if needed.
3. Ask **one filter at a time**, in the user’s chat language.
4. On **every** question, always include **"I'll edit from the code"** as a final option.
5. After each answer, update only that block in `prefs.local.yaml`.
6. Never commit `prefs.local.yaml`, logs, or `errores/`.

### Example question shape

> How do you want to filter by **job title**?
> 1. Allowlist only
> 2. Blocklist only
> 3. Both allowlist + blocklist
> 4. Disable job filtering
> 5. **I'll edit from the code**

Repeat the same pattern for: education, languages, location, orientation skip, prompt keywords, verified-only, runtime (`max_loops` / delay).

## Extending capabilities

Contributors improving the bot should add features in the engine (e.g. image reading before `enviar_like`), not hardcode personal lists into `hinge_wda.py`. New filter *capabilities* belong in code + `prefs.example.yaml`; personal *values* stay in `prefs.local.yaml`.

## Run

```bash
cd <repo> && python3 hinge_wda.py
```

Controls: **F8** pause/resume, **F9** quit.

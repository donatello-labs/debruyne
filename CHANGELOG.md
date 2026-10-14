# Changelog

All notable changes to this project are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

## [1.0.0] — 2026-10-14

First public baseline of debruyne.

### Added

- Human-editable filter prefs: `prefs.local.yaml` (gitignored) + `prefs.example.yaml` (max 2 examples per list).
- `prefs.py` loader with merge of missing keys from the example schema.
- `before_like(src)` extension hook for contributors (local code only).
- `AGENTS.md` and `.cursor/rules/` — AI for install/setup only; runtime stays token-free.
- SemVer files: `VERSION`, `CHANGELOG.md`, git tag `v1.0.0`.

### Changed

- Deduplicated `hinge_wda.py`; prompts/replies stay in the public engine.
- Runtime paths are relative to the project directory.

[Unreleased]: https://github.com/donatello-labs/debruyne/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/donatello-labs/debruyne/releases/tag/v1.0.0

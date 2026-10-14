"""Load filter preferences from prefs.local.yaml (or prefs.example.yaml).

Human-editable YAML is the source of truth for filter values. Missing keys are
filled from prefs.example.yaml so contributor schema updates do not break runs.
"""

from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install with: pip3 install -r requirements.txt"
    ) from e

ROOT = Path(__file__).resolve().parent
LOCAL_PATH = ROOT / "prefs.local.yaml"
EXAMPLE_PATH = ROOT / "prefs.example.yaml"

# Stable order — matches prefs.example.yaml / original hinge filter layout
KEY_ORDER = (
    "delay_entre_loops",
    "max_loops",
    "filtro_vitals_activo",
    "requiere_verificado",
    "categorias_op",
    "cargo_aprueba_activo",
    "cargos_clave",
    "cargo_op",
    "bloqueo_cargo_activo",
    "bloqueo_cargo_and_activo",
    "cargos_bloqueados",
    "estudios_activo",
    "estudios_clave",
    "estudios_op",
    "idiomas_activo",
    "idiomas_clave",
    "idiomas_op",
    "ubicacion_aprueba_activo",
    "ubicacion_ciudades_activo",
    "ubicacion_prestigio",
    "ubicacion_ciudades",
    "ubicacion_op",
    "filtro_orientacion_activo",
    "orientacion_bloqueada",
    "emojis_bloqueados",
    "descripciones_emoji",
    "filtro_palabras_prompts_activo",
    "palabras_prompts_bloqueadas",
)


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_prefs(root: Path | None = None) -> dict:
    """Prefer prefs.local.yaml; fall back to example; merge missing keys from example."""
    base = root or ROOT
    local = base / "prefs.local.yaml"
    example = base / "prefs.example.yaml"

    example_data = _read_yaml(example)
    if not example_data and not local.exists():
        raise FileNotFoundError(
            f"Missing prefs: expected {local.name} or {example.name} in {base}"
        )

    if local.exists():
        path = local
        using_local = True
        data = dict(example_data)  # defaults first
        data.update(_read_yaml(local))  # local overrides
    else:
        path = example
        using_local = False
        data = dict(example_data)
        print(
            "⚠️  prefs.local.yaml not found — using prefs.example.yaml "
            "(example values only). Copy the example and edit by hand, or ask an AI "
            "to set up filters (see AGENTS.md)."
        )

    missing = [k for k in KEY_ORDER if k not in data]
    if missing:
        raise KeyError(
            f"Prefs incomplete after merge with example. Missing: {', '.join(missing)}"
        )

    filled = [k for k in KEY_ORDER if k not in _read_yaml(path) and k in example_data]
    if using_local and filled:
        print(
            f"ℹ️  prefs.local.yaml missing keys (filled from example): {', '.join(filled)}"
        )

    data["_prefs_path"] = str(path)
    data["_using_local"] = using_local
    return data

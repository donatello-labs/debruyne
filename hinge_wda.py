#!/usr/bin/env python3
"""
Hinge Auto-Sender — Control directo por USB via WebDriverAgent

Controles:
  F8  → Pausar / Reanudar
  F9  → Salir
"""

import re
import time
import html
import threading
import subprocess
import sqlite3
import unicodedata
import os
import wda
import requests
from pynput import keyboard
from datetime import datetime
from collections import defaultdict, Counter
from pathlib import Path

from prefs import load_prefs

_ROOT = str(Path(__file__).resolve().parent)

# ── Configuración ──────────────────────────────────────────
WDA_URL   = 'http://localhost:8100'
BUNDLE_ID = 'co.hinge.mobile.ios'

WDA_PROJECT  = os.path.expanduser('~/WebDriverAgent/WebDriverAgent.xcodeproj')
WDA_SCHEME   = 'WebDriverAgentRunner'
WDA_BUILD_LOG = os.path.join(_ROOT, 'wda_build.log')
WDA_BOOT_TIMEOUT = 180  # segundos máx esperando a que WDA responda tras lanzar xcodebuild

# Frases exactas de Hinge → mensaje a enviar.
HINGE_PROMPTS = {
    'Heey, i like it!': [
        "biggest risk i've taken",
        "most spontaneous thing i've done",
        "best travel story",
        "one thing i'll never do again",
        "a life goal of mine",
        "i recently discovered that",
        "my greatest strength",
        "green flags i look for",
        "i'll brag about you to my friends if",
        "dating me is like",
        "this year, i really want to",
        "i geek out on",
        "i could stay up all night talking about",
        "i wish more people knew",
        "you'd never know it, but i",
        "teach me something about",
        "i won't shut up about",
        "change my mind about",
        "if loving this is wrong, i don't want to be right",
        "the best way to ask me out is by",
        "the way to win me over is",
        "i'll fall for you if",
        "an award my family would give me",
        "the one thing you should know about me is",
        "the one thing i'd love to know about you is",
        "me in the wild",
        "take me back to",
        "me and my best friend",
        "my simple pleasures",
        "most adventurous thing i've done",
        "a random fact i love is",
        "my weekends look like",
        "my self-care routine is",
        "my favorite line from a movie",
        "i'm in my element when",
        "my best dad joke",
        "my friends ask me for advice about",
    ],
    'Heey, sounds good to me, haha': [
        "typical sunday",
        "first round is on me if",
        "what i order for the table",
        "i know the best spot in town for",
        "it's not a vacation unless",
        "i'm looking for",
        "my best celebrity impression",
        "my therapist would say i",
        "my cry-in-the-car song is",
        "my last journal entry was about",
        "the hallmark of a good relationship is",
        "i wind down by",
        "where i go when i want to feel a little more like myself",
        "the kindest thing someone has ever done for me",
        "you should leave a comment if",
        "we'll get along if",
        "all i ask is that you",
        "i want someone who",
        "something that's non-negotiable for me is",
        "give me travel tips for",
        "to me, relaxation is",
        "i feel most supported when",
        "apparently, my life's soundtrack is",
        "how to pronounce my name",
        "i hype myself up by",
        "the key to my heart is",
        "in my friend group, i'm the one who",
        "let's make sure we're on the same page about",
        "i'll pick the topic if you start the conversation",
        "before we meet, you should listen to",
        "when i need advice, i go to",
        "together, we could",
        "i'm weirdly attracted to",
        "my love language is",
        "weirdest gift i have given or received",
        "you should *not* go out with me if",
        "i get myself out of a funk by",
        "i wind down by",
    ],
    'I can live with that! Hahah': [
        "my most irrational fear",
        "my biggest date fail",
        "i bet you can't",
        "two truths and a lie",
        "worst idea i've ever had",
        "never have i ever",
        "the dorkiest thing about me is",
        "don't hate me if i",
        "what if i told you that",
        "a quick rant about",
        "i'll give you the set up, you guess the punchline",
        "a shower thought i recently had",
        "therapy recently taught me",
        "a boundary of mine is",
        "the last time i cried happy tears was",
        "try to guess this about me",
        "unusual skills",
        "we're the same type of weird if",
        "do you agree or disagree that",
        "let's debate this topic",
        "proof i have musical talent",
        "my bff's take on why you should date me",
        "guess the song",
        "something my pet thinks about me",
        "plandid or candid?",
        "let me introduce you to my alter ego",
        "caught in the act",
        "behind the scenes",
        "my quarter life crisis looks like",
        "guess where this photo was taken",
        "life peaked when",
        "this could be us",
        "saying \"hi!\" in as many languages i know",
        "i get myself out of a funk by",
        "my therapist would say i",
        "i go crazy for",
    ],
}

# Lookup rápido: frase exacta (lowercase) → mensaje
_PROMPT_LOOKUP = {
    p: msg
    for msg, prompts in HINGE_PROMPTS.items()
    for p in prompts
}

def _normalize(s):
    """Normaliza comillas tipográficas a ASCII para comparación robusta."""
    return (s
        .replace('‘', "'").replace('’', "'")
        .replace('“', '"').replace('”', '"')
        .replace('—', '-').replace('–', '-')
        .lower().strip()
    )

_PROMPT_LOOKUP_NORM = {_normalize(p): msg for p, msg in _PROMPT_LOOKUP.items()}

MENSAJE_DEFAULT = 'Sounds good to me, hahah'

# Paths relative to this project (runtime data stays local / gitignored)
SCREENSHOTS_DIR = os.path.join(_ROOT, 'errores')
INSTAGRAM_LOG = os.path.join(_ROOT, 'instagram_matches.txt')
RESUMEN_FILTRO_LOG = os.path.join(_ROOT, 'resumen_filtro.txt')
IG_RE = re.compile(r'(?i)(instagram|\bIG\b|@[A-Za-z0-9_.]{2,30})')
IG_HANDLE_RE = re.compile(r'@[A-Za-z0-9_.]{2,30}')
IG_KEYWORD_RE = re.compile(r'(?i)\b(?:instagram|ig)\b\s*[:\-]\s*([A-Za-z0-9_.]{2,30})')

# ── Filter prefs (personal values live in prefs.local.yaml) ──
_P = load_prefs(Path(_ROOT))

DELAY_ENTRE_LOOPS = _P['delay_entre_loops']
MAX_LOOPS = _P['max_loops']

FILTRO_VITALS_ACTIVO = _P['filtro_vitals_activo']
REQUIERE_VERIFICADO = _P['requiere_verificado']
CATEGORIAS_OP = _P['categorias_op']

CARGO_APRUEBA_ACTIVO = _P['cargo_aprueba_activo']
CARGOS_CLAVE = list(_P['cargos_clave'] or [])
CARGO_OP = _P['cargo_op']

BLOQUEO_CARGO_ACTIVO = _P['bloqueo_cargo_activo']
BLOQUEO_CARGO_AND_ACTIVO = _P['bloqueo_cargo_and_activo']
CARGOS_BLOQUEADOS = list(_P['cargos_bloqueados'] or [])

ESTUDIOS_ACTIVO = _P['estudios_activo']
ESTUDIOS_CLAVE = list(_P['estudios_clave'] or [])
ESTUDIOS_OP = _P['estudios_op']

IDIOMAS_ACTIVO = _P['idiomas_activo']
IDIOMAS_CLAVE = list(_P['idiomas_clave'] or [])
IDIOMAS_OP = _P['idiomas_op']

UBICACION_APRUEBA_ACTIVO = _P['ubicacion_aprueba_activo']
UBICACION_CIUDADES_ACTIVO = _P['ubicacion_ciudades_activo']
UBICACION_PRESTIGIO = list(_P['ubicacion_prestigio'] or [])
UBICACION_CIUDADES = list(_P['ubicacion_ciudades'] or [])
UBICACION_OP = _P['ubicacion_op']
UBICACION_CLAVE = UBICACION_PRESTIGIO + (UBICACION_CIUDADES if UBICACION_CIUDADES_ACTIVO else [])

FILTRO_ORIENTACION_ACTIVO = _P['filtro_orientacion_activo']
ORIENTACION_BLOQUEADA = list(_P['orientacion_bloqueada'] or [])
EMOJIS_BLOQUEADOS = list(_P['emojis_bloqueados'] or [])
DESCRIPCIONES_EMOJI = list(_P['descripciones_emoji'] or [])

FILTRO_PALABRAS_PROMPTS_ACTIVO = _P['filtro_palabras_prompts_activo']
PALABRAS_PROMPTS_BLOQUEADAS = list(_P['palabras_prompts_bloqueadas'] or [])


def _sin_acentos(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def _clausula_like(columna, palabras, operador):
    partes = [f"{columna} LIKE '%{_sin_acentos(p.lower())}%'" for p in palabras]
    return '(' + f' {operador} '.join(partes) + ')' if partes else '(1=0)'


_clausulas_activas = []
if CARGO_APRUEBA_ACTIVO:
    _clausulas_activas.append(_clausula_like('job', CARGOS_CLAVE, CARGO_OP))
if ESTUDIOS_ACTIVO:
    _clausulas_activas.append(_clausula_like('educacion', ESTUDIOS_CLAVE, ESTUDIOS_OP))
if IDIOMAS_ACTIVO:
    _clausulas_activas.append(_clausula_like('idiomas', IDIOMAS_CLAVE, IDIOMAS_OP))
if UBICACION_APRUEBA_ACTIVO:
    _clausulas_activas.append(_clausula_like('ubicacion', UBICACION_CLAVE, UBICACION_OP))

FILTRO_WHERE = (
    '(' + f' {CATEGORIAS_OP} '.join(_clausulas_activas) + ')'
    if _clausulas_activas
    else '(1=1)'
)
if REQUIERE_VERIFICADO:
    FILTRO_WHERE = f"({FILTRO_WHERE}) AND (verificado = 1)"
if BLOQUEO_CARGO_ACTIVO:
    FILTRO_WHERE = f"({FILTRO_WHERE}) AND NOT ({_clausula_like('job', CARGOS_BLOQUEADOS, 'OR')})"
if BLOQUEO_CARGO_AND_ACTIVO:
    FILTRO_WHERE = f"({FILTRO_WHERE}) AND NOT (job LIKE '% and %')"

_ORIENTACION_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(_sin_acentos(p.lower()))
                        for p in ORIENTACION_BLOQUEADA) + r')\b'
) if ORIENTACION_BLOQUEADA else None

_PALABRAS_PROMPTS_RE = re.compile(
    r'\b(?:' + '|'.join(re.escape(_sin_acentos(p.lower()))
                        for p in PALABRAS_PROMPTS_BLOQUEADAS) + r')\b'
) if PALABRAS_PROMPTS_BLOQUEADAS else None

running    = False
stop_event = threading.Event()
count      = 0
errors     = 0
filtrados  = 0
client     = None
session    = None
_stats: dict[str, Counter] = defaultdict(Counter)
_ig_vistos: set[tuple[str, str]] = set()
_historial_filtro: list[dict] = []
_bloqueos_orientacion: list[dict] = []
_wda_proc = None
_relay_proc = None

SERVER_URL_RE = re.compile(r'ServerURLHere->(http://[^<\s]+)<-ServerURLHere')


def _wda_listo(url=None, timeout=2):
    try:
        r = requests.get(f'{url or WDA_URL}/status', timeout=timeout)
        return r.status_code == 200 and r.json().get('value', {}).get('ready', False)
    except Exception:
        return False


def _url_desde_log():
    try:
        with open(WDA_BUILD_LOG) as f:
            contenido = f.read()
        m = SERVER_URL_RE.search(contenido)
        return m.group(1) if m else None
    except Exception:
        return None


def _detectar_udid():
    try:
        out = subprocess.run(
            ['python3', '-m', 'tidevice', 'list'],
            capture_output=True, text=True, timeout=10
        ).stdout
        for line in out.splitlines():
            partes = line.split()
            if partes and re.fullmatch(r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}|[0-9A-Fa-f]{40}', partes[0]):
                return partes[0]
    except Exception:
        pass
    return None


def _iniciar_relay_usb():
    global _relay_proc
    if _relay_proc and _relay_proc.poll() is None:
        return
    try:
        _relay_proc = subprocess.Popen(
            ['python3', '-m', 'tidevice', 'relay', '8100', '8100'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        _relay_proc = None


def asegurar_wda():
    global _wda_proc, WDA_URL

    if _wda_listo():
        print(f"   ✅ WDA ya está corriendo en {WDA_URL}")
        return

    print("   ⚙️  WDA no responde — voy a intentar levantarlo con Xcode...")

    udid = _detectar_udid()
    if not udid:
        raise RuntimeError(
            "No se detectó ningún iPhone conectado (tidevice list vacío). "
            "Conecta el cable USB y desbloquea el teléfono."
        )
    print(f"   📱 Dispositivo detectado: {udid}")

    if not os.path.isdir(WDA_PROJECT):
        raise RuntimeError(f"No existe el proyecto de WebDriverAgent en {WDA_PROJECT}")

    os.makedirs(os.path.dirname(WDA_BUILD_LOG), exist_ok=True)
    logfile = open(WDA_BUILD_LOG, 'w')

    cmd = [
        'xcodebuild', 'test',
        '-project', WDA_PROJECT,
        '-scheme', WDA_SCHEME,
        '-destination', f'id={udid}',
    ]
    print(f"   🛠️  Ejecutando: {' '.join(cmd)}")
    print(f"      (log completo en {WDA_BUILD_LOG})")

    _wda_proc = subprocess.Popen(cmd, stdout=logfile, stderr=subprocess.STDOUT)
    _iniciar_relay_usb()

    inicio = time.time()
    url_dispositivo = None
    while time.time() - inicio < WDA_BOOT_TIMEOUT:
        if _wda_proc.poll() is not None:
            with open(WDA_BUILD_LOG) as f:
                cola = f.read()[-2000:]
            razon = _diagnosticar_fallo_xcodebuild(cola)
            raise RuntimeError(f"xcodebuild terminó antes de levantar WDA: {razon}")

        if _wda_listo(WDA_URL):
            print(f"   ✅ WDA arriba y respondiendo en {WDA_URL} ({int(time.time() - inicio)}s)")
            return

        if not url_dispositivo:
            url_dispositivo = _url_desde_log()
            if url_dispositivo:
                print(f"   🔎 WDA quedó escuchando en {url_dispositivo} (sin forwarding a localhost)")

        if url_dispositivo and _wda_listo(url_dispositivo):
            WDA_URL = url_dispositivo
            print(f"   ✅ WDA arriba y respondiendo en {WDA_URL} ({int(time.time() - inicio)}s)")
            return

        time.sleep(2)

    detener_wda()
    raise RuntimeError(
        f"WDA no respondió tras {WDA_BOOT_TIMEOUT}s. Revisa {WDA_BUILD_LOG} "
        "(posible teléfono bloqueado, cable USB flojo, o certificado sin confiar)."
    )


def _diagnosticar_fallo_xcodebuild(log_tail):
    pistas = [
        ('is locked', "el iPhone está bloqueado — desbloquéalo y vuelve a intentar"),
        ('not trusted', "el equipo no es de confianza en el iPhone — acepta el diálogo 'Confiar' en el teléfono"),
        ('requires a development team', "falta un Development Team válido en la firma de WebDriverAgent (ábrelo una vez en Xcode y selecciona tu cuenta de Apple)"),
        ('doesn\'t support', "el certificado/perfil de aprovisionamiento no es válido para este dispositivo"),
        ('No profiles for', "no hay perfil de aprovisionamiento — abre el proyecto en Xcode una vez para que se genere automáticamente"),
        ('Unable to install', "no se pudo instalar la app en el iPhone (revisa espacio y confianza del dispositivo)"),
        ('timed out', "tiempo de espera agotado durante el build/instalación"),
    ]
    bajo = log_tail.lower()
    for clave, explicacion in pistas:
        if clave.lower() in bajo:
            return explicacion
    return f"ver detalle en el log: ...{log_tail[-500:]}"


def detener_wda():
    global _wda_proc, _relay_proc
    if _wda_proc and _wda_proc.poll() is None:
        print("\n🛑 Deteniendo proceso de WDA (xcodebuild)...")
        _wda_proc.terminate()
        try:
            _wda_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _wda_proc.kill()
    _wda_proc = None

    if _relay_proc and _relay_proc.poll() is None:
        _relay_proc.terminate()
        try:
            _relay_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _relay_proc.kill()
    _relay_proc = None


def guardar_screenshot(motivo):
    try:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        ts = datetime.now().strftime('%H%M%S')
        path = f"{SCREENSHOTS_DIR}/error_{ts}_{motivo[:30].replace(' ','_')}.png"
        img = session.screenshot()
        img.save(path)
        print(f"\n📸 Screenshot: {os.path.basename(path)}")
    except Exception:
        pass


def _extraer_handle(texto):
    handles = IG_HANDLE_RE.findall(texto)
    if handles:
        return handles
    m = IG_KEYWORD_RE.search(texto)
    if m and m.group(1):
        return [m.group(1)]
    return ['IG']


def revisar_instagram(src=None):
    if src is None:
        try:
            src = session.source()
        except Exception:
            return

    m = re.search(r"Like ([^']+)'s (?:photo|answer)", src)
    nombre = m.group(1) if m else '?'

    handles = []
    for tipo in ('StaticText', 'TextView', 'Other'):
        for texto in re.findall(rf'<XCUIElementType{tipo}[^>]*\blabel="([^"]*)"', src):
            texto = texto.strip()
            if texto and IG_RE.search(texto):
                for handle in _extraer_handle(texto):
                    if (nombre, handle) not in _ig_vistos:
                        _ig_vistos.add((nombre, handle))
                        handles.append(handle)

    if not handles:
        return

    try:
        os.makedirs(os.path.dirname(INSTAGRAM_LOG), exist_ok=True)
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(INSTAGRAM_LOG, 'a', encoding='utf-8') as f:
            for handle in handles:
                f.write(f"[{ts}] {nombre}: {handle}\n")
        print(f"\n   📷 IG detectado — {nombre}: {' | '.join(handles)}")
    except Exception:
        pass


VITALS_RE = re.compile(r'value="([^"]*)" name="([^"]*)" label="\2"')


def _leer_vitals(src):
    campos = {}
    for valor, campo in VITALS_RE.findall(src):
        campos[campo] = valor
    return campos


def _texto_visible(src):
    textos = []
    for attr in ('label', 'value'):
        textos.extend(re.findall(rf'\s{attr}="([^"]*)"', src))
    return textos


def perfil_bloqueado_por_orientacion(src):
    if not src:
        return False, None

    for texto in _texto_visible(src):
        plano = _sin_acentos(html.unescape(texto).lower())

        if FILTRO_ORIENTACION_ACTIVO:
            for emoji in EMOJIS_BLOQUEADOS:
                if emoji in texto:
                    return True, f'emoji {emoji!r} en "{texto[:60]}"'
            for desc in DESCRIPCIONES_EMOJI:
                if desc in plano:
                    return True, f'"{desc}" en "{texto[:60]}"'
            if _ORIENTACION_RE:
                m = _ORIENTACION_RE.search(plano)
                if m:
                    return True, f'orientación: "{m.group(0)}" en "{texto[:60]}"'

        if FILTRO_PALABRAS_PROMPTS_ACTIVO and _PALABRAS_PROMPTS_RE:
            m = _PALABRAS_PROMPTS_RE.search(plano)
            if m:
                return True, f'palabra bloqueada: "{m.group(0)}" en "{texto[:60]}"'

    return False, None


def perfil_pasa_filtro(src):
    if not FILTRO_VITALS_ACTIVO:
        return True

    campos = _leer_vitals(src)
    job_raw = campos.get('Job', '')
    educacion_raw = campos.get('Education', '')
    ubicacion_raw = campos.get('Location', '')
    job = _sin_acentos(job_raw.lower())
    educacion = _sin_acentos(educacion_raw.lower())
    idiomas_txt = campos.get('Languages Spoken', '')
    idiomas_n = len([i for i in idiomas_txt.split(',') if i.strip()])
    idiomas = _sin_acentos(idiomas_txt.lower())
    ubicacion = _sin_acentos(ubicacion_raw.lower())
    verificado = 1 if 'Verified' in campos else 0

    m = re.search(r"Like ([^']+)'s (?:photo|answer)", src)
    nombre = m.group(1) if m else '?'

    con = sqlite3.connect(':memory:')
    try:
        con.execute(
            'CREATE TABLE perfil (job TEXT, educacion TEXT, idiomas TEXT, '
            'ubicacion TEXT, verificado INTEGER)'
        )
        con.execute(
            'INSERT INTO perfil VALUES (?, ?, ?, ?, ?)',
            (job, educacion, idiomas, ubicacion, verificado)
        )
        fila = con.execute(f'SELECT 1 FROM perfil WHERE {FILTRO_WHERE}').fetchone()
        pasa = fila is not None
        if not pasa:
            cargo_ok = any(_sin_acentos(p.lower()) in job for p in CARGOS_CLAVE)
            estudios_ok = any(_sin_acentos(p.lower()) in educacion for p in ESTUDIOS_CLAVE)
            idiomas_ok = any(_sin_acentos(p.lower()) in idiomas for p in IDIOMAS_CLAVE)
            ubicacion_ok = any(_sin_acentos(p.lower()) in ubicacion for p in UBICACION_CLAVE)
            _matches_bloqueo = [
                p for p in CARGOS_BLOQUEADOS if _sin_acentos(p.lower()) in job
            ] if BLOQUEO_CARGO_ACTIVO else []
            if BLOQUEO_CARGO_AND_ACTIVO and ' and ' in job:
                _matches_bloqueo.append(' and ')
            palabra_bloqueada = max(_matches_bloqueo, key=len) if _matches_bloqueo else None

            print(
                f"      (job={job_raw!r} educ={educacion_raw!r} idiomas={idiomas_txt!r} "
                f"ubicacion={ubicacion_raw!r} verificado={bool(verificado)}"
                + (f" bloqueado_por={palabra_bloqueada!r}" if palabra_bloqueada else "") + ")"
            )
            _historial_filtro.append({
                'nombre': nombre,
                'job': job_raw, 'job_ok': cargo_ok,
                'educacion': educacion_raw, 'educacion_ok': estudios_ok,
                'idiomas_n': idiomas_n, 'idiomas_txt': idiomas_txt, 'idiomas_ok': idiomas_ok,
                'ubicacion': ubicacion_raw, 'ubicacion_ok': ubicacion_ok,
                'verificado': bool(verificado),
                'palabra_bloqueada': palabra_bloqueada,
            })
        return pasa
    except sqlite3.Error as e:
        print(f"\n⚠️  Error de sintaxis en FILTRO_WHERE, dejo pasar el perfil: {e}")
        return True
    finally:
        con.close()


def descartar_upsell():
    try:
        btns = session(xpath=(
            "//XCUIElementTypeButton["
            "@label='No thanks' or @label='No Thanks' or "
            "@label='Maybe Later' or @label='Maybe later' or "
            "@label='Not Now' or @label='Not now' or "
            "@label='Skip' or @label='Close' or @label='Cancel' or @label='Dismiss'"
            "]"
        )).find_elements()
        if btns:
            btns[0].tap()
            print(f"\n   💬 Upsell descartado")
    except Exception:
        pass


def skip_profile():
    tocado = False
    try:
        btns = session(xpath=(
            "//XCUIElementTypeButton["
            "@name='decisionBar_skipButton' or "
            "starts-with(@label, 'Skip') or @label='Pass' or @label='X'"
            "]"
        )).find_elements()
        if btns:
            btns[0].tap()
            tocado = True
    except Exception:
        pass

    if not tocado:
        try:
            session.swipe(196, 700, 196, 100, duration=0.3)
        except Exception:
            pass


def get_answer_button(tipo='answer'):
    """
    Busca el botón de Like en el perfil.
    tipo='photo'  → Busca el botón de Like de la foto principal.
    tipo='answer' → Busca el botón de Like de las respuestas escritas.
    """
    filtro_xpath = "'s photo" if tipo == 'photo' else "'s answer"
    for _ in range(3):
        btns = session(
            xpath=f"//XCUIElementTypeButton[contains(@label, \"{filtro_xpath}\")]"
        ).find_elements()
        if btns:
            return btns[0]
        session.swipe(196, 600, 196, 300, duration=0.1)
        time.sleep(0.1)
    return None


def elegir_mensaje():
    try:
        elems = session(
            xpath="//XCUIElementTypeOther[starts-with(@label, 'Prompt:')]"
        ).find_elements()
        for e in elems:
            lbl = (e.label or '').strip()
            prompt_raw = re.split(r'[.,]\s*Answer:', lbl[len('Prompt:'):], maxsplit=1)[0].strip()
            norm = _normalize(prompt_raw)

            if norm in _PROMPT_LOOKUP_NORM:
                return _PROMPT_LOOKUP_NORM[norm], prompt_raw
            for prompt_norm, msg in _PROMPT_LOOKUP_NORM.items():
                if norm.startswith(prompt_norm):
                    return msg, prompt_norm

            return MENSAJE_DEFAULT, f"Sin match: {prompt_raw}"

        return MENSAJE_DEFAULT, 'Sin prompt'

    except Exception:
        pass
    return MENSAJE_DEFAULT, 'Error'


def before_like(src):
    """Contributor extension point (local code only — no cloud LLM).

    Return False to skip this profile without sending a like.
    Override or wrap from a small local module if you add capabilities
    (e.g. screenshot heuristics). Default: allow.
    """
    return True


def enviar_like():
    global errors, filtrados
    try:
        try:
            src = session.source()
        except Exception:
            src = ''

        if not before_like(src):
            filtrados += 1
            print("\n🚫 before_like() skipped profile")
            skip_profile()
            return None, None

        bloqueado, motivo = perfil_bloqueado_por_orientacion(src)
        if bloqueado:
            filtrados += 1
            m = re.search(r"Like ([^']+)'s (?:photo|answer)", src)
            nombre = m.group(1) if m else '?'
            _bloqueos_orientacion.append({'nombre': nombre, 'motivo': motivo})
            print(f"\n🚫 Bloqueado por orientación/identidad — {motivo}")
            skip_profile()
            return None, None

        if not perfil_pasa_filtro(src):
            filtrados += 1
            print(f"\n🚫 No cumple el filtro (cargo/estudios/idiomas) — saltando...")
            skip_profile()
            return None, None

        # --- EVALUACIÓN DE REGLAS BASADAS EN PALABRAS CLAVE ---
        texto_perfil = _sin_acentos(src.lower())
        usar_foto = False

        # Regla 1: "man with a plan"
        if "man with a plan" in texto_perfil:
            mensaje = "The details are confidential and you'll find out at the right time hahaha, what brings you to town?"
            prompt_log = "Match por 'man with a plan'"
            usar_foto = True

        # Regla 2: Intención + Idioma (Spanish/Español)
        elif any(p in texto_perfil for p in ["fluent", "fluido", "fluidamente", "improve", "mejorar", "work", "trabajar", "practice", "practicar", "learn", "aprender", "speak", "hablar"]) and any(p in texto_perfil for p in ["spanish", "espanol", "castellano"]):
            mensaje = "We can do it :) as a first lesson, do you know 'holi'?"
            prompt_log = "Match por idioma (spanish practice/fluent)"
            usar_foto = True

        # Regla 3: Recién llegada / Explorar la ciudad
        else:
            patrones_ciudad = [
                "new to", "new in", "new here", "new in town", "new to the city",
                "show me", "show me around",
                "around here", "around the city", "around town"
            ]
            tiene_patron_directo = any(p in texto_perfil for p in patrones_ciudad)
            tiene_around_ubicacion = "around" in texto_perfil and any(u in texto_perfil for u in ["city", "town", "area", "zone", "here"])

            if tiene_patron_directo or tiene_around_ubicacion:
                mensaje = "I have a few ideas for things to do in the city, but first I need to know about your interests... What did you like most about the city?"
                prompt_log = "Match por explorar/nueva en la ciudad"
                usar_foto = True
            else:
                # Comportamiento estándar por prompt exacto (lista HINGE_PROMPTS)
                mensaje, prompt_log = elegir_mensaje()
                usar_foto = False
        # ------------------------------------------------------

        # Selección del botón según la regla matched
        tipo_boton = 'photo' if usar_foto else 'answer'
        btn = get_answer_button(tipo=tipo_boton)

        # Respaldo: Si falló encontrar el botón de foto, intenta el de texto para no perder el perfil
        if not btn and usar_foto:
            btn = get_answer_button(tipo='answer')

        if not btn:
            print(f"\n⚠️  Sin sección de botón para enviar el like, saltando perfil...")
            skip_profile()
            return False, None

        raw = _normalize(btn.label or '').replace('like ', '', 1)
        nombre = raw.split("'s")[0].strip().capitalize() if "'s" in raw else '?'

        btn.tap()

        campo = None
        for _ in range(20):
            found = session(xpath=(
                "//XCUIElementTypeTextView["
                "@name='Edit comment' or @name='Add a comment']"
            )).find_elements()
            if found:
                campo = found[0]
                break
            time.sleep(0.1)

        if not campo:
            campo = session(type='XCUIElementTypeTextView', name='Edit comment')
        campo.tap()
        campo.set_text(mensaje)

        send_btns = session(xpath=(
            "//XCUIElementTypeButton["
            "@label='Send priority like' or @label='Send Priority Like' or "
            "@label='Send Like' or @label='Send like'"
            "]"
        )).find_elements()
        if not send_btns:
            raise RuntimeError('Botón de enviar like no encontrado (¿cambió la interfaz?)')
        send_btns[0].tap()

        descartar_upsell()
        revisar_instagram(src)

        ts = datetime.now().strftime('%H:%M:%S')
        print(f"\n{ts} | {nombre} | {prompt_log} | {mensaje}")
        _stats[mensaje][prompt_log] += 1

        return True, mensaje

    except Exception as e:
        errors += 1
        motivo = str(e)
        print(f"\n⚠️  Error #{errors} (continuando): {motivo}")
        guardar_screenshot(motivo)
        skip_profile()
        return False, None


def print_stats():
    print("\n── Prompts más frecuentes " + "─" * 30)
    for msg, counter in _stats.items():
        total = sum(counter.values())
        top = counter.most_common(5)
        top_str = " · ".join(f"{p} ×{n}" for p, n in top)
        label = msg[:22].ljust(22)
        print(f"  {label} ({total:>3})  {top_str}")
    print("─" * 56)


def generar_resumen_filtro(inicio_ts, fin_ts):
    if not _historial_filtro and not _bloqueos_orientacion:
        return

    dur_min = max(1, round((fin_ts - inicio_ts) / 60))

    lineas = []
    lineas.append("=" * 70)
    lineas.append("RESUMEN DE SESIÓN — PARA MEJORA CONTINUA DEL FILTRO DE HINGE")
    lineas.append("=" * 70)
    lineas.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lineas.append(f"Duración: ~{dur_min} min")
    lineas.append(f"Likes enviados: {count} | Perfiles filtrados: {filtrados} | Errores: {errors}")
    lineas.append("")
    lineas.append(f"REQUIERE_VERIFICADO={REQUIERE_VERIFICADO} | IDIOMAS_CLAVE={IDIOMAS_CLAVE} | "
                   f"CATEGORIAS_OP={CATEGORIAS_OP}")
    lineas.append("")

    if _bloqueos_orientacion:
        lineas.append(f"--- Perfiles saltados por FILTRO_ORIENTACION_ACTIVO ({len(_bloqueos_orientacion)}) ---")
        for r in _bloqueos_orientacion:
            lineas.append(f"  {r['nombre']}: {r['motivo']}")
        lineas.append("")

    def _campo(etiqueta, valor, ok, extra=""):
        valor_fmt = f"\"{valor}\"" if valor else "(vacío)"
        estado = "OK — sí matchea" if ok else "NO matchea"
        return f"      {etiqueta:11} {valor_fmt:45} -> {estado}{extra}"

    lineas.append("--- Detalle por perfil rechazado (TODOS los campos leídos, no solo los que fallaron) ---")
    for i, r in enumerate(_historial_filtro, 1):
        lineas.append(f"  [{i}] {r['nombre']}")
        extra_job = f" (BLOQUEADA por \"{r['palabra_bloqueada']}\")" if r.get('palabra_bloqueada') else ""
        lineas.append(_campo("rol:", r['job'], r['job_ok'], extra_job))
        lineas.append(_campo("estudios:", r['educacion'], r['educacion_ok']))
        lineas.append(_campo(
            "idiomas:", r['idiomas_txt'], r['idiomas_ok'],
            f" ({r['idiomas_n']} idioma(s) en total)"
        ))
        lineas.append(_campo("ubicacion:", r['ubicacion'], r['ubicacion_ok']))
        lineas.append(f"      {'verificado:':11} {r['verificado']!s:45} -> "
                       + ("requerido" if REQUIERE_VERIFICADO else "no se exige"))
        if r.get('palabra_bloqueada'):
            veredicto = f"RECHAZADA — bloqueada por palabra clave \"{r['palabra_bloqueada']}\""
        else:
            veredicto = "RECHAZADA — ninguna categoría matcheó"
        lineas.append(f"      => {veredicto}")
        lineas.append("")

    def _top_no_matchearon(campo, campo_ok):
        vals = [
            r[campo].strip() for r in _historial_filtro
            if not r[campo_ok] and r[campo].strip() and not r.get('palabra_bloqueada')
        ]
        return Counter(vals).most_common(15)

    bloqueados = [r for r in _historial_filtro if r.get('palabra_bloqueada')]
    if bloqueados:
        lineas.append("")
        lineas.append(f"--- Perfiles descartados por BLOQUEO_CARGO_ACTIVO ({len(bloqueados)}) ---")
        conteo_bloqueo = Counter(r['palabra_bloqueada'] for r in bloqueados)
        for palabra, n in conteo_bloqueo.most_common():
            lineas.append(f"  \"{palabra}\" ×{n}")

    lineas.append("")
    lineas.append("--- Valores de ROL/CARGO que NO matchearon ninguna palabra clave (candidatos a CARGOS_CLAVE) ---")
    for val, n in _top_no_matchearon('job', 'job_ok'):
        lineas.append(f"  \"{val}\" ×{n}")

    lineas.append("")
    lineas.append("--- Valores de ESTUDIOS que NO matchearon ninguna palabra clave (candidatos a ESTUDIOS_CLAVE) ---")
    for val, n in _top_no_matchearon('educacion', 'educacion_ok'):
        lineas.append(f"  \"{val}\" ×{n}")

    lineas.append("")
    lineas.append("--- Valores de UBICACIÓN que NO matchearon ninguna palabra clave (candidatos a UBICACION_CLAVE) ---")
    for val, n in _top_no_matchearon('ubicacion', 'ubicacion_ok'):
        lineas.append(f"  \"{val}\" ×{n}")

    lineas.append("")
    lineas.append("--- Instrucciones para la IA que analice esto ---")
    lineas.append(
        "Revisa las listas de 'NO matchearon' de arriba. Si ves roles, estudios o\n"
        "ubicaciones de valor que deberían haber pasado el filtro, proponé agregar\n"
        "esas palabras (o su raíz más corta, en minúsculas y sin tilde) a CARGOS_CLAVE,\n"
        "ESTUDIOS_CLAVE o UBICACION_CLAVE en hinge_wda.py, siguiendo el mismo estilo de\n"
        "raíces cortas ya usado ahí (ej. 'ingenier' en vez de 'ingeniero'/'ingeniera').\n"
        "No sugieras agregar valores irrelevantes (ej. 'camarera', 'estudiante') salvo\n"
        "que se repitan mucho y el usuario confirme que le interesan."
    )
    lineas.append("=" * 70)

    texto = "\n".join(lineas)
    print("\n" + texto)

    try:
        with open(RESUMEN_FILTRO_LOG, 'w', encoding='utf-8') as f:
            f.write(texto + "\n")
        print(f"\n📄 Resumen guardado en {RESUMEN_FILTRO_LOG}")
    except Exception:
        pass


def loop():
    global running, count, errors, filtrados, client, session

    count = 0
    errors = 0
    filtrados = 0
    _stats.clear()
    _historial_filtro.clear()
    _bloqueos_orientacion.clear()
    inicio_ts = time.time()

    try:
        asegurar_wda()
    except Exception as e:
        print(f"\n❌ No se pudo levantar WDA: {e}")
        running = False
        return

    print(f"\n▶  Conectando a WDA en {WDA_URL}...")

    try:
        client = wda.Client(WDA_URL)
        session = client.session(BUNDLE_ID)
        time.sleep(0.8)
        print(f"   App abierta — delay: {DELAY_ENTRE_LOOPS}s — máx: {MAX_LOOPS or '∞'}")
        print(f"   Modo: respuesta contextual por prompt")
    except Exception as e:
        print(f"\n❌ No se pudo conectar: {e}")
        running = False
        return

    consecutive_errors = 0
    sin_progreso = 0
    while not stop_event.is_set():
        ok, _ = enviar_like()
        if ok:
            count += 1
            consecutive_errors = 0
            sin_progreso = 0
            lim = f"/{MAX_LOOPS}" if MAX_LOOPS else ""
            print(f"  ✉  #{count}{lim}  🚫 {filtrados} filtrados  ⚠️ {errors} errores")
        elif ok is False:
            consecutive_errors += 1
            sin_progreso += 1
            if consecutive_errors >= 3:
                print(f"\n⚠️  3 errores seguidos — forzando skip...")
                skip_profile()
                consecutive_errors = 0
            if sin_progreso >= 10:
                print(
                    f"\n🛑 10 intentos seguidos sin ningún resultado (ni like ni filtro "
                    "limpio) — algo está roto de fondo. Deteniendo el script."
                )
                stop_event.set()
                break
        else:
            sin_progreso = 0

        if MAX_LOOPS and count >= MAX_LOOPS:
            print(f"\n✅ Listo — {count} likes, {filtrados} filtrados, {errors} errores.")
            break

        stop_event.wait(DELAY_ENTRE_LOOPS)

    running = False
    print_stats()
    generar_resumen_filtro(inicio_ts, time.time())
    print(f"\n⏸  Parado — {count} likes, {filtrados} filtrados, {errors} errores.")


def on_f8():
    global running
    if running:
        stop_event.set()
    else:
        stop_event.clear()
        running = True
        threading.Thread(target=loop, daemon=True).start()


def on_f9():
    stop_event.set()
    detener_wda()
    print("\n👋 Saliendo...")
    os._exit(0)


def main():
    print("=" * 40)
    print("  HINGE WDA AUTO-SENDER")
    print("=" * 40)
    print("  F8  →  Pausar / Reanudar")
    print("  F9  →  Salir")
    print("=" * 40)

    on_f8()

    hmap = {keyboard.Key.f8: on_f8, keyboard.Key.f9: on_f9}

    def on_press(k):
        fn = hmap.get(k)
        if fn:
            threading.Thread(target=fn, daemon=True).start()

    with keyboard.Listener(on_press=on_press) as lst:
        lst.join()


if __name__ == "__main__":
    main()

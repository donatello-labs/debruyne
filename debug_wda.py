#!/usr/bin/env python3
"""
Diagnóstico WDA — vuelca todos los elementos visibles.
Correr con el modal de Hinge abierto (después de tocar "Answer").
"""
import wda

WDA_URL = 'http://localhost:8100'

client = wda.Client(WDA_URL)
session = client.session()

print("\n=== TODOS LOS ELEMENTOS (type | name | label) ===\n")

# Obtener el árbol XML completo
source = session.source()

# También listar elemento por elemento los más comunes
for type_name in [
    'XCUIElementTypeStaticText',
    'XCUIElementTypeTextView',
    'XCUIElementTypeButton',
    'XCUIElementTypeOther',
]:
    elems = session(type=type_name).find_elements()
    if elems:
        print(f"── {type_name} ({len(elems)}) ──────────────")
        for e in elems:
            lbl  = (e.label  or '').strip()[:80]
            name = (e.name   or '').strip()[:40]
            val  = (e.value  or '').strip()[:40]
            print(f"  label={lbl!r:82}  name={name!r:42}  value={val!r}")
        print()

print("\n=== XML SOURCE (primeros 4000 chars) ===\n")
print(source[:4000])

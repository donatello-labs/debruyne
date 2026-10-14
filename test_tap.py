#!/usr/bin/env python3
import wda, time

c = wda.Client('http://localhost:8100')
s = c.session('co.hinge.mobile.ios')
time.sleep(3)  # espera que abra la app

size = s.window_size()
print(f"Pantalla: {size.width}x{size.height}")

# Botón inferior izquierdo (primero de 5)
# Pantalla 393px de ancho → cada botón ~78px → centro del primero en x≈40
x = 40
y = size.height - 30

print(f"Tocando: ({x}, {y})")
s.tap(x, y)
time.sleep(1)
print("Hecho")

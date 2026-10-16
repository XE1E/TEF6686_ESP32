"""Maqueta de la pantalla «Espectro» propuesta para el DP-666 (320x240, se dibuja a x3).

Datos SIMULADOS: emisoras de FM de la CDMX (cada 0.8 MHz aprox.), ruido y una apertura
de propagación que aparece a media pantalla. Sólo para discutir el diseño.
Uso: python maqueta_waterfall.py  -> maqueta_waterfall.svg (y PNG con svg2png)
"""
import math
import os
import random

random.seed(7)
S = 3                      # escala de la maqueta
W, H = 320, 240
F0, F1, PASO = 87.5, 108.0, 0.1
N = int(round((F1 - F0) / PASO)) + 1
LOCALES = [88.1, 88.9, 89.7, 90.5, 91.3, 92.1, 92.9, 93.7, 94.5, 95.3, 96.1, 96.9, 97.7, 98.5,
           99.3, 100.1, 100.9, 101.7, 102.5, 103.3, 104.1, 104.9, 105.7, 106.5, 107.3]
DX = [90.1, 95.7, 99.7]    # «apertura»: aparecen a la mitad del waterfall
FILAS = 40
CURSOR = 98.5


def nivel(f, fila):
    v = 6 + random.gauss(0, 2.5)
    for c in LOCALES:
        d = abs(f - c)
        if d < 0.25:
            v = max(v, 62 - 120 * d + random.gauss(0, 1.5) - (8 if c in (93.7, 104.9) else 0))
    if fila < FILAS // 2:
        for c in DX:
            d = abs(f - c)
            if d < 0.15:
                v = max(v, 24 - 90 * d + 6 * math.sin(fila / 2) + random.gauss(0, 2))
    return max(0, min(70, v))


def color(v):
    x = v / 70
    stops = [(0, (8, 12, 40)), (0.25, (20, 60, 160)), (0.45, (20, 170, 120)),
             (0.65, (240, 210, 40)), (0.85, (245, 120, 30)), (1, (220, 30, 40))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if x <= b:
            t = (x - a) / (b - a)
            return "#%02x%02x%02x" % tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(3))
    return "#dc1e28"


def X(f):
    return 4 + (f - F0) / (F1 - F0) * (W - 8)


def txt(x, y, s, size=11, fill="#e8edf5", w=400, anchor="start"):
    return (f'<text x="{x * S}" y="{y * S}" font-size="{size * S}" fill="{fill}" font-weight="{w}" '
            f'text-anchor="{anchor}" font-family="Segoe UI, Arial">{s}</text>')


b = f'<rect width="{W * S}" height="{H * S}" fill="#000"/>'
# Barra superior
b += txt(4, 13, "ESPECTRO  FM 87.5–108 MHz", 11, "#9fd3ff", 700)
b += txt(316, 13, "100 kHz · 1.2 s/fila", 10, "#c8d2e0", 400, "end")
# Lectura del cursor
b += txt(4, 30, f"{CURSOR:.1f} MHz", 16, "#ffffff", 700)
b += txt(118, 30, "54 dBµV · (nombre de la lista)", 11, "#ffd96a", 700)
b += txt(316, 30, "[OK] escuchar", 10, "#c8d2e0", 400, "end")
# Espectro (y = 40..110)
y0, y1 = 40, 108
b += f'<rect x="0" y="{y0 * S}" width="{W * S}" height="{(y1 - y0) * S}" fill="#05070f" stroke="#223" stroke-width="{S}"/>'
for db in (20, 40, 60):
    yy = y1 - (y1 - y0) * db / 70
    b += f'<line x1="0" y1="{yy * S}" x2="{W * S}" y2="{yy * S}" stroke="#1c2433" stroke-width="{S}"/>'
    b += txt(2, yy - 1, str(db), 8, "#7d8aa3")
puntos, picos = [], []
filas = [[nivel(F0 + i * PASO, r) for i in range(N)] for r in range(FILAS)]
for i in range(N):
    f = F0 + i * PASO
    v = filas[0][i]
    pk = max(row[i] for row in filas)
    puntos.append(f"{X(f) * S:.1f},{(y1 - (y1 - y0) * v / 70) * S:.1f}")
    picos.append(f"{X(f) * S:.1f},{(y1 - (y1 - y0) * pk / 70) * S:.1f}")
b += f'<polyline points="{" ".join(picos)}" fill="none" stroke="#5b6b8a" stroke-width="{S}" stroke-dasharray="{2 * S} {2 * S}"/>'
b += f'<polyline points="{" ".join(puntos)}" fill="none" stroke="#39d0ff" stroke-width="{1.5 * S}"/>'
# Escala de frecuencia
for f in range(88, 109, 2):
    b += f'<line x1="{X(f) * S}" y1="{y1 * S}" x2="{X(f) * S}" y2="{(y1 + 3) * S}" stroke="#7d8aa3" stroke-width="{S}"/>'
    b += txt(X(f), y1 + 12, str(f), 8, "#aab6cc", 400, "middle")
# Waterfall (y = 124..222)
wy0 = 124
alto = 2.4
for r, row in enumerate(filas):
    for i, v in enumerate(row):
        f = F0 + i * PASO
        b += (f'<rect x="{(X(f) - 0.8) * S:.1f}" y="{(wy0 + r * alto) * S:.1f}" width="{1.6 * S:.1f}" '
              f'height="{alto * S + 0.5:.1f}" fill="{color(v)}"/>')
# Cursor
b += f'<line x1="{X(CURSOR) * S}" y1="{y0 * S}" x2="{X(CURSOR) * S}" y2="{(wy0 + FILAS * alto) * S}" stroke="#ffffff" stroke-width="{S}" stroke-dasharray="{3 * S} {2 * S}"/>'
# Marca de la apertura
b += txt(X(95.7), wy0 + 6, "▼ nuevas", 8, "#ffd96a", 700, "middle")
# Botones inferiores (tocar o teclas)
ybt = 226
for k, (et, x0) in enumerate((("1 Span", 2), ("2 Paso", 66), ("3 Pico", 130), ("4 Pausa", 194), ("5 Alerta", 258))):
    b += f'<rect x="{x0 * S}" y="{ybt * S}" width="{60 * S}" height="{13 * S}" rx="{2 * S}" fill="#162038" stroke="#33507f" stroke-width="{S}"/>'
    b += txt(x0 + 30, ybt + 10, et, 9, "#dfe8f6", 700, "middle")

svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * S}" height="{H * S}" viewBox="0 0 {W * S} {H * S}">{b}</svg>'
aqui = os.path.dirname(os.path.abspath(__file__))
open(os.path.join(aqui, "maqueta_waterfall.svg"), "w", encoding="utf-8").write(svg)
print("ok")

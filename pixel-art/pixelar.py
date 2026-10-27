#!/usr/bin/env python3
"""Convierte una imagen normal en pixel art estilo consola retro (Atari, NES, Game Boy...).

Uso rápido:
    python3 pixelar.py foto.jpg --preset nes
    python3 pixelar.py foto.jpg --preset gameboy --crt
    python3 pixelar.py foto.jpg --galeria salida/      # todos los presets + hoja comparativa
    python3 pixelar.py foto.jpg --ancho 72 --paleta pico8 --dither atkinson --contorno

Etapas (cada una se puede ajustar por separado):
  1. Ajuste previo: contraste, saturación, brillo, nitidez, suavizado.
  2. Reducción: la imagen se lleva a pocos píxeles (--ancho), con píxel ancho opcional (--aspecto 2 = Atari/C64).
  3. Paleta: fija de consola (nes, gameboy, atari2600, pico8, c64, cga, zx, sms, ega) o adaptativa (--colores N),
     con límite de colores (--max-colores) y profundidad de bits de la consola (--bits 5 = SNES).
  4. Tramado (dithering): none, floyd, atkinson, sierra, bayer2, bayer4, bayer8 (--intensidad-dither).
  5. Contorno oscuro estilo sprite (--contorno).
  6. Ampliación con vecino más cercano (--escala) y efectos de pantalla: rejilla, scanlines, CRT, viñeta, curvatura.
"""
import argparse
import colorsys
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


# ---------------------------------------------------------------- paletas

def _hex(s):
    return [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in s.split()]


NES = _hex("""
7C7C7C 0000FC 0000BC 4428BC 940084 A80020 A81000 881400 503000 007800 006800 005800 004058 000000
BCBCBC 0078F8 0058F8 6844FC D800CC E40058 F83800 E45C10 AC7C00 00B800 00A800 00A844 008888
F8F8F8 3CBCFC 6888FC 9878F8 F878F8 F85898 F87858 FCA044 F8B800 B8F818 58D854 58F898 00E8D8 787878
FCFCFC A4E4FC B8B8F8 D8B8F8 F8B8F8 F8A4C0 F0D0B0 FCE0A8 F8D878 D8F878 B8F8B8 B8F8D8 00FCFC F8D8F8
""")

GAMEBOY = _hex("0F380F 306230 8BAC0F 9BBC0F")
GAMEBOY_POCKET = _hex("000000 555555 AAAAAA FFFFFF")
PICO8 = _hex("000000 1D2B53 7E2553 008751 AB5236 5F574F C2C3C7 FFF1E8 "
             "FF004D FFA300 FFEC27 00E436 29ADFF 83769C FF77A8 FFCCAA")
C64 = _hex("000000 FFFFFF 68372B 70A4B2 6F3D86 588D43 352879 B8C76F "
           "6F4F25 433900 9A6759 444444 6C6C6C 9AD284 6C5EB5 959595")
CGA = _hex("000000 55FFFF FF55FF FFFFFF")
CGA_CALIDA = _hex("000000 55FF55 FF5555 FFFF55")
ZX = _hex("000000 0000D7 D70000 D700D7 00D700 00D7D7 D7D700 D7D7D7 "
          "0000FF FF0000 FF00FF 00FF00 00FFFF FFFF00 FFFFFF")
EGA = _hex("000000 0000AA 00AA00 00AAAA AA0000 AA00AA AA5500 AAAAAA "
           "555555 5555FF 55FF55 55FFFF FF5555 FF55FF FFFF55 FFFFFF")
SMS = [(r, g, b) for r in (0, 85, 170, 255) for g in (0, 85, 170, 255) for b in (0, 85, 170, 255)]


def _atari2600():
    """Paleta NTSC del Atari 2600 (128 colores: 16 tonos x 8 luminancias), generada en YIQ (aproximada)."""
    out = []
    for hue in range(16):
        for lum in range(8):
            y = 0.06 + lum * 0.125
            if hue == 0:
                i = q = 0.0
            else:
                ang = np.deg2rad(-(hue - 1) * 25.7 + 180 + 33)
                sat = 0.20
                i, q = sat * np.cos(ang), sat * np.sin(ang)
            r = y + 0.956 * i + 0.621 * q
            g = y - 0.272 * i - 0.647 * q
            b = y - 1.106 * i + 1.703 * q
            out.append(tuple(int(np.clip(v, 0, 1) * 255) for v in (r, g, b)))
    return out


MONOCROMAS = {"gameboy", "gbpocket"}

PALETAS = {
    "nes": NES, "gameboy": GAMEBOY, "gbpocket": GAMEBOY_POCKET, "atari2600": _atari2600(),
    "pico8": PICO8, "c64": C64, "cga": CGA, "cga2": CGA_CALIDA, "zx": ZX, "ega": EGA, "sms": SMS,
}


# ---------------------------------------------------------------- color

def rgb_a_lab(rgb):
    """RGB 0-255 (…,3) -> CIELAB, para medir distancias de color como las ve el ojo."""
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def mas_cercano(pix, pal, pal_lab=None):
    """Índice del color de la paleta más cercano (en Lab) para cada píxel. pix: (N,3) float RGB."""
    if pal_lab is None:
        pal_lab = rgb_a_lab(pal)
    lab = rgb_a_lab(np.clip(pix, 0, 255))
    d = ((lab[:, None, :] - pal_lab[None, :, :]) ** 2).sum(-1)
    return d.argmin(1)


def paleta_adaptativa(img_small, n, bits=None, pesos=None):
    """N colores elegidos para esta imagen (k-means de PIL); opcionalmente encajados en la grilla de bits de la consola.
    pesos (H,W): cada píxel se repite según su peso, para que la cara reciba más colores."""
    if pesos is not None:
        px = np.asarray(img_small).reshape(-1, 3)
        px = np.repeat(px, np.maximum(1, np.round(pesos.ravel())).astype(int), axis=0)
        img_small = Image.fromarray(px[None].astype(np.uint8))
    q = img_small.quantize(colors=n, method=Image.Quantize.MAXCOVERAGE, kmeans=4)
    pal = np.array(q.getpalette()[:n * 3]).reshape(-1, 3)
    if bits:
        pal = cuantizar_bits(pal, bits)
    return np.unique(pal, axis=0)


def cuantizar_bits(arr, bits):
    """Lleva cada canal a 2**bits niveles (SNES 5 bits = 32768 colores, Genesis 3 bits = 512)."""
    niveles = 2 ** bits - 1
    return np.round(np.round(arr / 255 * niveles) / niveles * 255).astype(np.int64)


def limitar_paleta(small, pal, max_colores, pesos=None):
    """De una paleta fija grande, se queda con los max_colores más usados en esta imagen (como haría un artista).
    pesos (H,W): cuánto cuenta cada píxel; en modo retrato la cara pesa más, así sus tonos no se pierden."""
    if max_colores is None or max_colores >= len(pal):
        return pal
    idx = mas_cercano(small.reshape(-1, 3).astype(float), pal)
    conteo = np.bincount(idx, weights=None if pesos is None else pesos.ravel(), minlength=len(pal))
    # asegura el más oscuro y el más claro usados, que dan el contraste
    lum = pal @ np.array([0.299, 0.587, 0.114])
    usados = np.nonzero(conteo)[0]
    elegidos = set(np.argsort(-conteo)[:max_colores].tolist())
    elegidos |= {usados[lum[usados].argmin()], usados[lum[usados].argmax()]}
    orden = sorted(elegidos, key=lambda i: -conteo[i])[:max(max_colores, 2)]
    return pal[sorted(orden)]


# ---------------------------------------------------------------- tramado

def _bayer(n):
    m = np.array([[0, 2], [3, 1]])
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return (m + 0.5) / m.size - 0.5


DIFUSION = {
    "floyd": [(0, 1, 7 / 16), (1, -1, 3 / 16), (1, 0, 5 / 16), (1, 1, 1 / 16)],
    "atkinson": [(0, 1, 1 / 8), (0, 2, 1 / 8), (1, -1, 1 / 8), (1, 0, 1 / 8), (1, 1, 1 / 8), (2, 0, 1 / 8)],
    "sierra": [(0, 1, 2 / 4), (1, -1, 1 / 4), (1, 0, 1 / 4)],  # Sierra Lite
}


def aplicar_paleta(small, pal, dither="none", intensidad=1.0):
    """small: (H,W,3) uint8. Devuelve (H,W,3) uint8 usando solo colores de pal."""
    pal = np.asarray(pal, dtype=np.float64)
    pal_lab = rgb_a_lab(pal)
    h, w, _ = small.shape
    img = small.astype(np.float64)
    # intensidad puede ser un número o un mapa (H,W): en modo retrato la cara lleva menos tramado
    inten = np.broadcast_to(np.asarray(intensidad, dtype=np.float64), (h, w))

    if dither.startswith("bayer"):
        n = int(dither[5:])
        m = _bayer(n)
        umbral = np.tile(m, (h // n + 1, w // n + 1))[:h, :w, None]
        # el salto típico entre colores de la paleta da la amplitud del tramado
        dist = np.sqrt(((pal[:, None] - pal[None]) ** 2).sum(-1))
        dist[dist == 0] = np.inf
        paso = np.median(dist.min(1))
        img = img + umbral * paso * inten[..., None]
        idx = mas_cercano(img.reshape(-1, 3), pal, pal_lab).reshape(h, w)
        return pal[idx].astype(np.uint8)

    if dither in DIFUSION:
        reglas = DIFUSION[dither]
        out = np.zeros_like(img)
        for y in range(h):
            # recorrido serpentina: evita las "vetas" diagonales
            xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
            sgn = 1 if y % 2 == 0 else -1
            for x in xs:
                viejo = img[y, x]
                nuevo = pal[mas_cercano(viejo[None], pal, pal_lab)[0]]
                out[y, x] = nuevo
                err = (viejo - nuevo) * inten[y, x]
                for dy, dx, f in reglas:
                    yy, xx = y + dy, x + dx * sgn
                    if 0 <= yy < h and 0 <= xx < w:
                        img[yy, xx] += err * f
        return out.astype(np.uint8)

    idx = mas_cercano(img.reshape(-1, 3), pal, pal_lab).reshape(h, w)
    return pal[idx].astype(np.uint8)


# ---------------------------------------------------------------- contorno

def contorno(px, pal, umbral=60, color=None, zona=None):
    """Pinta de oscuro los bordes fuertes (diferencia de luminancia con el vecino), como el delineado de un sprite.
    zona (H,W) bool: limita el delineado a esa región (la persona, en modo retrato)."""
    lum = px.astype(float) @ np.array([0.299, 0.587, 0.114])
    borde = np.zeros(lum.shape, bool)
    dx = lum[:, 1:] - lum[:, :-1]
    dy = lum[1:, :] - lum[:-1, :]
    # marca el lado más oscuro de cada borde, para no engordar las zonas claras
    borde[:, :-1] |= dx > umbral
    borde[:, 1:] |= -dx > umbral
    borde[:-1, :] |= dy > umbral
    borde[1:, :] |= -dy > umbral
    if zona is not None:
        borde &= zona
    if color is None:
        color = mas_oscuro(pal)
    out = px.copy()
    out[borde] = color
    return out


def mas_oscuro(pal):
    pal = np.asarray(pal)
    return pal[(pal @ np.array([0.299, 0.587, 0.114])).argmin()]


def silueta(px, persona, color):
    """Delinea el borde exterior de la persona (los píxeles de fondo que la tocan), como un sprite sobre un escenario."""
    dentro = persona > 0.5
    vecino = np.zeros_like(dentro)
    vecino[1:] |= dentro[:-1]
    vecino[:-1] |= dentro[1:]
    vecino[:, 1:] |= dentro[:, :-1]
    vecino[:, :-1] |= dentro[:, 1:]
    out = px.copy()
    out[vecino & ~dentro] = color
    return out


# ---------------------------------------------------------------- modo retrato

def _opencv():
    try:
        import cv2
        return cv2
    except ImportError:
        return None


def detectar_sujeto(img):
    """Separa a la persona del fondo. Devuelve (persona, cara, caja_cara): máscaras 0-1 a resolución completa.

    Con OpenCV (pip install "opencv-python-headless<5"): detecta la cara y recorta la silueta con GrabCut,
    partiendo de la forma típica de un busto. Sin OpenCV usa esa forma de busto supuesta en el centro."""
    w, h = img.size
    cv2 = _opencv()
    bgr = np.ascontiguousarray(np.asarray(img)[..., ::-1])
    caja = None
    if cv2 is not None and hasattr(cv2, "CascadeClassifier"):
        casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        caras = casc.detectMultiScale(gris, 1.1, 5, minSize=(max(24, w // 12),) * 2)
        if len(caras):
            caja = tuple(int(v) for v in max(caras, key=lambda r: r[2] * r[3]))
    if caja is None:
        print("  aviso: no se detectó la cara (¿falta OpenCV?); se supone un retrato centrado", file=sys.stderr)
        lado = int(min(w, h) * 0.4)
        caja = ((w - lado) // 2, int(h * 0.22), lado, lado)
    x, y, fw, fh = caja
    cx, cy = x + fw / 2, y + fh / 2
    yy, xx = np.mgrid[0:h, 0:w]

    def elipse(sx, sy, dy=0.0):
        return ((xx - cx) / (fw * sx)) ** 2 + ((yy - (cy + dy * fh)) / (fh * sy)) ** 2 < 1

    # busto: cabeza ovalada + torso que se abre desde la barbilla hasta ~3 caras de ancho
    # sin GrabCut que la ajuste, la forma se dibuja más ceñida para no arrastrar fondo
    holgura = 1.0 if cv2 is not None else 0.82
    t = (yy - (y + fh * 0.8)) / (fh * 1.2)
    persona = (elipse(0.75 * holgura, 0.85 * holgura, -0.1)
               | ((t > 0) & (np.abs(xx - cx) < fw * holgura * (0.45 + 1.4 * np.clip(t, 0, 1)))))
    if cv2 is not None:
        m = np.full((h, w), cv2.GC_BGD, np.uint8)
        m[persona] = cv2.GC_PR_FGD
        m[(m == cv2.GC_BGD) & elipse(1.0, 1.1, -0.1)] = cv2.GC_PR_BGD
        m[elipse(0.35, 0.45)] = cv2.GC_FGD
        cv2.grabCut(bgr, m, None, np.zeros((1, 65)), np.zeros((1, 65)), 6, cv2.GC_INIT_WITH_MASK)
        persona = (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)
    persona = Image.fromarray(persona.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(max(1, w // 300)))
    cara = Image.fromarray(elipse(0.6, 0.75).astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(fw / 12))
    return np.asarray(persona) / 255.0, np.asarray(cara) / 255.0, caja


def tratar_fondo(img, persona, modo, color=None, ancho=64):
    """Simplifica el fondo para que la persona destaque: 'suave' (desenfoca y apaga), 'oscuro', 'plano', 'color'."""
    if modo == "original":
        return img
    bloque = img.width / ancho
    if modo == "suave":
        # desenfoca y apaga el color; el tono se lleva al contrario del borde de la persona
        # (pelo y traje oscuros -> fondo claro), para que la silueta se lea
        f = np.asarray(ImageEnhance.Color(img.filter(ImageFilter.GaussianBlur(bloque * 1.5))).enhance(0.45)).astype(float)
        lum = np.asarray(img.convert("L")).astype(float)
        borde = (persona > 0.2) & (persona < 0.8)
        claro = lum[borde].mean() < 128 if borde.any() else True
        objetivo = 175 if claro else 55
        f = objetivo + (f - f.mean()) * 0.35
        f = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
    elif modo == "oscuro":
        f = img.filter(ImageFilter.GaussianBlur(bloque * 1.5))
        f = ImageEnhance.Brightness(ImageEnhance.Color(f).enhance(0.45)).enhance(0.35)
    elif modo == "plano":
        a = np.asarray(img).reshape(-1, 3)[persona.ravel() < 0.1]
        f = Image.new("RGB", img.size, tuple(int(v) for v in np.median(a, 0) * 0.7))
    else:
        f = Image.new("RGB", img.size, _hex(color.lstrip("#"))[0] if color else (60, 188, 252))
    m = persona[..., None]
    return Image.fromarray((np.asarray(img) * m + np.asarray(f) * (1 - m)).astype(np.uint8))


def encuadrar(img, mascaras, caja, caras_de_ancho):
    """Recorta a primer plano (cabeza y hombros) para gastar los pocos píxeles en la persona."""
    x, y, fw, fh = caja
    lado = int(min(img.width, img.height, fw * caras_de_ancho))
    izq = int(np.clip(x + fw / 2 - lado / 2, 0, img.width - lado))
    arriba = int(np.clip(y - 0.55 * fh, 0, img.height - lado))
    b = (izq, arriba, izq + lado, arriba + lado)
    return img.crop(b), [m[b[1]:b[3], b[0]:b[2]] for m in mascaras]


def _reducir(m, size):
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(size, Image.BOX)) / 255.0


# ---------------------------------------------------------------- efectos de pantalla

def ampliar(px, escala, aspecto=1):
    im = Image.fromarray(px)
    return im.resize((px.shape[1] * escala * aspecto, px.shape[0] * escala), Image.NEAREST)


def rejilla(im, celda_x, celda_y, alfa=0.25):
    a = np.asarray(im).astype(float)
    a[::celda_y, :] *= 1 - alfa
    a[:, ::celda_x] *= 1 - alfa
    return Image.fromarray(a.astype(np.uint8))


def scanlines(im, periodo=3, fuerza=0.35):
    a = np.asarray(im).astype(float)
    filas = (np.arange(a.shape[0]) % periodo) == periodo - 1
    a[filas] *= 1 - fuerza
    return Image.fromarray(a.astype(np.uint8))


def crt(im, curvatura=0.08, brillo=1.15):
    """Máscara de fósforo RGB + scanlines + resplandor + viñeta + curvatura de tubo."""
    a = np.asarray(im).astype(float)
    h, w, _ = a.shape
    mascara = np.ones((h, w, 3)) * 0.65
    for c in range(3):
        mascara[:, c::3, c] = 1.0
    a = a * mascara
    a[(np.arange(h) % 3) == 2] *= 0.6
    glow = np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(max(2, w // 200)))).astype(float)
    a = np.clip(a * brillo + glow * 0.35, 0, 255)
    yy, xx = np.mgrid[0:h, 0:w]
    nx, ny = xx / w * 2 - 1, yy / h * 2 - 1
    r2 = nx ** 2 + ny ** 2
    a *= (1 - 0.35 * r2 ** 1.5).clip(0, 1)[..., None]
    if curvatura:
        f = 1 + curvatura * r2
        sx = ((nx * f + 1) / 2 * w).astype(int)
        sy = ((ny * f + 1) / 2 * h).astype(int)
        fuera = (sx < 0) | (sx >= w) | (sy < 0) | (sy >= h)
        a = a[sy.clip(0, h - 1), sx.clip(0, w - 1)]
        a[fuera] = 0
    return Image.fromarray(a.astype(np.uint8))


# ---------------------------------------------------------------- presets

PRESETS = {
    # ancho = píxeles "reales" de la consola a lo ancho del retrato
    "atari2600": dict(ancho=56, aspecto=2, paleta="atari2600", max_colores=10, dither="none",
                      contraste=1.3, saturacion=1.3, desc="Atari 2600: píxeles anchos 2:1, 10 colores NTSC"),
    "nes": dict(ancho=64, paleta="nes", max_colores=12, dither="bayer4", intensidad=0.5, contorno=True,
                contraste=1.2, saturacion=1.25, desc="NES/Famicom: paleta 2C02, 12 colores, tramado Bayer"),
    "gameboy": dict(ancho=80, paleta="gameboy", dither="bayer4", intensidad=0.5, autocontraste=True,
                    desc="Game Boy DMG: 4 verdes, tramado ordenado"),
    "gbpocket": dict(ancho=80, paleta="gbpocket", dither="floyd", intensidad=0.6, autocontraste=True,
                     desc="Game Boy Pocket: 4 grises, Floyd-Steinberg"),
    "snes": dict(ancho=120, paleta="adaptativa", colores=32, bits=5, dither="bayer2", intensidad=0.3,
                 contraste=1.1, saturacion=1.15, desc="SNES: 32 colores de 15 bits"),
    "genesis": dict(ancho=104, paleta="adaptativa", colores=16, bits=3, dither="bayer2", intensidad=0.6,
                    contraste=1.15, saturacion=1.2, desc="Sega Genesis: 16 colores de 9 bits"),
    "sms": dict(ancho=88, paleta="sms", max_colores=16, dither="bayer4", intensidad=0.5,
                contraste=1.2, saturacion=1.3, desc="Master System: 64 colores RGB222, 16 en pantalla"),
    "pico8": dict(ancho=64, paleta="pico8", dither="bayer4", intensidad=0.4, contorno=True, umbral_contorno=80,
                  contraste=1.15, saturacion=1.2, desc="PICO-8: 16 colores, contorno de sprite"),
    "c64": dict(ancho=80, aspecto=2, paleta="c64", dither="bayer4", intensidad=0.6,
                contraste=1.2, saturacion=1.0, brillo=0.85, desc="Commodore 64 multicolor: píxeles anchos, 16 colores"),
    "cga": dict(ancho=80, paleta="cga", dither="bayer4", intensidad=1.0, autocontraste=True,
                desc="PC CGA modo 4: negro, cian, magenta, blanco"),
    "zx": dict(ancho=96, paleta="zx", dither="bayer4", intensidad=0.7, contraste=1.2, saturacion=1.1,
               desc="ZX Spectrum: 15 colores, tramado ordenado"),
}


# ---------------------------------------------------------------- pipeline

def pixelar(img, ancho=64, aspecto=1, paleta="adaptativa", colores=16, max_colores=None, bits=None,
            dither="none", intensidad=1.0, contorno_on=False, umbral_contorno=60,
            contraste=1.0, saturacion=1.0, brillo=1.0, nitidez=1.0, suavizar=0, autocontraste=False, recorte=None,
            retrato=False, fondo=None, color_fondo=None, encuadre=None, silueta_on=None, **_):
    """Devuelve la imagen en su resolución "de consola" (H,W,3) uint8.

    retrato=True prioriza a la persona: fondo simplificado, más colores y nitidez para la cara,
    menos tramado sobre la piel, delineado de la silueta y del interior solo en la persona."""
    img = img.convert("RGB")
    if recorte:
        img = img.crop(recorte)
    persona = cara = None
    if retrato:
        persona, cara, caja = detectar_sujeto(img)
        if encuadre:
            img, (persona, cara) = encuadrar(img, (persona, cara), caja, encuadre)
        # piel sin textura (la mediana aplana manchas y conserva bordes) y luego nitidez a la escala del píxel
        # final, para que ojos, cejas y barba sobrevivan a la reducción
        bloque = img.width / ancho
        lisa = img.filter(ImageFilter.MedianFilter(max(3, int(bloque * 0.6) | 1)))
        nitida = np.asarray(lisa.filter(ImageFilter.UnsharpMask(radius=bloque * 0.8, percent=70, threshold=2)))
        m = np.clip(persona * 0.5 + cara, 0, 1)[..., None]
        img = Image.fromarray((nitida * m + np.asarray(img) * (1 - m)).astype(np.uint8))
        img = tratar_fondo(img, persona, fondo or "suave", color_fondo, ancho)
    if autocontraste:
        img = ImageOps.autocontrast(img, cutoff=1)  # estira el rango: clave con paletas de 4 colores
    if suavizar:
        img = img.filter(ImageFilter.MedianFilter(suavizar))
    for enh, v in ((ImageEnhance.Contrast, contraste), (ImageEnhance.Color, saturacion),
                   (ImageEnhance.Brightness, brillo), (ImageEnhance.Sharpness, nitidez)):
        if v != 1.0:
            img = enh(img).enhance(v)
    w = max(1, ancho // aspecto)
    h = max(1, round(img.height / img.width * ancho))
    small = img.resize((w, h), Image.BOX)  # promedio por bloque: menos ruido que tomar un píxel suelto
    arr = np.asarray(small)
    pesos = zona = None
    if retrato:
        persona, cara = _reducir(persona, (w, h)), _reducir(cara, (w, h))
        pesos = 1 + 3 * persona + 10 * cara
        intensidad = intensidad * (0.3 + 0.7 * persona) * (1 - 0.7 * cara)  # tramado sobre la ropa, no en piel ni fondo
        zona = persona > 0.5
        if silueta_on is None:
            silueta_on = True

    if paleta in MONOCROMAS:
        # consolas de un solo tono: se trabaja en grises y luego se tiñe con la rampa de la paleta
        rampa = np.array(sorted(PALETAS[paleta], key=lambda c: sum(c)))
        gris = np.repeat(np.asarray(small.convert("L"))[..., None], 3, -1)
        grises = np.linspace(0, 255, len(rampa)).round()[:, None].repeat(3, 1)
        px = aplicar_paleta(gris, grises, dither, intensidad)
        px = rampa[np.abs(px[..., :1] - grises[None, None, :, 0]).argmin(-1)].astype(np.uint8)
        pal = rampa
    else:
        if paleta == "adaptativa":
            pal = paleta_adaptativa(small, colores, bits, pesos)
        else:
            pal = limitar_paleta(arr, np.array(PALETAS[paleta]), max_colores, pesos)
        px = aplicar_paleta(arr, pal, dither, intensidad)
    if contorno_on:
        px = contorno(px, pal, umbral_contorno, zona=zona)
    if silueta_on and persona is not None:
        px = silueta(px, persona, mas_oscuro(pal))
    return px


def salida(px, escala=8, aspecto=1, grid=False, lineas=False, efecto_crt=False):
    im = ampliar(px, escala, aspecto)
    if grid:
        im = rejilla(im, escala * aspecto, escala)
    if lineas:
        im = scanlines(im, max(2, escala // 2))
    if efecto_crt:
        im = crt(im)
    return im


def config(args, preset=None):
    c = dict(PRESETS.get(preset, {})) if preset else {}
    for k in ("ancho", "aspecto", "paleta", "colores", "max_colores", "bits", "dither", "intensidad",
              "contraste", "saturacion", "brillo", "nitidez", "suavizar", "umbral_contorno"):
        v = getattr(args, k)
        if v is not None:
            c[k] = v
    c["autocontraste"] = args.autocontraste or c.get("autocontraste", False)
    c["contorno_on"] = args.contorno or c.pop("contorno", False)
    c.update(retrato=args.retrato, fondo=args.fondo, color_fondo=args.color_fondo, encuadre=args.encuadre,
             silueta_on=False if args.sin_silueta else None)
    c.setdefault("aspecto", 1)
    return c


def galeria(img, carpeta, args):
    os.makedirs(carpeta, exist_ok=True)
    tam = 480
    fichas = [("original", img.convert("RGB").resize((tam, round(img.height / img.width * tam)), Image.LANCZOS))]
    for nombre in PRESETS:
        c = config(args, nombre)
        px = pixelar(img, **c)
        escala = max(1, tam // px.shape[1] // c["aspecto"])
        im = salida(px, escala, c["aspecto"])
        im.save(os.path.join(carpeta, f"{nombre}.png"))
        salida(px, max(1, 960 // px.shape[1] // c["aspecto"]), c["aspecto"], efecto_crt=True).save(os.path.join(carpeta, f"{nombre}_crt.png"))
        fichas.append((nombre, im.resize((tam, round(im.height / im.width * tam)), Image.NEAREST)))
        print(f"  {nombre:10s} {px.shape[1]}x{px.shape[0]} px, {len(np.unique(px.reshape(-1, 3), axis=0))} colores")
    # hoja comparativa
    cols, pad, rot = 4, 16, 28
    filas = -(-len(fichas) // cols)
    alto = max(f[1].height for f in fichas)
    hoja = Image.new("RGB", (cols * (tam + pad) + pad, filas * (alto + rot + pad) + pad), (18, 18, 24))
    d = ImageDraw.Draw(hoja)
    try:
        fuente = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 18)
    except OSError:
        fuente = ImageFont.load_default()
    for i, (nombre, im) in enumerate(fichas):
        x = pad + (i % cols) * (tam + pad)
        y = pad + (i // cols) * (alto + rot + pad)
        hoja.paste(im, (x, y + rot))
        d.text((x, y + 2), nombre.upper(), fill=(240, 240, 240), font=fuente)
    hoja.save(os.path.join(carpeta, "_comparativa.png"))
    print(f"  hoja comparativa: {os.path.join(carpeta, '_comparativa.png')}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada")
    p.add_argument("-o", "--salida", help="archivo PNG de salida (por defecto <entrada>_<preset>.png)")
    p.add_argument("--preset", choices=sorted(PRESETS), help="estilo de consola listo para usar")
    p.add_argument("--galeria", metavar="CARPETA", help="genera todos los presets y una hoja comparativa")
    p.add_argument("--listar", action="store_true", help="muestra presets y paletas")
    g = p.add_argument_group("resolución")
    g.add_argument("--ancho", type=int, help="píxeles de ancho de la versión retro (p. ej. 32 a 160)")
    g.add_argument("--aspecto", type=int, help="2 = píxeles anchos (Atari 2600, C64 multicolor)")
    g.add_argument("--escala", type=int, help="tamaño final de cada píxel en pantalla (por defecto llena ~600 px)")
    g = p.add_argument_group("color")
    g.add_argument("--paleta", choices=["adaptativa"] + sorted(PALETAS))
    g.add_argument("--colores", type=int, help="nº de colores de la paleta adaptativa")
    g.add_argument("--max-colores", type=int, help="usa solo los N colores más útiles de una paleta fija")
    g.add_argument("--bits", type=int, help="bits por canal de la consola (5 = SNES, 3 = Genesis, 2 = SMS)")
    g.add_argument("--dither", choices=["none", "floyd", "atkinson", "sierra", "bayer2", "bayer4", "bayer8"])
    g.add_argument("--intensidad", type=float, help="fuerza del tramado, 0 a 1.5")
    g = p.add_argument_group("ajuste previo")
    for k in ("contraste", "saturacion", "brillo", "nitidez"):
        g.add_argument(f"--{k}", type=float, help="1.0 = sin cambio")
    g.add_argument("--autocontraste", action="store_true", help="estira luces y sombras al rango completo")
    g.add_argument("--suavizar", type=int, help="filtro de mediana impar (3, 5) para quitar textura de piel/ruido")
    g = p.add_argument_group("estilo")
    g.add_argument("--contorno", action="store_true", help="delineado oscuro tipo sprite")
    g.add_argument("--umbral-contorno", type=int, help="sensibilidad del delineado (menor = más líneas)")
    g = p.add_argument_group("modo retrato (que se aprecie más la persona)")
    g.add_argument("--retrato", action="store_true",
                   help="detecta a la persona: fondo simple, más colores y nitidez en la cara, silueta delineada")
    g.add_argument("--fondo", choices=["suave", "oscuro", "plano", "color", "original"],
                   help="tratamiento del fondo en modo retrato (por defecto suave)")
    g.add_argument("--color-fondo", help="color hex para --fondo color, p. ej. 3CBCFC (cielo NES)")
    g.add_argument("--encuadre", type=float, help="recorta a primer plano: ancho del cuadro en caras (p. ej. 2.5)")
    g.add_argument("--sin-silueta", action="store_true", help="no delinear el borde de la persona")
    g = p.add_argument_group("pantalla")
    g.add_argument("--rejilla", action="store_true", help="dibuja la cuadrícula de píxeles")
    g.add_argument("--scanlines", action="store_true", help="líneas horizontales de TV")
    g.add_argument("--crt", action="store_true", help="simula un televisor de tubo")
    g.add_argument("--nativo", action="store_true", help="guarda también la versión sin ampliar (1 píxel = 1 píxel)")
    args = p.parse_args()

    if args.listar:
        for k, v in PRESETS.items():
            print(f"{k:10s} {v['desc']}")
        print("\npaletas:", ", ".join(f"{k} ({len(v)})" for k, v in PALETAS.items()))
        return

    img = Image.open(args.entrada)
    if args.galeria:
        galeria(img, args.galeria, args)
        return

    c = config(args, args.preset)
    px = pixelar(img, **c)
    escala = args.escala or max(1, 600 // px.shape[1] // c["aspecto"])
    im = salida(px, escala, c["aspecto"], args.rejilla, args.scanlines, args.crt)
    destino = args.salida or f"{os.path.splitext(args.entrada)[0]}_{args.preset or 'pixel'}.png"
    im.save(destino)
    if args.nativo:
        Image.fromarray(px).save(os.path.splitext(destino)[0] + "_nativo.png")
    print(f"{destino}: {px.shape[1]}x{px.shape[0]} px retro, "
          f"{len(np.unique(px.reshape(-1, 3), axis=0))} colores, ampliado a {im.width}x{im.height}")


if __name__ == "__main__":
    sys.exit(main())

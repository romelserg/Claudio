"""Renderiza la historia de Instagram (1080x1920, 15 s, 30 fps) a partir de layers.npz y stats.json.

Uso: python 03_render.py <dir_datos> <dir_fuentes> <salida.mp4> [--preview]
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DATA, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
PREVIEW = "--preview" in sys.argv
# Borrador: capa de peligro de prueba -> se ocultan sus cifras y se marca el video.
DRAFT = "--draft" in sys.argv

W, H, FPS, DUR = 1080, 1920, 30, 15.0
N = int(FPS * DUR)

# Paleta (validada sobre superficie oscura #0A0E13).
BG = (10, 14, 19)
INK = (236, 240, 243)
INK2 = (160, 170, 180)
MUTED = (100, 112, 124)
NEW = (22, 163, 150)      # edificación nueva 2016-2023
ALTA = (168, 140, 20)     # susceptibilidad alta (con trama)
MALTA = (224, 54, 79)     # susceptibilidad muy alta
OLD = (196, 204, 212)     # edificación existente

HANDLE = "@sieteborreguitos"

# Layout (zonas seguras de stories: ~220 px arriba y ~280 px abajo libres de texto crítico).
MAP_Y, MAP_H = 540, 720
PANEL_Y = MAP_Y + MAP_H + 30


# ---------- tipografía ----------
def font(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if wght is not None:
        try:
            f.set_variation_by_axes([wght] if "opsz" not in name else [min(max(size, 14), 32), wght])
        except Exception:
            pass
    return f


def SG(size, w=700):
    return font("SpaceGrotesk[wght].ttf", size, w)


def MONO(size, bold=False):
    return font("IBMPlexMono-Medium.ttf" if bold else "IBMPlexMono-Regular.ttf", size)


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def seg(t, a, b):
    return clamp((t - a) / (b - a))


# ---------- datos ----------
L = np.load(os.path.join(DATA, "layers.npz"))
S = json.load(open(os.path.join(DATA, "stats.json")))
hs = L["hs"].astype(np.float32)
B = L["b"].astype(np.float32)          # (8, h, w) presencia 2016..2023
hz = L["hz"]
ids = L["ids"]
names = list(L["names"])
gh, gw = hs.shape

b_ini = (B[0] + B[1]) / 2
built_ini = b_ini >= 0.5

# Encuadre: ventana de la ciudad en píxeles de la grilla (5 m), con proporción del mapa.
ASPECT = W / MAP_H
CX, CY = 2780, 1700           # centro aprox. (Huatanay, entre Wanchaq y San Sebastián)
CAM0 = 3300                   # ancho inicial (px de grilla = 16.5 km)
CAM1 = 2500                   # ancho final (12.5 km)


def cam(t):
    w = CAM0 + (CAM1 - CAM0) * ease(t / DUR)
    cx = CX + 120 * ease(seg(t, 6.5, 11))
    return cx, CY, w


# Pre-recorte a la ventana más amplia y submuestreo 2x de la salida para componer rápido.
PAD = 200
X0 = int(CX - CAM0 / 2 - PAD)
X1 = int(CX + CAM0 / 2 + PAD + 240)
Y0 = int(CY - CAM0 / ASPECT / 2 - PAD)
Y1 = int(CY + CAM0 / ASPECT / 2 + PAD)
X0, Y0 = max(X0, 0), max(Y0, 0)
X1, Y1 = min(X1, gw), min(Y1, gh)


def crop(a):
    return a[..., Y0:Y1, X0:X1]


hs_c = crop(hs)
B_c = crop(B)
hz_c = crop(hz)
ids_c = crop(ids)
bini_c = crop(built_ini)
ch, cw = hs_c.shape

# Base de relieve: hillshade oscuro + leve tinte por pendiente.
relief = (0.10 + 0.55 * hs_c ** 1.4)
base_rgb = np.stack([relief * 0.20, relief * 0.25, relief * 0.30], -1) * 255 + np.array(BG) * 0.6

# Trama diagonal para "alta" (codificación secundaria, no solo color).
yy, xx = np.mgrid[0:ch, 0:cw]
hatch = (((xx + yy) // 6) % 3 == 0).astype(np.float32)

# Contornos distritales.
edge = np.zeros_like(ids_c, dtype=bool)
edge[:-1, :] |= ids_c[:-1, :] != ids_c[1:, :]
edge[:, :-1] |= ids_c[:, :-1] != ids_c[:, 1:]
edge = np.array(Image.fromarray(edge.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) / 255.0

# Contorno de zonas alta+muy alta.
high_c = hz_c >= 4
hedge = np.zeros_like(high_c)
hedge[:-1, :] |= high_c[:-1, :] != high_c[1:, :]
hedge[:, :-1] |= high_c[:, :-1] != high_c[:, 1:]
hedge = np.array(Image.fromarray(hedge.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) / 255.0

# Crecimiento neto por celdas de 80 m (16x16 px): más robusto que comparar píxel a píxel.
CELL = 16
chc, cwc = ch // CELL, cw // CELL


def cellfrac(a):
    a = (a[: chc * CELL, : cwc * CELL] >= 0.5).astype(np.float32)
    return a.reshape(chc, CELL, cwc, CELL).mean((1, 3))


f_ini = cellfrac((B_c[0] + B_c[1]) / 2)
cell_mask = np.zeros((ch, cw), np.float32)
yy2, xx2 = np.mgrid[0:CELL, 0:CELL]
dot = ((yy2 >= 1) & (yy2 <= CELL - 2) & (xx2 >= 1) & (xx2 <= CELL - 2)).astype(np.float32)
dot_tile = np.tile(dot, (chc, cwc))


def new_cells(fr):
    """Celdas que suman ≥ 8 puntos de cobertura edificada respecto a 2016-17 (pleno a ≥ 18)."""
    g = np.clip((fr - f_ini - 0.05) / 0.13, 0, 1) * (fr - f_ini >= 0.08)
    up = np.kron(g, np.ones((CELL, CELL), np.float32)) * dot_tile
    out = np.zeros((ch, cw), np.float32)
    out[: chc * CELL, : cwc * CELL] = up
    return out


new_by_year = [np.zeros((ch, cw), np.float32)]
for k in range(1, 8):
    pair = (B_c[k - 1] + B_c[k]) / 2 if k < 7 else (B_c[6] + B_c[7]) / 2
    new_by_year.append(new_cells(cellfrac(pair)))
new_final = new_by_year[7]


def lerp_year(t):
    """Fracción continua del año 2016..2023 durante la escena 2."""
    return 2016 + 7 * ease(seg(t, 2.6, 6.6))


def compose(t):
    rgb = base_rgb.copy()
    # Edificación existente
    a_old = ease(seg(t, 0.2, 1.6)) * np.clip(B_c[0] * 1.2, 0, 1)
    rgb = rgb * (1 - a_old[..., None] * 0.85) + np.array(OLD) * (a_old[..., None] * 0.85)

    # Peligro (escena 3 en adelante)
    a_hz = ease(seg(t, 7.0, 8.2))
    if a_hz > 0:
        m_alta = (hz_c == 4).astype(np.float32)
        m_malta = (hz_c == 5).astype(np.float32)
        a1 = a_hz * (0.10 + 0.40 * hatch) * m_alta
        a2 = a_hz * 0.36 * m_malta
        rgb = rgb * (1 - a1[..., None]) + np.array(ALTA) * a1[..., None]
        rgb = rgb * (1 - a2[..., None]) + np.array(MALTA) * a2[..., None]
        ae = a_hz * 0.9 * hedge
        rgb = rgb * (1 - ae[..., None]) + np.array(MALTA) * ae[..., None]

    # Edificación nueva (aparece año a año)
    yr = lerp_year(t)
    if yr > 2016:
        k = min(int(yr) - 2016, 7)
        frac = yr - int(yr)
        cur = new_by_year[k]
        if k < 7:
            cur = cur * (1 - frac) + new_by_year[k + 1] * frac
        if t > 6.6:
            cur = new_final
        a_new = np.clip(cur, 0, 1)
        col = np.broadcast_to(np.array(NEW, np.float32), rgb.shape)
        if t > 8.0:
            # Tras mostrar el peligro, resalta lo nuevo dentro de alta/muy alta.
            k8 = ease(seg(t, 8.0, 9.0))
            a_new = a_new * (1 - 0.6 * k8 * (~high_c))
            col = np.where(high_c[..., None], np.array(NEW) + (np.array(INK) - np.array(NEW)) * 0.35 * k8, col)
        rgb = rgb * (1 - a_new[..., None]) + col * a_new[..., None]

    # Límites distritales
    a_e = 0.22 * ease(seg(t, 0.8, 2.0)) + 0.25 * ease(seg(t, 10.8, 11.6))
    rgb = rgb * (1 - edge[..., None] * a_e) + np.array(INK) * (edge[..., None] * a_e)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def map_frame(t):
    rgb = compose(t)
    cx, cy, w = cam(t)
    h = w / ASPECT
    box = (cx - w / 2 - X0, cy - h / 2 - Y0, cx + w / 2 - X0, cy + h / 2 - Y0)
    img = Image.fromarray(rgb).resize((W, MAP_H), Image.LANCZOS, box=box)
    # Brillo suave para lo nuevo: glow aditivo
    return img, box, w


def to_screen(px, py, box):
    x0, y0, x1, y1 = box
    return ((px - X0 - x0) / (x1 - x0) * W, MAP_Y + (py - Y0 - y0) / (y1 - y0) * MAP_H)


# Centroides de distritos (en píxeles de la grilla completa).
CENT = {}
for i, n in enumerate(names):
    ys, xs = np.nonzero(ids == i + 1)
    if len(xs):
        CENT[n] = (np.median(xs), np.median(ys))
LABEL_NUDGE = {"Cusco": (-140, -120), "Wanchaq": (0, 0), "Santiago": (-120, 90),
               "San Sebastián": (0, -100), "San Jerónimo": (80, -60), "Saylla": (0, 0),
               "Poroy": (0, 0), "Ccorca": (0, 0)}


def fmt(n):
    return f"{n:,.0f}".replace(",", " ")


def text(d, xy, s, f, fill, anchor="la", alpha=1.0):
    if alpha <= 0:
        return
    c = tuple(int(BG[i] + (fill[i] - BG[i]) * alpha) for i in range(3))
    d.text(xy, s, font=f, fill=c, anchor=anchor)


def draw_frame(fi):
    t = fi / FPS
    im = Image.new("RGB", (W, H), BG)
    mp, box, camw = map_frame(t)
    im.paste(mp, (0, MAP_Y))
    d = ImageDraw.Draw(im)

    # Marco técnico del mapa
    a_ui = ease(seg(t, 0.3, 1.2))
    lc = tuple(int(BG[i] + (MUTED[i] - BG[i]) * a_ui) for i in range(3))
    for (x, y, dx, dy) in [(24, MAP_Y + 16, 1, 1), (W - 24, MAP_Y + 16, -1, 1),
                           (24, MAP_Y + MAP_H - 16, 1, -1), (W - 24, MAP_Y + MAP_H - 16, -1, -1)]:
        d.line([(x, y), (x + 28 * dx, y)], fill=lc, width=2)
        d.line([(x, y), (x, y + 28 * dy)], fill=lc, width=2)
    # Escala gráfica (1 km)
    km_px = 200 / (camw * 5) * W
    sx, sy = 48, MAP_Y + MAP_H - 44
    d.line([(sx, sy), (sx + km_px, sy)], fill=lc, width=3)
    d.line([(sx, sy - 7), (sx, sy + 7)], fill=lc, width=2)
    d.line([(sx + km_px, sy - 7), (sx + km_px, sy + 7)], fill=lc, width=2)
    text(d, (sx + km_px + 12, sy), "1 km", MONO(20), INK2, "lm", a_ui)
    # Norte
    nx, ny = W - 60, MAP_Y + 64
    d.polygon([(nx, ny - 22), (nx - 10, ny + 8), (nx, ny + 2), (nx + 10, ny + 8)], fill=lc)
    text(d, (nx, ny + 28), "N", MONO(20, True), INK2, "mm", a_ui)
    text(d, (W - 48, MAP_Y + MAP_H - 44), "13°31'S · 71°58'O", MONO(20), INK2, "rm", a_ui)

    # Etiquetas de distritos
    a_lab = ease(seg(t, 1.0, 2.0)) * (1 - 0.6 * ease(seg(t, 7.0, 8.0))) + 0.6 * ease(seg(t, 10.8, 11.6))
    for n in ("Cusco", "Santiago", "Wanchaq", "San Sebastián", "San Jerónimo"):
        if n not in CENT:
            continue
        px, py = CENT[n]
        nx_, ny_ = LABEL_NUDGE.get(n, (0, 0))
        x, y = to_screen(px + nx_, py + ny_, box)
        if 40 < x < W - 40 and MAP_Y + 40 < y < MAP_Y + MAP_H - 70:
            text(d, (x, y), n.upper(), MONO(20, True), INK, "mm", clamp(a_lab))

    # ---------- Cabecera ----------
    a_h = ease_out(seg(t, 0.0, 0.8))
    text(d, (56, 236), "CUSCO · URBANISMO Y RIESGO", MONO(24, True), NEW, "la", a_h)
    title_y = 280 + 24 * (1 - a_h)
    text(d, (54, title_y), "El Niño 2026–27", SG(84, 700), INK, "la", a_h)
    text(d, (54, title_y + 98), "y una ciudad que sube por las laderas", SG(42, 500), INK2, "la", a_h)

    # ---------- Paneles por escena ----------
    px0 = 56
    # Escena 1: estado ENFEN (0.4–2.6 s)
    a1 = ease(seg(t, 0.5, 1.1)) * (1 - ease(seg(t, 2.4, 2.8)))
    if a1 > 0:
        r = (px0, PANEL_Y, W - 56, PANEL_Y + 190)
        oc = tuple(int(BG[i] + (MALTA[i] - BG[i]) * a1) for i in range(3))
        d.rectangle(r, outline=oc, width=2)
        text(d, (px0 + 26, PANEL_Y + 26), "ENFEN · ALERTA DE EL NIÑO COSTERO", MONO(26, True), MALTA, "la", a1)
        text(d, (px0 + 26, PANEL_Y + 74), "Magnitud más probable: extraordinaria", SG(38, 600), INK, "la", a1)
        text(d, (px0 + 26, PANEL_Y + 122), "(Niño 1+2) · se extendería hasta el otoño 2027", SG(30, 400), INK2, "la", a1)

    # Escena 2: crecimiento (2.6–7 s)
    a2 = ease(seg(t, 2.7, 3.2)) * (1 - ease(seg(t, 6.8, 7.2)))
    if a2 > 0:
        yr = lerp_year(t)
        ini, fin = S["edificado_ha_2016_17"], S["edificado_ha_2022_23"]
        ser = S["edificado_ha_serie"]
        y0 = min(int(yr), 2022)
        fr = yr - y0
        cur = ser[str(y0)] * (1 - fr) + ser[str(y0 + 1)] * fr
        ini = ser["2016"]
        text(d, (px0, PANEL_Y), f"{int(yr)}", MONO(30, True), NEW, "la", a2)
        text(d, (px0, PANEL_Y + 40), f"+{fmt(cur - ini)} ha", SG(104, 700), INK, "la", a2)
        text(d, (px0, PANEL_Y + 160), "de nueva superficie edificada", SG(34, 500), INK2, "la", a2)
        text(d, (px0, PANEL_Y + 204), f"(+{(cur / ini - 1) * 100:.0f} % desde 2016)", SG(30, 400), INK2, "la", a2)
        # Leyenda
        ly = MAP_Y - 34
        d.rectangle((px0, ly - 10, px0 + 20, ly + 10), fill=tuple(int(BG[i] + (NEW[i] - BG[i]) * a2) for i in range(3)))
        text(d, (px0 + 32, ly), "Nuevo 2016→2023", MONO(22), INK2, "lm", a2)
        d.rectangle((px0 + 300, ly - 10, px0 + 320, ly + 10), fill=tuple(int(BG[i] + (OLD[i] - BG[i]) * a2) for i in range(3)))
        text(d, (px0 + 332, ly), "Existente 2016", MONO(22), INK2, "lm", a2)

    # Escena 3: peligro (7–11 s)
    a3 = ease(seg(t, 7.3, 7.9)) * (1 - ease(seg(t, 10.6, 11.0)))
    if a3 > 0:
        pct = S["crecimiento_neto_en_alta_muy_alta_pct"] * ease_out(seg(t, 7.4, 8.8))
        text(d, (px0, PANEL_Y + 6), "XX %" if DRAFT else f"{pct:.0f} %", SG(120, 700), MALTA, "la", a3)
        text(d, (px0 + 300, PANEL_Y + 30), "del crecimiento ocurrió", SG(34, 500), INK, "la", a3)
        text(d, (px0 + 300, PANEL_Y + 72), "en zonas de susceptibilidad", SG(34, 500), INK, "la", a3)
        text(d, (px0 + 300, PANEL_Y + 114), "ALTA o MUY ALTA a", SG(34, 700), INK, "la", a3)
        text(d, (px0 + 300, PANEL_Y + 156), "movimientos en masa", SG(34, 500), INK, "la", a3)
        ly = MAP_Y - 34
        # Leyenda con trama para "alta"
        sw = Image.new("RGB", (20, 20), BG)
        sd = ImageDraw.Draw(sw)
        for k in range(-20, 40, 6):
            sd.line([(k, 20), (k + 20, 0)], fill=ALTA, width=2)
        im.paste(Image.blend(Image.new("RGB", (20, 20), BG), sw, a3), (px0, ly - 10))
        text(d, (px0 + 32, ly), "Alta", MONO(22), INK2, "lm", a3)
        d.rectangle((px0 + 120, ly - 10, px0 + 140, ly + 10), fill=tuple(int(BG[i] + (MALTA[i] - BG[i]) * a3) for i in range(3)))
        text(d, (px0 + 152, ly), "Muy alta", MONO(22), INK2, "lm", a3)
        d.rectangle((px0 + 300, ly - 10, px0 + 320, ly + 10), fill=tuple(int(BG[i] + (NEW[i] - BG[i]) * a3) for i in range(3)))
        text(d, (px0 + 332, ly), "Nuevo 2016→2023", MONO(22), INK2, "lm", a3)

    # Escena 4: población por distrito (11–14.2 s)
    a4 = ease(seg(t, 11.0, 11.5)) * (1 - ease(seg(t, 14.0, 14.3)))
    if a4 > 0:
        tot = S["poblacion_2017_en_alta_muy_alta"]
        text(d, (px0, PANEL_Y - 6), "≈ XX XXX" if DRAFT else f"≈ {fmt(tot * ease_out(seg(t, 11.1, 12.3)))}",
             SG(76, 700), INK, "la", a4)
        text(d, (px0, PANEL_Y + 80), "habitantes viven sobre suelo de susceptibilidad alta o muy alta", SG(25, 500), INK2, "la", a4)
        dist = sorted(S["distritos"].items(), key=lambda kv: -kv[1]["pob_alta_muy_alta"])[:5]
        mx = max(v["pob_alta_muy_alta"] for _, v in dist) or 1
        by = PANEL_Y + 124
        for j, (n, v) in enumerate(dist):
            g = ease_out(seg(t, 11.4 + j * 0.12, 12.4 + j * 0.12))
            y = by + j * 30
            text(d, (px0, y + 12), n, MONO(21), INK2, "lm", a4)
            bw = (W - 56 - 280 - 150) * v["pob_alta_muy_alta"] / mx * g
            if bw > 2:
                c = tuple(int(BG[i] + (MALTA[i] - BG[i]) * a4) for i in range(3))
                d.rounded_rectangle((px0 + 250, y + 2, px0 + 250 + bw, y + 22), radius=4, fill=c)
            lab = "XX XXX · XX %" if DRAFT else f"{fmt(v['pob_alta_muy_alta'])} · {v['pob_alta_muy_alta_pct']:.0f} %"
            text(d, (px0 + 262 + bw, y + 12), lab, MONO(20), INK, "lm", a4 * g)

    # Escena 5: cierre (14–15 s)
    a5 = ease(seg(t, 14.1, 14.5))
    if a5 > 0:
        text(d, (W / 2, PANEL_Y + 70), HANDLE, SG(64, 700), INK, "mm", a5)
        text(d, (W / 2, PANEL_Y + 130), "Datos abiertos · mapas urbanos", MONO(24), INK2, "mm", a5)

    # ---------- Pie: firma y fuentes (siempre visible) ----------
    fy = 1636
    text(d, (56, fy), HANDLE, MONO(22, True), INK, "la", a_h)
    src = [
        "Fuentes: ENFEN Com. Of. 16-2026 · INGEMMET/CENEPRED susceptibilidad",
        "Google Open Buildings 2.5D Temporal (2016–23) · INEI Censo 2017",
        "Copernicus DEM GLO-30 · Límites: Overture Maps / OSM",
    ]
    for k, s in enumerate(src):
        text(d, (56, fy + 32 + k * 24), s, MONO(17), MUTED, "la", a_h)
    if DRAFT:
        wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        wd = ImageDraw.Draw(wm)
        wd.text((W / 2, MAP_Y + MAP_H / 2), "BORRADOR · PELIGRO DE PRUEBA, NO OFICIAL", font=MONO(34, True),
                fill=(255, 255, 255, 150), anchor="mm")
        im = Image.alpha_composite(im.convert("RGBA"), wm).convert("RGB")
    return im


def main():
    if PREVIEW:
        for t in (1.5, 5.0, 9.5, 12.8, 14.7):
            draw_frame(int(t * FPS)).save(OUT.replace(".mp4", f"_t{t:04.1f}.png"))
        return
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(N):
        p.stdin.write(draw_frame(fi).tobytes())
        if fi % 30 == 0:
            print("frame", fi, flush=True)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    main()

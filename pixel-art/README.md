# Pixel art retro

`pixelar.py` convierte una foto en pixel art con la estética de consolas clásicas
(Atari 2600, NES, Game Boy, SNES, Genesis, Master System, PICO-8, C64, CGA, ZX Spectrum).
Solo necesita Python 3, Pillow y NumPy.

```bash
python3 pixelar.py foto.jpg --listar                  # presets y paletas
python3 pixelar.py foto.jpg --preset nes              # un estilo
python3 pixelar.py foto.jpg --preset gameboy --crt    # con efecto de televisor de tubo
python3 pixelar.py foto.jpg --galeria salida/         # todos los estilos + hoja comparativa
python3 pixelar.py foto.jpg --ancho 48 --paleta pico8 --dither none --contorno --suavizar 5 --nativo
```

## Herramientas incluidas

| Etapa | Opciones |
|---|---|
| Ajuste previo | `--contraste --saturacion --brillo --nitidez` (1.0 = igual), `--autocontraste`, `--suavizar 3/5` (quita textura de piel) |
| Resolución | `--ancho` (píxeles reales, 32–160), `--aspecto 2` (píxel ancho de Atari/C64), `--escala` (tamaño de cada píxel al ampliar) |
| Paleta | fijas: `nes atari2600 gameboy gbpocket pico8 c64 cga cga2 zx ega sms`; `adaptativa` con `--colores N`; `--max-colores N` (usa solo los N más útiles de una paleta fija); `--bits` (5 = SNES, 3 = Genesis) |
| Tramado | `--dither none floyd atkinson sierra bayer2 bayer4 bayer8`, `--intensidad 0–1.5` |
| Estilo sprite | `--contorno` (delineado oscuro), `--umbral-contorno` |
| Pantalla | `--rejilla`, `--scanlines`, `--crt` (máscara RGB, resplandor, viñeta, curvatura), `--nativo` (guarda también la versión 1:1) |

Los colores se comparan en CIELAB (como los percibe el ojo), la reducción promedia cada bloque
y el recorrido de Floyd/Atkinson es en serpentina para evitar vetas.

Ejemplo: `entrada/retrato.png` → `salida/` (`_comparativa.png` reúne todos los estilos; `*_crt.png` con efecto TV).

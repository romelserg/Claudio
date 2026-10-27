# Pixel art retro

`pixelar.py` convierte una foto en pixel art con la estética de consolas clásicas
(Atari 2600, NES, Game Boy, SNES, Genesis, Master System, PICO-8, C64, CGA, ZX Spectrum).
Necesita Python 3, Pillow y NumPy. Para el modo retrato conviene además OpenCV
(`pip install -r requirements.txt`); sin él funciona igual, pero recorta a la persona con una forma aproximada.

```bash
python3 pixelar.py foto.jpg --listar                  # presets y paletas
python3 pixelar.py foto.jpg --preset nes              # un estilo
python3 pixelar.py foto.jpg --preset gameboy --crt    # con efecto de televisor de tubo
python3 pixelar.py foto.jpg --galeria salida/         # todos los estilos + hoja comparativa
python3 pixelar.py foto.jpg --preset nes --retrato    # que la persona destaque
python3 pixelar.py foto.jpg --galeria salida/ --retrato
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
| Modo retrato | `--retrato`: detecta la cara y recorta la silueta (GrabCut); `--fondo suave/oscuro/plano/color/original`, `--color-fondo 3CBCFC`, `--encuadre 2.5` (primer plano, ancho en caras), `--sin-silueta` |
| Pantalla | `--rejilla`, `--scanlines`, `--crt` (máscara RGB, resplandor, viñeta, curvatura), `--nativo` (guarda también la versión 1:1) |

Los colores se comparan en CIELAB (como los percibe el ojo), la reducción promedia cada bloque
y el recorrido de Floyd/Atkinson es en serpentina para evitar vetas.

## Modo retrato

Con pocos píxeles la cara compite con el fondo por los colores y el detalle. `--retrato`:

1. detecta la cara y separa a la persona del fondo;
2. simplifica el fondo (desenfocado, sin color y con el tono contrario al borde de la persona: pelo y traje
   oscuros → fondo claro), o lo reemplaza por un color liso;
3. alisa la textura de la piel y aplica nitidez a la escala del píxel final (ojos, cejas, barba);
4. reparte la paleta dando más peso a la cara, así sus tonos no se pierden;
5. quita el tramado de la piel y del fondo (queda solo en la ropa);
6. delinea la silueta y limita el contorno interior a la persona, como un sprite.

Para aún más detalle en la cara: `--encuadre 2` (primer plano) o un `--ancho` mayor (p. ej. 96 en NES).

Ejemplo: `entrada/retrato.png` → `salida/` (`_comparativa.png` reúne todos los estilos; `*_crt.png` con efecto TV; `_antes_despues.png` compara sin y con `--retrato`).

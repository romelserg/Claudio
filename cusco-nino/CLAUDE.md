# Contexto del proyecto (para Claude Code)

Historia de Instagram (MP4 1080×1920, 20 s, 30 fps) para **@sieteborreguitos**: *El fenómeno del Niño
2026–27: susceptibilidad a huaycos y deslizamientos* en la ciudad del Cusco. Enfoque de urbanismo,
estilo oscuro y técnico. Requisito del autor: **solo datos corroborados y serios, con fuentes citadas**.

## Estructura

- `scripts/01_download.py`: descarga y lleva a una grilla común (UTM 19S, 5 m) el Copernicus DEM, Google Open Buildings
  2.5D Temporal (2016–2023, overview de 4 m) y los límites de Overture. Escribe en `datos/`.
- `scripts/02_analysis.py <datos> <peligro.zip|.tif>`: cruza las capas y escribe `stats.json` (las cifras del video)
  y `layers.npz` (las capas para el render).
- `scripts/03_render.py <datos> <fonts> <salida.mp4> [--preview]`: genera el video fotograma a fotograma con PIL y
  lo pasa a ffmpeg (libx264). `--preview` saca 5 PNG de control en segundos.
- `run.sh`: atajos (`./run.sh analisis`, `./run.sh preview`, `./run.sh video`).
- `data/MOVIMIENTOS EN MASA  INGEMMET geogpsperu.zip`: capa oficial de peligro (ver abajo).
- `README.md`: método, resultados, sensibilidad y limitaciones (es la nota metodológica pública).

## Decisiones ya tomadas con el autor (no cambiar sin consultar)

- **Zona crítica** = susceptibilidad INGEMMET alta o muy alta (clases 4–5) **y** pendiente ≥ 20° (Copernicus DEM,
  suavizado a ~30 m). El mapa INGEMMET (2010) es de escala 1:2 000 000, con celdas de 200 m; usado solo,
  marca como "alta" hasta la pampa plana de Wanchaq (≈307 000 habitantes, una cifra alarmista).
  El autor eligió el criterio combinado.
- Clases del ráster INGEMMET: 1 = muy baja … 5 = muy alta. El orden se verificó: la pendiente media crece por clase,
  Iquitos = 1 y cordillera = 4, y coincide con la leyenda del metadato.
- **Población**: Censo 2017 (INEI) por distrito, repartida de forma dasimétrica sobre lo edificado en 2016–17.
  No se usa HRSL de Meta: su año base es incierto y tiene artefactos (el aeropuerto aparece poblado).
- **Edificado**: `building_presence ≥ 0.5`, con promedios de dos años (base 2016–17, final 2022–23) por el ruido
  entre años. En el mapa, el crecimiento se dibuja en celdas de 80 m.
- **Paleta validada** sobre fondo `#0A0E13` (lightness band, CVD, contraste): nuevo `#16A396`,
  INGEMMET alta/muy alta `#A88C14` con trama (codificación secundaria), zona crítica `#E0364F`.
- **Título**: "El fenómeno del Niño 2026–27:" + "susceptibilidad a huaycos y deslizamientos" (sin antetítulo).
  Grafía "huaycos" en todo el video.
- Las escenas están coreografiadas en 15 s de guion (`STORY`) y se estiran a `DUR` = 20 s.

## Cifras actuales (stats.json)

+299 ha edificadas (+29 %) entre 2016–17 y 2022–23. El 11,6 % del crecimiento neto cayó en zona crítica, frente al
4,7 % de la ciudad de 2016 (2,5×). ≈34 600 habitantes en zona crítica: Cusco 19 430 (17 %), Santiago 8 620 (9 %),
San Sebastián 4 270 (4 %), San Jerónimo 1 270 (2 %) y Saylla 630 (12 %).

## Pendientes / por verificar

- **ENFEN**: el video cita el Comunicado Oficial 16-2026 (14 de setiembre de 2026), corroborado solo con prensa
  (Canal N, América TV, El Búho), porque los dominios `.gob.pe` estaban bloqueados en la nube. Hay reportes de un
  **17-2026 (28 de setiembre)** y quizá uno posterior: verificar en https://enfen.imarpe.gob.pe/comunicados/ y actualizar
  el texto de la escena 1 en `03_render.py` si cambió la magnitud o la duración.
- **Censo 2017**: las cifras por distrito vienen de una tabla municipal que cita al INEI y suman exactamente 447 588.
  Conviene contrastarlas con la publicación oficial del INEI.
- Si se consigue una capa de peligro más detallada (por ejemplo, la regional de GEOCATMIN `smm_cusco.zip`, o la de
  CENEPRED "susceptibilidad ante lluvias asociadas a El Niño"), `02_analysis.py` ya acepta shapefiles/zip con
  una columna de clase (detecta textos como "Muy Alta" o "Alta"). Habría que revisar si sigue haciendo falta el
  filtro de pendiente.

## Cómo trabajar

- Para iterar en el diseño, usar siempre `./run.sh preview` (unos segundos) y mirar los PNG en `build/`. El video
  completo tarda de 20 a 35 minutos.
- Antes de publicar cifras nuevas, revisar `stats.json` y actualizar `README.md` (resultados y sensibilidad).
- No inventar ni redondear cifras más allá de lo que hace el render. Toda cifra nueva debe tener fuente o método
  documentado.

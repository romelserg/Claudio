# Cusco frente a El Niño 2026–27: una ciudad que sube por las laderas

Historia de Instagram (1080×1920, 15 s, 30 fps) para **@sieteborreguitos**.

## Qué muestra

| Escena | Tiempo | Contenido |
|---|---|---|
| 1 | 0–2.5 s | Estado oficial: ENFEN mantiene la **Alerta de El Niño Costero** (Com. Of. 16-2026). |
| 2 | 2.5–7 s | Crecimiento de la superficie edificada, 2016 → 2023, año por año. |
| 3 | 7–11 s | **Zona crítica**: susceptibilidad alta o muy alta (INGEMMET) y ladera ≥ 20°. Muestra qué % del crecimiento cayó ahí. |
| 4 | 11–14 s | Habitantes (Censo 2017) que viven en zona crítica, por distrito. |
| 5 | 14–15 s | Firma y fuentes. |

## Fuentes

- **ENFEN**: Comunicado Oficial N° 16-2026. Alerta de El Niño Costero; magnitud extraordinaria más probable en Niño 1+2 hasta enero de 2027; continuidad hasta mediados del otoño de 2027.
- **INGEMMET (2010)**: Mapa de susceptibilidad por movimientos en masa del Perú, escala 1:2 000 000, ráster de 200 m (`su_mm_peru`). Obtenido vía GeoGPS Perú; el zip original está en `data/`. Es un modelo heurístico (pendiente, geomorfología, litología, hidrogeología y cobertura) con un 86 % de coincidencia con el inventario de eventos. Clases: 1 = muy baja … 5 = muy alta; el orden se verificó con la pendiente media por clase.
- **Google Open Buildings 2.5D Temporal v1**: presencia de edificaciones anual, 2016–2023. Viene superresuelta desde Sentinel-2; se lee a 4 m y se agrega a 5 m.
- **INEI, Censos Nacionales 2017**: población censada por distrito, provincia del Cusco (total 447 588).
- **Copernicus DEM GLO-30** (ESA / Airbus): relieve y sombreado.
- **Overture Maps Foundation, divisions** (derivado de OpenStreetMap): límites distritales, solo de referencia.

## Método (resumen)

1. Todas las capas se llevan a una grilla UTM 19S de 5 m.
2. **Edificado**: `building_presence ≥ 0.5`. Para atenuar el ruido del modelo entre años, se promedian pares de años: la línea base es 2016–17 y el final es 2022–23.
3. **Zona crítica** = INGEMMET alta o muy alta **y** pendiente ≥ 20° (Copernicus DEM, ~30 m). El mapa nacional, solo, también marca como 'alta' el fondo plano del valle (por ejemplo, el 70 % de Wanchaq). Su metadato advierte que a escalas mayores es preliminar, así que la pendiente lo lleva a escala urbana. El umbral de 20° es el límite inferior que la leyenda de INGEMMET da para susceptibilidad media; 25° es el de alta.
4. **Crecimiento en zona crítica**: es el cambio neto de cobertura edificada dentro de la zona crítica, dividido entre el cambio neto total de los 8 distritos.
5. **Población expuesta**: la población del Censo 2017 de cada distrito se reparte de forma dasimétrica sobre la cobertura edificada de 2016–17 y se suma la que cae en zona crítica.
6. **Mapa**: el crecimiento se dibuja en celdas de 80 m, las que suman al menos 8 puntos de cobertura edificada respecto a 2016–17.

## Resultados (8 distritos de la provincia del Cusco)

- Superficie edificada: 1 042 ha (2016–17) → 1 342 ha (2022–23), **+299 ha (+29 %)**.
- **11,6 %** del crecimiento neto cayó en zona crítica, frente al **4,7 %** de la ciudad de 2016–17 (unas 2,5 veces más).
- **≈ 34 600 habitantes** (Censo 2017) viven en zona crítica. Por distrito: Cusco 19 430 (17 %), Santiago 8 620 (9 %), San Sebastián 4 270 (4 %), San Jerónimo 1 270 (2 %) y Saylla 630 (12 %).
- Sensibilidad: con pendiente ≥ 25° la cifra baja a 5,6 % del crecimiento y ≈ 13 800 habitantes. Con el mapa INGEMMET sin pendiente sube a 63 % y ≈ 307 000 habitantes; esa versión no se usa, por lo explicado arriba.

## Limitaciones

- La susceptibilidad oficial es de escala nacional (1:2 000 000); se refina con la pendiente, pero no reemplaza un estudio de peligro a escala de manzana (EVAR o estudios de INGEMMET/CENEPRED). Indica dónde el terreno es propenso a movimientos en masa, no un riesgo vivienda por vivienda.
- Los límites de OSM/Overture no coinciden exactamente con los del INEI.
- El modelo de edificaciones tiene ruido entre años. Por eso se usan promedios de dos años y un análisis de cambio neto.

## Reproducir

```bash
python scripts/01_download.py <datos>
unzip 'data/MOVIMIENTOS EN MASA  INGEMMET geogpsperu.zip'   # extrae RASTER/su_mm_peru.tif
python scripts/02_analysis.py <datos> <ruta>/RASTER/su_mm_peru.tif
python scripts/03_render.py <datos> <fuentes_ttf> build/cusco_nino.mp4
```

Fuentes tipográficas: Space Grotesk e IBM Plex Mono (OFL, repositorio google/fonts).

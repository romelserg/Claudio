# Cusco frente a El Niño 2026–27: una ciudad que sube por las laderas

Historia de Instagram (1080×1920, 15 s, 30 fps) para **@sieteborreguitos**.

## Qué muestra

| Escena | Tiempo | Contenido |
|---|---|---|
| 1 | 0–2.5 s | Estado oficial: ENFEN mantiene la **Alerta de El Niño Costero** (Com. Of. 16-2026). |
| 2 | 2.5–7 s | Crecimiento de la superficie edificada, 2016 → 2023, año por año. |
| 3 | 7–11 s | Superposición con susceptibilidad **alta / muy alta** a movimientos en masa. Muestra qué % del crecimiento cae ahí. |
| 4 | 11–14 s | Habitantes (Censo 2017) que viven sobre esas zonas, por distrito. |
| 5 | 14–15 s | Firma y fuentes. |

## Fuentes

- **ENFEN**: Comunicado Oficial N° 16-2026. Alerta de El Niño Costero; magnitud extraordinaria más probable en Niño 1+2 hasta enero de 2027; continuidad hasta mediados del otoño de 2027.
- **INGEMMET (GEOCATMIN) / CENEPRED (SIGRID)**: susceptibilidad a movimientos en masa (capa oficial, en `data/`).
- **Google Open Buildings 2.5D Temporal v1**: presencia de edificaciones anual, 2016–2023. Viene superresuelta desde Sentinel-2; se lee a 4 m y se agrega a 5 m.
- **INEI, Censos Nacionales 2017**: población censada por distrito, provincia del Cusco (total 447 588).
- **Copernicus DEM GLO-30** (ESA / Airbus): relieve y sombreado.
- **Overture Maps Foundation, divisions** (derivado de OpenStreetMap): límites distritales, solo de referencia.

## Método (resumen)

1. Todas las capas se llevan a una grilla UTM 19S de 5 m.
2. **Edificado**: `building_presence ≥ 0.5`. Para atenuar el ruido del modelo entre años, se promedian pares de años: la línea base es 2016–17 y el final es 2022–23.
3. **Crecimiento en zonas de peligro**: es el cambio neto de cobertura edificada dentro de las zonas de clase alta o muy alta, dividido entre el cambio neto total de los 8 distritos.
4. **Población expuesta**: la población del Censo 2017 de cada distrito se reparte de forma dasimétrica sobre la cobertura edificada de 2016–17 y se suma la que cae en las clases alta o muy alta.
5. **Mapa**: el crecimiento se dibuja en celdas de 80 m, las que suman al menos 8 puntos de cobertura edificada respecto a 2016–17.

## Limitaciones

- La susceptibilidad oficial está mapeada a escala regional, no de manzana. Indica dónde el terreno es propenso a movimientos en masa, no un riesgo vivienda por vivienda.
- Los límites de OSM/Overture no coinciden exactamente con los del INEI.
- El modelo de edificaciones tiene ruido entre años. Por eso se usan promedios de dos años y un análisis de cambio neto.

## Reproducir

```bash
python scripts/01_download.py <datos>
python scripts/02_analysis.py <datos> data/<capa_oficial>.zip
python scripts/03_render.py <datos> <fuentes_ttf> build/cusco_nino.mp4
```

Fuentes tipográficas: Space Grotesk e IBM Plex Mono (OFL, repositorio google/fonts).

#!/usr/bin/env bash
# Pipeline completo. Uso: ./run.sh [descarga|analisis|preview|video|todo]
# Requiere: Python 3.10+, ffmpeg en el PATH y el entorno de requirements.txt.
set -euo pipefail
cd "$(dirname "$0")"

DATOS="datos"                                              # datos procesados (grilla común)
FUENTES="fonts"                                            # Space Grotesk + IBM Plex Mono
PELIGRO="data/MOVIMIENTOS EN MASA  INGEMMET geogpsperu.zip"
VIDEO="build/cusco_nino_sieteborreguitos.mp4"
export GDAL_HTTP_MAX_RETRY=5 GDAL_HTTP_RETRY_DELAY=3 GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR

paso="${1:-todo}"
mkdir -p "$DATOS" build

if [[ "$paso" == descarga || "$paso" == todo ]]; then
  python scripts/01_download.py "$DATOS"          # se salta lo que ya existe
fi
if [[ "$paso" == analisis || "$paso" == todo ]]; then
  python scripts/02_analysis.py "$DATOS" "$PELIGRO"  # escribe stats.json y layers.npz
fi
if [[ "$paso" == preview ]]; then
  python scripts/03_render.py "$DATOS" "$FUENTES" build/preview.mp4 --preview  # 5 PNG de control
fi
if [[ "$paso" == video || "$paso" == todo ]]; then
  python scripts/03_render.py "$DATOS" "$FUENTES" "$VIDEO"   # ~20-35 min
fi

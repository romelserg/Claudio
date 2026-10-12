"""Descarga y armoniza los datos base para el área urbana de Cusco.

Todas las capas se llevan a una grilla común UTM 19S (EPSG:32719).

Fuentes:
- Google Open Buildings 2.5D Temporal v1 (2016-2023), banda building_presence.
- Copernicus DEM GLO-30 (ESA / Airbus).
- Meta & CIESIN High Resolution Settlement Layer v1.5 (población total, <5 años, 60+).
- Overture Maps Foundation, divisions (límites distritales derivados de OSM).
"""
import json
import os
import sys

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

DATA = sys.argv[1] if len(sys.argv) > 1 else "data"
os.makedirs(DATA, exist_ok=True)

DST_CRS = "EPSG:32719"
# Área urbana de Cusco: Poroy (O) a Saylla (E), en coordenadas UTM 19S.
X0, X1 = 168000, 197000
Y0, Y1 = 8494000, 8510000
RES = 5.0
W, H = int((X1 - X0) / RES), int((Y1 - Y0) / RES)
DST_TF = from_origin(X0, Y1, RES, RES)

GCS = "https://storage.googleapis.com/open-buildings-temporal-data/v1"
YEARS = range(2016, 2024)


def tiles_for(year, epsg):
    """Teselas del manifiesto (celda S2 '91') que cortan el área de estudio."""
    url = f"{GCS}/manifests/91_EPSG_{epsg}_{year}_06_30.json"
    path = os.path.join(DATA, f"manifest_{epsg}_{year}.json")
    if not os.path.exists(path):
        os.system(f"curl -sf -o {path} {url}")
    m = json.load(open(path))
    t = Transformer.from_crs(DST_CRS, f"EPSG:{epsg}", always_xy=True)
    xs, ys = zip(*[t.transform(x, y) for x in (X0, X1) for y in (Y0, Y1)])
    out = []
    for ts in m["tilesets"]:
        for s in ts["sources"]:
            a, d = s["affineTransform"], s["dimensions"]
            tx0, ty1 = a["translateX"], a["translateY"]
            tx1, ty0 = tx0 + d["width"] * a["scaleX"], ty1 + d["height"] * a["scaleY"]
            if tx0 < max(xs) and tx1 > min(xs) and ty0 < max(ys) and ty1 > min(ys):
                out.append(f"{GCS}/geotiffs/91{s['uris'][0]}")
    return out


def buildings(year):
    out = os.path.join(DATA, f"buildings_{year}.tif")
    if os.path.exists(out):
        return
    acc = np.zeros((H, W), np.float32)
    for epsg in (32718, 32719):
        for url in tiles_for(year, epsg):
            # Nivel de overview 11 = 4 m de resolución (el original es 0.5 m superresuelto).
            with rasterio.open("/vsicurl/" + url, overview_level=11) as src:
                arr = src.read(3)  # building_presence (0-1)
                arr = np.where(arr < 0, 0, arr)
                dst = np.zeros((H, W), np.float32)
                reproject(arr, dst, src_transform=src.transform, src_crs=src.crs,
                          dst_transform=DST_TF, dst_crs=DST_CRS,
                          resampling=Resampling.average, src_nodata=None, dst_nodata=0)
                acc = np.maximum(acc, dst)
            print(year, url.split("/")[-2:], flush=True)
    write(out, acc, "float32")


def write(path, arr, dtype, tf=DST_TF):
    prof = dict(driver="GTiff", width=arr.shape[1], height=arr.shape[0], count=1,
                dtype=dtype, crs=DST_CRS, transform=tf, compress="deflate")
    with rasterio.open(path, "w", **prof) as d:
        d.write(arr.astype(dtype), 1)


def dem():
    out = os.path.join(DATA, "dem.tif")
    if os.path.exists(out):
        return
    dst = np.full((H, W), np.nan, np.float32)
    for lon in ("W072", "W073"):
        name = f"Copernicus_DSM_COG_10_S14_00_{lon}_00_DEM"
        url = f"/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
        with rasterio.open(url) as src:
            tmp = np.full((H, W), np.nan, np.float32)
            reproject(rasterio.band(src, 1), tmp, dst_transform=DST_TF, dst_crs=DST_CRS,
                      resampling=Resampling.cubic, dst_nodata=np.nan)
            dst = np.where(np.isnan(dst), tmp, dst)
    write(out, dst, "float32")


def hrsl(kind):
    out = os.path.join(DATA, f"pop_{kind}.tif")
    if os.path.exists(out):
        return
    sub = {"general": "general", "under5": "children_under_five", "60plus": "elderly_60_plus"}[kind]
    url = (f"/vsicurl/https://dataforgood-fb-data.s3.amazonaws.com/hrsl-cogs/hrsl_{sub}/v1.5/"
           f"cog_globallat_-20_lon_-80_{sub}-v1.5.4.tif")
    with rasterio.open(url) as src:
        # Ventana geográfica del área; la población es un conteo, se reparte por área.
        win = src.window(-72.15, -13.70, -71.70, -13.38)
        arr = src.read(1, window=win).astype(np.float32)
        arr = np.where(np.isnan(arr) | (arr < 0), 0, arr)
        tf = src.window_transform(win)
        total_src = arr.sum()
        dst = np.zeros((H, W), np.float32)
        reproject(arr, dst, src_transform=tf, src_crs=src.crs, dst_transform=DST_TF,
                  dst_crs=DST_CRS, resampling=Resampling.sum, dst_nodata=0)
    print(kind, "pob. en ventana fuente", round(float(total_src)), "en grilla", round(float(dst.sum())))
    write(out, dst, "float32")


if __name__ == "__main__":
    dem()
    for k in ("general", "under5", "60plus"):
        hrsl(k)
    for y in YEARS:
        buildings(y)

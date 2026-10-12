"""Cruza crecimiento edificado, susceptibilidad oficial y población por distrito.

Uso: python 02_analysis.py <dir_datos> <archivo_peligro (.zip/.shp)>

Salidas en <dir_datos>:
- hazard.tif   clase de susceptibilidad 0-5 (5 = muy alta) en la grilla común.
- layers.npz   capas listas para el render (relieve, edificado, cambio, peligro, población).
- stats.json   cifras que aparecen en el video.
"""
import json
import os
import sys
import unicodedata

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features

DATA, HAZARD = sys.argv[1], sys.argv[2]
REF = rasterio.open(os.path.join(DATA, "dem.tif"))
H, W, TF, CRS = REF.height, REF.width, REF.transform, REF.crs
RES = TF.a
PX_HA = RES * RES / 1e4

# Censo Nacional 2017 (INEI), población censada por distrito (provincia del Cusco).
CENSO_2017 = {
    "Cusco": 114630, "San Sebastián": 112536, "Santiago": 94756, "Wanchaq": 58541,
    "San Jerónimo": 57075, "Saylla": 5368, "Poroy": 2436, "Ccorca": 2246,
}
BUILT_T = 0.5  # umbral de building_presence
SLOPE_T = 20.0  # grados


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    return " ".join(s.split())


def hazard_class(v):
    v = norm(v)
    if "MUY ALT" in v:
        return 5
    if "ALT" in v:
        return 4
    if "MEDI" in v or "MODER" in v:
        return 3
    if "MUY BAJ" in v:
        return 1
    if "BAJ" in v:
        return 2
    return 0


def load_hazard_raster(path):
    """Ráster INGEMMET 2010 (celdas de 200 m): valores 1 = muy baja ... 5 = muy alta.

    El orden se verificó con la pendiente media por clase (crece de 2 a 5) y con
    puntos de control (llano amazónico = 1, cordillera = 4)."""
    from rasterio.warp import reproject
    from rasterio.enums import Resampling
    hz = np.full((H, W), 0, np.uint8)
    with rasterio.open(path) as src:
        reproject(rasterio.band(src, 1), hz, dst_transform=TF, dst_crs=CRS,
                  resampling=Resampling.nearest, src_nodata=255, dst_nodata=0)
    return np.where(hz > 5, 0, hz).astype(np.uint8), "Value (1-5)"


def load_hazard():
    path = HAZARD
    if path.lower().endswith(".zip"):
        # Zip de INGEMMET vía GeoGPS Perú: usa el ráster que trae dentro.
        import zipfile
        names = zipfile.ZipFile(path).namelist()
        tif = [n for n in names if n.lower().endswith("su_mm_peru.tif") and "__MACOSX" not in n]
        if tif:
            return load_hazard_raster(f"/vsizip/{os.path.abspath(path)}/{tif[0]}")
    if path.lower().endswith((".tif", ".tiff")):
        return load_hazard_raster(path)
    if path.endswith(".zip"):
        path = "zip://" + os.path.abspath(path)
    g = gpd.read_file(path)
    print("columnas:", list(g.columns), "CRS:", g.crs, "n:", len(g))
    # Busca la columna cuyo contenido parece una clase de susceptibilidad.
    best = None
    for c in g.columns:
        if c == "geometry":
            continue
        vals = g[c].dropna().astype(str)
        score = sum(hazard_class(v) > 0 for v in vals.unique())
        if best is None or score > best[1]:
            best = (c, score)
    col = best[0]
    print("campo de clase:", col, sorted(g[col].dropna().astype(str).unique())[:20])
    g = g.to_crs(CRS)
    g["cls"] = g[col].map(hazard_class)
    shapes = [(geom, int(c)) for geom, c in zip(g.geometry, g.cls) if c > 0 and geom is not None]
    # Si hay solapes, gana la clase más alta.
    shapes.sort(key=lambda s: s[1])
    hz = features.rasterize(shapes, out_shape=(H, W), transform=TF, fill=0, dtype="uint8")
    return hz, col


def districts():
    d = gpd.read_file(os.path.join(DATA, "divisions.gpkg"))
    d = d[(d.subtype == "locality") & d.name.isin(CENSO_2017)].to_crs(CRS)
    d = d.drop_duplicates("name").reset_index(drop=True)
    ids = features.rasterize([(g, i + 1) for i, g in enumerate(d.geometry)],
                             out_shape=(H, W), transform=TF, fill=0, dtype="uint8")
    return d, ids


def hillshade(z, az=315, alt=40):
    dy, dx = np.gradient(z, RES)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    a, e = np.radians(az), np.radians(alt)
    hs = np.sin(e) * np.cos(slope) + np.cos(e) * np.sin(slope) * np.cos(a - aspect)
    return np.clip(hs, 0, 1), np.degrees(slope)


def main():
    dem = REF.read(1)
    hs, slope = hillshade(dem)
    b = {y: rasterio.open(os.path.join(DATA, f"buildings_{y}.tif")).read(1) for y in range(2016, 2024)}
    # Promedios de dos años para atenuar el ruido entre años del modelo.
    b_ini = (b[2016] + b[2017]) / 2
    b_fin = (b[2022] + b[2023]) / 2
    built_ini = b_ini >= BUILT_T
    built_fin = b_fin >= BUILT_T

    hz, hz_field = load_hazard()
    with rasterio.open(os.path.join(DATA, "hazard.tif"), "w", driver="GTiff", width=W, height=H,
                       count=1, dtype="uint8", crs=CRS, transform=TF, compress="deflate") as o:
        o.write(hz, 1)
    # Zona crítica: susceptibilidad alta/muy alta (INGEMMET, 1:2 000 000) Y ladera >= 20°
    # según Copernicus DEM a su resolución nativa (~30 m). El mapa nacional, solo, marca
    # también el fondo plano del valle; la pendiente lo lleva a escala urbana.
    from scipy.ndimage import uniform_filter
    _, slope30 = hillshade(uniform_filter(dem.astype(np.float64), 6))
    high = (hz >= 4) & (slope30 >= SLOPE_T)

    dist, ids = districts()

    # Población: Censo 2017 repartida sobre lo edificado en 2016-2017 dentro de cada distrito
    # (método dasimétrico).
    pop = np.zeros((H, W), np.float32)
    rows = []
    for i, r in dist.iterrows():
        m = ids == i + 1
        w = np.where(m, b_ini, 0)
        if w.sum() > 0:
            pop += w / w.sum() * CENSO_2017[r["name"]]
        rows.append(r["name"])

    stats = {"distritos": {}}
    in_prov = ids > 0
    tot_ini = (built_ini & in_prov).sum() * PX_HA
    tot_fin = (built_fin & in_prov).sum() * PX_HA
    net = (b_fin - b_ini)
    net_pos = np.clip(net, 0, None)
    stats["edificado_ha_2016_17"] = round(float(tot_ini), 1)
    stats["edificado_ha_2022_23"] = round(float(tot_fin), 1)
    stats["crecimiento_pct"] = round(float((tot_fin / tot_ini - 1) * 100), 1)
    stats["crecimiento_ha"] = round(float(tot_fin - tot_ini), 1)
    g_all = (np.where(in_prov, net, 0)).sum()
    g_high = (np.where(in_prov & high, net, 0)).sum()
    stats["crecimiento_neto_en_alta_muy_alta_pct"] = round(float(g_high / g_all * 100), 1)
    stats["edificado_2016_17_en_zona_critica_pct"] = round(
        float((built_ini & high & in_prov).sum() / (built_ini & in_prov).sum() * 100), 1)
    stats["criterio"] = f"INGEMMET alta/muy alta y pendiente >= {SLOPE_T:.0f}°"
    stats["edificado_2022_23_en_alta_muy_alta_pct"] = round(
        float((built_fin & high & in_prov).sum() / (built_fin & in_prov).sum() * 100), 1)
    stats["poblacion_2017_en_alta_muy_alta"] = int(round(float(pop[high].sum())))
    stats["poblacion_2017_total"] = int(sum(CENSO_2017.values()))
    stats["campo_peligro"] = hz_field
    # Serie anual con promedio móvil de 2 años (año y año previo) para atenuar ruido;
    # 2016 usa 2016-17, igual que la línea base.
    serie = {}
    for y in range(2016, 2024):
        ys = [2016, 2017] if y == 2016 else [y - 1, y]
        m = (sum(b[k] for k in ys) / 2) >= BUILT_T
        serie[str(y)] = round(float((m & in_prov).sum() * PX_HA), 1)
    stats["edificado_ha_serie"] = serie
    for i, name in enumerate(rows):
        m = ids == i + 1
        bi, bf = (built_ini & m).sum() * PX_HA, (built_fin & m).sum() * PX_HA
        stats["distritos"][name] = {
            "pob_2017": CENSO_2017[name],
            "pob_alta_muy_alta": int(round(float(pop[m & high].sum()))),
            "pob_alta_muy_alta_pct": round(float(pop[m & high].sum() / max(pop[m].sum(), 1) * 100), 1),
            "edificado_ha_ini": round(float(bi), 1),
            "edificado_ha_fin": round(float(bf), 1),
            "edificado_fin_en_alta_muy_alta_pct": round(
                float((built_fin & m & high).sum() / max((built_fin & m).sum(), 1) * 100), 1),
        }
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    json.dump(stats, open(os.path.join(DATA, "stats.json"), "w"), ensure_ascii=False, indent=1)

    np.savez_compressed(
        os.path.join(DATA, "layers.npz"),
        dem=dem.astype(np.float32), hs=hs.astype(np.float16), slope=slope.astype(np.float16),
        b=np.stack([b[y] for y in range(2016, 2024)]).astype(np.float16),
        hz=hz, crit=high, ids=ids, pop=pop, names=np.array(rows),
    )


if __name__ == "__main__":
    main()

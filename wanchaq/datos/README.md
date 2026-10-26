# Datos de ejecución presupuestal (MEF – Consulta Amigable)

Descargados el 25–26 de octubre de 2026 desde https://apps5.mineco.gob.pe/transparencia/Navegador/ con `../scripts/mef_consulta_amigable.py`.

Ruta de navegación: Nivel de Gobierno → M: Gobiernos Locales → Gob.Loc./Mancom. → M: Municipalidades → Departamento 08 Cusco → Provincia 0801 Cusco → Municipalidad.

| Archivo | Contenido |
|---|---|
| `prov_<año>_ActProy.txt` | Las 8 municipalidades de la provincia del Cusco, presupuesto total (actividades + proyectos). |
| `prov_<año>_Proyecto.txt` | Lo mismo, solo proyectos de inversión. |
| `w_<año>_fuente.txt` / `w_<año>_rubro.txt` | Municipalidad de Wánchaq por fuente / rubro de financiamiento. |
| `w_<año>_funcion.txt` | Municipalidad de Wánchaq por función. |
| `w_<año>_proy.txt` | Municipalidad de Wánchaq, lista de proyectos de inversión. |

Columnas (en soles): PIA | PIM | Certificación | Compromiso anual | Atención de compromiso mensual | Devengado | Girado | Avance % (devengado/PIM).

Las cifras de 2026 son parciales (corte al 24 de octubre de 2026).

Para reproducir, por ejemplo:

```
python3 ../scripts/mef_consulta_amigable.py 2025 Proyecto \
  "TOTAL::Nivel de Gobierno" "GOBIERNOS LOCALES::Gob.Loc./Mancom." \
  "MUNICIPALIDADES::Departamento" "08: CUSCO::Departamento" \
  "08: CUSCO::Provincia" "0801: CUSCO::Municipalidad" "WANCHAQ::Producto/Proyecto"
```

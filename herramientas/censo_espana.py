"""Escribe docs/CENSO-ESPANA.md: el censo nacional de SOCIMIs cotizadas que hay en la base, por mercado, por provincia del
domicilio y por provincia de los inmuebles (con el gazetteer de `socimis/geo.py`), más lo que NO se ha podido mirar y por
qué. Es la ampliación del piloto vasco al resto de España (encargo de Juan, 2026-10-27). `python3 herramientas/censo_espana.py`
desde la raíz. Puro salvo la escritura del fichero."""
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from socimis import geo, modelo  # noqa: E402


def _eur(v):
    return "—" if v is None else ("%.1f M€" % (v / 1e6)).replace(".", ",")


def main():
    fichas = [modelo.cargar(p) for p in sorted(glob.glob(os.path.join(RAIZ, "base", "fichas", "*.json")))]
    rp = os.path.join(RAIZ, "base", "puntuaciones.json")
    punt = {k: v["evaluacion"] for k, v in json.load(open(rp, encoding="utf-8")).items()} if os.path.exists(rp) else {}
    hoy = date.today().isoformat()
    con_docs = [f for f in fichas if any(d.get("tipo") != "censo" for d in f.get("documentos", []))]
    solo_censo = [f for f in fichas if f not in con_docs]
    escaneadas = [f for f in con_docs if any(d.get("escaneado") and d.get("tipo") == "cuentas_anuales" for d in f.get("documentos", []))]
    con_balance = [f for f in con_docs if modelo.ultimo_ejercicio(f) and modelo.valor(f, modelo.ultimo_ejercicio(f), "tesoreria") is not None]

    por_seg = Counter(f["sociedad"].get("segmento") or "?" for f in fichas)
    por_prov = Counter(f["sociedad"].get("provincia") or "sin domicilio publicado" for f in fichas)
    por_ca = Counter(geo.comunidad(f["sociedad"].get("provincia")) or "sin domicilio publicado" for f in fichas)

    # inmuebles por provincia (solo los que tienen ubicación legible y provincia reconocida)
    inm = defaultdict(lambda: {"n": 0, "valor": 0.0, "sociedades": set()})
    sin_prov = 0
    total_inm = 0
    for f in fichas:
        for a in f.get("activos", []):
            total_inm += 1
            prov = geo.provincia_de_activo(a)
            if not prov:
                sin_prov += 1
                continue
            inm[prov]["n"] += 1
            inm[prov]["valor"] += a.get("valor") or 0
            inm[prov]["sociedades"].add(f["sociedad"].get("nombre"))

    L = ["# Censo nacional: SOCIMIs cotizadas en la base", "",
         "Generado el %s por `herramientas/censo_espana.py` desde `base/fichas/` (%d sociedades). Cada dato tiene su fuente en la ficha JSON y en `base/socimis.sqlite`. "
         "Es la ampliación del piloto vasco (`CENSO-VINCULO-VASCO.md`) al resto de España: mismo motor, mismo esquema, más mercados." % (hoy, len(fichas)), "",
         "## En una frase", "",
         "**%d sociedades censadas** en cinco mercados; **%d con documentos bajados** (BME Growth, BME Scaleup y Continuo), de las que **%d tienen el balance leído** y **%d publican las cuentas escaneadas** (sin OCR no se leen); "
         "**%d son solo censo** (Portfolio Stock Exchange y Euronext Access París: nombre, ISIN, precio; documentos sin leer, ver abajo)." % (len(fichas), len(con_docs), len(con_balance), len(escaneadas), len(solo_censo)), "",
         "## Por mercado", "", "| Mercado / segmento | Sociedades | Qué hay de cada una |", "|---|---|---|"]
    que = {"BME Growth": "ficha completa: 5 documentos, cuentas leídas si tienen texto", "BME Scaleup": "ficha completa: 5 documentos, cuentas leídas si tienen texto",
           "Continuo": "ESEF de la CNMV (iXBRL) y accionistas ≥ 3 %", "Portfolio SE": "solo censo: nombre, ISIN, capitalización, precio (documentos tras login)",
           "Euronext Access": "solo censo: nombre recortado, ISIN, símbolo, último precio (fichas sin recorrer: condiciones de uso)"}
    L += ["| %s | %d | %s |" % (s, n, que.get(s, "")) for s, n in sorted(por_seg.items(), key=lambda kv: -kv[1])]

    L += ["", "## Dónde están domiciliadas", "", "Provincia del domicilio social (código postal o ciudad del domicilio que publica el mercado; Portfolio y Euronext no lo publican en el listado).", "",
          "| Provincia | Sociedades |", "|---|---|"] + ["| %s | %d |" % (p, n) for p, n in por_prov.most_common()]
    L += ["", "| Comunidad autónoma | Sociedades |", "|---|---|"] + ["| %s | %d |" % (p, n) for p, n in por_ca.most_common()]

    L += ["", "## Dónde están los inmuebles", "",
          "Solo cuentan los inmuebles de la tabla de inversiones inmobiliarias de la memoria con ubicación publicada: **%d inmuebles leídos, %d con provincia reconocida** por `socimis/geo.py` (gazetteer de provincias, capitales y municipios grandes; lo que falte no se detecta: se amplía el diccionario). "
          "El valor es el que publica la sociedad (valor razonable o coste, según su tabla), y solo de las %d sociedades con balance leído: **no es el mapa del sector, es el mapa de lo leído**." % (total_inm, total_inm - sin_prov, len(con_balance)), "",
          "| Provincia | Inmuebles | Valor publicado | Sociedades |", "|---|---|---|---|"]
    for prov, d in sorted(inm.items(), key=lambda kv: -kv[1]["valor"]):
        L.append("| %s | %d | %s | %s |" % (prov, d["n"], _eur(d["valor"]), ", ".join(sorted(x[:35] for x in d["sociedades"]))))
    if not inm:
        L.append("| — | 0 | — | — |")

    L += ["", "## Las mejor puntuadas (todo el país)", "", "| Sociedad | Segmento | Provincia | Puntos | Tramo | Cobertura |", "|---|---|---|---|---|---|"]
    orden = sorted(fichas, key=lambda f: -(punt.get(modelo.clave(f), {}).get("puntos") or 0))
    for f in orden[:15]:
        s, ev = f["sociedad"], punt.get(modelo.clave(f), {})
        L.append("| %s | %s | %s | %s | %s | %s/6 |" % (s.get("nombre"), s.get("segmento"), s.get("provincia") or "—", "%.1f" % ev["puntos"] if ev else "—", ev.get("tramo", "—"), ev.get("cobertura", "—")))

    L += ["", "## Lo que no se ha mirado, y por qué", "",
          "- **Portfolio Stock Exchange (%d)**: la página pública del mercado da nombre, ISIN, capitalización y precio; los documentos (cuentas, valoraciones, hechos relevantes) están tras el login de la plataforma. Su aviso legal prohíbe la reproducción del contenido; aquí solo se guardan esos cuatro datos con su URL." % por_seg.get("Portfolio SE", 0),
          "- **Euronext Access París (%d)**: el listado público se leyó una vez con navegador; la ficha de cada valor tiene cuentas auditadas y dividendos en PDF y una pestaña de información de empresa (perfil, cifras, accionistas, domicilio, de Cofisem). **No se recorren**: las condiciones de uso de Euronext prohíben, sin permiso escrito, el acceso con herramientas automáticas y la recopilación sistemática en bases de datos; la información de Cofisem además no puede reproducirse sin su consentimiento. La vía limpia son las webs de las propias sociedades. Decisión pendiente de Juan (PRD). Además el listado recorta los nombres y mezcla SOCIMIs con otras sociedades (biotecnológicas, gimnasios, colegios): `regimen_socimi` dice «sin confirmar» cuando la palabra no aparece." % por_seg.get("Euronext Access", 0),
          "- **Las %d escaneadas** de BME: hasta el OCR del Mac, solo se ve lo de los avisos cortos." % len(escaneadas),
          "- **Lar España** (antes Continuo) está como BME Scaleup: Helios la excluyó de bolsa en 2025 y la llevó a ese segmento (ficha por su NIF).",
          "- Registro Mercantil, no cotizadas y BORME: fuera por decisión de Juan («céntrate en lo cotizado»).", ""]
    salida = os.path.join(RAIZ, "docs", "CENSO-ESPANA.md")
    with open(salida, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("%s: %d sociedades, %d con documentos, %d con balance, %d solo censo, %d inmuebles con provincia" % (salida, len(fichas), len(con_docs), len(con_balance), len(solo_censo), total_inm - sin_prov))


if __name__ == "__main__":
    main()

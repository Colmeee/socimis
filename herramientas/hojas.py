"""Prepara los CSV (con coma) que se suben a Google Sheets, una hoja por tabla.

Por qué existe: la subida a Drive va dentro de la llamada y una tabla de 200 KB no pasa; además una hoja se lee mejor ancha.
Así que las tablas largas se compactan: `cifras` pone un ejercicio por fila con las partidas en columnas (la fuente de cada
cifra sigue en base/csv/dato.csv y en la ficha JSON), `puntuacion` pone una sociedad por fila con las seis dimensiones,
`vinculo_vasco` deja fuera el JSON de detalle, `documento` deja fuera la huella (está en el CSV largo). `sociedad`,
`accionista`, `activo` y `vencimiento` van enteras. Salida en la carpeta que se pase. Puro salvo la escritura.
`python3 herramientas/hojas.py <carpeta_salida>`
"""
import csv
import glob
import json
import os
import sys
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from socimis import modelo  # noqa: E402

CAMPOS_CIFRAS = ["tesoreria", "valor_razonable_inmuebles", "gav_valoracion", "deuda_financiera", "deuda_financiera_neta", "ltv_declarado", "ltv_neto",
                 "ingresos", "ingresos_rentas", "resultado", "patrimonio_neto", "activo_total", "dividendos_pagados", "dividendo_acordado",
                 "dividendo_por_accion", "capitalizacion", "cotizacion", "nav_por_accion"]


def escribir(carpeta, nombre, filas, campos):
    ruta = os.path.join(carpeta, nombre + ".csv")
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    print("%-14s %5d filas %7d bytes" % (nombre, len(filas), os.path.getsize(ruta)))


def main(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    fichas = [modelo.cargar(p) for p in sorted(glob.glob(os.path.join(RAIZ, "base", "fichas", "*.json")))]
    rp = os.path.join(RAIZ, "base", "puntuaciones.json")
    punt = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {}
    hoy = date.today().isoformat()

    # copias enteras desde base/csv (ya con la clave)
    for t in ("sociedad", "accionista", "activo", "vencimiento"):
        filas = list(csv.DictReader(open(os.path.join(RAIZ, "base", "csv", t + ".csv"), encoding="utf-8"), delimiter=";"))
        escribir(carpeta, t, filas, list(filas[0].keys()) if filas else ["clave"])

    docs = list(csv.DictReader(open(os.path.join(RAIZ, "base", "csv", "documento.csv"), encoding="utf-8"), delimiter=";"))
    escribir(carpeta, "documento", docs, [c for c in docs[0].keys() if c not in ("huella", "bytes")])

    cifras = []
    for f in fichas:
        s = f["sociedad"]
        for anio, ej in sorted(f.get("ejercicios", {}).items()):
            fila = {"clave": modelo.clave(f), "nombre": s.get("nombre"), "segmento": s.get("segmento"), "ejercicio": anio}
            fuentes = set()
            for c in CAMPOS_CIFRAS:
                d = ej.get(c)
                fila[c] = d.get("valor") if d else ""
                if d and d.get("fuente"):
                    fuentes.add(d["fuente"])
            fila["contraste_min"] = "derivado" if any((ej.get(c) or {}).get("contraste") == "derivado" for c in CAMPOS_CIFRAS) else ""
            fila["fuentes"] = " | ".join(sorted(fuentes))[:1500]
            cifras.append(fila)
    escribir(carpeta, "cifras", cifras, ["clave", "nombre", "segmento", "ejercicio"] + CAMPOS_CIFRAS + ["contraste_min", "fuentes"])

    filas = []
    for f in fichas:
        s = f["sociedad"]
        p = punt.get(modelo.clave(f))
        fila = {"clave": modelo.clave(f), "nombre": s.get("nombre"), "segmento": s.get("segmento"), "provincia": s.get("provincia")}
        if p:
            ev = p["evaluacion"]
            fila.update({"fecha": p["hoy"], "puntos": ev["puntos"], "tramo": ev["tramo"], "cobertura": ev["cobertura"]})
            for d in ev["dimensiones"]:
                fila[d["id"] + "_puntos"] = d["puntos"]
                fila[d["id"] + "_max"] = d["max"]
                fila[d["id"] + "_estado"] = d["estado"]
                fila[d["id"] + "_detalle"] = " | ".join("%s: %s" % (x["etiqueta"], x["detalle"]) for x in d["partes"])[:160]
        filas.append(fila)
    dims = ["apalancamiento", "dividendos", "valor_liquidativo", "concentracion", "activos", "madurez"]
    escribir(carpeta, "puntuacion", filas, ["clave", "nombre", "segmento", "provincia", "fecha", "puntos", "tramo", "cobertura"] + [d + s for d in dims for s in ("_puntos", "_max", "_estado")])
    # el porqué de cada parte, en una hoja aparte y larga (una fila por sociedad y dimensión), para no engordar la principal
    largas = [{"clave": f["clave"], "nombre": f["nombre"], "dimension": d, "puntos": f.get(d + "_puntos"), "max": f.get(d + "_max"), "estado": f.get(d + "_estado"), "porque": f.get(d + "_detalle")}
              for f in filas if f.get("puntos") is not None for d in dims if f.get(d + "_detalle")]
    escribir(carpeta, "puntuacion_porque", largas, ["clave", "nombre", "dimension", "puntos", "max", "estado", "porque"])

    filas = []
    for f in fichas:
        vv = f.get("vinculo_vasco") or {}
        if not vv:
            continue
        s = f["sociedad"]
        filas.append({"clave": modelo.clave(f), "nombre": s.get("nombre"), "grado": vv.get("grado"), "n_activos_vascos": len(vv.get("activos", [])),
                      "valor_activos_vascos": sum((a.get("valor") or 0) for a in vv.get("activos", [])), "pct_valor_en_pais_vasco": vv.get("pct_valor_en_pais_vasco"),
                      "n_prestamos_vascos": len(vv.get("financiacion", [])), "n_menciones": len(vv.get("menciones", [])),
                      "primera_mencion": (vv.get("menciones") or [{}])[0].get("linea", "")[:200], "activos": "; ".join("%s (%s)" % (a.get("nombre"), a.get("ubicacion")) for a in vv.get("activos", []))[:500],
                      "entidades": "; ".join(sorted(set(x["entidad"] for x in vv.get("financiacion", []))))[:300]})
    escribir(carpeta, "vinculo_vasco", filas, list(filas[0].keys()))

    leeme = [
        {"hoja": "sociedad", "que_es": "Una fila por sociedad: identidad, mercado, domicilio, provincia, capitalización y la URL de su ficha en el mercado. clave = NIF o, si la fuente no lo publica, ISIN.", "fuente": "BME Growth/Scaleup (bolsasymercados.es), CNMV, Portfolio Stock Exchange, Euronext Access París", "nota": "Portfolio y Euronext: solo censo (sin documentos)."},
        {"hoja": "cifras", "que_es": "Un ejercicio por fila con las partidas leídas (euros; LTV en %). Las derivadas (deuda, deuda neta, LTV neto) llevan fórmula en la ficha. La fuente de cada cifra, en la columna fuentes y en base/csv/dato.csv del repositorio.", "fuente": "Cuentas anuales (PDF de BME, ESEF de la CNMV), avisos de dividendo y valoración", "nota": "Solo las sociedades con cuentas legibles; 57 publican las cuentas escaneadas (pendientes de OCR)."},
        {"hoja": "accionista", "que_es": "Accionistas significativos tal como los publica la sociedad (BME ≥ 5 %, CNMV ≥ 3 %), con tipo (jurídica/física) y fuente.", "fuente": "Avisos de participaciones significativas (BME), notificaciones de derechos de voto (CNMV)", "nota": "Sin cruzar con nada (decisión de Juan, 2026-10-26)."},
        {"hoja": "documento", "que_es": "Cada documento bajado: tipo, fecha, URL, si está escaneado. La huella SHA-256 está en base/csv/documento.csv.", "fuente": "BME, CNMV, Portfolio, Euronext", "nota": ""},
        {"hoja": "puntuacion", "que_es": "El motor: 100 puntos en seis dimensiones (apalancamiento 25, dividendos 20, valor liquidativo 15, concentración 15, activos 15, madurez 10) con el porqué de cada parte. ≥ 70 prioritaria, 50-69 interesante.", "fuente": "socimis/criterios.json", "nota": "Una nota baja con cobertura 1-2/6 significa «faltan datos», no «mala»."},
        {"hoja": "vinculo_vasco", "que_es": "El piloto: activos, préstamos de entidades vascas y menciones de lugares vascos en los documentos. Grado fuerte / indicio / ninguno.", "fuente": "Documentos de cada sociedad; gazetteer socimis/vasco.json", "nota": "Ninguna SOCIMI puede tener domicilio fiscal vasco (Normas Forales)."},
        {"hoja": "activo", "que_es": "Inmuebles de la tabla de inversiones inmobiliarias con ubicación y provincia (gazetteer nacional).", "fuente": "Memoria de las cuentas anuales", "nota": "Solo donde la tabla tiene texto legible."},
        {"hoja": "vencimiento", "que_es": "Tabla de vencimientos de deuda: entidad, importe, vencimiento.", "fuente": "Memoria de las cuentas anuales", "nota": ""},
    ]
    for l in leeme:
        l["generado"] = hoy
        l["repositorio"] = "Colmeee/socimis (privado), herramientas/hojas.py"
    escribir(carpeta, "LEEME", leeme, ["hoja", "que_es", "fuente", "nota", "generado", "repositorio"])


if __name__ == "__main__":
    main(sys.argv[1])

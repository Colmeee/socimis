"""La base estructurada: SQLite y CSV construidos desde las fichas JSON (`base/fichas/<NIF>.json`).

Por qué así: las fichas JSON son la verdad (una por sociedad, cada dato con su fuente); el SQLite y los CSV se
regeneran enteros a partir de ellas con `python3 -m socimis base`, así que son reproducibles y se versionan sin miedo.
Vale para todas las SOCIMIs de España aunque solo se carguen las del piloto.

Tablas: sociedad · dato (una fila por sociedad, ejercicio y campo, con valor, unidad, fecha, fuente, huella, consultado,
contraste, nota, donde) · accionista · vencimiento · activo · documento · puntuacion (una fila por sociedad y dimensión)
· vinculo_vasco. Los PDF no están aquí: solo su URL y su huella (tabla documento).
"""
import csv
import glob
import json
import os
import sqlite3

from . import modelo, geo

ESQUEMA = """
CREATE TABLE sociedad (clave TEXT PRIMARY KEY, nif TEXT, nombre TEXT, isin TEXT, ticker TEXT, mercado TEXT, segmento TEXT, domicilio TEXT, provincia TEXT,
  web TEXT, auditor TEXT, asesor_registrado TEXT, proveedor_liquidez TEXT, fecha_incorporacion TEXT, fecha_regimen_socimi TEXT,
  estado_cotizacion TEXT, capitalizacion REAL, cotizacion REAL, fecha_cotizacion TEXT, url_ficha TEXT, regimen_socimi TEXT);
CREATE TABLE dato (clave TEXT, ejercicio TEXT, campo TEXT, valor REAL, unidad TEXT, fecha TEXT, fuente TEXT, huella TEXT, consultado TEXT,
  contraste TEXT, nota TEXT, donde TEXT, PRIMARY KEY (clave, ejercicio, campo));
CREATE TABLE accionista (clave TEXT, accionista TEXT, tipo TEXT, pct_total REAL, pct_directo REAL, pct_indirecto REAL, a_traves_de TEXT, fecha TEXT,
  fuente TEXT, huella TEXT, contraste TEXT);
CREATE TABLE administrador (clave TEXT, nombre TEXT, cargo TEXT, desde TEXT, hasta TEXT, fuente TEXT);
CREATE TABLE vencimiento (clave TEXT, entidad TEXT, importe REAL, importe_anterior REAL, vencimiento TEXT, tipo_interes TEXT, fecha TEXT, fuente TEXT, huella TEXT);
CREATE TABLE activo (clave TEXT, nombre TEXT, ubicacion TEXT, provincia TEXT, valor REAL, valor_anterior REAL, fecha TEXT, fuente TEXT, huella TEXT);
CREATE TABLE documento (clave TEXT, tipo TEXT, fecha TEXT, url TEXT, huella TEXT, titulo TEXT, bytes INTEGER, escaneado INTEGER, revisar INTEGER, consultado TEXT);
CREATE TABLE puntuacion (clave TEXT, hoy TEXT, puntos REAL, tramo TEXT, cobertura INTEGER, dimension TEXT, puntos_dim REAL, max_dim INTEGER, estado TEXT, detalle TEXT);
CREATE TABLE vinculo_vasco (clave TEXT PRIMARY KEY, grado TEXT, n_activos INTEGER, valor_activos REAL, pct_valor REAL, n_prestamos INTEGER, n_menciones INTEGER, detalle TEXT);
"""

TABLAS = ["sociedad", "dato", "accionista", "administrador", "vencimiento", "activo", "documento", "puntuacion", "vinculo_vasco"]


def fichas_de(carpeta):
    for ruta in sorted(glob.glob(os.path.join(carpeta, "*.json"))):
        yield modelo.cargar(ruta)


def construir(carpeta_fichas, ruta_sqlite, carpeta_csv=None, puntuaciones=None):
    """Regenera el SQLite (y los CSV) desde las fichas. `puntuaciones`: {clave: (hoy, evaluacion)} opcional (clave = NIF o ISIN)."""
    if os.path.exists(ruta_sqlite):
        os.remove(ruta_sqlite)
    con = sqlite3.connect(ruta_sqlite)
    con.executescript(ESQUEMA)
    n = 0
    for f in fichas_de(carpeta_fichas):
        s = f["sociedad"]
        nif = modelo.clave(f) or ("SIN-CLAVE-%d" % n)  # la clave: NIF, o ISIN si la fuente no publica el NIF
        con.execute("INSERT OR REPLACE INTO sociedad VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (nif, s.get("nif"), s.get("nombre"), s.get("isin"), s.get("ticker"), s.get("mercado"), s.get("segmento"), s.get("domicilio"), s.get("provincia"),
                     s.get("web"), s.get("auditor"), s.get("asesor_registrado"), s.get("proveedor_liquidez"), s.get("fecha_incorporacion"),
                     s.get("fecha_regimen_socimi"), s.get("estado_cotizacion"), s.get("capitalizacion"), s.get("cotizacion"), s.get("fecha_cotizacion"), s.get("url_ficha"), s.get("regimen_socimi")))
        for anio, ej in f.get("ejercicios", {}).items():
            for campo, d in ej.items():
                con.execute("INSERT OR REPLACE INTO dato VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            (nif, anio, campo, d.get("valor"), d.get("unidad"), d.get("fecha"), d.get("fuente"), d.get("huella"), d.get("consultado"),
                             d.get("contraste"), d.get("nota"), d.get("donde")))
        for a in f.get("accionistas", []):
            con.execute("INSERT INTO accionista VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (nif, a.get("accionista"), a.get("tipo"), a.get("pct_total"), a.get("pct_directo"), a.get("pct_indirecto"), a.get("a_traves_de"),
                         a.get("fecha"), a.get("fuente"), a.get("huella"), a.get("contraste", "oficial")))
        for a in f.get("administradores", []):
            con.execute("INSERT INTO administrador VALUES (?,?,?,?,?,?)", (nif, a.get("nombre"), a.get("cargo"), a.get("desde"), a.get("hasta"), a.get("fuente")))
        for v in f.get("vencimientos", []):
            con.execute("INSERT INTO vencimiento VALUES (?,?,?,?,?,?,?,?,?)",
                        (nif, v.get("entidad"), v.get("importe"), v.get("importe_anterior"), v.get("vencimiento"), v.get("tipo_interes"), v.get("fecha"), v.get("fuente"), v.get("huella")))
        for a in f.get("activos", []):
            con.execute("INSERT INTO activo VALUES (?,?,?,?,?,?,?,?,?)",
                        (nif, a.get("nombre"), a.get("ubicacion"), geo.provincia_de_activo(a), a.get("valor"), a.get("valor_anterior"), a.get("fecha"), a.get("fuente"), a.get("huella")))
        for d in f.get("documentos", []):
            con.execute("INSERT INTO documento VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (nif, d.get("tipo"), d.get("fecha"), d.get("url"), d.get("huella"), d.get("titulo"), d.get("bytes"), 1 if d.get("escaneado") else 0, 1 if d.get("revisar") else 0, d.get("consultado")))
        vv = f.get("vinculo_vasco")
        if vv:
            con.execute("INSERT OR REPLACE INTO vinculo_vasco VALUES (?,?,?,?,?,?,?,?)",
                        (nif, vv.get("grado"), len(vv.get("activos", [])), sum((a.get("valor") or 0) for a in vv.get("activos", [])), vv.get("pct_valor_en_pais_vasco"),
                         len(vv.get("financiacion", [])), len(vv.get("menciones", [])), json.dumps(vv, ensure_ascii=False)))
        if puntuaciones and nif in puntuaciones:
            hoy, ev = puntuaciones[nif]
            for d in ev["dimensiones"]:
                con.execute("INSERT INTO puntuacion VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (nif, hoy, ev["puntos"], ev["tramo"], ev["cobertura"], d["id"], d["puntos"], d["max"], d["estado"],
                             " | ".join("%s: %s" % (p["etiqueta"], p["detalle"]) for p in d["partes"])))
        n += 1
    con.commit()
    if carpeta_csv:
        exportar_csv(con, carpeta_csv)
    con.close()
    return n


def exportar_csv(con, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    for t in TABLAS:
        cur = con.execute("SELECT * FROM %s ORDER BY 1, 2, 3" % t)
        with open(os.path.join(carpeta, t + ".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow([d[0] for d in cur.description])
            for fila in cur:
                w.writerow(["" if v is None else v for v in fila])

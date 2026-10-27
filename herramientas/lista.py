"""Escribe docs/LISTA-SOCIMIS.md: todas las sociedades de la base en una tabla, ordenadas por puntuación, con lo que hace
falta para leerla de un vistazo (segmento, provincia, puntos, vínculo vasco, si las cuentas están escaneadas, GAV, documentos).
`python3 herramientas/lista.py` desde la raíz. Puro salvo la escritura del fichero."""
import glob
import json
import os
import sys
from collections import Counter
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from socimis import modelo  # noqa: E402


def _eur(v):
    return "—" if v is None else "%.0f M€" % (v / 1e6)


def main():
    fichas = [modelo.cargar(p) for p in sorted(glob.glob(os.path.join(RAIZ, "base", "fichas", "*.json")))]
    rp = os.path.join(RAIZ, "base", "puntuaciones.json")
    punt = {k: v["evaluacion"] for k, v in json.load(open(rp, encoding="utf-8")).items()} if os.path.exists(rp) else {}
    filas = []
    for f in fichas:
        s, ev = f["sociedad"], punt.get(modelo.clave(f), {})
        vv = f.get("vinculo_vasco") or {}
        esc = any(d.get("escaneado") and d.get("tipo") == "cuentas_anuales" for d in f.get("documentos", []))
        ej = modelo.ultimo_ejercicio(f)
        gav = (modelo.valor(f, ej, "gav_valoracion") or modelo.valor(f, ej, "valor_razonable_inmuebles")) if ej else None
        docs = len([d for d in f.get("documentos", []) if d.get("tipo") != "censo"])
        filas.append((s.get("nombre"), s.get("segmento"), s.get("provincia") or "—", modelo.clave(f), ev.get("puntos"), ev.get("tramo"), vv.get("grado"), esc, gav, docs, s.get("regimen_socimi")))
    filas.sort(key=lambda r: (-(r[4] or 0), r[0] or ""))
    L = ["# Las SOCIMIs de la base (%s)" % date.today().isoformat(), "",
         "%d sociedades, ordenadas por la puntuación del motor. «Escaneada» = cuentas anuales sin capa de texto (a la cola de OCR del Mac): la nota es baja por falta de datos, no por malas cifras. "
         "Las de Portfolio Stock Exchange y Euronext Access París son **solo censo** (nombre, ISIN, precio): sus documentos no se han leído (ver `docs/CENSO-ESPANA.md`, «Lo que no se ha mirado»). "
         "«Régimen»: si la palabra SOCIMI está en el nombre; Portfolio y Euronext no publican el régimen fiscal y los nombres de Euronext vienen recortados. GAV = valor de los inmuebles cuando se ha leído." % len(filas), "",
         "| # | Sociedad | Segmento | Provincia | Clave (NIF o ISIN) | Puntos | Tramo | Vínculo vasco | Escaneada | GAV | Docs | Régimen |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(filas, 1):
        L.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %d | %s |" % (i, r[0], r[1], r[2], r[3], "—" if r[4] is None else "%.1f" % r[4], r[5] or "—", r[6] or "—", "sí" if r[7] else "no", _eur(r[8]), r[9], r[10] or "—"))
    for titulo, idx in (("Por provincia del domicilio social", 2), ("Por segmento", 1)):
        c = Counter(r[idx] for r in filas)
        L += ["", "## %s" % titulo, "", "| %s | Sociedades |" % titulo.split(" ")[1].capitalize(), "|---|---|"] + ["| %s | %d |" % (k, n) for k, n in c.most_common()]
    with open(os.path.join(RAIZ, "docs", "LISTA-SOCIMIS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("docs/LISTA-SOCIMIS.md: %d sociedades" % len(filas))


if __name__ == "__main__":
    main()

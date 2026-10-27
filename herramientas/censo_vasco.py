"""Escribe docs/CENSO-VINCULO-VASCO.md a partir de las fichas: el censo del piloto.

Por qué existe: el piloto del País Vasco no es «SOCIMIs con domicilio vasco» (no puede haberlas: las Normas Forales
eliminaron el régimen) sino «SOCIMIs con vínculo vasco» (decisión de Juan, 2026-10-26): activos en Álava, Bizkaia o
Gipuzkoa, préstamos de entidades vascas, menciones en sus documentos. Este guion lee `base/fichas/*.json` y escribe el
censo con la evidencia de cada vínculo, más el estado de la base (cuántas leídas, cuántas escaneadas) para que el
documento diga también lo que NO se ha podido mirar. Puro salvo la escritura del fichero; se lanza con
`python3 herramientas/censo_vasco.py` desde la raíz del repositorio.
"""
import glob
import json
import os
import sys
from datetime import date

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from socimis import modelo  # noqa: E402


def _eur(v):
    if v is None:
        return "—"
    return ("%.1f M€" % (v / 1e6)).replace(".", ",") if abs(v) >= 1e5 else ("%.0f €" % v)


def _f(s):
    return s if s is not None else "—"


def main():
    fichas = [modelo.cargar(p) for p in sorted(glob.glob(os.path.join(RAIZ, "base", "fichas", "*.json")))]
    punt = {}
    rp = os.path.join(RAIZ, "base", "puntuaciones.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as fh:
            punt = {nif: v["evaluacion"] for nif, v in json.load(fh).items()}
    hoy = date.today().isoformat()
    por_seg = {}
    for f in fichas:
        por_seg[f["sociedad"].get("segmento") or "?"] = por_seg.get(f["sociedad"].get("segmento") or "?", 0) + 1
    domicilio_vasco = [f for f in fichas if (f["sociedad"].get("provincia") or "") in ("Álava", "Bizkaia", "Gipuzkoa")]
    fuertes = [f for f in fichas if (f.get("vinculo_vasco") or {}).get("grado") == "fuerte"]
    indicios = [f for f in fichas if (f.get("vinculo_vasco") or {}).get("grado") == "indicio"]
    escaneadas = [f for f in fichas if any(d.get("escaneado") and d.get("tipo") == "cuentas_anuales" for d in f.get("documentos", []))]
    con_cuentas = [f for f in fichas if modelo.ultimo_ejercicio(f) and modelo.valor(f, modelo.ultimo_ejercicio(f), "tesoreria") is not None]

    L = ["# Censo del piloto: SOCIMIs cotizadas con vínculo vasco", "",
         "Generado el %s por `herramientas/censo_vasco.py` desde `base/fichas/` (%d sociedades). Las fuentes de cada dato están en las fichas y en `base/socimis.sqlite`." % (hoy, len(fichas)), "",
         "## Lo primero: por domicilio no hay ninguna", "",
         "Sociedades con domicilio social en Álava, Bizkaia o Gipuzkoa: **%d de %d**. Es lo esperado: las tres Normas Forales del Impuesto sobre Sociedades eliminaron el régimen SOCIMI (ver `VEREDICTO-FASE-1.md`, pero 1). Por eso el piloto mide el **vínculo**: activos, financiación y menciones en los documentos que la propia sociedad publica." % (len(domicilio_vasco), len(fichas)), "",
         "## Estado de la base", "",
         "| Segmento | Sociedades |", "|---|---|"] + ["| %s | %d |" % (s, n) for s, n in sorted(por_seg.items())] + ["",
         "- Con cuentas anuales leídas (tesorería en la base): **%d**." % len(con_cuentas),
         "- Con las cuentas anuales **escaneadas** (sin capa de texto; a la cola de OCR del Mac, `python3 -m socimis ocr-pendientes`): **%d**. En estas el vínculo solo puede verse en los avisos cortos (participaciones, dividendos, valoración), no en la memoria." % len(escaneadas),
         "- Vínculo vasco **fuerte** (activos o financiación): **%d**. **Indicio** (solo menciones): **%d**. **Ninguno**: **%d**." % (len(fuertes), len(indicios), len(fichas) - len(fuertes) - len(indicios)), ""]

    L += ["## Vínculo fuerte", ""]
    if not fuertes:
        L.append("Ninguna todavía.")
    for f in sorted(fuertes, key=lambda x: -((x.get("vinculo_vasco") or {}).get("pct_valor_en_pais_vasco") or 0)):
        s, vv = f["sociedad"], f["vinculo_vasco"]
        ev = punt.get(modelo.clave(f), {})
        L += ["### %s · %s · %s" % (s.get("nombre"), s.get("segmento"), "%s puntos (%s)" % (ev.get("puntos"), ev.get("tramo")) if ev else "sin puntuar"),
              "Domicilio: %s. NIF %s. Web: %s." % (_f(s.get("domicilio")), _f(s.get("nif")), _f(s.get("web"))),
              "Valor en el País Vasco: **%s %% del valor de los inmuebles con ubicación publicada**." % _f(vv.get("pct_valor_en_pais_vasco")), ""]
        if vv.get("activos"):
            L += ["| Activo | Ubicación | Provincia | Valor | Fuente |", "|---|---|---|---|---|"]
            L += ["| %s | %s | %s | %s | %s |" % (a.get("nombre"), a.get("ubicacion"), a.get("provincia"), _eur(a.get("valor")), a.get("fuente") or "—") for a in vv["activos"]]
            L.append("")
        if vv.get("financiacion"):
            L += ["Préstamos de entidades vascas (tabla de vencimientos de la memoria):", ""]
            L += ["- %s: %s, vence %s" % (x["entidad"], _eur(x.get("importe")), x.get("vencimiento")) for x in vv["financiacion"][:12]]
            if len(vv["financiacion"]) > 12:
                L.append("- … y %d más" % (len(vv["financiacion"]) - 12))
            L.append("")
        if vv.get("menciones"):
            L += ["Menciones (%d; las primeras):" % len(vv["menciones"]), ""]
            L += ["- *%s* — «%s»" % (m["lugar"], m["linea"]) for m in vv["menciones"][:5]]
            L.append("")

    L += ["## Indicio (solo menciones en los textos)", ""]
    if not indicios:
        L.append("Ninguna.")
    for f in indicios:
        s, vv = f["sociedad"], f["vinculo_vasco"]
        L += ["- **%s** (%s): %d menciones; p. ej. *%s* — «%s»" % (s.get("nombre"), s.get("segmento"), len(vv["menciones"]), vv["menciones"][0]["lugar"], vv["menciones"][0]["linea"][:120])]
    L += ["", "## Sin vínculo encontrado", "", "Las %d restantes no nombran ningún lugar vasco ni tienen préstamos de entidades vascas en lo leído. Para las escaneadas (%d) esto no significa «no»: significa «no leído». La lista completa, con segmento y domicilio, está en `base/csv/sociedad.csv` y `base/csv/vinculo_vasco.csv`." % (len(fichas) - len(fuertes) - len(indicios), len(escaneadas)), "",
          "## Cómo se ha medido", "",
          "`socimis/vinculo_vasco.py` con el gazetteer `socimis/vasco.json` (provincias en castellano y euskera, municipios de más de 15.000 habitantes y entidades financieras con sede vasca) sobre la tabla de inversiones inmobiliarias, la tabla de vencimientos y el texto de los documentos bajados (cuentas anuales, semestral, valoración, participaciones, dividendo). Un lugar que falte en el gazetteer no se detecta: se amplía el JSON y se repite `python3 -m socimis vasco todas`."]
    salida = os.path.join(RAIZ, "docs", "CENSO-VINCULO-VASCO.md")
    with open(salida, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("%s: %d sociedades, %d fuertes, %d indicios, %d escaneadas" % (salida, len(fichas), len(fuertes), len(indicios), len(escaneadas)))


if __name__ == "__main__":
    main()

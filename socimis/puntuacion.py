"""El motor: de una ficha a 100 puntos en seis dimensiones, cada punto con su porqué y su fuente.

Rehecho para SOCIMIs (2026-10-26). Una SOCIMI no es una empresa con caja ociosa: lo que distingue a una de otra es el
apalancamiento (LTV y vencimientos), si reparte dividendo, cómo cotiza frente a su valor liquidativo, quién manda
(concentración accionarial), qué activos tiene y cuánto lleva en el mercado. Los pesos y umbrales están en
criterios.json; aquí solo la lógica. Como en Cantera: cada parte sale «cumplida», «parcial», «no cumplida» o
«sin datos»; la cobertura cuenta las dimensiones con datos; lo que no consta no resta ni se supone.

Puro: ni ficheros, ni red, ni la fecha de hoy (entra por parámetro). Dos ejecuciones iguales dan lo mismo.
Python 3.9.
"""
import json
import math
from pathlib import Path

from . import modelo

AQUI = Path(__file__).resolve().parent
ORDEN = ["apalancamiento", "dividendos", "valor_liquidativo", "concentracion", "activos", "madurez"]
NOMBRES = {"apalancamiento": "Apalancamiento", "dividendos": "Dividendos", "valor_liquidativo": "Valor liquidativo",
           "concentracion": "Concentración accionarial", "activos": "Activos", "madurez": "Madurez en el mercado"}


class CriteriosInvalidos(Exception):
    pass


def cargar_criterios(ruta=None):
    with open(ruta or AQUI / "criterios.json", encoding="utf-8") as f:
        c = json.load(f)
    validar(c)
    return c


def validar(c):
    errores = []
    total = sum(c[d]["peso"] for d in ORDEN)
    if total != 100:
        errores.append("los pesos suman %d, no 100" % total)
    for d in ORDEN:
        partes = sum(v["puntos"] for k, v in c[d].items() if isinstance(v, dict) and "puntos" in v)
        if partes != c[d]["peso"]:
            errores.append("%s: las partes suman %d y el peso es %d" % (d, partes, c[d]["peso"]))
    if errores:
        raise CriteriosInvalidos("criterios.json no cuadra: " + "; ".join(errores))


# ----------------------------------------------------------------------------- utilidades
def _lineal(x, cero, maximo):
    """0 en `cero`, 1 en `maximo`, lineal entre medias (sirve con cero > maximo para escalas descendentes)."""
    if x is None:
        return None
    if cero == maximo:
        return 1.0 if x >= maximo else 0.0
    t = (x - cero) / float(maximo - cero)
    return max(0.0, min(1.0, t))


def _estado(pts, mx):
    if pts is None:
        return "sin datos"
    if pts >= mx - 1e-9:
        return "cumplida"
    if pts <= 1e-9:
        return "no cumplida"
    return "parcial"


def _parte(etiqueta, pts, mx, detalle, fuente=None):
    return {"etiqueta": etiqueta, "puntos": None if pts is None else round(pts, 1), "max": mx, "estado": _estado(pts, mx), "detalle": detalle, "fuente": fuente}


def _dimension(id_, peso, partes):
    con_datos = [p for p in partes if p["puntos"] is not None]
    pts = round(sum(p["puntos"] for p in con_datos), 1) if con_datos else None
    return {"id": id_, "nombre": NOMBRES[id_], "puntos": pts, "max": peso, "estado": _estado(pts, peso) if con_datos else "sin datos", "partes": partes}


def _d(ficha, anio, campo):
    """(valor, fuente) del dato de un ejercicio, o (None, None)."""
    if anio is None:
        return None, None
    d = ficha["ejercicios"].get(anio, {}).get(campo)
    if not d or d.get("valor") is None:
        return None, None
    return d["valor"], d.get("fuente") or d.get("nota")


def _fmt_eur(v):
    if v is None:
        return "—"
    if abs(v) >= 1e6:
        return "%s M€" % ("%.1f" % (v / 1e6)).replace(".", ",")
    return "%s €" % ("{:,.0f}".format(v)).replace(",", ".")


# ----------------------------------------------------------------------------- dimensiones
def dim_apalancamiento(ficha, c, hoy):
    cfg = c["apalancamiento"]
    anio = modelo.ultimo_ejercicio(ficha)
    ltv, f_ltv = _d(ficha, anio, "ltv_declarado")
    origen = "declarado por la sociedad"
    if ltv is None:
        ltv, f_ltv = _d(ficha, anio, "ltv_neto")
        origen = "calculado: deuda neta / valor de los inmuebles"
    k = cfg["ltv"]
    if ltv is None:
        p1 = _parte("LTV", None, k["puntos"], "sin deuda ni valor de inmuebles con que calcularlo (no consta)")
    else:
        pts = k["puntos"] * _lineal(ltv, k["maximo_pct"], k["holgado_pct"])
        p1 = _parte("LTV", pts, k["puntos"], "LTV %s %% (%s); %d %% o menos da el máximo, %d %% o más da 0" % (str(ltv).replace(".", ","), origen, k["holgado_pct"], k["maximo_pct"]), f_ltv)
    k = cfg["vencimientos"]
    venc = [v for v in ficha.get("vencimientos", []) if v.get("vencimiento") and v.get("importe")]
    total = sum(v["importe"] for v in venc)
    if not venc or total <= 0:
        p2 = _parte("Vencimientos a %d años" % k["horizonte_anios"], None, k["puntos"], "sin tabla de vencimientos de la deuda (no consta)")
    else:
        limite = "%04d-%s" % (int(hoy[:4]) + k["horizonte_anios"], hoy[5:])
        pronto = sum(v["importe"] for v in venc if v["vencimiento"] <= limite)
        pct = 100.0 * pronto / total
        pts = k["puntos"] * _lineal(pct, k["tenso_pct"], k["tranquilo_pct"])
        p2 = _parte("Vencimientos a %d años" % k["horizonte_anios"], pts, k["puntos"],
                    "%s de %s (%s %%) vence antes de %s en %d préstamos; ≤ %d %% da el máximo, ≥ %d %% da 0" % (_fmt_eur(pronto), _fmt_eur(total), ("%.0f" % pct), limite, len(venc), k["tranquilo_pct"], k["tenso_pct"]),
                    venc[0].get("fuente"))
    return _dimension("apalancamiento", cfg["peso"], [p1, p2])


def dim_dividendos(ficha, c, hoy):
    cfg = c["dividendos"]
    anio = modelo.ultimo_ejercicio(ficha)
    acordado, f1 = _d(ficha, anio, "dividendo_acordado")
    pagado, f2 = _d(ficha, anio, "dividendos_pagados")
    div = acordado if acordado is not None else pagado
    fuente = f1 if acordado is not None else f2
    k = cfg["reparte"]
    if div is None:
        p1 = _parte("Reparte dividendo", None, k["puntos"], "ni dividendo acordado ni pagado en el último ejercicio (no consta)")
    else:
        p1 = _parte("Reparte dividendo", k["puntos"] if div > 0 else 0.0, k["puntos"],
                    "%s %s con cargo a %s" % (_fmt_eur(div), "acordados" if acordado is not None else "pagados", anio), fuente)
    k = cfg["rendimiento"]
    cap = ficha["sociedad"].get("capitalizacion")
    if div is None or not cap:
        p2 = _parte("Rendimiento sobre capitalización", None, k["puntos"], "falta el dividendo o la capitalización")
    else:
        pct = 100.0 * div / cap
        p2 = _parte("Rendimiento sobre capitalización", k["puntos"] * _lineal(pct, k["minimo_pct"], k["bueno_pct"]), k["puntos"],
                    "%s %% (%s sobre %s de capitalización)" % (("%.1f" % pct).replace(".", ","), _fmt_eur(div), _fmt_eur(cap)), fuente)
    k = cfg["crece"]
    anterior = str(int(anio) - 1) if anio else None
    ant_a, _ = _d(ficha, anterior, "dividendo_acordado")
    ant_p, _ = _d(ficha, anterior, "dividendos_pagados")
    ant = ant_a if ant_a is not None else ant_p
    if div is None or ant is None:
        p3 = _parte("Crece", None, k["puntos"], "sin dividendo del ejercicio anterior con que comparar")
    else:
        p3 = _parte("Crece", k["puntos"] if div > ant else 0.0, k["puntos"], "%s frente a %s del ejercicio anterior" % (_fmt_eur(div), _fmt_eur(ant)), fuente)
    return _dimension("dividendos", cfg["peso"], [p1, p2, p3])


def dim_valor_liquidativo(ficha, c, hoy):
    cfg = c["valor_liquidativo"]
    anio = modelo.ultimo_ejercicio(ficha)
    k = cfg["descuento"]
    nav, f_nav = _d(ficha, anio, "nav_por_accion")
    cot = ficha["sociedad"].get("cotizacion")
    if nav is None or not cot:
        # sin NAV por acción, se usa patrimonio neto frente a capitalización
        pn, f_nav = _d(ficha, anio, "patrimonio_neto")
        cap = ficha["sociedad"].get("capitalizacion")
        if pn and cap:
            desc = 100.0 * (1 - cap / pn)
            p1 = _parte("Cotización frente al valor", k["puntos"] * _lineal(desc, k["descuento_maximo_pct"], 0), k["puntos"],
                        "capitalización %s frente a patrimonio neto %s: %s %% de %s (por falta de NAV por acción)" % (_fmt_eur(cap), _fmt_eur(pn), ("%.0f" % abs(desc)), "descuento" if desc > 0 else "prima"), f_nav)
        else:
            p1 = _parte("Cotización frente al valor", None, k["puntos"], "sin NAV por acción ni patrimonio neto con capitalización (no consta)")
    else:
        desc = 100.0 * (1 - cot / nav)
        p1 = _parte("Cotización frente al valor", k["puntos"] * _lineal(desc, k["descuento_maximo_pct"], 0), k["puntos"],
                    "cotiza a %s con NAV de %s por acción: %s %% de %s" % (_fmt_eur(cot), _fmt_eur(nav), ("%.0f" % abs(desc)), "descuento" if desc > 0 else "prima"), f_nav)
    k = cfg["valoracion_externa"]
    gav, f_gav = _d(ficha, anio, "gav_valoracion")
    if gav is None:
        p2 = _parte("Valoración externa", 0.0 if anio else None, k["puntos"], "no se ha encontrado una valoración externa comunicada al mercado" if anio else "sin ejercicio")
    else:
        p2 = _parte("Valoración externa", k["puntos"], k["puntos"], "valoración externa de %s comunicada al mercado" % _fmt_eur(gav), f_gav)
    return _dimension("valor_liquidativo", cfg["peso"], [p1, p2])


def dim_concentracion(ficha, c, hoy):
    cfg = c["concentracion"]
    acc = [a for a in ficha.get("accionistas", []) if a.get("pct_total") is not None]
    if not acc:
        return _dimension("concentracion", cfg["peso"], [_parte(e, None, cfg[k]["puntos"], "sin participaciones significativas publicadas (no consta)")
                                                           for e, k in (("Mayor accionista", "mayor_accionista"), ("Suma de significativos", "suma_significativos"), ("Persona física detrás", "persona_fisica_detras"))])
    fuente = acc[0].get("fuente")
    # las personas físicas que participan «a través de» una sociedad ya listada no se suman dos veces
    juridicas = [a for a in acc if a.get("tipo") != "fisica"]
    base = juridicas if juridicas else acc
    k = cfg["mayor_accionista"]
    mayor = max(base, key=lambda a: a["pct_total"])
    p1 = _parte("Mayor accionista", k["puntos"] * _lineal(mayor["pct_total"], 5, k["control_pct"]), k["puntos"],
                "%s con el %s %%" % (mayor["accionista"], str(mayor["pct_total"]).replace(".", ",")), fuente)
    k = cfg["suma_significativos"]
    suma = sum(a["pct_total"] for a in base)
    p2 = _parte("Suma de significativos", k["puntos"] * _lineal(suma, 5, k["alto_pct"]), k["puntos"],
                "%d accionistas ≥ 5 %% suman el %s %%" % (len(base), ("%.1f" % suma).replace(".", ",")), fuente)
    k = cfg["persona_fisica_detras"]
    fisicas = [a for a in acc if a.get("tipo") == "fisica"]
    p3 = _parte("Persona física detrás", k["puntos"] if fisicas else 0.0, k["puntos"],
                "%d persona(s) física(s) publicadas como titulares significativos" % len(fisicas) if fisicas else "ninguna persona física publicada entre los significativos", fuente)
    return _dimension("concentracion", cfg["peso"], [p1, p2, p3])


def dim_activos(ficha, c, hoy):
    cfg = c["activos"]
    anio = modelo.ultimo_ejercicio(ficha)
    gav, f_gav = _d(ficha, anio, "gav_valoracion")
    if gav is None:
        gav, f_gav = _d(ficha, anio, "valor_razonable_inmuebles")
    k = cfg["tamano"]
    if gav is None or gav <= 0:
        p1 = _parte("Tamaño de la cartera", None, k["puntos"], "sin valor de los inmuebles (no consta)")
    else:
        t = _lineal(math.log10(gav), math.log10(k["minimo_eur"]), math.log10(k["grande_eur"]))
        p1 = _parte("Tamaño de la cartera", k["puntos"] * t, k["puntos"], "inmuebles por %s" % _fmt_eur(gav), f_gav)
    k = cfg["diversificacion"]
    activos = [a for a in ficha.get("activos", []) if a.get("valor")]
    if not activos:
        p2 = _parte("Diversificación", None, k["puntos"], "sin lista de activos con valor (no consta)")
    else:
        p2 = _parte("Diversificación", k["puntos"] * _lineal(len(activos), k["pocos"], k["muchos"]), k["puntos"], "%d activos con valor publicado" % len(activos), activos[0].get("fuente"))
    k = cfg["rentas_sobre_valor"]
    rentas, f_r = _d(ficha, anio, "ingresos_rentas")
    if rentas is None:
        rentas, f_r = _d(ficha, anio, "ingresos")
    if rentas is None or gav is None or gav <= 0:
        p3 = _parte("Rentas sobre valor", None, k["puntos"], "faltan las rentas o el valor de los inmuebles")
    else:
        pct = 100.0 * rentas / gav
        p3 = _parte("Rentas sobre valor", k["puntos"] * _lineal(pct, k["minimo_pct"], k["bueno_pct"]), k["puntos"], "%s %% (%s de rentas sobre %s)" % (("%.1f" % pct).replace(".", ","), _fmt_eur(rentas), _fmt_eur(gav)), f_r)
    return _dimension("activos", cfg["peso"], [p1, p2, p3])


def dim_madurez(ficha, c, hoy):
    cfg = c["madurez"]
    s = ficha["sociedad"]
    k = cfg["mercado"]
    seg = s.get("segmento") or s.get("mercado")
    pts = None
    for nombre, v in k["valores"].items():
        if seg and nombre.lower() in seg.lower():
            pts = float(v)
    p1 = _parte("Mercado", pts, k["puntos"], "%s" % (seg or "mercado no consta"), s.get("url_ficha"))
    k = cfg["antiguedad"]
    inc = s.get("fecha_incorporacion")
    if not inc:
        p2 = _parte("Antigüedad en el mercado", None, k["puntos"], "sin fecha de incorporación (no consta)")
    else:
        anios = (int(hoy[:4]) - int(inc[:4])) + (int(hoy[5:7]) - int(inc[5:7])) / 12.0
        p2 = _parte("Antigüedad en el mercado", k["puntos"] * _lineal(anios, 0, k["anios_pleno"]), k["puntos"], "cotiza desde %s (%.1f años)" % (inc, anios), s.get("url_ficha"))
    k = cfg["informa"]
    docs = ficha.get("documentos", [])
    cerrado = str(int(hoy[:4]) - 1)
    anual = [d for d in docs if d.get("tipo") == "cuentas_anuales" and (d.get("fecha") or "") >= cerrado]
    semestral = [d for d in docs if d.get("tipo") == "semestral" and (d.get("fecha") or "") >= cerrado]
    if not docs:
        p3 = _parte("Publica lo que debe", None, k["puntos"], "sin lista de documentos (no consta)")
    else:
        pts = (k["puntos"] / 2.0 if anual else 0.0) + (k["puntos"] / 2.0 if semestral else 0.0)
        p3 = _parte("Publica lo que debe", pts, k["puntos"], "cuentas anuales recientes: %s; semestral reciente: %s" % ("sí" if anual else "no", "sí" if semestral else "no"),
                    (anual or semestral or docs)[0].get("url"))
    return _dimension("madurez", cfg["peso"], [p1, p2, p3])


DIMENSIONES = {"apalancamiento": dim_apalancamiento, "dividendos": dim_dividendos, "valor_liquidativo": dim_valor_liquidativo,
               "concentracion": dim_concentracion, "activos": dim_activos, "madurez": dim_madurez}


def tramo_de(puntos, c):
    if puntos is None:
        return "sin datos"
    if puntos >= c["tramos"]["prioritaria"]:
        return "prioritaria"
    if puntos >= c["tramos"]["interesante"]:
        return "interesante"
    return "de momento no"


def evaluar(ficha, c, hoy):
    """{puntos, tramo, cobertura, dimensiones, avisos}. `hoy` = 'AAAA-MM-DD'."""
    dims = [DIMENSIONES[d](ficha, c, hoy) for d in ORDEN]
    con_datos = [d for d in dims if d["puntos"] is not None]
    puntos = round(sum(d["puntos"] for d in con_datos), 1) if con_datos else None
    cobertura = len(con_datos)
    avisos = []
    if cobertura < c["cobertura_minima"]:
        avisos.append("cobertura %d de %d: la puntuación dice poco" % (cobertura, len(ORDEN)))
    return {"puntos": puntos, "tramo": tramo_de(puntos, c), "cobertura": cobertura, "de": len(ORDEN), "dimensiones": dims, "avisos": avisos}


def texto(ev, ficha):
    """La ficha de puntuación en Markdown, con el porqué de cada parte."""
    s = ficha["sociedad"]
    lineas = ["### %s · %s puntos · %s · cobertura %d/%d" % (s.get("nombre"), ev["puntos"] if ev["puntos"] is not None else "—", ev["tramo"], ev["cobertura"], ev["de"])]
    for d in ev["dimensiones"]:
        lineas.append("- **%s** %s/%d (%s)" % (d["nombre"], d["puntos"] if d["puntos"] is not None else "—", d["max"], d["estado"]))
        for p in d["partes"]:
            f = (" · fuente: %s" % p["fuente"]) if p.get("fuente") else ""
            lineas.append("  - %s: %s/%d, %s — %s%s" % (p["etiqueta"], p["puntos"] if p["puntos"] is not None else "—", p["max"], p["estado"], p["detalle"], f))
    for a in ev["avisos"]:
        lineas.append("- ⚠️ " + a)
    return "\n".join(lineas)

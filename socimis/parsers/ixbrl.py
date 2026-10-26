"""Lector de informes financieros anuales en formato ESEF (xhtml con iXBRL), los que la CNMV publica de las SOCIMIs
del mercado principal.

Por qué existe: es la única vía realmente programática a las cuentas de una SOCIMI. Cada cifra va etiquetada con un
concepto de la taxonomía IFRS (`ifrs-full:CashAndCashEquivalents`), un contexto (fecha o periodo, y si lleva
dimensiones) y una escala (3 = miles). Aquí se leen los hechos sin dimensión (el total consolidado) de los conceptos
que necesita la base. Sin dependencias: expresiones regulares sobre el xhtml, que puede pesar 50 MB (Merlin, 2025).

Lo que no hace: no valida la taxonomía, no lee hechos con dimensiones (segmentos), no lee texto (ix:nonNumeric).
Lo que Merlin NO etiqueta y por tanto no sale de aquí: el LTV, las rentas brutas (solo `Revenue`), el NAV por acción.
"""
import re

# concepto IFRS -> campo de la ficha (ver modelo.CAMPOS_EJERCICIO)
CONCEPTOS = {
    "ifrs-full:CashAndCashEquivalents": "tesoreria",
    "ifrs-full:InvestmentProperty": "valor_razonable_inmuebles",
    "ifrs-full:NoncurrentPortionOfNoncurrentBondsIssued": "bonos_lp",
    "ifrs-full:CurrentBondsIssuedAndCurrentPortionOfNoncurrentBondsIssued": "bonos_cp",
    "ifrs-full:NoncurrentPortionOfNoncurrentLoansReceived": "prestamos_lp",
    "ifrs-full:CurrentLoansReceivedAndCurrentPortionOfNoncurrentLoansReceived": "prestamos_cp",
    "ifrs-full:Revenue": "ingresos",
    "ifrs-full:DividendsPaid": "dividendos_pagados",
    "ifrs-full:Equity": "patrimonio_neto",
    "ifrs-full:Assets": "activo_total",
    "ifrs-full:NoncurrentLiabilities": "pasivo_no_corriente",
    "ifrs-full:CurrentLiabilities": "pasivo_corriente",
}

RE_CONTEXTO = re.compile(r'<xbrli:context\s+id="([^"]+)"\s*>(.*?)</xbrli:context>', re.S)
RE_HECHO = re.compile(r"<ix:nonFraction([^>]*)>(.*?)</ix:nonFraction>", re.S)
RE_ATRIBUTOS = re.compile(r'([\w:.-]+)="([^"]*)"')
RE_ETIQUETA = re.compile(r"<[^>]+>")


def contextos(texto):
    """id -> {"fin": AAAA-MM-DD, "inicio": AAAA-MM-DD o None, "dimensiones": bool}."""
    salida = {}
    for m in RE_CONTEXTO.finditer(texto):
        cuerpo = m.group(2)
        instante = re.search(r"<xbrli:instant>\s*([^<\s]+)", cuerpo)
        inicio = re.search(r"<xbrli:startDate>\s*([^<\s]+)", cuerpo)
        fin = re.search(r"<xbrli:endDate>\s*([^<\s]+)", cuerpo)
        salida[m.group(1)] = {
            "fin": (instante or fin).group(1) if (instante or fin) else None,
            "inicio": inicio.group(1) if inicio else None,
            "dimensiones": "explicitMember" in cuerpo or "typedMember" in cuerpo,
        }
    return salida


def _numero(texto, formato):
    """El texto visible de un hecho («1.214.945», «(10.033)», «-») a float, según el formato iXBRL declarado
    (ixt:num-dot-decimal, ixt:num-comma-decimal, ixt4:num-dot-decimal...). Sin formato se supone el español (punto de miles)."""
    t = RE_ETIQUETA.sub("", texto).strip().replace("\xa0", "").replace(" ", "")
    if t in ("", "-", "—", "–"):
        return 0.0
    negativo = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if "comma-decimal" in (formato or ""):
        t = t.replace(".", "").replace(",", ".")
    elif "dot-decimal" in (formato or ""):
        t = t.replace(",", "")
    else:
        t = t.replace(".", "").replace(",", ".")      # sin formato declarado se supone el español (los ESEF de la CNMV usan num-comma-decimal)
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if negativo else v


def hechos(texto, conceptos=CONCEPTOS):
    """Lista de {concepto, campo, valor (euros, ya escalado y con signo), fin, inicio, id}. Solo hechos sin dimensiones.
    Si un mismo concepto y periodo aparece varias veces (balance y notas), se queda con el primero y comprueba que coinciden."""
    ctx = contextos(texto)
    vistos = {}
    salida = []
    for m in RE_HECHO.finditer(texto):
        a = dict(RE_ATRIBUTOS.findall(m.group(1)))
        nombre = a.get("name")
        if nombre not in conceptos:
            continue
        c = ctx.get(a.get("contextRef"))
        if c is None or c["dimensiones"]:
            continue
        v = _numero(m.group(2), a.get("format"))
        if v is None:
            continue
        escala = int(a.get("scale", "0") or 0)
        v = v * (10 ** escala)
        if a.get("sign") == "-":
            v = -v
        clave = (nombre, c["fin"], c["inicio"])
        if clave in vistos:
            if abs(vistos[clave] - v) > 0.5:
                salida.append({"concepto": nombre, "campo": conceptos[nombre], "aviso": "valores distintos para el mismo periodo: %s y %s" % (vistos[clave], v), "fin": c["fin"], "inicio": c["inicio"], "id": a.get("id")})
            continue
        vistos[clave] = v
        salida.append({"concepto": nombre, "campo": conceptos[nombre], "valor": v, "fin": c["fin"], "inicio": c["inicio"], "id": a.get("id")})
    return salida


def por_ejercicio(texto, conceptos=CONCEPTOS):
    """{"2025": {"tesoreria": {"valor": 1214945000.0, "concepto": ..., "id": "f-69", "fecha": "2025-12-31"}, ...}, "2024": {...}}.
    El ejercicio es el año de la fecha de fin del contexto. `avisos` con lo raro."""
    ej = {}
    avisos = []
    for h in hechos(texto, conceptos):
        if "aviso" in h:
            avisos.append("%s (%s): %s" % (h["concepto"], h["fin"], h["aviso"]))
            continue
        anio = (h["fin"] or "")[:4]
        if not anio.isdigit():
            continue
        ej.setdefault(anio, {})
        if h["campo"] in ej[anio]:
            continue
        ej[anio][h["campo"]] = {"valor": h["valor"], "concepto": h["concepto"], "id": h["id"], "fecha": h["fin"], "inicio": h["inicio"]}
    return ej, avisos


def leer_fichero(ruta, conceptos=CONCEPTOS):
    with open(ruta, encoding="utf-8", errors="replace") as f:
        return por_ejercicio(f.read(), conceptos)

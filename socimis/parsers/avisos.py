"""Lector de los avisos de «Otra Información Relevante» de BME Growth / Scaleup (texto de PDF cortos, 1-2 páginas).

Tres tipos, los que importan a la base:
  - participaciones significativas (Circular 3/2020: accionistas con ≥ 5 %, cada semestre): tabla con
    accionista, nº de acciones y % directo / indirecto / total. Las personas físicas van precedidas de «D.», «Dª»,
    «Dña.» o «Don/Doña»; se marcan como tipo «fisica» (decisión de Juan del 2026-10-26: se guardan tal como la
    sociedad las publica, sin cruzar con otras fuentes).
  - distribución de dividendos: importe bruto total, importe bruto por acción, fecha de pago, ejercicio con cargo al que se reparte.
  - valoración de activos: el total de la valoración (GAV) a la fecha, y quién valora si se nombra.

Qué no hace: no lee firmantes (el secretario del consejo no entra en la base), no deduce nada.
"""
import re

RE_PCT = re.compile(r"(\d{1,3}(?:,\d+)?)\s*%")
RE_ACCIONES = re.compile(r"\b\d{1,3}(?:\.\d{3})+\b")
RE_PERSONA = re.compile(r"^\s*(D\.|Dª|Dña\.?|Doña|Don)\s+", re.I)
RE_IMPORTE_EUR = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*(?:€|euros)", re.I)
RE_FECHA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
RE_PROSA = re.compile(r"\b(que|del capital|indirectamente|directamente|or over|than|holds?|shareholders?|ostent\w+|siendo|tiene|tienen|siguientes|participaci[oó]n directa|a \d{1,2} de|los accionistas|la sociedad|el cual|con un|en el capital|titular de)\b", re.I)
RE_SOCIEDAD = re.compile(r"\b(S\.?A\.?U?\.?|S\.?L\.?U?\.?|SOCIMI|F\.?I\.?|SICAV|B\.?V\.?|LTD|LLC|GMBH|S\.?à\.?r\.?l\.?|SCA|SCR|FCR|SIL)\b", re.I)


def tipo_accionista(nombre):
    if RE_PERSONA.match(nombre):
        return "fisica"
    if RE_SOCIEDAD.search(nombre) or re.search(r"\b(inversiones|holding|capital|patrimon|cartera|fondo|gestora|partners|invest)", nombre, re.I):
        return "juridica"
    return "no consta"


def _nombre_limpio(nombre):
    return re.sub(r"\s+", " ", nombre).strip(" ,;:")


def participaciones(texto):
    """[{accionista, tipo, acciones, pct_directo, pct_indirecto, pct_total, a_traves_de}], más la fecha «A dd de mes de aaaa».
    Lee línea a línea: una fila es una línea con un nombre al principio y al menos un porcentaje. Las filas de personas
    físicas con «(a través de X)» repartidas en dos o tres líneas se juntan: el porcentaje total es el último de la fila."""
    filas = []
    fecha = None
    m = re.search(r"A\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto)
    if m:
        fecha = _fecha_es(m.group(1), m.group(2), m.group(3))
    pendiente = None          # la última fila leída, a la que se pegan los trozos de «a través de» que vienen debajo
    via_previa = None         # el «(a través de …» que a veces va en la línea de ENCIMA de la fila de la persona física
    for linea in texto.splitlines():
        l = linea.rstrip()
        if not l.strip():
            continue
        pcts = RE_PCT.findall(l)
        es_fila = bool(pcts) and re.match(r"\s{0,8}[A-ZÁÉÍÓÚÑa-záéíóúñ]", l) and not re.search(r"igual o superior|superior al|inferior al|con una participaci", l)
        if es_fila:
            nombre = _nombre_limpio(re.split(r"\s{2,}|\s+\d{1,3}(?:\.\d{3})+\b|\s+\d{1,3},\d+\s*%", l.strip(), maxsplit=1)[0])
            if not nombre or len(nombre) < 3 or nombre.lower().startswith(("accionista", "participaci", "total")):
                continue
            if len(nombre) > 70 or len(nombre.split()) > 9 or RE_PROSA.search(nombre):
                continue          # una frase con un porcentaje dentro («... el cual ostentaba un 99,67 %») no es una fila de la tabla
            resto = l.strip()[len(nombre):] if l.strip().startswith(nombre) else l
            acciones = RE_ACCIONES.search(resto)
            vals = [float(p.replace(",", ".")) for p in pcts]
            medio = RE_PCT.sub(" ", RE_ACCIONES.sub(" ", resto)).replace("-", " ").replace("%", " ")
            medio = re.sub(r"\(?\s*a trav[eé]s de\s*", " ", medio, flags=re.I)
            medio = _nombre_limpio(re.sub(r"\s+", " ", medio)).strip("() ")
            via = " ".join(x for x in (via_previa, medio) if x).strip() or None
            if vals[-1] > 100:
                continue
            fila = {"accionista": nombre, "tipo": tipo_accionista(nombre), "acciones": int(acciones.group(0).replace(".", "")) if acciones else None,
                    "pct_directo": None, "pct_indirecto": None, "pct_total": vals[-1], "a_traves_de": via if (via or via_previa is not None) else None}
            indirecta = fila["a_traves_de"] is not None or re.search(r"a trav[eé]s de", l) or fila["tipo"] == "fisica"
            if len(vals) >= 3:
                fila["pct_directo"], fila["pct_indirecto"] = vals[0], vals[1]
            elif len(vals) == 2:
                if indirecta:
                    fila["pct_indirecto"] = vals[0]
                else:
                    fila["pct_directo"] = vals[0]
            else:
                if indirecta:
                    fila["pct_indirecto"] = vals[0]
                else:
                    fila["pct_directo"] = vals[0]
            if indirecta and fila["a_traves_de"] is None:
                fila["a_traves_de"] = ""
            filas.append(fila)
            pendiente, via_previa = fila, None
            continue
        indentada = re.match(r"\s{8,}\S", l) and len(l.strip()) < 60 and not RE_ACCIONES.search(l)
        if indentada and re.search(r"a trav[eé]s de", l, re.I):
            # «5,73% (a través de» encima de la fila de la persona: se guarda para la fila siguiente
            via_previa = _nombre_limpio(re.sub(r".*a trav[eé]s de\s*", "", l, flags=re.I).rstrip(")"))
        elif indentada and pendiente is not None and pendiente.get("a_traves_de") is not None and not pcts:
            # un trozo del nombre de la sociedad interpuesta («Uno, S.L.)») debajo de la fila
            pendiente["a_traves_de"] = _nombre_limpio((pendiente["a_traves_de"] + " " + l.strip()).rstrip(")"))
        elif indentada and pendiente is not None and pcts and pendiente["pct_indirecto"] is None:
            pendiente["pct_indirecto"] = float(pcts[0].replace(",", "."))
        elif not re.match(r"\s{6,}", l):
            pendiente, via_previa = None, None
    for f in filas:
        if f["a_traves_de"] == "":
            f["a_traves_de"] = None
    return {"fecha": fecha, "accionistas": filas}


MESES = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", "julio": "07",
         "agosto": "08", "septiembre": "09", "setiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}


def _fecha_es(d, mes, a):
    m = MESES.get(mes.lower())
    return "%s-%s-%02d" % (a, m, int(d)) if m else None


def dividendo(texto):
    """{importe_total, importe_por_accion, fecha_pago, con_cargo_a (ejercicio), fecha_acuerdo}."""
    salida = {"importe_total": None, "importe_por_accion": None, "fecha_pago": None, "con_cargo_a": None, "fecha_acuerdo": None}
    m = re.search(r"Dividendo bruto total[^\d]*(\d{1,3}(?:\.\d{3})*(?:,\d+)?)", texto, re.I)
    if m:
        salida["importe_total"] = _num(m.group(1))
    else:
        m = re.search(r"en la cantidad de .*?\((\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*€\)", texto, re.S | re.I)
        if m:
            salida["importe_total"] = _num(m.group(1))
    m = re.search(r"Importe bruto unitario[^\d]*(\d+,\d+)", texto, re.I)
    if m:
        salida["importe_por_accion"] = _num(m.group(1))
    m = re.search(r"Fecha de pago(?: de dividendo)?\s+(\d{2}/\d{2}/\d{4})", texto, re.I)
    if m:
        salida["fecha_pago"] = _iso(m.group(1))
    m = re.search(r"con cargo a (?:los )?(?:beneficios|resultados?)(?: del)? (?:del )?ejercicio (\d{4})", texto, re.I)
    if m:
        salida["con_cargo_a"] = m.group(1)
    m = re.search(r"celebrada el\s+d[ií]a\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", texto, re.I)
    if m:
        salida["fecha_acuerdo"] = _fecha_es(m.group(1), m.group(2), m.group(3))
    return salida


def valoracion(texto):
    """{total, fecha, valoradores: [...]} del aviso «la valoración de sus activos a 31 de diciembre de 2025 asciende a ... €»."""
    salida = {"total": None, "fecha": None, "valoradores": []}
    m = re.search(r"valoraci[oó]n de (?:sus|los) activos a\s+(\d{1,2}) de (\w+) de (\d{4})\s+asciende\s+a\s+(?:un total de\s+)?(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*€", texto, re.I | re.S)
    if m:
        salida["fecha"] = _fecha_es(m.group(1), m.group(2), m.group(3))
        salida["total"] = _num(m.group(4))
    for v in re.findall(r"compa[ñn][ií]a\s+([A-Z].{3,90}?(?:S\.A\.U\.|S\.A\.|S\.L\.U\.|S\.L\.|Limited|Ltd))", texto, re.S):
        v = _nombre_limpio(v)
        if v not in salida["valoradores"]:
            salida["valoradores"].append(v)
    return salida


def _num(t):
    return float(t.replace(".", "").replace(",", "."))


def _iso(ddmmaaaa):
    d, m, a = ddmmaaaa.split("/")
    return "%s-%s-%s" % (a, m, d)

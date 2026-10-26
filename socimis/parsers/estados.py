"""Lector de estados financieros en texto (PDF de cuentas anuales de BME Growth / BME Scaleup, pasado por texto_pdf).

Por qué existe: las SOCIMIs de los mercados de crecimiento publican sus cuentas como PDF, no como XBRL. El balance y
la cuenta de resultados siguen los modelos del PGC (o NIIF consolidadas con los mismos rótulos en castellano): un
rótulo a la izquierda y dos columnas de cifras a la derecha (ejercicio y ejercicio anterior). Se lee por RÓTULO con
expresiones regulares tolerantes (acentos, mayúsculas, numerales romanos) y se toman las dos primeras cifras de la
línea. Las cifras de notas («9», «11.1») que van entre el rótulo y los importes se descartan porque no llevan punto de
miles ni son grandes.

Qué saca (euros, ya en la unidad del documento convertida): tesorería, inversiones inmobiliarias, deudas con entidades
de crédito a largo y a corto, otros pasivos financieros, patrimonio neto, total activo, ingresos por arrendamientos /
cifra de negocios, variación del valor razonable, resultado, pagos por dividendos (flujo de efectivo), EPRA LTV declarado.
Además, las tablas de vencimientos de deuda (entidad, importe, vencimiento, tipo) y de inversiones inmobiliarias
(nombre, ubicación, valor), que alimentan las dimensiones de vencimientos y de activos.

Nunca inventa: lo que no aparece queda en None y se anota en `avisos`. Puro: texto dentro, dict fuera.
"""
import re

RE_CIFRA = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})+(?:,\d+)?\)?|\(?-?\d+,\d+\)?|\(?-?\d{4,}\)?")
RE_FECHA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")

# rótulo -> (campo, patrón). El orden importa: el primero que casa en una línea manda.
ROTULOS = [
    ("tesoreria", r"efectivo y otros activos l[ií]quidos equivalentes"),
    ("inversiones_inmobiliarias", r"^\s*(?:[ivx]+\.\s*)?inversiones inmobiliarias\s+(?:\d+(?:\.\d+)?\s+)?[\(\d]"),
    ("deuda_entidades_lp", r"deudas con entidades de cr[eé]dito"),       # la primera aparición (pasivo no corriente)
    ("deuda_entidades_cp", r"deudas con entidades de cr[eé]dito"),       # la segunda (pasivo corriente)
    ("patrimonio_neto", r"^\s*(?:a\)\s*)?patrimonio neto\s+[\(\d]"),
    ("activo_total", r"^\s*total activo\b"),
    ("ingresos_rentas", r"ingresos por arrendamientos?"),
    ("cifra_negocios", r"importe neto de la cifra de negocios\s+[\(\d]"),
    ("variacion_valor_razonable", r"variaci[oó]n (?:en el|del) valor razonable de las inversiones inmobiliarias"),
    ("resultado", r"^\s*resultado (?:consolidado )?del ejercicio\b(?! atribuido)"),
    ("pagos_dividendos", r"pagos por dividendos"),
]

UNIDADES = ((r"miles de euros|€ miles|miles de €|thousands? of euros|€ ?000|\(miles\)", 1e3), (r"millones de euros|€ millones|millions? of euros", 1e6), (r"\(euros\)|en euros|\(€\)", 1.0))


def numero(t):
    """«13.217.301» -> 13217301.0; «(2.245.589)» -> -2245589.0; «-» -> None."""
    t = t.strip()
    if t in ("", "-", "—", "–"):
        return None
    neg = t.startswith("(") or t.startswith("-")
    t = t.strip("()").lstrip("-").replace(".", "").replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def cifras_de(linea):
    """Las cifras «grandes» de una línea (con punto de miles o con coma decimal o de 4+ dígitos), en orden.
    Deja fuera los números de nota (un dígito o «11.1») y los años sueltos de las cabeceras se filtran aparte."""
    salida = []
    for m in RE_CIFRA.finditer(linea):
        v = numero(m.group(0))
        if v is None:
            continue
        salida.append(v)
    return salida


def unidad_del_texto(texto, defecto=1.0):
    """La unidad declarada en un trozo de texto (una página): el primer rótulo de unidad que aparezca; sin rótulo, euros."""
    cabecera = texto[:20000].lower()
    mejor = None
    for patron, factor in UNIDADES:
        m = re.search(patron, cabecera)
        if m and (mejor is None or m.start() < mejor[0]):
            mejor = (m.start(), factor)
    return mejor[1] if mejor else defecto


def unidad_de_linea(baja):
    """El factor que declara una línea de cabecera de tabla, o None si la línea no habla de unidades."""
    for patron, factor in UNIDADES:
        if re.search(patron, baja):
            return factor
    return None


def ejercicios_de(texto):
    """Los dos ejercicios de las cabeceras «31/12/2025  31/12/2024» -> ["2025", "2024"]."""
    for linea in texto.splitlines():
        fechas = RE_FECHA.findall(linea)
        # dos fechas de cierre iguales en día y mes («31/12/2025  31/12/2024»; Castellana cierra a 31/03): ejercicio y anterior
        if len(fechas) >= 2 and fechas[0][:2] == fechas[1][:2] and int(fechas[0][2]) == int(fechas[1][2]) + 1:
            return [fechas[0][2], fechas[1][2]]
    anios = re.findall(r"\b(20\d\d)\b", texto[:5000])
    return sorted(set(anios), reverse=True)[:2]


def partidas(texto):
    """{campo: [cifra_ejercicio, cifra_anterior]} de los rótulos de ROTULOS, más `avisos`.

    La unidad se mira PÁGINA a página (muchas cuentas llevan delante un resumen «en miles de euros» y detrás los
    estados completos en euros). Si un rótulo sale varias veces, manda la aparición en una página en euros (los
    estados completos); si no hay ninguna en euros, la primera que haya. Las deudas con entidades de crédito son dos
    rótulos iguales: el primero de la página es largo plazo y el segundo corto plazo."""
    candidatos = {}            # campo -> [(factor, [cifras])] en orden de aparición
    for pagina in texto.split("\f"):
        factor = 1.0           # la unidad vigente cambia con cada rótulo de unidad que aparece en la página («(en miles de euros)», «(Expresado en euros)»)
        creditos = 0
        for linea in pagina.splitlines():
            baja = linea.lower()
            marca = unidad_de_linea(baja)
            if marca is not None:
                factor = marca
            for campo, patron in ROTULOS:
                if not re.search(patron, baja):
                    continue
                cifras = cifras_de(linea)
                if not cifras:
                    break
                if campo.startswith("deuda_entidades"):
                    campo = "deuda_entidades_lp" if creditos == 0 else "deuda_entidades_cp"
                    creditos += 1
                    if creditos > 2:
                        break
                candidatos.setdefault(campo, []).append((factor, cifras[:2]))
                break
    salida, avisos = {}, []
    for campo, lista in candidatos.items():
        en_euros = [c for c in lista if c[0] == 1.0]
        factor, cifras = (en_euros or lista)[0]
        salida[campo] = [c * factor for c in cifras]
        if len({c[0] for c in lista}) > 1 and not en_euros:
            avisos.append("%s: aparece con unidades distintas y ninguna en euros; se toma la primera" % campo)
    for campo, _ in ROTULOS:
        if campo not in salida:
            avisos.append("no encontrado: %s" % campo)
    return salida, avisos


def ltv_declarado(texto):
    """El «EPRA LTV 31,8%» que las SOCIMIs ponen en el informe de gestión: (porcentaje, porcentaje anterior) o (None, None)."""
    for linea in texto.splitlines():
        if re.search(r"\bLTV\b|loan to value", linea, re.I) and "%" in linea:
            pcts = re.findall(r"(\d{1,2}(?:[.,]\d+)?)\s*%", linea)
            if pcts:
                vals = [float(p.replace(",", ".")) for p in pcts]
                return vals[0], (vals[1] if len(vals) > 1 else None)
    return None, None


def bloque(texto, cabecera, max_lineas=80, huecos=3):
    """Las líneas de UNA tabla: desde la primera línea que casa con `cabecera` hasta `huecos` líneas en blanco seguidas,
    una línea que empiece por «Total» ya leída, o `max_lineas`. Si no hay cabecera, devuelve todas las líneas (el que
    llama se apaña con sus propios filtros)."""
    lineas = texto.splitlines()
    inicio = next((i for i, l in enumerate(lineas) if re.search(cabecera, l, re.I)), None)
    if inicio is None:
        return []                 # sin cabecera no hay tabla: antes se devolvía todo el texto y salían 100 «activos» de las líneas del balance
    salida, vacias = [], 0
    for l in lineas[inicio + 1:inicio + 1 + max_lineas]:
        if not l.strip():
            vacias += 1
            if vacias >= huecos and salida:
                break
            continue
        vacias = 0
        salida.append(l)
        if re.match(r"\s*total\b", l, re.I):
            break
    return salida


def vencimientos(texto):
    """Las filas «Entidad  importe  importe_anterior  dd/mm/aaaa  tipo» de la nota de deudas con entidades de crédito.
    Devuelve [{entidad, importe, importe_anterior, vencimiento (AAAA-MM-DD), tipo_interes}]. Solo filas con fecha de vencimiento."""
    filas = []
    for linea in bloque(texto, r"vencimiento\s{2,}(?:tipo de\s+)?inter[eé]s|\d{2}/\d{2}/\d{4}\s{2,}vencimiento|vencimiento\s{2,}\d{2}/\d{2}/\d{4}", max_lineas=120, huecos=4):
        m = RE_FECHA.search(linea)
        if not m:
            continue
        antes = linea[:m.start()]
        despues = linea[m.end():]
        # la entidad son las palabras hasta la primera cifra o el primer «-» (un importe ya amortizado)
        tokens = antes.split()
        palabras, valores = [], []
        for t in tokens:
            if not valores and not RE_CIFRA.fullmatch(t) and t not in ("-", "—", "–"):
                palabras.append(t)
            elif t in ("-", "—", "–"):
                valores.append(0.0)
            else:
                v = numero(t)
                if v is not None:
                    valores.append(v)
        nombre = " ".join(palabras).strip(" :")
        if not nombre or not valores or re.search(r"\d", nombre):
            continue
        tipo = re.search(r"(Euribor\s*\+\s*\d+(?:,\d+)?\s*%|\d+(?:,\d+)?\s*%)", despues)
        fila = {"entidad": nombre, "importe": valores[0],
                "importe_anterior": valores[1] if len(valores) > 1 else None,
                "vencimiento": "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)),
                "tipo_interes": tipo.group(1).replace(" ", "") if tipo else None}
        # la misma tabla sale dos veces en muchas memorias (ejercicio y anterior): la primera aparición manda
        if not any(x["entidad"] == fila["entidad"] and x["vencimiento"] == fila["vencimiento"] and x["importe"] == fila["importe"] for x in filas):
            filas.append(fila)
    return filas


def inversiones_inmobiliarias(texto):
    """La tabla «Inversión inmobiliaria | Ubicación | 31/12/2025 | 31/12/2024» de la nota de inversiones inmobiliarias:
    [{nombre, ubicacion, valor, valor_anterior}]. Se reconoce por las líneas con tres bloques separados por 2+ espacios
    cuyos dos últimos son cifras o «-»."""
    filas = []
    for linea in bloque(texto, r"inversi[oó]n inmobiliaria\s{2,}ubicaci[oó]n|ubicaci[oó]n\s{2,}31/12", max_lineas=120, huecos=3):
        partes = [p.strip() for p in re.split(r"\s{2,}", linea.strip()) if p.strip()]
        if len(partes) < 3:
            continue
        valores = [numero(p) if RE_CIFRA.fullmatch(p) or p in ("-", "—") else "no" for p in partes[-2:]]
        if "no" in valores:
            continue
        nombre, ubicacion = partes[0], partes[1] if len(partes) > 3 else ""
        if len(partes) == 3:
            nombre, ubicacion = partes[0], ""
        if re.search(r"\d", nombre) and not re.search(r"[A-Za-z]", nombre):
            continue
        if not re.search(r",", ubicacion) and not ubicacion:
            # sin ubicación: puede ser una fila de totales u otra tabla; la dejamos solo si el nombre parece un activo
            if not re.search(r"edificio|aparta|hotel|hostel|local|nave|oficina|parking|residencia|centro", nombre, re.I):
                continue
        nombre = nombre.rstrip("*() ")
        if any(x["nombre"] == nombre for x in filas):
            continue          # las tablas de sensibilidad y de movimientos repiten los nombres: solo la primera tabla (la de valores) cuenta
        filas.append({"nombre": nombre, "ubicacion": ubicacion, "valor": valores[0], "valor_anterior": valores[1]})
    return filas


def leer(texto):
    """Todo lo que este lector saca de un PDF de cuentas: {ejercicios, unidad, partidas, ltv, vencimientos, activos, avisos}."""
    p, avisos = partidas(texto)
    ltv, ltv_ant = ltv_declarado(texto)
    basicas = [c for c in ("tesoreria", "inversiones_inmobiliarias", "patrimonio_neto", "activo_total") if c in p]
    if len(basicas) < 3:
        avisos.append("estados no reconocidos (%d de 4 partidas básicas): el PDF puede estar escaneado en parte o usar otro formato; a revisar" % len(basicas))
    return {"ejercicios": ejercicios_de(texto), "unidad": unidad_del_texto(texto), "partidas": p, "estados_reconocidos": len(basicas) >= 3,
            "ltv_declarado": ltv, "ltv_declarado_anterior": ltv_ant,
            "vencimientos": vencimientos(texto), "activos": inversiones_inmobiliarias(texto), "avisos": avisos}

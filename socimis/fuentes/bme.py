"""BME Growth y BME Scaleup (segmentos de BME MTF Equity): fichas y documentos de las SOCIMIs que cotizan ahí.

Lo que hay (comprobado el 2026-10-26): la ficha de cada sociedad en bolsasymercados.es se pinta con JavaScript; sus
pestañas «Datos Empresa» (domicilio, NIF, auditor, asesor registrado, proveedor de liquidez) y «I. Privilegiada / O. I.
Relevante» (los avisos, cada uno un PDF con URL estable
`https://apiweb.bolsasymercados.es/Market/MTFDocuments/<Tipo>/<AAAA>/<MM>/<código>_<tipo>_<fecha>.pdf`) no están en el
HTML que devuelve el servidor. Por eso la ficha se recoge con un navegador (`herramientas/recolectar_bme.js`, Playwright)
que deja un JSON por sociedad, y este módulo LEE ese JSON y decide qué PDF bajar: no llama a la API interna del sitio.

Condiciones de BME (pie de cada página): información «destinada exclusivamente al uso interno»; cualquier uso
comercial o redifusión a terceros no gratuita exige autorización de BME Market Data. Esta base es de uso propio de Juan.

Qué documentos elige por sociedad (los mínimos para la ficha, decisión «lote educado» del 2026-10-26):
  - las cuentas anuales más recientes («Informes financieros anuales y de auditoría», la de más MB si hay rectificación)
  - la última valoración de activos
  - las últimas participaciones significativas
  - el último aviso de dividendos
  - el último informe semestral (para saber si está escaneado y para la fecha del dato más fresco)
"""
import re

TIPOS = {
    "cuentas_anuales": r"informes? financieros? anual",
    "valoracion": r"valoraci[oó]n de (?:sus |los )?activos",
    "participaciones": r"participaciones significativas",
    "dividendo": r"dividendo",
    "semestral": r"informes? financieros? semestral",
}

RE_FECHA_URL = re.compile(r"_(\d{8})(?:_\d+)?\.pdf$", re.I)


RE_NIF = re.compile(r"^[A-Z][0-9]{7}[0-9A-Z]$")


def nif_valido(texto):
    """El NIF de una sociedad («A-87.934.741», «A87934741») limpio, o None si no tiene la forma de un NIF: nunca se usa un NIF
    sin validar para nombrar ficheros (auditoría de Cancerbero, 2026-10-26)."""
    limpio = re.sub(r"[\s.\-]", "", texto or "").upper()
    return limpio if RE_NIF.match(limpio) else None


def fecha_de_url(url):
    m = RE_FECHA_URL.search(url or "")
    if not m:
        return None
    d = m.group(1)
    return "%s-%s-%s" % (d[:4], d[4:6], d[6:8])


def clasificar(doc):
    """El tipo de un documento de la lista de la ficha a partir de su categoría y su título."""
    texto = " ".join(str(doc.get(k, "")) for k in ("categoria", "titulo", "descripcion")).lower()
    if re.search(TIPOS["valoracion"], texto):
        return "valoracion"
    for tipo, patron in TIPOS.items():
        if re.search(patron, texto):
            return tipo
    return "otro"


def megas(doc):
    m = re.search(r"\((\d+(?:,\d+)?)\s*(MB|KB)\)", str(doc.get("titulo", "")) + str(doc.get("descripcion", "")), re.I)
    if not m:
        return 0.0
    v = float(m.group(1).replace(",", "."))
    return v if m.group(2).upper() == "MB" else v / 1024


def elegir_documentos(documentos):
    """De la lista de documentos de una ficha (dicts con url, categoria, titulo, descripcion, fecha), los que se bajan:
    {tipo: doc}. Para cada tipo, el más reciente; en cuentas anuales, si dos tienen la misma fecha o uno rectifica a otro,
    el más pesado (suele ser el completo con la auditoría)."""
    por_tipo = {}
    for d in documentos:
        tipo = clasificar(d)
        if tipo == "otro":
            continue
        d = dict(d)
        d["tipo"] = tipo
        d["fecha"] = fecha_de_url(d.get("url")) or d.get("fecha")      # la fecha del nombre del PDF manda: la de la lista a veces es la del aviso relacionado
        actual = por_tipo.get(tipo)
        if actual is None:
            por_tipo[tipo] = d
            continue
        if (d["fecha"] or "") > (actual["fecha"] or ""):
            if tipo == "cuentas_anuales" and (d["fecha"] or "")[:4] == (actual["fecha"] or "")[:4] and megas(d) < megas(actual):
                continue       # misma campaña anual, el nuevo es un aviso corto (una rectificación de 60 KB): se queda el gordo
            por_tipo[tipo] = d
        elif (d["fecha"] or "") == (actual["fecha"] or "") and megas(d) > megas(actual):
            por_tipo[tipo] = d
    return por_tipo


def nombre_fichero(nif, doc):
    """descargas/bme/<NIF>/<tipo>-<fecha>.pdf"""
    fecha = doc.get("fecha") if re.match(r"^\d{4}-\d{2}-\d{2}$", doc.get("fecha") or "") else "sin-fecha"
    return "bme/%s/%s-%s.pdf" % (nif_valido(nif) or "sin-nif", doc["tipo"], fecha)


def sociedad_desde_ficha(ficha):
    """Lo que la pestaña «Datos Empresa» y la cabecera de la ficha dan de la sociedad, ya con nombres de la base."""
    e = ficha.get("empresa", {})
    return {
        "nombre": ficha.get("nombre"),
        "nif": nif_valido(e.get("nif")),
        "isin": ficha.get("isin"),
        "ticker": ficha.get("ticker"),
        "mercado": "BME MTF Equity",
        "segmento": ficha.get("segmento"),
        "domicilio": e.get("domicilio"),
        "web": ficha.get("web"),
        "auditor": e.get("auditor") if e.get("auditor") not in ("-", "") else None,
        "asesor_registrado": e.get("asesor_registrado") if e.get("asesor_registrado") not in ("-", "") else None,
        "proveedor_liquidez": e.get("proveedor_liquidez") if e.get("proveedor_liquidez") not in ("-", "") else None,
        "capitalizacion": ficha.get("capitalizacion"),
        "cotizacion": ficha.get("cierre"),
        "fecha_cotizacion": ficha.get("fecha_cierre"),
        "url_ficha": ficha.get("url"),
    }


PROVINCIAS_CP = {"01": "Álava", "20": "Gipuzkoa", "48": "Bizkaia", "28": "Madrid", "08": "Barcelona", "46": "Valencia", "41": "Sevilla",
                 "29": "Málaga", "07": "Illes Balears", "31": "Navarra", "50": "Zaragoza", "03": "Alicante", "15": "A Coruña", "36": "Pontevedra",
                 "33": "Asturias", "39": "Cantabria", "47": "Valladolid", "18": "Granada", "11": "Cádiz", "35": "Las Palmas", "38": "Santa Cruz de Tenerife",
                 "43": "Tarragona", "17": "Girona", "25": "Lleida", "12": "Castellón", "30": "Murcia", "26": "La Rioja", "06": "Badajoz", "10": "Cáceres",
                 "02": "Albacete", "13": "Ciudad Real", "16": "Cuenca", "19": "Guadalajara", "45": "Toledo", "14": "Córdoba", "21": "Huelva", "23": "Jaén",
                 "04": "Almería", "22": "Huesca", "44": "Teruel", "09": "Burgos", "24": "León", "34": "Palencia", "37": "Salamanca", "40": "Segovia",
                 "42": "Soria", "49": "Zamora", "05": "Ávila", "27": "Lugo", "32": "Ourense", "51": "Ceuta", "52": "Melilla"}


def provincia_de_domicilio(domicilio):
    """La provincia por el código postal del domicilio («PASEO DE LA HABANA 74, 28036 MADRID» -> Madrid)."""
    m = re.search(r"\b(\d{5})\b", domicilio or "")
    return PROVINCIAS_CP.get(m.group(1)[:2]) if m else None

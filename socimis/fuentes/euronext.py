"""Euronext Access París (MIC XMLI): el censo de las sociedades españolas que cotizan ahí, y nada más de momento.

Lo que hay (comprobado el 2026-10-27): `https://live.euronext.com/en/products/equities/list` es un listado público de todas
las acciones de Euronext (3.826 líneas, 100 por página); 129 tienen ISIN español y 46 cotizan en Euronext Access París
(XMLI). La ficha de cada valor (`/en/product/equities/<ISIN>-XMLI`) enseña precio, capitalización, «Regulated news»
(cuentas auditadas, dividendos, actas, en PDF) y una pestaña «Company information» con perfil, cifras clave de cinco
años, accionistas y domicilio, todo de un tercero (Cofisem).

**Por qué este módulo solo censa.** Las condiciones de uso de Euronext (leídas el 2026-10-27) prohíben expresamente, sin
permiso escrito, el acceso con «spiders, robots, agents, tools» y la «systematic retrieval to create collections,
compilations, databases»; y la información de terceros (Cofisem) «may not be reproduced … without such owner's prior
written consent». Es más restrictivo que BME («uso interno») y que Portfolio (no dice nada). El `robots.txt` de
live.euronext.com, en cambio, permite /product/ al agente genérico y solo veda a los bots de IA. Se hizo UNA lectura del
listado y de una ficha para saber qué hay; con eso se escribe el censo (nombre, ISIN, símbolo, último precio y la URL de
la ficha, que es lo que cualquier visitante ve) y **no se bajan documentos ni se recorren fichas hasta que Juan decida**
(pregunta pendiente en el PRD). Los documentos de estas sociedades también están en sus propias webs, que es la vía
limpia si se quiere ir a por ellos.

El listado no distingue SOCIMIs de otras sociedades (hay biotecnológicas, gimnasios, colegios) y recorta los nombres:
`socimi_en_nombre` dice si la palabra aparece; el resto queda «sin confirmar» hasta leer su ficha.
"""
import json
import re

URL_LISTADO = "https://live.euronext.com/en/products/equities/list"
RE_ISIN = re.compile(r"^ES[0-9A-Z]{10}$")


def _precio(texto):
    """«EUR 1,320.00» -> 1320.0; «-» -> None."""
    m = re.search(r"([\d,]+\.\d+|\d+)", texto or "")
    return float(m.group(1).replace(",", "")) if m else None


def _fecha(texto):
    """«26 Oct 2026» -> 2026-10-26."""
    meses = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06", "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"}
    m = re.match(r"(\d{1,2}) ([A-Za-z]{3}) (\d{4})", (texto or "").strip())
    return "%s-%s-%02d" % (m.group(3), meses.get(m.group(2).lower(), "01"), int(m.group(1))) if m else None


def emisores(listado):
    """listado: el dict guardado en descargas/euronext/listado-AAAA-MM-DD.json (ver `herramientas`), con `filas` y `consultado`."""
    salida = []
    for f in listado.get("filas", []):
        if f.get("mic") != "XMLI" or not RE_ISIN.match(f.get("isin") or ""):
            continue
        salida.append({
            "nombre": f.get("nombre"),
            "isin": f["isin"],
            "ticker": f.get("simbolo"),
            "cotizacion": _precio(f.get("ultimo")),
            "fecha_cotizacion": _fecha(f.get("fecha")),
            "url": f.get("url"),
            "socimi_en_nombre": bool(re.search(r"socimi", f.get("nombre") or "", re.I)),
        })
    return salida


def sociedad_desde_emisor(e):
    return {
        "nombre": e.get("nombre"),
        "nif": None,
        "isin": e.get("isin"),
        "ticker": e.get("ticker"),
        "mercado": "Euronext Access París",
        "segmento": "Euronext Access",
        "cotizacion": e.get("cotizacion"),
        "fecha_cotizacion": e.get("fecha_cotizacion"),
        "url_ficha": e.get("url"),
    }


def cargar_listado(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)

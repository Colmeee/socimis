"""Portfolio Stock Exchange (SMN español, operado por European Digital Securities Exchange, S.V., S.A.): el censo de sus SOCIMIs.

Lo que hay (comprobado el 2026-10-27): la página pública `https://www.portfolio.exchange/portfolio-market` llega del
servidor con las 32 emisiones de renta variable ya en el HTML (sin JavaScript): ticker, nombre, ISIN, valor liquidativo
por acción y total (casi siempre vacíos), capitalización y último precio. Las fichas de cada emisor (`/portfolio-market/
<slug>`) repiten eso y el libro de órdenes; **los documentos (cuentas, valoraciones, hechos relevantes) están detrás del
login de app.portfolio.exchange**, así que de estas sociedades la base solo tiene lo del censo, y el resto queda «no consta».
No publica el NIF: la ficha se guarda con el ISIN como clave.

Aviso legal del sitio (leído el 2026-10-27): contenido «a efectos informativos»; prohíbe la «distribución, reproducción,
comunicación pública» sin permiso; no dice nada de acceso automatizado; `robots.txt` lo permite todo. Esta base es de uso
propio de Juan: una lectura de la página, con pausa, y los datos de cada emisor con su fuente. No se redistribuye.
"""
import html
import re

BASE = "https://www.portfolio.exchange"
URL_MERCADO = BASE + "/portfolio-market"

RE_FILA = re.compile(r'<a href="(/portfolio-market/[^"]+)"[^>]*class="tableList__row"[^>]*>(.*?)</a>', re.S)
RE_ISIN = re.compile(r"^ES[0-9A-Z]{10}$")


def _campo(bloque, clase):
    m = re.search(r'class="%s"[^>]*>(.*?)</div>' % re.escape(clase), bloque, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def _importe(trozo):
    """«<span class="currency__integer">29,872,824</span><span class="currency__decimal">.00</span>» -> 29872824.0; sin cifra -> None."""
    mi = re.search(r'currency__integer"[^>]*>([^<]*)<', trozo)
    if not mi:
        return None
    md = re.search(r'currency__decimal"[^>]*>([^<]*)<', trozo)
    try:
        return float(mi.group(1).replace(",", "") + (md.group(1) if md else ""))
    except ValueError:
        return None


def emisores(html_pagina):
    """[{url, ticker, nombre, nombre_corto, isin, pais, nav_por_accion, nav_total, capitalizacion, cotizacion, socimi_en_nombre}] de la
    página del mercado. `socimi_en_nombre` dice si la sociedad se llama SOCIMI (o Portfolio la etiqueta así); las que no
    (Libeen Properties, Trajano II…) se guardan igual y se marcan, porque Portfolio no publica el régimen fiscal."""
    salida = []
    for href, bloque in RE_FILA.findall(html_pagina):
        organizacion = (_campo(bloque, "product__organization") or "").lstrip("- ").strip()
        corto = _campo(bloque, "product__name")
        isin = _campo(bloque, "product__isinCode")
        bandera = re.search(r'/flags/([A-Z]{2})\.svg', bloque)
        metricas = {}
        for trozo in re.split(r'tableList__cellLabel">', bloque)[1:]:
            etiqueta = html.unescape(trozo.split("</div>", 1)[0]).strip()
            metricas[etiqueta] = _importe(trozo)
        salida.append({
            "url": BASE + html.unescape(href),
            "ticker": _campo(bloque, "product__ticker"),
            "nombre": organizacion or corto,
            "nombre_corto": corto,
            "isin": isin if isin and RE_ISIN.match(isin) else None,
            "pais": bandera.group(1) if bandera else None,
            "nav_por_accion": metricas.get("Net Asset Value Per Share"),
            "nav_total": metricas.get("Total NAV"),
            "capitalizacion": metricas.get("Capitalization"),
            "cotizacion": metricas.get("Last Price"),
            "socimi_en_nombre": bool(re.search(r"socimi", (organizacion or "") + " " + (corto or ""), re.I)),
        })
    return salida


def sociedad_desde_emisor(e):
    """Lo del emisor con los nombres de la base. Sin NIF (Portfolio no lo publica) y sin domicilio."""
    return {
        "nombre": e.get("nombre"),
        "nif": None,
        "isin": e.get("isin"),
        "ticker": e.get("ticker"),
        "mercado": "Portfolio Stock Exchange",
        "segmento": "Portfolio SE",
        "capitalizacion": e.get("capitalizacion"),
        "cotizacion": e.get("cotizacion"),
        "url_ficha": e.get("url"),
    }

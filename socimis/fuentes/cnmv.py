"""CNMV: los registros oficiales de una SOCIMI del mercado principal, por NIF.

Páginas (HTML estático, se leen con urllib; comprobado el 2026-10-26 que contestan 200 sin navegador):
  - informes financieros anuales: /portal/Consultas/ifa/listadoifa.aspx?id=0&nif=<NIF>
      tabla con nº de registro, fecha de estados, fecha de publicación, auditor, enlaces «Individual» y «Consolidada»
      (xhtml ESEF por /webservices/verdocumento/ver?e=…), fichero ZIP/Xbri y opinión del auditor.
  - participaciones significativas: /portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=<NIF>, que enlaza a
      Notificaciones-Participaciones.aspx?qS={…} con la tabla de accionistas (≥ 3 %) y el total de derechos de voto.
Condiciones (nota legal de la CNMV): uso privado libre, reproducción fiel, y si se cobra por la información hay que
avisar de que en la CNMV es gratis. robots.txt solo prohíbe *.shtml.

Puro salvo las dos funciones que piden páginas (`pedir_*`), que usan red.pedir_bytes.
"""
import html
import re
import urllib.parse

from .. import red

BASE = "https://www.cnmv.es"
URL_IFA = BASE + "/portal/Consultas/ifa/listadoifa.aspx?id=0&nif={nif}"
URL_PS = BASE + "/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif={nif}"
URL_ENTIDAD = BASE + "/portal/Consultas/DatosEntidad.aspx?nif={nif}"

RE_FILA = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
RE_CELDA = re.compile(r'<td[^>]*data-th="([^"]*)"[^>]*>(.*?)</td>', re.S)
RE_ENLACE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
RE_ETIQ = re.compile(r"<[^>]+>")


def _texto(fragmento):
    return re.sub(r"\s+", " ", html.unescape(RE_ETIQ.sub(" ", fragmento))).strip()


def _iso(ddmmaaaa):
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", ddmmaaaa or "")
    return "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)) if m else None


def nombre_entidad(html_pagina):
    """El nombre de la sociedad, que la CNMV pone como <caption> de la tabla."""
    m = re.search(r"<caption>\s*(.*?)\s*</caption>", html_pagina, re.S)
    return _texto(m.group(1)) if m else None


def informes_anuales(html_pagina):
    """[{registro, fecha_estados, publicado, auditor, url_individual, url_consolidada, url_zip, opinion}] de la tabla de IFA."""
    tabla = re.search(r'<table[^>]*id="ctl00_ContentPrincipal_gridInformes"[^>]*>(.*?)</table>', html_pagina, re.S)
    if not tabla:
        return []
    salida = []
    for fila in RE_FILA.findall(tabla.group(1)):
        celdas = {_texto(k): v for k, v in RE_CELDA.findall(fila)}
        if not celdas or "Nº Registro Oficial" not in celdas:
            continue
        tipo = celdas.get("Tipo", "")
        enlaces = {_texto(t).lower(): html.unescape(u) for u, t in RE_ENLACE.findall(tipo)}
        zip_ = RE_ENLACE.search(celdas.get("Fichero ZIP/Xbri (2)", ""))
        salida.append({
            "registro": _texto(celdas["Nº Registro Oficial"]),
            "fecha_estados": _iso(_texto(celdas.get("Fecha Estados Financieros", ""))),
            "publicado": _iso(_texto(celdas.get("Fecha de publicación (1)", ""))),
            "auditor": _texto(celdas.get("Nombre del auditor", "")),
            "url_individual": enlaces.get("individual"),
            "url_consolidada": enlaces.get("consolidada"),
            "url_zip": html.unescape(zip_.group(1)) if zip_ else None,
            "opinion": _texto(celdas.get("Opinión del auditor (5)", "")),
        })
    return salida


def enlace_notificaciones(html_pagina):
    """La URL de «Notificaciones de derechos de voto e instrumentos financieros» dentro de la página ps_ac_ini."""
    m = re.search(r'href="(Notificaciones-Participaciones\.aspx\?qS=\{[^}]+\})"', html_pagina)
    return urllib.parse.urljoin(BASE + "/portal/Consultas/derechosvoto/", html.unescape(m.group(1))) if m else None


def participaciones(html_pagina):
    """{derechos_voto_total, fecha_modificacion, publicado, accionistas: [{accionista, tipo, pct_total, pct_directo, pct_indirecto, pct_instrumentos, pct_total_ab, fecha_registro, url_pdf}]}."""
    salida = {"derechos_voto_total": None, "fecha_modificacion": None, "publicado": None, "accionistas": []}
    m = re.search(r"Número total de derechos de voto[^:]*:\s*([\d.]+)", html_pagina)
    if m:
        salida["derechos_voto_total"] = int(m.group(1).replace(".", ""))
    m = re.search(r"Fecha de última modificación[^:]*:\s*(\d{2}/\d{2}/\d{4})", html_pagina)
    if m:
        salida["fecha_modificacion"] = _iso(m.group(1))
    m = re.search(r"Fecha de publicación en la pagina web CNMV:\s*(\d{2}/\d{2}/\d{4})", html_pagina)
    if m:
        salida["publicado"] = _iso(m.group(1))
    tabla = re.search(r'<table[^>]*id="ctl00_ContentPrincipal_gridAccionistasSignificativos"[^>]*>(.*?)</table>', html_pagina, re.S)
    if not tabla:
        return salida
    for fila in RE_FILA.findall(tabla.group(1)):
        celdas = {_texto(k): v for k, v in RE_CELDA.findall(fila)}
        if "Denominación" not in celdas:
            continue
        nombre = _texto(celdas["Denominación"])
        if not nombre:
            continue
        pdf = RE_ENLACE.search(celdas.get("F.Registro Entrada CNMV", ""))
        salida["accionistas"].append({
            "accionista": nombre,
            "tipo": "fisica" if _parece_persona(nombre) else "juridica",
            "pct_total": _pct(celdas.get("% Total (A)")),
            "pct_directo": _pct(celdas.get("% Directo")),
            "pct_indirecto": _pct(celdas.get("% Indirecto")),
            "pct_instrumentos": _pct(celdas.get("% (B)")),
            "pct_total_ab": _pct(celdas.get("(A+B)")),
            "fecha_registro": _iso(_texto(celdas.get("F.Registro Entrada CNMV", ""))),
            "url_pdf": html.unescape(pdf.group(1)) if pdf else None,
        })
    return salida


def _pct(celda):
    t = _texto(celda or "")
    m = re.search(r"\d+(?:,\d+)?", t)
    return float(m.group(0).replace(",", ".")) if m else None


def _parece_persona(nombre):
    """La CNMV escribe a las personas físicas «APELLIDO APELLIDO, NOMBRE» y a las sociedades con su forma («S.A.», «INC.», «LTD», «B.V.»…)."""
    if re.search(r"\b(S\.?A\.?U?|S\.?L\.?U?|INC|LTD|LLC|PLC|GMBH|B\.?V|N\.?V|SOCIMI|SICAV|F\.?I|FUND|PARTNERS|CAPITAL|HOLDING|GROUP|CORP|BANK|BANCO|SE|AG|LP|SARL|S\.?à\.?r\.?l)\b", nombre, re.I):
        return False
    return "," in nombre


def pedir(url, ua=red.UA):
    r = red.pedir_bytes(url, ua, timeout=30, max_bytes=4 * 1024 * 1024, limite=60)
    if r["codigo"] != 200:
        raise red.ErrorFuente("La CNMV contestó HTTP %s a %s" % (r["codigo"], url), r["codigo"])
    return r["cuerpo"].decode("utf-8", errors="replace")


def con_guion(nif):
    """«A28027399» → «A-28027399». La CNMV guarda algunas entidades con el NIF con guion (Colonial, 2026-10-27) y con el NIF
    sin guion devuelve la página vacía; Merlin y Lar contestan con las dos formas. Se prueba primero sin guion y, si no hay
    nada, con él."""
    nif = nif.replace("-", "").upper()
    return "%s-%s" % (nif[0], nif[1:]) if len(nif) == 9 else nif


def pedir_informes_anuales(nif, ua=red.UA):
    """(informes, nombre de la entidad)."""
    pagina = pedir(URL_IFA.format(nif=nif), ua)
    informes, nombre = informes_anuales(pagina), nombre_entidad(pagina)
    if not informes and not nombre and con_guion(nif) != nif:
        pagina = pedir(URL_IFA.format(nif=con_guion(nif)), ua)
        informes, nombre = informes_anuales(pagina), nombre_entidad(pagina)
    return informes, nombre


def pedir_participaciones(nif, ua=red.UA):
    """Dos peticiones: la página de entrada y la de notificaciones a la que enlaza."""
    inicio = pedir(URL_PS.format(nif=nif), ua)
    if nombre_entidad(inicio) is None and con_guion(nif) != nif:
        inicio = pedir(URL_PS.format(nif=con_guion(nif)), ua)
    destino = enlace_notificaciones(inicio)
    if not destino:
        return participaciones(inicio), None
    return participaciones(pedir(destino, ua)), destino

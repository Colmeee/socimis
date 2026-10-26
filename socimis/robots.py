"""¿Permite el robots.txt de un sitio leer esta URL?

Portado de `tools/robots_check.py` del repositorio Doc de Juan Colmenarejo (licencia MIT, 2026), que decidía si
reintentar una página con cabeceras de navegador. Aquí decide si se baja un documento. Mismas reglas, deliberadamente
cautas (RFC 9309):
  * gana la coincidencia más larga; a igual longitud gana Disallow
  * un Disallow para «*» o para nuestro agente bloquea
  * las líneas en blanco dentro de un grupo no lo cierran (robotparser las trata mal y falla abierto)
  * se salta una marca de orden de bytes inicial (si se deja, esconde el primer «User-agent»)
  * 404 = no hay política publicada = permiso
  * cualquier otro fallo al leer robots.txt deja el permiso sin confirmar y NO se baja (incluidas las líneas de
    regla con U+FFFD: un byte que no era UTF-8)
Cambios respecto al original: usa `red.pedir_bytes` (IPv4 primero, tope duro) en vez de curl, y devuelve
(permitido, motivo) en vez de un código de salida. Sin dependencias.
"""
import re
import urllib.parse

from . import red

CAMPOS = ("user-agent", "allow", "disallow", "sitemap", "crawl-delay", "host")


def es_robots(texto):
    """¿Esto parece un robots.txt? Un servidor mal configurado contesta 200 con una página HTML de error: cero
    reglas, que leído a la ligera sería «todo permitido». Vacío o solo espacios sí es un robots.txt válido (permite todo)."""
    texto = texto.lstrip("\ufeff")
    if not texto.strip():
        return True
    for cruda in texto.splitlines():
        linea = cruda.split("#", 1)[0].strip().lower()
        if ":" in linea and linea.split(":", 1)[0].strip() in CAMPOS:
            return True
    return False


def regla_ilegible(texto):
    """¿Alguna línea User-agent/Allow/Disallow trae U+FFFD? Entonces el fichero no se pudo decodificar: no es permisivo, es ilegible."""
    for cruda in texto.lstrip("\ufeff").splitlines():
        linea = cruda.split("#", 1)[0]
        if "\ufffd" in linea and ":" in linea:
            campo = linea.split(":", 1)[0].replace("\ufffd", "").strip().lower()
            if campo in ("user-agent", "allow", "disallow"):
                return True
    return False


def grupos(texto):
    """agente -> [(es_allow, patrón)], tolerando líneas en blanco dentro de un grupo."""
    salida, agentes, esperando = {}, [], True
    for cruda in texto.lstrip("\ufeff").splitlines():
        linea = cruda.split("#", 1)[0].strip()
        if not linea or ":" not in linea:
            continue
        campo, _, valor = linea.partition(":")
        campo, valor = campo.strip().lower(), valor.strip()
        if campo == "user-agent":
            if not esperando:
                agentes, esperando = [], True
            agentes.append(valor.lower())
            salida.setdefault(valor.lower(), [])
        elif campo in ("allow", "disallow") and agentes:
            esperando = False
            for a in agentes:
                salida[a].append((campo == "allow", valor))
    return salida


def _casa(patron, ruta):
    """Coincidencia con comodines de la RFC 9309; devuelve la longitud del patrón o -1. El patrón se descodifica
    (%20) para compararlo con la ruta ya descodificada; «$» ancla el final solo si va al final del patrón."""
    if patron == "":
        return -1
    patron = urllib.parse.unquote(patron)
    ancla = patron.endswith("$")
    cuerpo = patron[:-1] if ancla else patron
    rx = "^" + "".join(".*" if c == "*" else re.escape(c) for c in cuerpo) + ("$" if ancla else "")
    return len(patron) if re.match(rx, ruta) else -1


def permitido(texto, agente, ruta):
    g = grupos(texto)
    reglas = g.get(agente.lower()) or g.get("*") or []
    mejor_len, mejor_allow = -1, True
    for es_allow, pat in reglas:
        n = _casa(pat, ruta)
        if n > mejor_len or (n == mejor_len and n >= 0 and not es_allow):
            mejor_len, mejor_allow = n, es_allow
    return True if mejor_len < 0 else mejor_allow


def nombre_agente(ua):
    """El token del producto («socimis») a partir del User-Agent completo."""
    return ua.split("/")[0].split()[0] if ua else "*"


def puerta(url, ua=red.UA):
    """(permitido, motivo). Lee robots.txt una vez (quien llama lo cachea) con nuestro propio User-Agent."""
    p = urllib.parse.urlsplit(url)
    ruta = urllib.parse.unquote(p.path) or "/"
    if p.query:
        ruta += "?" + urllib.parse.unquote(p.query)
    direccion = "%s://%s/robots.txt" % (p.scheme, p.netloc)
    try:
        r = red.pedir_bytes(direccion, ua, timeout=12, max_bytes=512 * 1024, limite=30)
    except red.ErrorFuente as e:
        return False, "SIN CONFIRMAR (%s): no se baja" % e
    if r["codigo"] == 404:
        return True, "PERMITIDO: no hay robots.txt publicado"
    if r["codigo"] != 200:
        return False, "SIN CONFIRMAR (HTTP %s): no se baja" % r["codigo"]
    texto = r["cuerpo"].decode("utf-8", errors="replace")
    if not es_robots(texto):
        return False, "SIN CONFIRMAR (200 pero el cuerpo no es un robots.txt): no se baja"
    if regla_ilegible(texto):
        return False, "SIN CONFIRMAR (una regla no es UTF-8 válido): no se baja"
    for a in (nombre_agente(ua), "*"):
        if not permitido(texto, a, ruta):
            return False, "PROHIBIDO para %s en robots.txt: no se baja" % a
    return True, "PERMITIDO: robots.txt permite esta ruta"

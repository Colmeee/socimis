"""Descargas educadas: un ritmo por servidor, robots.txt antes de cada URL y un diario para reanudar.

Por qué existe: Juan descartó el scraping masivo (octubre de 2026) y eligió el «lote educado» el 2026-10-26: una ficha
y sus pocos documentos por sociedad, con pausa entre peticiones, respetando robots.txt, IPv4 primero (red.py) y
con puntos de reanudación para que un corte (el Mac se duerme, la nube se cierra) no obligue a repetir nada.

Lo que hace:
  - `Cola.bajar(url, destino)`: espera lo que toque para ese servidor (PAUSA_S por defecto), comprueba robots.txt
    (una vez por servidor y ruta), baja por red.pedir_bytes, escribe el fichero y apunta en el diario URL, huella,
    tamaño y fecha. Si el diario ya tiene esa URL con su fichero en disco, no vuelve a bajarla.
  - El diario es un JSON por líneas (`descargas/diario.jsonl`): una línea por descarga, se puede leer a medias.
Sin dependencias. Python 3.9.
"""
import json
import os
import time
import urllib.parse
from datetime import date

from . import red, robots
from .huella import sha256_bytes

PAUSA_S = 2.0            # entre dos peticiones al mismo servidor
MAX_PDF = 60 * 1024 * 1024

# Solo se baja de estos servidores (lista blanca; auditoría de Cancerbero, 2026-10-26): una URL que venga de una página y
# apunte a otro sitio (una IP interna, otro dominio) no se baja. Una fuente nueva se añade aquí a propósito.
SERVIDORES = ("apiweb.bolsasymercados.es", "www.bolsasymercados.es", "www.cnmv.es", "cnmv.es")

# Servidores cuyo robots.txt se pasa por alto A PROPÓSITO, con el porqué. Decisión de Juan por pantalla el 2026-10-26:
# apiweb.bolsasymercados.es sirve TODOS los PDF que BME Growth y Scaleup enseñan a cualquier visitante («Ver PDF») y su
# robots.txt dice «Disallow: /» para todos; se bajan igual, uno a uno, con pausa y solo los cinco por sociedad que elige
# fuentes/bme.py. Queda apuntado en cada línea del diario (`excepcion_robots`) y en docs/PRD.md, decisión 6.
EXCEPCIONES_ROBOTS = {
    "apiweb.bolsasymercados.es": "decisión de Juan (2026-10-26): enlaces públicos de la ficha de BME, uno a uno, 5 por sociedad",
}


class Rechazada(Exception):
    """La URL no se baja: robots.txt lo prohíbe o no se pudo confirmar."""


class Cola:
    def __init__(self, carpeta, pausa=PAUSA_S, ua=red.UA, hoy=None):
        self.carpeta = carpeta
        self.pausa = pausa
        self.ua = ua
        self.hoy = hoy or date.today().isoformat()
        self.diario = os.path.join(carpeta, "diario.jsonl")
        self._ultima = {}          # host -> monotonic de la última petición
        self._robots = {}          # (host, ruta) -> (permitido, motivo)
        self._hechas = self._leer_diario()
        os.makedirs(carpeta, exist_ok=True)

    def _leer_diario(self):
        hechas = {}
        if os.path.exists(self.diario):
            with open(self.diario, encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if linea:
                        try:
                            r = json.loads(linea)
                            hechas[r["url"]] = r
                        except (ValueError, KeyError):
                            continue
        return hechas

    def _esperar(self, host):
        ahora = time.monotonic()
        antes = self._ultima.get(host)
        if antes is not None and ahora - antes < self.pausa:
            time.sleep(self.pausa - (ahora - antes))
        self._ultima[host] = time.monotonic()

    def permitida(self, url):
        p = urllib.parse.urlsplit(url)
        clave = (p.netloc, p.path)
        if clave not in self._robots:
            self._esperar(p.netloc)
            self._robots[clave] = robots.puerta(url, ua=self.ua)
        return self._robots[clave]

    def ya_bajada(self, url):
        r = self._hechas.get(url)
        if r and os.path.exists(os.path.join(self.carpeta, r["fichero"])):
            return r
        return None

    def bajar(self, url, nombre, max_bytes=MAX_PDF):
        """Devuelve el registro del diario {url, fichero, huella, bytes, fecha, codigo}. Lanza Rechazada o red.ErrorFuente."""
        previa = self.ya_bajada(url)
        if previa:
            return previa
        partes = urllib.parse.urlsplit(url)
        host = partes.hostname or ""
        if partes.scheme != "https" or host not in SERVIDORES:
            raise Rechazada("%s: el servidor no está en la lista blanca (%s) o no es https" % (url, ", ".join(SERVIDORES)))
        excepcion = EXCEPCIONES_ROBOTS.get(host)
        if excepcion is None:
            permitido, motivo = self.permitida(url)
            if not permitido:
                raise Rechazada("%s: %s" % (url, motivo))
        self._esperar(host)
        r = red.pedir_bytes(url, self.ua, timeout=30, max_bytes=max_bytes, limite=300)
        if r["codigo"] != 200:
            raise red.ErrorFuente("HTTP %s al bajar %s" % (r["codigo"], url), r["codigo"])
        if r["truncado"]:
            raise red.ErrorFuente("%s pasa de %d MB: no se guarda." % (url, max_bytes // (1024 * 1024)))
        destino = os.path.join(self.carpeta, nombre)
        if not os.path.realpath(destino).startswith(os.path.realpath(self.carpeta) + os.sep):
            raise Rechazada("el destino %s se sale de %s" % (nombre, self.carpeta))
        if r["url"] and (urllib.parse.urlsplit(r["url"]).hostname or "") not in SERVIDORES:
            raise red.ErrorFuente("%s redirigió fuera de la lista blanca (%s): no se guarda" % (url, r["url"]))
        os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
        with open(destino, "wb") as f:
            f.write(r["cuerpo"])
        reg = {"url": url, "fichero": nombre, "huella": sha256_bytes(r["cuerpo"]), "bytes": len(r["cuerpo"]),
               "fecha": self.hoy, "codigo": r["codigo"], "tipo": r["cabeceras"].get("content-type", "")}
        if excepcion:
            reg["excepcion_robots"] = excepcion
        with open(self.diario, "a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        self._hechas[url] = reg
        return reg

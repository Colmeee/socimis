"""La única puerta de salida a internet de socimis. Todo lo que sale pasa por aquí.

Copiado de Cantera (herramientas/cantera/red.py, obra de Bob para Juan Colmenarejo, 2026-10-22) el 2026-10-26, con
el candado renombrado: es el arreglo del «cuelgue de Lugo» (IPv4 primero, tope duro por intento) y no se reescribe.

En las pruebas se cierra con la variable SOCIMIS_SIN_RED=1: cualquier intento de salir
revienta con un error claro, así una prueba que se olvidara de simular algo no llama a
nadie. Sin dependencias: urllib.
"""
import base64
import http.client
import json
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPException

UA = "socimis/0.1 (+uso propio; base de SOCIMIs cotizadas)"

# Tres relojes por petición (2026-10-22, tras un `buscar --openmercantil` que estuvo 20 minutos «colgado» sin gastar CPU):
#   CONEXION = lo que se espera a CADA dirección del servidor al conectar. Era el verdadero culpable: openmercantil.es tiene dos direcciones IPv6 y dos
#              IPv4; en este Mac el IPv6 no sale a ninguna parte, y Python prueba las direcciones EN ORDEN con el timeout ENTERO en cada una (2 × 25 s
#              por conexión, y reintento, y tres peticiones por empresa: horas). Ahora se prueba el IPv4 primero y el IPv6 queda de reserva, y cada
#              dirección espera como mucho CONEXION. (curl no lo sufre porque prueba las dos familias a la vez.)
#   TIMEOUT  = lo que tarda cada lectura del socket una vez conectado. Corta al servidor que acepta y calla.
#   LIMITE   = el tope DURO de un intento entero, de la resolución del nombre al último byte del cuerpo. Es el que corta lo que
#              los otros dos no ven: un DNS que no contesta (getaddrinfo no obedece al timeout del socket), un servidor que gotea un byte
#              cada pocos segundos (cada lectura cumple, la respuesta no acaba nunca), un cuerpo sin fin.
# El intento se hace en un hilo aparte (daemon) y quien llama espera como mucho LIMITE: si no ha acabado, se da por perdido y se sigue.
CONEXION = 5
TIMEOUT = 25
LIMITE = 60
MAX_CUERPO = 20 * 1024 * 1024        # lo que se acepta de una respuesta JSON (un cuerpo sin fin no puede llenar la memoria)


class ErrorFuente(Exception):
    """Algo falló al hablar con una fuente. El mensaje está pensado para leerlo Juan.
    `codigo` es el número HTTP cuando lo hay (401, 403, 404, 429...): así quien llama puede
    distinguir «no existe» de «has pasado el tope» sin leer el texto."""

    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


class ErrorTiempo(ErrorFuente):
    """La fuente no contestó a tiempo (conectar, leer o el tope duro del intento). Sin código HTTP. Es un ErrorFuente: quien ya capturaba
    ese lo sigue capturando; quien quiera decir «tiempo agotado» a Juan la distingue con isinstance."""


def _conectar(direccion, timeout, conexion, source_address=None):
    """Abre el socket a (host, puerto): las direcciones IPv4 primero y las IPv6 de reserva, cada una con un máximo de `conexion` segundos para conectar;
    ya conectado, el timeout del socket pasa a ser `timeout` (cada lectura). Es `socket.create_connection` con otro orden y otro reloj de conexión.
    Lanza el último error si no conecta con ninguna."""
    host, puerto = direccion
    infos = socket.getaddrinfo(host, puerto, 0, socket.SOCK_STREAM)
    infos.sort(key=lambda i: 0 if i[0] == socket.AF_INET else 1)         # estable: el orden del sistema se conserva dentro de cada familia
    ultimo = None
    for familia, tipo, proto, _, sa in infos:
        sock = None
        try:
            sock = socket.socket(familia, tipo, proto)
            sock.settimeout(conexion if timeout is None else min(conexion, timeout))
            if source_address:
                sock.bind(source_address)
            sock.connect(sa)
            sock.settimeout(timeout)
            return sock
        except OSError as e:
            ultimo = e
            if sock is not None:
                sock.close()
    raise ultimo or OSError("el nombre %s no tiene direcciones" % host)


def _conexion_con(base, conexion):
    """Una clase de conexión (http.client.HTTPConnection o HTTPSConnection) que conecta con `_conectar` y no con `socket.create_connection`."""
    class _Conexion(base):
        def __init__(self, *a, **k):
            base.__init__(self, *a, **k)
            self._create_connection = lambda dir_, timeout=None, source_address=None: _conectar(dir_, timeout, conexion, source_address)
    return _Conexion


def _manejadores(contexto, conexion):
    """Los manejadores de urllib que usan `_conectar`: http (las pruebas, 127.0.0.1) y https (todo lo demás)."""
    http_con, https_con = _conexion_con(http.client.HTTPConnection, conexion), _conexion_con(http.client.HTTPSConnection, conexion)

    class _HTTP(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(http_con, req)

    class _HTTPS(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(https_con, req, context=contexto)

    return [_HTTP(), _HTTPS(context=contexto)]


def _abrir(req, timeout, conexion, extra=()):
    """Abre la petición con los manejadores de arriba (más los `extra`, p. ej. el de redirecciones con candado). Devuelve la respuesta de urllib."""
    return urllib.request.build_opener(*(_manejadores(contexto_ssl(), conexion) + list(extra))).open(req, timeout=timeout)


def _es_de_tiempo(e):
    """¿Este fallo de red es un tiempo agotado? (el timeout del socket llega de varias formas según la versión de Python y el punto donde salta)"""
    if isinstance(e, (TimeoutError, socket.timeout)):
        return True
    motivo = getattr(e, "reason", None)
    return isinstance(motivo, (TimeoutError, socket.timeout)) or "timed out" in str(motivo or e).lower()


def _con_limite(fn, limite, que):
    """Ejecuta fn() y devuelve lo que devuelva (o lanza lo que lance). Si en `limite` segundos no ha acabado, lanza ErrorTiempo y deja el hilo
    atrás: es un hilo daemon, muere solo cuando su socket cumpla el timeout (o con el proceso). `que`: de qué se trata, para el mensaje."""
    caja = {}

    def _corre():
        try:
            caja["ok"] = fn()
        except BaseException as e:           # noqa: BLE001 - se vuelve a lanzar en quien llama
            caja["error"] = e

    hilo = threading.Thread(target=_corre, daemon=True)
    hilo.start()
    hilo.join(limite)
    if hilo.is_alive():
        raise ErrorTiempo("Tiempo agotado: %s no acabó en %g s (tope duro por intento)." % (que, limite))
    if "error" in caja:
        raise caja["error"]
    return caja["ok"]


def _leer_cuerpo(r, plazo, max_bytes):
    """El cuerpo de la respuesta, a trozos (una lectura por trozo) y mirando el reloj entre ellos: un servidor que gotea no pasa del plazo.
    Devuelve (bytes, truncado)."""
    partes, total = [], 0
    while True:
        if time.monotonic() > plazo:
            raise ErrorTiempo("Tiempo agotado: la respuesta llegaba a cuentagotas y no acabó a tiempo.")
        trozo = r.read1(65536) if hasattr(r, "read1") else r.read(65536)
        if not trozo:
            return b"".join(partes), False
        partes.append(trozo)
        total += len(trozo)
        if total > max_bytes:
            return b"".join(partes)[:max_bytes + 1], True


def contexto_ssl():
    """El Python de python.org no trae certificados hasta ejecutar su «Install
    Certificates.command» y entonces todo https falla con CERTIFICATE_VERIFY_FAILED. macOS
    trae los suyos en /etc/ssl/cert.pem: si los de Python no están, se usan esos.
    Sigue verificando; no se desactiva nada. (Mismo arreglo que el radar y el Prospector.)"""
    ctx = ssl.create_default_context()
    if not os.environ.get("SSL_CERT_FILE"):
        propio = ssl.get_default_verify_paths().cafile
        if (not propio or not os.path.exists(propio)) and os.path.exists("/etc/ssl/cert.pem"):
            ctx.load_verify_locations("/etc/ssl/cert.pem")
    return ctx


def _sin_secretos(url):
    """Solo esquema y servidor: una plantilla con {usuario}/{clave} en la ruta o en la query no se filtra."""
    p = urllib.parse.urlsplit(url)
    return "%s://%s/..." % (p.scheme, p.hostname or "")


def pedir_json(url, usuario=None, clave=None, auth="basic", reintentos=2, cabeceras=None, timeout=None, limite=None, conexion=None):
    """GET que devuelve el JSON ya leído.
      auth="basic": usuario y clave en la cabecera Authorization.
      auth="query": van en la propia URL (la plantilla del config ya los lleva; aquí no se tocan).
      auth="cabeceras": ninguna de las dos; `cabeceras` (un dict) lleva las que pida el proveedor (una API-Key y un API-Secret, por ejemplo). Nunca se imprimen.
    `conexion` (por defecto CONEXION): lo que espera cada dirección del servidor al conectar (IPv4 primero). `timeout` (por defecto TIMEOUT): lo que
    tarda cada lectura del socket. `limite` (por defecto LIMITE): el tope DURO de cada intento entero, DNS y cuerpo incluidos (ver arriba). Reintenta con espera creciente solo lo transitorio (5xx, timeouts), `reintentos`
    veces como mucho: el peor caso es (reintentos + 1) intentos de `limite` segundos más las esperas de 1, 2, 4... s. Un 401/403 o un 429
    paran en seco con un mensaje claro: insistir con una clave mala o pasado el tope no sirve. Si todos los intentos se agotan por tiempo,
    lanza ErrorTiempo (que es un ErrorFuente)."""
    if os.environ.get("SOCIMIS_SIN_RED") == "1":
        raise RuntimeError("SOCIMIS_SIN_RED=1: se intentó salir a internet (%s)" % _sin_secretos(url))
    timeout = TIMEOUT if timeout is None else timeout
    limite = LIMITE if limite is None else limite
    conexion = CONEXION if conexion is None else conexion
    cab = {"User-Agent": UA, "Accept": "application/json"}
    if auth == "basic" and usuario:
        token = base64.b64encode(("%s:%s" % (usuario, clave or "")).encode("utf-8")).decode("ascii")
        cab["Authorization"] = "Basic " + token
    for k, v in (cabeceras or {}).items():
        cab[str(k)] = str(v)

    def _un_intento():
        req = urllib.request.Request(url, headers=cab)
        plazo = time.monotonic() + limite
        with _abrir(req, timeout, conexion) as r:
            cuerpo, truncado = _leer_cuerpo(r, plazo, MAX_CUERPO)
        if truncado:
            raise ErrorFuente("La fuente contestó una respuesta de más de %d MB: no se lee." % (MAX_CUERPO // (1024 * 1024)))
        return json.loads(cuerpo.decode("utf-8"))

    ultimo, codigo_final, de_tiempo = None, None, False
    for intento in range(reintentos + 1):
        de_tiempo = False
        try:
            return _con_limite(_un_intento, limite, "la petición a %s" % _sin_secretos(url))
        except ErrorTiempo as e:
            ultimo, codigo_final, de_tiempo = str(e), None, True
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ErrorFuente("La fuente rechazó el usuario o la clave (HTTP %d). Revisa la configuración." % e.code, e.code)
            if e.code == 429:
                raise ErrorFuente("La fuente dice que has pasado el tope de consultas (HTTP 429). Espera y repite; no se insiste.", 429)
            if e.code == 404:
                raise ErrorFuente("La fuente no conoce esa dirección (HTTP 404). Revisa la URL.", 404)
            ultimo, codigo_final = "HTTP %d" % e.code, e.code
            if e.code < 500:
                break
        except ErrorFuente:
            raise
        except (urllib.error.URLError, TimeoutError, OSError, HTTPException) as e:
            de_tiempo = _es_de_tiempo(e)
            ultimo, codigo_final = ("tiempo agotado (sin conectar en %g s por dirección o sin datos en %g s)" % (conexion, timeout)) if de_tiempo else str(getattr(e, "reason", e)), None
        except ValueError as e:
            raise ErrorFuente("La fuente contestó algo que no es JSON (%s)." % e)
        if intento < reintentos:
            time.sleep(2 ** intento)
    if de_tiempo:
        raise ErrorTiempo("La fuente no contestó a tiempo tras %d intento(s): %s" % (reintentos + 1, ultimo))
    raise ErrorFuente("No se pudo hablar con la fuente: %s" % ultimo, codigo_final)


# --------------------------------------------------------------------------- páginas y feeds abiertos (el vigilante de prensa)
LOCAL = ("localhost", "127.0.0.1", "::1")


def es_local(url):
    """True si la URL apunta a esta misma máquina (localhost, 127.0.0.1 o ::1)."""
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower() in LOCAL
    except ValueError:
        return False


def _comprobar_candado(url):
    """Con SOCIMIS_SIN_RED=1 solo se puede hablar con esta misma máquina: así las pruebas del vigilante usan un servidor local de mentira y
    ninguna sale de verdad. Cualquier otra dirección revienta, también las que llegan por una redirección."""
    esquema = urllib.parse.urlsplit(url).scheme.lower()
    if esquema not in ("http", "https"):
        raise ErrorFuente("Solo se leen direcciones http o https (esta es «%s»)." % (esquema or "sin esquema"))
    if os.environ.get("SOCIMIS_SIN_RED") == "1" and not es_local(url):
        raise RuntimeError("SOCIMIS_SIN_RED=1: se intentó salir a internet (%s)" % _sin_secretos(url))


class _Redireccion(urllib.request.HTTPRedirectHandler):
    """Sigue las redirecciones de siempre, pero cada salto pasa por el mismo candado (y no se puede saltar a file:// ni a ftp://)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _comprobar_candado(urllib.parse.urljoin(req.full_url, newurl))
        return urllib.request.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)


LIMITE_PAGINA = 30                    # tope duro de una página o un feed del vigilante de prensa (más corto que el de una API: son muchos y de uno en uno)


def pedir_bytes(url, ua, timeout=10, max_bytes=2000000, limite=None, conexion=None):
    """GET de una página o un feed abierto: {codigo, cabeceras (en minúsculas), cuerpo (bytes, como mucho max_bytes), truncado, url (la final)}.
    A diferencia de `pedir_json`, un código HTTP de error NO lanza: se devuelve (el vigilante decide qué hace con un 404 o un 403). Lanza
    ErrorFuente si no hay respuesta (sin red, dirección que no es http/https) y ErrorTiempo (un ErrorFuente) si se agota el tiempo: `timeout`
    es el de cada lectura del socket, `conexion` (por defecto CONEXION) el de cada dirección al conectar (IPv4 primero) y `limite` (por defecto LIMITE_PAGINA)
    el tope duro de la página entera, redirecciones incluidas.
    Sin sesión, sin cookies, sin saltarse nada."""
    _comprobar_candado(url)
    limite = LIMITE_PAGINA if limite is None else limite
    conexion = CONEXION if conexion is None else conexion
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})

    def _bajar():
        plazo = time.monotonic() + limite
        try:
            r = _abrir(req, timeout, conexion, extra=[_Redireccion()])
        except urllib.error.HTTPError as e:
            r = e
        except (urllib.error.URLError, TimeoutError, OSError, HTTPException, ValueError) as e:
            if _es_de_tiempo(e):
                raise ErrorTiempo("Tiempo agotado: %s no contestó en %g s." % (_sin_secretos(url), timeout))
            raise ErrorFuente("No se pudo leer %s: %s" % (_sin_secretos(url), getattr(e, "reason", e)))
        try:
            cuerpo, truncado = _leer_cuerpo(r, plazo, max_bytes)
        except ErrorTiempo:
            raise ErrorTiempo("Tiempo agotado: %s llegaba a cuentagotas y no acabó en %g s." % (_sin_secretos(url), limite))
        except (TimeoutError, OSError, HTTPException) as e:
            if _es_de_tiempo(e):
                raise ErrorTiempo("Tiempo agotado: se cortó la lectura de %s (%g s sin datos)." % (_sin_secretos(url), timeout))
            raise ErrorFuente("Se cortó la lectura de %s: %s" % (_sin_secretos(url), e))
        finally:
            r.close()
        cab = {k.lower(): v for k, v in r.headers.items()}
        return {"codigo": getattr(r, "status", None) or r.getcode(), "cabeceras": cab, "cuerpo": cuerpo[:max_bytes],
                "truncado": truncado, "url": r.geturl() if hasattr(r, "geturl") else url}

    return _con_limite(_bajar, limite, "la página %s" % _sin_secretos(url))

"""Del PDF al texto, conservando las columnas.

Por qué existe: todos los parsers de este paquete leen TEXTO con la disposición de la página (las cifras de un balance
están en columnas: ejercicio y ejercicio anterior). Se intenta `pdftotext -layout` (Poppler; está en la nube) y si no,
`pypdf` con `extraction_mode="layout"` (el Mac no trae Poppler sin Homebrew; `python3 -m pip install pypdf` sí vale).
Si el PDF es un escaneo (sin capa de texto) el texto sale casi vacío y `es_escaneado` lo dice: ese PDF va a la cola de
OCR del Mac (decisión de Juan del 2026-10-26: la nube baja, el Mac hace OCR), nunca se inventa.

Sin dependencias obligatorias. Python 3.9.
"""
import shutil
import subprocess

SALTO_PAGINA = "\f"
UMBRAL_ESCANEADO = 80     # caracteres por página por debajo de los cuales el PDF se considera escaneado


def extractores():
    lista = []
    if shutil.which("pdftotext"):
        lista.append("pdftotext")
    try:
        import pypdf  # noqa: F401
        lista.append("pypdf")
    except ImportError:
        pass
    return lista


def _pdftotext(ruta):
    r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", ruta, "-"], capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("pdftotext falló: %s" % r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout.decode("utf-8", "replace")


def _pypdf(ruta):
    import pypdf
    lector = pypdf.PdfReader(ruta)
    paginas = []
    for p in lector.pages:
        try:
            paginas.append(p.extract_text(extraction_mode="layout") or "")
        except TypeError:          # pypdf viejo sin modo layout
            paginas.append(p.extract_text() or "")
    return SALTO_PAGINA.join(paginas)


def texto_de_pdf(ruta):
    """(texto, extractor). Lanza RuntimeError si no hay ningún extractor."""
    for nombre in extractores():
        try:
            return ((_pdftotext if nombre == "pdftotext" else _pypdf)(ruta), nombre)
        except Exception as e:  # noqa: BLE001 - se prueba el siguiente
            ultimo = e
            continue
    if not extractores():
        raise RuntimeError("No hay lector de PDF: instala Poppler (pdftotext) o `python3 -m pip install pypdf`.")
    raise RuntimeError("No se pudo leer %s: %s" % (ruta, ultimo))


def paginas(texto):
    return texto.split(SALTO_PAGINA)


def paginas_sin_texto(texto):
    """(páginas casi vacías, páginas totales). Una página con menos de UMBRAL_ESCANEADO caracteres es una imagen."""
    pags = [p for p in paginas(texto) if True]
    if len(pags) > 1 and not pags[-1].strip():
        pags = pags[:-1]          # pdftotext deja un salto de página final
    vacias = sum(1 for p in pags if len(p.strip()) < UMBRAL_ESCANEADO)
    return vacias, len(pags)


def es_escaneado(texto):
    """True si la mitad o más de las páginas no tienen texto: el PDF es un escaneo entero o en parte (cuentas en imagen y
    carta de presentación en texto, que es lo habitual en las pequeñas de BME). Lo que no se puede leer va a la cola de OCR."""
    vacias, total = paginas_sin_texto(texto)
    if total == 0:
        return True
    return vacias / float(total) >= 0.5

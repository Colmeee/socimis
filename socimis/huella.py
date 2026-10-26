"""La huella de un documento: SHA-256 del fichero tal cual se bajó.

Por qué existe: los PDF y los xhtml no suben al repositorio (tamaño y derechos). Lo que sí sube es la URL y esta
huella, para que cualquiera pueda bajar el mismo documento y comprobar que es el mismo byte a byte.
"""
import hashlib


def sha256_fichero(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1 << 20), b""):
            h.update(trozo)
    return h.hexdigest()


def sha256_bytes(datos):
    return hashlib.sha256(datos).hexdigest()

"""El modelo de la base: una ficha por SOCIMI y, dentro, cada dato con su origen.

Por qué así: la regla de la casa (Cantera) es que cada cifra lleve su fuente y que «no consta» sea un valor. Aquí
un dato nunca es un número suelto: es un `dato` con valor, unidad, fecha a la que se refiere, URL de la fuente, huella
del documento, fecha de consulta y nivel de contraste. El esquema vale para TODAS las SOCIMIs de España aunque la
primera carga sea la del piloto vasco.

Niveles de contraste (de más a menos fiable):
  oficial    la cifra está en un documento oficial depositado (cuentas auditadas, ESEF de la CNMV, aviso al mercado)
  mercado    la da la página del mercado (BME, CNMV) y no un documento (capitalización, domicilio de la ficha)
  empresa    la publica la propia sociedad en su web
  derivado   calculado aquí a partir de datos oficiales (deuda financiera total, LTV neto); lleva la fórmula en `nota`
  prensa     la dice la prensa
  no_consta  no se ha encontrado en ninguna fuente

Python 3.9, sin dependencias.
"""
import json
from datetime import date

CONTRASTES = ("oficial", "mercado", "empresa", "derivado", "prensa", "no_consta")

# los campos numéricos por ejercicio, con su unidad; es la lista que la base escribe como filas de `dato`
CAMPOS_EJERCICIO = {
    "tesoreria": "EUR",
    "valor_razonable_inmuebles": "EUR",     # inversiones inmobiliarias del balance (valor razonable si el modelo es NIIF; coste si PGC: lo dice la nota)
    "gav_valoracion": "EUR",                # la valoración externa comunicada al mercado (RICS)
    "bonos_lp": "EUR", "bonos_cp": "EUR", "prestamos_lp": "EUR", "prestamos_cp": "EUR",
    "deuda_financiera": "EUR",              # derivado: bonos + préstamos (CNMV) o deudas con entidades de crédito LP + CP (BME)
    "deuda_financiera_neta": "EUR",         # derivado: deuda financiera - tesorería
    "ltv_declarado": "%",                   # el que publica la sociedad (EPRA LTV o LTV)
    "ltv_neto": "%",                        # derivado: deuda neta / valor de los inmuebles
    "ingresos": "EUR",                      # cifra de negocios / revenue
    "ingresos_rentas": "EUR",               # ingresos por arrendamientos cuando se desglosan
    "resultado": "EUR",
    "patrimonio_neto": "EUR",
    "activo_total": "EUR",
    "pasivo_no_corriente": "EUR", "pasivo_corriente": "EUR",
    "dividendos_pagados": "EUR",            # pagados en el ejercicio (flujo de efectivo)
    "dividendo_acordado": "EUR",            # con cargo al ejercicio, acordado por la junta del año siguiente
    "dividendo_por_accion": "EUR",
    "capitalizacion": "EUR",
    "cotizacion": "EUR",
    "nav_por_accion": "EUR",
}


def dato(valor, fuente, fecha=None, huella=None, contraste="oficial", consultado=None, nota=None, unidad="EUR", donde=None):
    """Un dato con su origen. `donde` es la pista dentro del documento (id del hecho iXBRL, rótulo, página)."""
    if contraste not in CONTRASTES:
        raise ValueError("contraste desconocido: %s" % contraste)
    return {"valor": valor, "unidad": unidad, "fecha": fecha, "fuente": fuente, "huella": huella,
            "consultado": consultado or date.today().isoformat(), "contraste": contraste, "nota": nota, "donde": donde}


def no_consta(nota=None):
    return dato(None, None, contraste="no_consta", nota=nota, unidad=None)


def ficha_vacia():
    return {
        "esquema": 1,
        "sociedad": {"nombre": None, "nif": None, "isin": None, "ticker": None, "mercado": None, "segmento": None,
                     "domicilio": None, "provincia": None, "web": None, "auditor": None, "asesor_registrado": None,
                     "proveedor_liquidez": None, "fecha_incorporacion": None, "fecha_regimen_socimi": None,
                     "estado_cotizacion": "cotiza", "capitalizacion": None, "cotizacion": None, "fecha_cotizacion": None,
                     "url_ficha": None},
        "ejercicios": {},          # "2025": {campo: dato}
        "accionistas": [],         # {accionista, tipo, pct_total, pct_directo, pct_indirecto, fecha, fuente, huella, contraste}
        "administradores": [],     # {nombre, cargo, desde, hasta, fuente}: se rellena cuando haya fuente (IAGC / ficha); hoy no se extrae
        "vencimientos": [],        # {entidad, importe, vencimiento, tipo_interes, fecha, fuente, huella}
        "activos": [],             # {nombre, ubicacion, valor, fecha, fuente, huella}
        "documentos": [],          # {tipo, fecha, url, huella, titulo, bytes, escaneado}
        "vinculo_vasco": None,     # lo que escribe vinculo_vasco.evaluar
        "avisos": [],
    }


def valor(ficha, ejercicio, campo):
    d = ficha.get("ejercicios", {}).get(str(ejercicio), {}).get(campo)
    return None if d is None else d.get("valor")


def ultimo_ejercicio(ficha):
    anios = [a for a in ficha.get("ejercicios", {}) if a.isdigit()]
    return max(anios) if anios else None


def poner(ficha, ejercicio, campo, d):
    if campo not in CAMPOS_EJERCICIO:
        raise KeyError("campo desconocido: %s" % campo)
    ficha["ejercicios"].setdefault(str(ejercicio), {})[campo] = d


def completar_derivados(ficha):
    """Deuda financiera, deuda neta y LTV neto cuando hay con qué. Cada derivado lleva su fórmula en `nota`.
    Los derivados se recalculan SIEMPRE (se borran y se vuelven a poner): si una relectura corrige un sumando, el total cambia."""
    for anio, ej in ficha["ejercicios"].items():
        for c in ("deuda_financiera", "deuda_financiera_neta", "ltv_neto"):
            if c in ej and ej[c].get("contraste") == "derivado":
                del ej[c]
        partes = [ej[c]["valor"] for c in ("bonos_lp", "bonos_cp", "prestamos_lp", "prestamos_cp") if c in ej and ej[c]["valor"] is not None]
        if partes:
            ej["deuda_financiera"] = dato(sum(partes), None, fecha=_fecha(ej), contraste="derivado",
                                          nota="bonos LP + bonos CP + préstamos LP + préstamos CP (%d sumandos)" % len(partes))
        if "deuda_financiera" in ej and "tesoreria" in ej and ej["tesoreria"]["valor"] is not None and ej["deuda_financiera"]["valor"] is not None:
            ej["deuda_financiera_neta"] = dato(ej["deuda_financiera"]["valor"] - ej["tesoreria"]["valor"], None, fecha=_fecha(ej),
                                               contraste="derivado", nota="deuda financiera - tesorería")
        base = ej.get("gav_valoracion") or ej.get("valor_razonable_inmuebles")
        if "deuda_financiera_neta" in ej and base and base.get("valor"):
            ej["ltv_neto"] = dato(round(100.0 * ej["deuda_financiera_neta"]["valor"] / base["valor"], 1), None, fecha=_fecha(ej),
                                  contraste="derivado", unidad="%",
                                  nota="deuda financiera neta / %s" % ("valoración externa (GAV)" if "gav_valoracion" in ej else "inversiones inmobiliarias del balance"))
    return ficha


def _fecha(ej):
    for d in ej.values():
        if d.get("fecha"):
            return d["fecha"]
    return None


def guardar(ficha, ruta):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(ficha, f, ensure_ascii=False, indent=1, sort_keys=True)


def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

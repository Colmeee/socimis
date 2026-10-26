"""El vínculo vasco de una SOCIMI: activos, financiación, fundadores o accionistas en Álava, Bizkaia o Gipuzkoa.

Por qué existe: el 2026-10-26 se comprobó que ninguna SOCIMI puede tener domicilio fiscal en el País Vasco (las tres
Normas Forales del Impuesto sobre Sociedades eliminaron el régimen), así que un censo por domicilio sale vacío. Juan
eligió redefinir el piloto como «vínculo vasco»: lo que la propia sociedad publica (cuentas, valoración, avisos)
delata activos en Bilbao o Vitoria, préstamos de Kutxabank o Caja Laboral, domicilio anterior o fundadores. Aquí se
mide ese vínculo sobre los textos ya bajados, con evidencia línea a línea, y nada más: no se busca a personas.

Tres señales, cada una con sus pruebas:
  activos       activos de la tabla de inversiones inmobiliarias con ubicación vasca, y su valor
  financiacion  préstamos de entidades vascas (Kutxabank, Laboral Kutxa, Bankoa) en la tabla de vencimientos
  menciones     líneas del texto que nombran lugares vascos (fuera de las dos tablas), como pista para leer a mano; antes se
                quitan las frases que engañan (BBVA, «Príncipe de Vergara», «Navas de Tolosa», «San Sebastián de los Reyes»,
                apellidos tras «Don/Dña»): `exclusiones` en vasco.json
El resultado lleva `grado`: «fuerte» (activos o financiación), «indicio» (solo menciones) o «ninguno».
"""
import json
import re
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def cargar_gazetteer(ruta=None):
    with open(ruta or AQUI / "vasco.json", encoding="utf-8") as f:
        return json.load(f)


def _patron(nombres):
    return re.compile(r"(?<![\wáéíóúñ])(" + "|".join(re.escape(n) for n in sorted(nombres, key=len, reverse=True)) + r")(?![\wáéíóúñ])", re.I)


def evaluar(ficha, textos, gaz=None):
    """ficha: la de modelo; textos: {nombre_documento: texto}. Devuelve el dict que va en ficha['vinculo_vasco']."""
    gaz = gaz or cargar_gazetteer()
    lugares = _patron([n for prov in gaz["provincias"].values() for n in prov])
    bancos = _patron(gaz["entidades_financieras"])
    exclusiones = [re.compile(x, re.I) for x in gaz.get("exclusiones", [])]

    def limpia(texto):
        for rx in exclusiones:
            texto = rx.sub(" ", texto)
        return texto
    salida = {"grado": "ninguno", "activos": [], "financiacion": [], "menciones": [], "provincias": {}}
    for a in ficha.get("activos", []):
        m = lugares.search(limpia("%s %s" % (a.get("nombre", ""), a.get("ubicacion", ""))))
        if m:
            prov = _provincia(m.group(1), gaz)
            salida["activos"].append({"nombre": a.get("nombre"), "ubicacion": a.get("ubicacion"), "valor": a.get("valor"), "provincia": prov, "fuente": a.get("fuente")})
            salida["provincias"][prov] = salida["provincias"].get(prov, 0) + (a.get("valor") or 0)
    for v in ficha.get("vencimientos", []):
        if bancos.search(v.get("entidad", "")):
            salida["financiacion"].append({"entidad": v["entidad"], "importe": v.get("importe"), "vencimiento": v.get("vencimiento"), "fuente": v.get("fuente")})
    vistas = set()
    for nombre, texto in (textos or {}).items():
        for linea in texto.splitlines():
            m = lugares.search(limpia(linea))
            if m and len(linea.strip()) > 8:
                l = re.sub(r"\s+", " ", linea.strip())[:160]
                if l in vistas:
                    continue
                vistas.add(l)
                salida["menciones"].append({"documento": nombre, "lugar": m.group(1), "provincia": _provincia(m.group(1), gaz), "linea": l})
                if len(salida["menciones"]) >= 40:
                    break
    valor_vasco = sum(salida["provincias"].values())
    total = sum(a.get("valor") or 0 for a in ficha.get("activos", []))
    salida["pct_valor_en_pais_vasco"] = round(100.0 * valor_vasco / total, 1) if total else None
    if salida["activos"] or salida["financiacion"]:
        salida["grado"] = "fuerte"
    elif salida["menciones"]:
        salida["grado"] = "indicio"
    return salida


def _provincia(lugar, gaz):
    l = lugar.lower()
    for prov, nombres in gaz["provincias"].items():
        if l in (n.lower() for n in nombres):
            return prov
    return None

"""`python3 -m socimis <orden>`: la línea de mandos. La lógica vive en los módulos; aquí solo se enlazan.

Órdenes:
  cnmv <NIF>                 lee en la CNMV los informes anuales y las participaciones de una SOCIMI del Continuo, baja el ESEF
                             consolidado más reciente, lo lee y escribe base/fichas/<NIF>.json
  bme <ficha-recolectada.json> lee el JSON que deja herramientas/recolectar_bme.js, baja los PDF elegidos (educadamente),
                             los lee y escribe base/fichas/<NIF>.json (los escaneados quedan en la cola de OCR)
  puntuar [NIF|todas]        puntúa las fichas y escribe base/puntuaciones.json y base/informe.md
  vasco [NIF|todas]          calcula el vínculo vasco con los textos de descargas/
  base                       regenera base/socimis.sqlite y base/csv/*.csv desde las fichas
  portfolio                  censo de Portfolio Stock Exchange (página pública del mercado; sin documentos, están tras login)
  euronext <listado.json>    censo de Euronext Access París desde el listado leído con navegador (sin fichas ni documentos)
  ocr-pendientes             lista los documentos escaneados que esperan OCR en el Mac
Variables: SOCIMIS_DIR (raíz de datos; por defecto la carpeta del repositorio), SOCIMIS_SIN_RED=1 (sin internet, pruebas).
"""
import argparse
import json
import os
import re
import sys
from datetime import date

from . import base, cortesia, modelo, puntuacion, red, texto_pdf, vinculo_vasco
from .fuentes import bme, cnmv, euronext, portfolio
from .parsers import avisos, estados, ixbrl

RAIZ = os.environ.get("SOCIMIS_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHAS = os.path.join(RAIZ, "base", "fichas")
DESCARGAS = os.path.join(RAIZ, "descargas")
TEXTOS = os.path.join(DESCARGAS, "texto")


def _ruta_ficha(clave):
    """clave: NIF (A12345678) o, si la fuente no publica el NIF, ISIN (ES0105746004)."""
    if not modelo.clave_valida(clave):
        raise SystemExit("Clave no válida: %r (hace falta un NIF A12345678 o un ISIN ES0105746004)" % clave)
    os.makedirs(FICHAS, exist_ok=True)
    return os.path.join(FICHAS, "%s.json" % modelo.clave_valida(clave))


def _guardar_texto(nombre, texto):
    os.makedirs(TEXTOS, exist_ok=True)
    ruta = os.path.join(TEXTOS, nombre.replace("/", "__") + ".txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)
    return ruta


def _textos_de(nif):
    salida = {}
    if not os.path.isdir(TEXTOS):
        return salida
    for n in sorted(os.listdir(TEXTOS)):
        if nif in n and n.endswith(".txt"):
            with open(os.path.join(TEXTOS, n), encoding="utf-8") as f:
                salida[n] = f.read()
    return salida


def orden_cnmv(args):
    hoy = date.today().isoformat()
    nif = args.nif.upper()
    ficha = modelo.cargar(_ruta_ficha(nif)) if os.path.exists(_ruta_ficha(nif)) else modelo.ficha_vacia()
    ficha["sociedad"].update({"nif": nif, "mercado": "Mercado Continuo", "segmento": "Continuo", "url_ficha": cnmv.URL_ENTIDAD.format(nif=nif)})
    informes, nombre = cnmv.pedir_informes_anuales(nif)
    if nombre:
        ficha["sociedad"]["nombre"] = nombre
    if not informes:
        print("La CNMV no tiene informes anuales para %s" % nif)
        return 1
    ultimo = informes[0]
    ficha["sociedad"]["auditor"] = ultimo["auditor"]
    print("%d informes anuales; el último: estados a %s, publicado %s, %s" % (len(informes), ultimo["fecha_estados"], ultimo["publicado"], ultimo["auditor"]))
    cola = cortesia.Cola(DESCARGAS, hoy=hoy)
    nombre = "cnmv/%s/ifa-consolidado-%s.xhtml" % (nif, ultimo["fecha_estados"])
    reg = cola.bajar(ultimo["url_consolidada"] or ultimo["url_individual"], nombre, max_bytes=120 * 1024 * 1024)
    print("ESEF: %s (%d bytes, sha256 %s…)" % (reg["fichero"], reg["bytes"], reg["huella"][:12]))
    ej, av = ixbrl.leer_fichero(os.path.join(DESCARGAS, reg["fichero"]))
    with open(os.path.join(DESCARGAS, reg["fichero"]), encoding="utf-8", errors="replace") as fh:
        portada = ixbrl.textos(fh.read())
    if portada.get("domicilio"):
        ficha["sociedad"]["domicilio"] = portada["domicilio"]
        ficha["sociedad"]["provincia"] = bme.provincia_de_domicilio(portada["domicilio"])
    for anio, campos in ej.items():
        for campo, h in campos.items():
            modelo.poner(ficha, anio, campo, modelo.dato(h["valor"], reg["url"], fecha=h["fecha"], huella=reg["huella"], consultado=hoy,
                                                        donde="%s %s" % (h["concepto"], h["id"]), nota="iXBRL ESEF, hecho sin dimensiones"))
    ficha["avisos"].extend(av)
    ficha["documentos"] = [d for d in ficha["documentos"] if d.get("url") != reg["url"]] + [
        {"tipo": "cuentas_anuales", "fecha": ultimo["publicado"], "url": reg["url"], "huella": reg["huella"], "titulo": "IFA %s consolidado (ESEF), registro %s" % (ultimo["fecha_estados"][:4], ultimo["registro"]),
         "bytes": reg["bytes"], "escaneado": False, "consultado": hoy}]
    try:
        ps, url_ps = cnmv.pedir_participaciones(nif)
        ficha["accionistas"] = [dict(a, fecha=a.get("fecha_registro"), fuente=url_ps or cnmv.URL_PS.format(nif=nif), huella=None, contraste="mercado") for a in ps["accionistas"]]
        print("%d accionistas significativos (CNMV, ≥ 3 %%)" % len(ficha["accionistas"]))
    except red.ErrorFuente as e:
        ficha["avisos"].append("participaciones: %s" % e)
    modelo.completar_derivados(ficha)
    modelo.guardar(ficha, _ruta_ficha(nif))
    print("Ficha: %s" % _ruta_ficha(nif))
    return 0


def _ficha_censo(soc, hoy, fuente, huella, nota):
    """Ficha de censo (Portfolio, Euronext): la sociedad y un aviso de por qué no hay más; lo demás «no consta»."""
    clave = modelo.clave({"sociedad": soc})
    if not clave:
        return None
    ficha = modelo.cargar(_ruta_ficha(clave)) if os.path.exists(_ruta_ficha(clave)) else modelo.ficha_vacia()
    ficha["sociedad"].update({k: v for k, v in soc.items() if v is not None})
    ficha["sociedad"]["regimen_socimi"] = "SOCIMI en el nombre" if soc.get("socimi_en_nombre") else "sin confirmar"
    ficha["avisos"] = [a for a in ficha.get("avisos", []) if not a.startswith("censo:")] + ["censo: " + nota]
    ficha["documentos"] = [d for d in ficha["documentos"] if d.get("tipo") != "censo"] + [
        {"tipo": "censo", "fecha": hoy, "url": fuente, "huella": huella, "titulo": "Página del mercado de la que sale el censo", "bytes": None, "escaneado": False, "consultado": hoy}]
    modelo.guardar(ficha, _ruta_ficha(clave))
    return clave


def orden_portfolio(args):
    """Censo de Portfolio Stock Exchange: una lectura de la página pública del mercado (con pausa y diario); sin documentos
    (están tras login). Las fichas se guardan por ISIN porque Portfolio no publica el NIF."""
    hoy = date.today().isoformat()
    cola = cortesia.Cola(DESCARGAS, hoy=hoy)
    reg = cola.bajar(portfolio.URL_MERCADO, "portfolio/mercado-%s.html" % hoy, max_bytes=5 * 1024 * 1024)
    with open(os.path.join(DESCARGAS, reg["fichero"]), encoding="utf-8", errors="replace") as fh:
        emisores = portfolio.emisores(fh.read())
    n = 0
    for e in emisores:
        if e.get("pais") not in (None, "ES") or re.search(r"\bSCR\b", e.get("nombre") or ""):
            print("fuera del censo (no es sociedad española de inmuebles): %s" % e.get("nombre"))
            continue
        soc = dict(portfolio.sociedad_desde_emisor(e), socimi_en_nombre=e.get("socimi_en_nombre"), fecha_cotizacion=hoy)
        if _ficha_censo(soc, hoy, reg["url"], reg["huella"], "Portfolio Stock Exchange solo enseña sin login nombre, ISIN, capitalización y precio; los documentos están tras login (2026-10-27)"):
            n += 1
    print("Portfolio: %d emisores en la página, %d fichas de censo" % (len(emisores), n))
    return 0


def orden_euronext(args):
    """Censo de Euronext Access París desde el listado guardado (descargas/euronext/listado-AAAA-MM-DD.json, una lectura con
    navegador). No recorre fichas ni baja documentos: las condiciones de uso de Euronext lo prohíben sin permiso escrito y
    la decisión es de Juan (PRD)."""
    hoy = date.today().isoformat()
    listado = euronext.cargar_listado(args.listado)
    n = 0
    for e in euronext.emisores(listado):
        soc = dict(euronext.sociedad_desde_emisor(e), socimi_en_nombre=e.get("socimi_en_nombre"))
        if _ficha_censo(soc, listado.get("consultado") or hoy, listado.get("fuente") or euronext.URL_LISTADO, None,
                        "Euronext Access París: solo el listado público (nombre recortado, ISIN, símbolo, último precio); fichas y documentos sin recorrer por sus condiciones de uso (2026-10-27)"):
            n += 1
    print("Euronext Access París: %d fichas de censo" % n)
    return 0


def orden_bme(args):
    hoy = date.today().isoformat()
    with open(args.recolectada, encoding="utf-8") as f:
        rec = json.load(f)
    soc = bme.sociedad_desde_ficha(rec)
    nif = soc["nif"] or bme.nif_valido(args.nif)
    if not nif:
        print("La ficha recolectada no trae un NIF válido; pásalo con --nif A12345678")
        return 1
    ficha = modelo.cargar(_ruta_ficha(nif)) if os.path.exists(_ruta_ficha(nif)) else modelo.ficha_vacia()
    ficha["avisos"] = []
    ficha["sociedad"].update({k: v for k, v in soc.items() if v is not None})
    ficha["sociedad"]["provincia"] = bme.provincia_de_domicilio(soc.get("domicilio"))
    ficha["sociedad"]["fecha_incorporacion"] = ficha["sociedad"].get("fecha_incorporacion") or rec.get("fecha_incorporacion")
    elegidos = bme.elegir_documentos(rec.get("documentos", []))
    print("%s (%s): %d documentos en la ficha, %d elegidos: %s" % (soc["nombre"], nif, len(rec.get("documentos", [])), len(elegidos), ", ".join(sorted(elegidos))))
    cola = cortesia.Cola(DESCARGAS, hoy=hoy)
    docs_previos = {d["url"]: d for d in ficha.get("documentos", [])}
    for tipo, doc in sorted(elegidos.items()):
        try:
            reg = cola.bajar(doc["url"], bme.nombre_fichero(nif, doc))
        except (cortesia.Rechazada, red.ErrorFuente) as e:
            ficha["avisos"].append("%s: %s" % (tipo, e))
            print("  ✗ %s: %s" % (tipo, e))
            continue
        ruta = os.path.join(DESCARGAS, reg["fichero"])
        texto, extractor = texto_pdf.texto_de_pdf(ruta)
        escaneado = texto_pdf.es_escaneado(texto)
        _guardar_texto("%s-%s-%s" % (nif, tipo, doc.get("fecha")), texto)
        docs_previos[reg["url"]] = {"tipo": tipo, "fecha": doc.get("fecha"), "url": reg["url"], "huella": reg["huella"], "titulo": (doc.get("titulo") or doc.get("descripcion") or "")[:200],
                                    "bytes": reg["bytes"], "escaneado": escaneado, "consultado": hoy}
        print("  ✓ %s: %s, %d KB, %s%s" % (tipo, doc.get("fecha"), reg["bytes"] // 1024, extractor, " — ESCANEADO: a la cola de OCR" if escaneado else ""))
        if escaneado:
            continue
        revisar = _volcar(ficha, tipo, texto, reg, doc, hoy)
        if revisar:
            docs_previos[reg["url"]]["revisar"] = True
            print("    ⚠️ estados no reconocidos: queda marcado para revisar")
    ficha["documentos"] = list(docs_previos.values())
    modelo.completar_derivados(ficha)
    modelo.guardar(ficha, _ruta_ficha(nif))
    print("Ficha: %s" % _ruta_ficha(nif))
    return 0


def _volcar(ficha, tipo, texto, reg, doc, hoy):
    """Lo que cada tipo de documento aporta a la ficha, con su fuente y su huella. Devuelve True si hay que revisar el documento a mano."""
    comun = dict(fuente=reg["url"], huella=reg["huella"], consultado=hoy)
    if tipo == "cuentas_anuales":
        r = estados.leer(texto)
        anios = r["ejercicios"] or [None, None]
        cierre = ("%s-12-31" % anios[0]) if anios[0] else None
        mapa = {"tesoreria": "tesoreria", "inversiones_inmobiliarias": "valor_razonable_inmuebles", "deuda_entidades_lp": "prestamos_lp", "deuda_entidades_cp": "prestamos_cp",
                "patrimonio_neto": "patrimonio_neto", "activo_total": "activo_total", "ingresos_rentas": "ingresos_rentas", "cifra_negocios": "ingresos",
                "resultado": "resultado", "pagos_dividendos": "dividendos_pagados"}
        for campo, valores in r["partidas"].items():
            if campo not in mapa:
                continue
            for i, v in enumerate(valores[:2]):
                anio = anios[i] if i < len(anios) else None
                if anio is None or v is None:
                    continue
                v = abs(v) if campo == "pagos_dividendos" else v
                modelo.poner(ficha, anio, mapa[campo], modelo.dato(v, fecha="%s-12-31" % anio, donde="rótulo «%s», columna %d" % (campo, i + 1), **comun))
        if r["ltv_declarado"] is not None and anios[0]:
            modelo.poner(ficha, anios[0], "ltv_declarado", modelo.dato(r["ltv_declarado"], fecha=cierre, unidad="%", donde="«LTV» en el informe de gestión", **comun))
        ficha["vencimientos"] = [dict(v, fecha=cierre, **comun) for v in r["vencimientos"]] or ficha.get("vencimientos", [])
        ficha["activos"] = [dict(a, fecha=cierre, **comun) for a in r["activos"]] or ficha.get("activos", [])
        ficha["avisos"].extend("cuentas %s: %s" % (anios[0], a) for a in r["avisos"])
        return not r["estados_reconocidos"]
    elif tipo == "valoracion":
        v = avisos.valoracion(texto)
        if v["total"] and v["fecha"]:
            modelo.poner(ficha, v["fecha"][:4], "gav_valoracion", modelo.dato(v["total"], fecha=v["fecha"], donde="aviso de valoración; valoradores: %s" % ", ".join(v["valoradores"]) or None, **comun))
    elif tipo == "participaciones":
        p = avisos.participaciones(texto)
        if p["accionistas"]:
            ficha["accionistas"] = [dict(a, fecha=p["fecha"], contraste="oficial", **comun) for a in p["accionistas"]]
    elif tipo == "dividendo":
        d = avisos.dividendo(texto)
        anio = d["con_cargo_a"] or (doc.get("fecha") or "")[:4]
        if d["importe_total"] and anio:
            modelo.poner(ficha, anio, "dividendo_acordado", modelo.dato(d["importe_total"], fecha=d["fecha_acuerdo"] or doc.get("fecha"), donde="aviso de dividendo; pago %s" % d["fecha_pago"], **comun))
        if d["importe_por_accion"] and anio:
            modelo.poner(ficha, anio, "dividendo_por_accion", modelo.dato(d["importe_por_accion"], fecha=d["fecha_acuerdo"] or doc.get("fecha"), donde="aviso de dividendo", **comun))


def _fichas(cual):
    if cual and cual != "todas":
        return [(cual.upper(), modelo.cargar(_ruta_ficha(cual.upper())))]
    return [(modelo.clave(f), f) for f in base.fichas_de(FICHAS)]


def orden_puntuar(args):
    hoy = args.fecha or date.today().isoformat()
    c = puntuacion.cargar_criterios()
    resultados = {}
    lineas = ["# SOCIMIs puntuadas · %s\n" % hoy, "| # | Sociedad | Segmento | Puntos | Tramo | Cobertura | LTV | Dividendo | Mayor accionista | Vínculo vasco |", "|---|---|---|---|---|---|---|---|---|---|"]
    filas = []
    for nif, f in _fichas(args.cual):
        ev = puntuacion.evaluar(f, c, hoy)
        resultados[nif] = (hoy, ev)
        anio = modelo.ultimo_ejercicio(f)
        ltv = modelo.valor(f, anio, "ltv_declarado") or modelo.valor(f, anio, "ltv_neto")
        div = modelo.valor(f, anio, "dividendo_acordado") or modelo.valor(f, anio, "dividendos_pagados")
        acc = max((a for a in f.get("accionistas", []) if a.get("pct_total") is not None and a.get("tipo") != "fisica"), key=lambda a: a["pct_total"], default=None)
        vv = (f.get("vinculo_vasco") or {}).get("grado", "—")
        filas.append((ev["puntos"] if ev["puntos"] is not None else -1, f["sociedad"].get("nombre"), f["sociedad"].get("segmento"), ev, ltv, div, acc, vv))
    for i, (pts, nombre, seg, ev, ltv, div, acc, vv) in enumerate(sorted(filas, key=lambda x: -x[0]), 1):
        lineas.append("| %d | %s | %s | %s | %s | %d/%d | %s | %s | %s | %s |" % (i, nombre, seg, ev["puntos"] if ev["puntos"] is not None else "—", ev["tramo"], ev["cobertura"], ev["de"],
                                                                     ("%s %%" % str(ltv).replace(".", ",")) if ltv is not None else "—", puntuacion._fmt_eur(div) if div else "—",
                                                                     ("%s (%s %%)" % (acc["accionista"], str(acc["pct_total"]).replace(".", ","))) if acc else "—", vv))
    lineas.append("")
    for nif, f in _fichas(args.cual):
        lineas.append(puntuacion.texto(resultados[nif][1], f))
        lineas.append("")
    os.makedirs(os.path.join(RAIZ, "base"), exist_ok=True)
    with open(os.path.join(RAIZ, "base", "puntuaciones.json"), "w", encoding="utf-8") as fh:
        json.dump({nif: {"hoy": h, "evaluacion": ev} for nif, (h, ev) in resultados.items()}, fh, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(RAIZ, "base", "informe.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas))
    print("\n".join(lineas[:3 + len(filas)]))
    print("\nInforme: base/informe.md · Puntuaciones: base/puntuaciones.json")
    return 0


def orden_vasco(args):
    for nif, f in _fichas(args.cual):
        f["vinculo_vasco"] = vinculo_vasco.evaluar(f, _textos_de(nif))
        modelo.guardar(f, _ruta_ficha(nif))
        vv = f["vinculo_vasco"]
        print("%s: %s · %d activos vascos (%s %% del valor) · %d préstamos de entidades vascas · %d menciones" % (
            f["sociedad"].get("nombre"), vv["grado"], len(vv["activos"]), vv["pct_valor_en_pais_vasco"] if vv["pct_valor_en_pais_vasco"] is not None else "—", len(vv["financiacion"]), len(vv["menciones"])))
    return 0


def orden_base(args):
    punt = {}
    ruta_p = os.path.join(RAIZ, "base", "puntuaciones.json")
    if os.path.exists(ruta_p):
        with open(ruta_p, encoding="utf-8") as f:
            punt = {nif: (v["hoy"], v["evaluacion"]) for nif, v in json.load(f).items()}
    n = base.construir(FICHAS, os.path.join(RAIZ, "base", "socimis.sqlite"), os.path.join(RAIZ, "base", "csv"), punt)
    print("%d sociedades en base/socimis.sqlite y base/csv/" % n)
    return 0


def orden_ocr(args):
    for nif, f in _fichas("todas"):
        for d in f.get("documentos", []):
            if d.get("escaneado") or d.get("revisar"):
                print("%s · %s · %s · %s · %s" % (nif, "ESCANEADO" if d.get("escaneado") else "REVISAR", d.get("tipo"), d.get("fecha"), d.get("url")))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="socimis", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="orden")
    a = sub.add_parser("cnmv"); a.add_argument("nif"); a.set_defaults(fn=orden_cnmv)
    a = sub.add_parser("bme"); a.add_argument("recolectada"); a.add_argument("--nif"); a.set_defaults(fn=orden_bme)
    a = sub.add_parser("puntuar"); a.add_argument("cual", nargs="?", default="todas"); a.add_argument("--fecha"); a.set_defaults(fn=orden_puntuar)
    a = sub.add_parser("vasco"); a.add_argument("cual", nargs="?", default="todas"); a.set_defaults(fn=orden_vasco)
    a = sub.add_parser("base"); a.set_defaults(fn=orden_base)
    a = sub.add_parser("portfolio"); a.set_defaults(fn=orden_portfolio)
    a = sub.add_parser("euronext"); a.add_argument("listado"); a.set_defaults(fn=orden_euronext)
    a = sub.add_parser("ocr-pendientes"); a.set_defaults(fn=orden_ocr)
    args = p.parse_args(argv)
    if not args.orden:
        p.print_help()
        return 2
    try:
        return args.fn(args)
    except (red.ErrorFuente, cortesia.Rechazada) as e:
        print("Error de fuente: %s" % e, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())

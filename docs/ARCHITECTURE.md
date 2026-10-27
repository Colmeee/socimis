# Arquitectura — cómo conecta socimis

Qué construimos: `PRD.md`. Cómo se ve: `DESIGN_SYSTEM.md`. Cómo se trabaja: `../AGENTS.md`.

## Mapa

```
 BME Growth / Scaleup (bolsasymercados.es, JavaScript)          CNMV (HTML estático, por NIF)
   │ navegador (Playwright, en la nube, 2,5 s entre páginas)       │ urllib por red.py
   ▼                                                               ▼
 descargas/bme/fichas/<ISIN>.json  ──►  python3 -m socimis bme   python3 -m socimis cnmv <NIF>
   (domicilio, NIF, lista de PDF)        │ elige 5 PDF (fuentes/bme.py)   │ IFA: ESEF xhtml + participaciones (fuentes/cnmv.py)
                                         ▼                                ▼
                                   cortesia.Cola.bajar ── robots.py ── red.py (IPv4 primero, tope duro) ── descargas/ (fuera de Git)
                                         │ texto_pdf (pdftotext | pypdf) · ¿escaneado? → cola de OCR del Mac
                                         ▼
                              parsers/estados.py · parsers/avisos.py · parsers/ixbrl.py
                                         │ cada cifra -> modelo.dato(valor, fuente, fecha, huella, contraste, donde)
                                         ▼
                                  base/fichas/<clave>.json  (la verdad; se versiona; clave = NIF, o ISIN si no hay NIF)
                                         ▲
   Portfolio SE (HTML estático) ── python3 -m socimis portfolio ──┤  solo censo (nombre, ISIN, capitalización, precio)
   Euronext Access (listado leído 1 vez con navegador) ── python3 -m socimis euronext <listado.json> ──┘  solo censo
                                         │
                 ┌───────────────────────┼─────────────────────────┐
                 ▼                       ▼                         ▼
     vinculo_vasco.evaluar      puntuacion.evaluar (puro)     base.construir
     (activos, bancos, menciones) (6 dimensiones, porqués)    base/socimis.sqlite + base/csv/*.csv
                                         ▼
                            base/informe.md · base/puntuaciones.json
```

## Stack

Python 3 (compatible 3.9), solo librería estándar: `urllib`, `re`, `json`, `sqlite3`, `csv`, `hashlib`. Lectura de PDF por
`pdftotext -layout` (Poppler) o `pypdf` (opcional). Playwright + Chromium para la recolección de fichas de BME (solo
en la nube, donde ya está instalado). Sin servidor, sin base externa, sin claves.

## Carpetas

```
socimis/                 el paquete
  red.py                 la única puerta a internet (copiado de Cantera): IPv4 primero, tres relojes, candado SOCIMIS_SIN_RED
  robots.py              robots.txt a la RFC 9309 (portado de Doc, MIT)
  cortesia.py            pausa por servidor, robots antes de cada URL, diario jsonl para reanudar
  huella.py              SHA-256
  texto_pdf.py           PDF -> texto con columnas; detecta escaneados
  modelo.py              ficha, dato con origen, campos por ejercicio, derivados con fórmula
  parsers/ixbrl.py       ESEF (CNMV): hechos sin dimensión de 12 conceptos IFRS
  parsers/estados.py     balance, resultados, flujos, LTV, vencimientos, activos (texto de PDF en castellano)
  parsers/avisos.py      participaciones, dividendo, valoración (avisos de BME)
  fuentes/cnmv.py        URLs por NIF y lectura de las tablas de IFA y participaciones
  fuentes/bme.py         qué PDF se baja de cada ficha recolectada; nombre de fichero; provincia por CP o por ciudad
  fuentes/portfolio.py   Portfolio Stock Exchange: emisores de la página pública del mercado (censo; documentos tras login)
  fuentes/euronext.py    Euronext Access París: emisores del listado guardado (censo; fichas sin recorrer por sus condiciones)
  geo.py                 gazetteer nacional: provincia (y comunidad) de la ubicación de un inmueble; reutiliza vasco.json
  vinculo_vasco.py       + vasco.json (lugares y entidades)
  puntuacion.py          + criterios.json (pesos y umbrales con porqué)
  base.py                SQLite + CSV desde las fichas
  __main__.py            la línea de mandos
herramientas/recolectar_bme.js   el navegador que recoge fichas (listado, Datos Empresa, O. I. Relevante, Datos Financieros)
herramientas/censo_vasco.py      docs/CENSO-VINCULO-VASCO.md desde las fichas
herramientas/censo_espana.py     docs/CENSO-ESPANA.md: por mercado, provincia del domicilio y provincia de los inmuebles
herramientas/lista.py            docs/LISTA-SOCIMIS.md: todas las sociedades en una tabla
pruebas/                 unittest + fixtures reales recortados (LEEME.md con huellas) · correr.py
probar.sh                batería sin red + comprobaciones de la casa
base/                    fichas/*.json (verdad), socimis.sqlite, csv/, informe.md, puntuaciones.json  — se versiona
descargas/               PDF, xhtml, textos, diario.jsonl                                              — NO se versiona
exportacion/             ORDEN-AAAA-MM-DD.md (ver abajo)                                                — se versiona
docs/                    PRD, ARCHITECTURE, DESIGN_SYSTEM, veredicto y fuentes de la Fase 1
```

## Flujo de una sociedad de BME

1. `recolectar_bme.js` abre la ficha, lee «Datos Empresa» (domicilio, NIF, auditor, asesor, proveedor de liquidez) y las
   listas de «O. I. Relevante» y «Datos Financieros» (categoría, título, URL de cada PDF). Escribe un JSON. Si ya existe,
   salta (reanudable). Tres fallos seguidos: para.
2. `python3 -m socimis bme <json>`: `fuentes/bme.elegir_documentos` escoge las últimas cuentas anuales (la más pesada
   de la campaña), valoración, participaciones, dividendo y semestral. `cortesia.Cola` comprueba `robots.txt`, espera
   2 s por servidor, baja por `red.pedir_bytes`, apunta URL + huella en `descargas/diario.jsonl`.
3. `texto_pdf` extrae texto; si es un escaneo, el documento se marca `escaneado` y no se lee (cola de OCR del Mac).
4. Los lectores sacan las cifras; `modelo.poner` las guarda con fuente, fecha, huella, contraste y `donde` (rótulo,
   columna, id del hecho). `modelo.completar_derivados` añade deuda financiera, deuda neta y LTV neto con su fórmula.
5. `vasco` y `puntuar` leen la ficha; `base` regenera SQLite y CSV.

## Datos y ficheros

- La ficha JSON es la verdad; SQLite y CSV se regeneran enteros (`base`). Esquema en `base.ESQUEMA`: sociedad, dato,
  accionista, administrador, vencimiento, activo, documento, puntuacion, vinculo_vasco.
- Niveles de contraste: oficial, mercado, empresa, derivado, prensa, no_consta (`modelo.CONTRASTES`).
- Los PDF viven en `descargas/` y se pueden borrar: la base guarda URL y huella para volver a bajarlos.

## Servicios externos

bolsasymercados.es (páginas y PDF en `apiweb.bolsasymercados.es/Market/MTFDocuments/…`), cnmv.es (HTML y
`webservices/verdocumento`), portfolio.exchange (una página pública, censo) y live.euronext.com (un listado, leído una vez
con navegador; sin recorrer fichas: sus condiciones de uso lo prohíben sin permiso, ver PRD decisión 7). Ninguna API con
clave. Condiciones y robots en `fuentes-fase-1.md`.

## Dónde corre qué

- **Nube** (claude.ai/code): recolección con Playwright, descargas, lectura, puntuación, base; `git push`.
- **Mac** (8 GB, una tarea a la vez): `git pull`, OCR de los escaneados con la OCR de Apple (`ocrmac`, pip, sin Homebrew),
  lectura con Obsidian/visor SQLite. La nube no alcanza `bmescaleup.es` (dominio viejo), `opendata.registradores.org` ni
  LibreBORME; sí alcanza BME, CNMV, BOE, Euronext y Portfolio.

## La orden de exportación (solo la ejecuta Juan)

«Exportar» = llevar código y base al Mac (decisión de Juan, 2026-10-26). La orden es un fichero
`exportacion/ORDEN-AAAA-MM-DD.md` que **solo se escribe si pasan las puertas**: `probar.sh` en «0 mal», cifras
contrastadas con su fuente en una muestra, rendimiento medido, `/cancerbero-publicar` sin pendientes críticos, los
cuatro ficheros al día, ningún secreto ni dato personal fuera de lo publicado por las sociedades. Lleva el resultado de
cada puerta, el **hash exacto del commit** y el comando que la ejecuta (`git -C ~/Proyectos/socimis pull --ff-only` y
la comprobación `git rev-parse HEAD` contra el hash). Si el código cambia, la orden deja de valer. La sesión nunca la
ejecuta ni tiene credenciales: el `git pull` lo teclea Juan.

## Escala

98 sociedades en BME (55 Growth + 43 Scaleup) × 5 PDF ≈ 500 descargas, muchas de 5-25 MB: se hace por tandas de 20
(≈ 1 hora por tanda con las pausas) y los PDF se pueden borrar tras extraer el texto. Euronext Access y Portfolio SE
(68) quedan para una fase posterior con sus propias fuentes.

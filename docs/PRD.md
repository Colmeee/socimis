# PRD — socimis

Qué construimos. Cómo conecta: `ARCHITECTURE.md`. Cómo se ve: `DESIGN_SYSTEM.md`. Cómo se trabaja: `../AGENTS.md`.

## Producto

**socimis**: la base de las SOCIMIs cotizadas españolas, con cada dato y su fuente, y el motor que las ordena para
quien capta patrimonio. Objetivo: que Juan pueda abrir una sociedad y ver en un minuto cuánto debe (LTV y
vencimientos), qué reparte, cómo cotiza frente a su valor, quién manda, qué tiene y cuánto lleva en el mercado, con el
enlace de cada cifra, y que la base entera se pueda recargar sola, sin pagar y sin molestar a nadie.

## Problema

Hay 169 SOCIMIs cotizadas (30-6-2026: 3 en el Continuo, 55 en BME Growth, 43 en BME Scaleup, 40 en Euronext Access
París, 28 en Portfolio Stock Exchange). Sus tripas son públicas —cuentas auditadas, semestrales, valoraciones,
dividendos, accionistas significativos— pero están en 169 fichas distintas, en PDF (BME) o en iXBRL (CNMV), y nadie las
ha puesto en una tabla con la fuente al lado. La Fase 1 (`VEREDICTO-FASE-1.md`, 2026-10-26) lo corroboró: viable con
peros.

## Para quién

Juan, en su Mac o desde la nube. **Uso propio**: la información de BME es «para uso interno» y venderla exigiría una
licencia de BME Market Data (decisión futura, no de este PRD).

## Alcance (decisiones de Juan del 2026-10-26)

- **Solo lo cotizado y lo que se puede saber gratis.** Fuera el Registro Mercantil y las SOCIMIs no cotizadas.
- **Piloto: «vínculo vasco»**, no domicilio vasco. Ninguna SOCIMI puede tener domicilio fiscal en Álava, Bizkaia o
  Gipuzkoa (las tres Normas Forales eliminaron el régimen SOCIMI); se buscan las que tienen activos, financiación,
  fundadores o accionistas en el País Vasco, con la evidencia línea a línea.
- **Personas físicas**: los accionistas significativos se guardan tal como la sociedad los publica, sin cruzarlos
  con nada.
- **Descargas en lote educado**: pausa por servidor, robots.txt, IPv4, reanudable, solo los PDF que la web enseña.
- **La nube baja y lee; el Mac hace OCR** de los PDF escaneados (con la OCR de Apple) y guarda la base.
- **Exportar = llevar código y base al Mac**, por `git pull`, con una orden atada al hash del commit (ver
  `ARCHITECTURE.md`, «La orden de exportación»). Gasto: 0 €; cualquier gasto se pide.
- **Resto de España (encargo de Juan, 2026-10-27: «ponte a trabajar en el resto de España»)**: el mismo esquema y el mismo
  motor para todas las cotizadas españolas. Continuo por la CNMV (Merlin, Colonial); Portfolio Stock Exchange y Euronext
  Access París **solo como censo** (nombre, ISIN, precio) hasta que Juan decida sobre sus condiciones (decisión 7).
  Censo nacional por provincia del domicilio y de los inmuebles en `docs/CENSO-ESPANA.md`.

## Funciones de la primera versión

1. **Censo** de BME Growth y BME Scaleup (listado + ficha por sociedad con domicilio, NIF, auditor, asesor registrado,
   proveedor de liquidez, capitalización, cotización) con un navegador, despacio.
2. **Documentos** por sociedad: las últimas cuentas anuales, la última valoración de activos, las últimas participaciones
   significativas, el último dividendo y el último semestral; URL, huella SHA-256 y fecha de consulta en la base, el PDF
   fuera del repo.
3. **Lectura**: iXBRL ESEF (CNMV) y PDF con texto (BME). De las cuentas: tesorería, inversiones inmobiliarias, deudas con
   entidades de crédito LP/CP, patrimonio neto, activo, rentas, resultado, dividendos pagados, LTV declarado, tabla de
   vencimientos, tabla de activos con ubicación. De los avisos: GAV y valoradores, dividendo (total, por acción, fechas),
   accionistas ≥ 5 % con tipo (jurídica/física). Lo escaneado se marca y va a la cola de OCR.
4. **Derivados** con fórmula: deuda financiera, deuda neta, LTV neto.
5. **Motor**: 100 puntos en seis dimensiones (apalancamiento 25, dividendos 20, valor liquidativo 15, concentración 15,
   activos 15, madurez 10), cada parte cumplida / parcial / no cumplida / sin datos, cobertura, tramos ≥ 70 prioritaria,
   50-69 interesante. Pesos y umbrales en `socimis/criterios.json`, cada uno con su porqué.
6. **Vínculo vasco**: activos, financiación y menciones con evidencia; grado fuerte / indicio / ninguno.
7. **Base**: fichas JSON (la verdad), SQLite y CSV regenerados desde ellas, informe Markdown con el ranking y la ficha de
   puntuación de cada sociedad.

## Recorridos clave

- *Cargar una del Continuo*: `python3 -m socimis cnmv <NIF>` → ficha con el ESEF leído y los accionistas de la CNMV.
- *Cargar BME*: `node herramientas/recolectar_bme.js growth --solo-socimi` → `python3 -m socimis bme <ficha.json>` por
  sociedad → `vasco` → `puntuar` → `base`.
- *Leer*: abrir `base/informe.md` (ranking + porqués) o `base/socimis.sqlite` con cualquier visor.
- *OCR en el Mac*: `python3 -m socimis ocr-pendientes` lista los escaneados; se pasan por la OCR de Apple y el texto
  resultante entra como si fuera el extraído.

## Requisitos

- Funcionales: cada cifra con URL, fecha, huella y nivel de contraste; «no consta» como valor; derivados con fórmula;
  determinista (dos ejecuciones iguales dan ficheros iguales); reanudable.
- Uso: una persona, Terminal, Mac de 8 GB (una tarea a la vez) o nube; Python 3.9 sin instalar nada (PDF: `pdftotext` o
  `pypdf`).
- Rendimiento: una sociedad de BME en menos de 2 minutos (5 PDF con pausa de 2 s); el ESEF de Merlin (48 MB) en menos
  de 30 s.
- Plataforma: librería estándar; Playwright solo para la recolección en la nube.

## Métricas de éxito

- Cifras extraídas bien sobre cifras esperadas en la muestra: ≥ 85 % en PDF con texto (Fase 1: 7/7 Merlin, 7/7 All Iron).
- Cero datos sin fuente en la base. Cero PDF versionados. Cero secretos. `probar.sh` en «0 mal».
- Censo del piloto: todas las SOCIMIs de BME Growth y Scaleup con ficha y grado de vínculo vasco.

## Fuera de alcance (todavía)

- Registro Mercantil, no cotizadas, BORME.
- Los **documentos** de Portfolio Stock Exchange (tras login) y de Euronext Access París (condiciones de uso que prohíben
  el acceso automatizado): las sociedades están censadas, sus tripas no. Ver decisión 7 y la pregunta pendiente.
- Administradores (hace falta leer el IAGC o la ficha; no se extraen en esta versión).
- OCR en la nube; venta o publicación de la base; pantalla web; prensa.
- NAV por acción (no está etiquetado en iXBRL ni en un aviso estándar; se lee a mano cuando haga falta).

## Decisiones (con fecha)

1. 2026-10-26 — Historial nuevo, sin nada de Cantera salvo `red.py` copiado (el arreglo del IPv6) y la lógica de
   `robots_check.py` de Doc (MIT).
2. 2026-10-26 — Las seis dimensiones y sus pesos (arriba). Juan puede cambiarlos; es un cambio de PRD.
3. 2026-10-26 — Los documentos que se bajan por sociedad: los cinco de «Funciones, 2». Ni uno más sin decidirlo.
4. 2026-10-26 — No se usa la API interna de BME. Se renderizan las páginas públicas y se bajan los PDF que enseñan.
5. 2026-10-26 — Fixtures: documentos reales recortados a texto, sin nombres de personas; tabla con huellas en
   `pruebas/fixtures/LEEME.md`.
6. 2026-10-26 — **Los PDF de BME se bajan aunque el robots.txt de `apiweb.bolsasymercados.es` diga «Disallow: /»**
   (decisión de Juan por pantalla, con las alternativas delante: web corporativa + a mano, pedir permiso a BME, o solo
   CNMV). Razón: son los enlaces «Ver PDF» que BME enseña a cualquier visitante; se bajan uno a uno, con 2 s de pausa y
   solo los cinco por sociedad. Es la única excepción (`cortesia.EXCEPCIONES_ROBOTS`) y cada descarga la lleva apuntada.
7. 2026-10-27 — **Portfolio Stock Exchange y Euronext Access París entran como censo, sin documentos.** Portfolio: una
   lectura de la página pública del mercado (32 emisores, sin JavaScript), con pausa y diario; los documentos están tras
   login y su aviso legal prohíbe reproducir el contenido, así que solo se guardan nombre, ISIN, capitalización y precio con
   su URL. Euronext: una lectura del listado público con navegador (3.826 valores, 46 españoles en Euronext Access) y una
   sola ficha abierta para saber qué hay; **no se recorren fichas ni se bajan documentos** porque sus condiciones de uso
   prohíben, sin permiso escrito, «spiders, robots, agents, tools» y la «systematic retrieval to create … databases», y la
   información de empresa es de un tercero (Cofisem) que tampoco permite reproducirla. Esto lo decidió la sesión por
   prudencia, no Juan: **pregunta pendiente para él**, con tres salidas: (a) dejarlo así y, si hace falta una sociedad, ir
   a su web corporativa; (b) escribir a Euronext pidiendo permiso; (c) pasar por encima, como con el robots de BME (sería la
   segunda excepción, y esta es de condiciones de uso, no de robots). Mientras, las 46 van con `regimen_socimi` «sin
   confirmar» cuando el nombre recortado no dice SOCIMI.
8. 2026-10-27 — **La clave de una ficha es el NIF y, si la fuente no lo publica (Portfolio, Euronext), el ISIN**
   (`modelo.clave`). La base lleva `clave` como clave primaria en todas las tablas y `nif` como atributo. Lar España, que dejó
   el Continuo en 2025 y cotiza en BME Scaleup, está una sola vez, por su NIF.

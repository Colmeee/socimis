# AGENTS.md — socimis

Cómo se trabaja en este repositorio, para cualquier agente (Claude Code, Codex, Cursor). `CLAUDE.md` apunta aquí.
Qué construimos: `docs/PRD.md`. Cómo conecta: `docs/ARCHITECTURE.md`. Cómo se ve: `docs/DESIGN_SYSTEM.md`.
**Léelos antes de tocar código.** Si se contradicen o falta una decisión, para y pregunta a Juan (por pantalla, con
alternativas y lo que implica cada una).

## Qué es

La base de las **SOCIMIs cotizadas** españolas con cada dato y su fuente, y el motor que las puntúa. Hijo de Cantera
(el motor de leads de Juan Colmenarejo) con **historial nuevo**: aquí solo hay código, fixtures recortados y la base
estructurada. Python 3, **solo librería estándar** (lectura de PDF: `pdftotext` de Poppler si está, o `pypdf` opcional,
importado dentro de la función). **Sintaxis compatible con Python 3.9** (el del Mac): nada de `match`, nada de `X | Y`.
La recolección de fichas de BME usa Playwright (`herramientas/recolectar_bme.js`) y corre en la nube.

## Comandos

```
bash probar.sh                                   # TODA la batería sin red + comprobaciones de la casa. «N bien, 0 mal»
SOCIMIS_SIN_RED=1 python3 pruebas/correr.py      # solo las pruebas unitarias
python3 -m socimis cnmv A86977790                # una SOCIMI del Continuo: IFA (ESEF) + participaciones -> base/fichas/<NIF>.json
node herramientas/recolectar_bme.js growth --solo-socimi --max 5     # fichas de BME Growth con navegador -> descargas/bme/fichas/*.json
python3 -m socimis bme descargas/bme/fichas/ES0105495008.json         # baja los PDF elegidos, los lee -> base/fichas/<NIF>.json
python3 -m socimis vasco [NIF|todas]             # vínculo vasco de cada ficha con los textos bajados
python3 -m socimis puntuar [NIF|todas] [--fecha AAAA-MM-DD]   # puntúa -> base/puntuaciones.json, base/informe.md
python3 -m socimis base                          # regenera base/socimis.sqlite y base/csv/ desde las fichas
python3 -m socimis ocr-pendientes                # los PDF escaneados que esperan OCR en el Mac
python3 -m socimis portfolio                     # censo de Portfolio Stock Exchange (página pública; sin documentos)
python3 -m socimis euronext descargas/euronext/listado-AAAA-MM-DD.json   # censo de Euronext Access desde el listado leído
python3 herramientas/censo_vasco.py · herramientas/censo_espana.py · herramientas/lista.py   # los tres documentos de docs/
```

## Reglas que no se negocian

- **Solo fuentes públicas y gratuitas, lo cotizado.** BME Growth/Scaleup (bolsasymercados.es), CNMV, webs de las
  sociedades. **Nada del Registro Mercantil ni de no cotizadas** (Juan, 2026-10-26: «céntrate en lo cotizado»). Nada de
  pago; gasto por defecto 0 €: cualquier gasto se pide.
- **Descargas educadas** («lote educado», Juan 2026-10-26): toda petición pasa por `socimis/red.py` (IPv4 primero, tope
  duro por intento) y por `socimis/cortesia.py` (pausa por servidor, `robots.txt` antes de cada URL, diario para
  reanudar). Solo se bajan los PDF que la web enseña a cualquier visitante. **No se llama a la API interna de BME**
  (`apiweb.bolsasymercados.es/Market/v1/…`): no está documentada y las condiciones de BME hablan de uso interno.
  **Única excepción al robots.txt, decidida por Juan por pantalla el 2026-10-26**: `apiweb.bolsasymercados.es` (que sirve
  los PDF de BME con «Disallow: /») se baja igual, uno a uno, con pausa y solo los cinco documentos por sociedad; está en
  `cortesia.EXCEPCIONES_ROBOTS` con su porqué y se apunta en cada línea del diario. Ninguna otra excepción sin que él lo decida.
  Nunca `urllib.request.urlopen` suelto: una llamada nueva a la red va por `red.pedir_bytes` con su `limite`. Solo se baja
  de los servidores de `cortesia.SERVIDORES` (lista blanca, https) y a rutas dentro de `descargas/`; el NIF se valida
  (`fuentes.bme.nif_valido`) antes de nombrar un fichero (auditoría de Cancerbero del 2026-10-26); desde el 2026-10-27 la clave
  de una ficha puede ser el ISIN cuando la fuente no publica el NIF (`modelo.clave_valida`).
  **Euronext (live.euronext.com) no se recorre con herramientas**: sus condiciones de uso lo prohíben sin permiso escrito.
  Solo está el listado leído una vez (PRD, decisión 7). Si Juan decide otra cosa, se escribe ahí primero.
- **Nada de red en las pruebas.** `SOCIMIS_SIN_RED=1` cierra `red.py`; `probar.sh` lo comprueba.
- **Los PDF no suben al repositorio.** Ni los xhtml ESEF ni los textos extraídos: `descargas/` está en `.gitignore`. En la
  base solo va la URL, la huella SHA-256 y la fecha de consulta de cada documento. El único xhtml versionado es el
  extracto recortado de `pruebas/fixtures/`.
- **Cada dato con su origen.** Un dato es `modelo.dato(valor, fuente, fecha, huella, contraste, consultado, nota, donde)`;
  «no consta» es un valor (`modelo.no_consta`). Lo derivado (deuda financiera, LTV neto) lleva su fórmula en `nota` y
  `contraste="derivado"`. **Lo numérico que no viene es `None`, nunca 0.**
- **Personas físicas** (decisión de Juan, 2026-10-26): los accionistas significativos se guardan **tal como la sociedad
  los publica** en BME o la CNMV (nombre y %), marcados `tipo: "fisica"`. **No se cruzan con ninguna otra fuente**, no se
  buscan teléfonos, correos, domicilios ni perfiles, no se entra en LinkedIn. Los administradores solo si una fuente
  oficial los da con fecha. Los **fixtures** no llevan nombres de personas reales (`pruebas/fixtures/LEEME.md`).
- **Condiciones de BME**: la información es «para uso interno»; esta base es de uso propio de Juan. Si algún día se
  vende o se redistribuye, hace falta la autorización de BME Market Data y una decisión expresa de Juan. CNMV: uso privado
  libre y reproducción fiel. BOE: reutilización con atribución.
- **El motor es puro**: `puntuacion.py` no toca ficheros, ni red, ni la fecha de hoy (entra por parámetro). Pesos y
  umbrales en `socimis/criterios.json`, cada uno con su `_por_que`; `validar()` exige que sumen 100. Un cambio de
  criterio: edita el JSON, pasa `probar.sh`, **actualiza `docs/PRD.md` el mismo día**.
- **Ningún nombre del banco donde Juan hace prácticas, ningún cliente, ninguna cifra cotejada allí** entra aquí, ni como
  ejemplo. Nada del Cerebro privado de Juan.
- **Ninguna clave en el repositorio.** No hay claves que guardar (todo es público); si alguna vez hiciera falta, vive
  fuera del repo y aquí se escribe la referencia.

## Estilo

- Español en textos, comentarios y nombres. Frases cortas. Cada módulo empieza con **por qué** existe.
- Un lector nuevo: `socimis/parsers/<nombre>.py` + fixture recortado real + caso en `pruebas/test_parsers.py`.
  Una fuente nueva: `socimis/fuentes/<nombre>.py` + página guardada + caso en `pruebas/test_fuentes.py`.
- Un campo nuevo de la ficha: `modelo.CAMPOS_EJERCICIO` (con unidad), `base.ESQUEMA` si es tabla nueva, y su prueba.

## Antes de dar algo por hecho

`bash probar.sh` tiene que acabar en **«N bien, 0 mal»**. Si cambias algo que la batería no cubre, añade antes el caso.

## No se toca sin permiso de Juan

Los pesos de `criterios.json`; la política de personas físicas; el alcance (cotizadas, sin Registro); las fuentes;
cualquier cosa que haga una petición nueva a un servidor; la carpeta `exportacion/` (ver `docs/ARCHITECTURE.md`).

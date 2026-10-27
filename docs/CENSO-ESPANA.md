# Censo nacional: SOCIMIs cotizadas en la base

Generado el 2026-10-27 por `herramientas/censo_espana.py` desde `base/fichas/` (178 sociedades). Cada dato tiene su fuente en la ficha JSON y en `base/socimis.sqlite`. Es la ampliación del piloto vasco (`CENSO-VINCULO-VASCO.md`) al resto de España: mismo motor, mismo esquema, más mercados.

## En una frase

**178 sociedades censadas** en cinco mercados; **95 con documentos bajados** (BME Growth, BME Scaleup y Continuo), de las que **26 tienen el balance leído** y **57 publican las cuentas escaneadas** (sin OCR no se leen); **83 son solo censo** (Portfolio Stock Exchange y Euronext Access París: nombre, ISIN, precio; documentos sin leer, ver abajo).

## Por mercado

| Mercado / segmento | Sociedades | Qué hay de cada una |
|---|---|---|
| BME Growth | 54 | ficha completa: 5 documentos, cuentas leídas si tienen texto |
| Euronext Access | 46 | solo censo: nombre recortado, ISIN, símbolo, último precio (fichas sin recorrer: condiciones de uso) |
| BME Scaleup | 45 | ficha completa: 5 documentos, cuentas leídas si tienen texto |
| Portfolio SE | 31 | solo censo: nombre, ISIN, capitalización, precio (documentos tras login) |
| Continuo | 2 | ESEF de la CNMV (iXBRL) y accionistas ≥ 3 % |

## Dónde están domiciliadas

Provincia del domicilio social (código postal o ciudad del domicilio que publica el mercado; Portfolio y Euronext no lo publican en el listado).

| Provincia | Sociedades |
|---|---|
| Madrid | 82 |
| sin domicilio publicado | 77 |
| Barcelona | 11 |
| Málaga | 5 |
| Valencia | 1 |
| Alicante | 1 |
| Granada | 1 |

| Comunidad autónoma | Sociedades |
|---|---|
| Madrid | 82 |
| sin domicilio publicado | 77 |
| Cataluña | 11 |
| Andalucía | 6 |
| Comunidad Valenciana | 2 |

## Dónde están los inmuebles

Solo cuentan los inmuebles de la tabla de inversiones inmobiliarias de la memoria con ubicación publicada: **19 inmuebles leídos, 19 con provincia reconocida** por `socimis/geo.py` (gazetteer de provincias, capitales y municipios grandes; lo que falte no se detecta: se amplía el diccionario). El valor es el que publica la sociedad (valor razonable o coste, según su tabla), y solo de las 26 sociedades con balance leído: **no es el mapa del sector, es el mapa de lo leído**.

| Provincia | Inmuebles | Valor publicado | Sociedades |
|---|---|---|---|
| Madrid | 3 | 83,8 M€ | ALL IRON RE I SOCIMI, S.A |
| Barcelona | 2 | 72,5 M€ | ALL IRON RE I SOCIMI, S.A |
| Valencia | 1 | 60,7 M€ | ALL IRON RE I SOCIMI, S.A |
| Álava | 1 | 34,8 M€ | ALL IRON RE I SOCIMI, S.A |
| Sevilla | 2 | 32,2 M€ | ALL IRON RE I SOCIMI, S.A |
| Málaga | 3 | 29,7 M€ | ALL IRON RE I SOCIMI, S.A |
| Bizkaia | 3 | 21,1 M€ | ALL IRON RE I SOCIMI, S.A |
| Alicante | 1 | 18,6 M€ | ALL IRON RE I SOCIMI, S.A |
| Navarra | 1 | 10,0 M€ | ALL IRON RE I SOCIMI, S.A |
| Gipuzkoa | 1 | 0,0 M€ | ALL IRON RE I SOCIMI, S.A |
| Córdoba | 1 | 0,0 M€ | ALL IRON RE I SOCIMI, S.A |

## Las mejor puntuadas (todo el país)

| Sociedad | Segmento | Provincia | Puntos | Tramo | Cobertura |
|---|---|---|---|---|---|
| ALL IRON RE I SOCIMI, S.A | BME Growth | Madrid | 71.2 | prioritaria | 6/6 |
| GESRENTA BCN SOCIMI, S.A. | BME Scaleup | Barcelona | 58.2 | interesante | 6/6 |
| AP67 SOCIMI, S.A. | BME Scaleup | Madrid | 53.3 | interesante | 6/6 |
| ADVERO PROPERTIES SOCIMI, S.A | BME Growth | Barcelona | 52.9 | interesante | 5/6 |
| MERLIN PROPERTIES, SOCIMI, S.A. | Continuo | Madrid | 51.5 | interesante | 6/6 |
| SAINT CROIX HOLDING IMMOBILIER, SOCIMI, S.A | BME Scaleup | Madrid | 50.3 | interesante | 6/6 |
| VERACRUZ PROPERTIES SOCIMI, S.A. | BME Growth | Valencia | 50.2 | interesante | 5/6 |
| TARJAR XAIRO SOCIMI, S.A. | BME Scaleup | Madrid | 49.4 | de momento no | 5/6 |
| COLONIAL SFL, SOCIMI, S.A. | Continuo | Madrid | 45.1 | de momento no | 6/6 |
| HELIOS RE SOCIMI, S.A. | BME Scaleup | Madrid | 44.3 | de momento no | 6/6 |
| LAFINCA GLOBAL ASSETS SOCIMI, S.A. | BME Growth | Madrid | 40.5 | de momento no | 6/6 |
| INMUEBLES EN ALQUILER RESYDENZA SOCIMI, S.A.U. | BME Scaleup | Madrid | 32.5 | de momento no | 4/6 |
| CASTELLANA PROPERTIES SOCIMI, S.A. | BME Growth | Madrid | 32.2 | de momento no | 5/6 |
| CUPULAS PROPERTIES SOCIMI, S.A.U. | BME Scaleup | Alicante | 32.0 | de momento no | 5/6 |
| LAR RETAIL | BME Scaleup | Madrid | 31.2 | de momento no | 4/6 |

## Lo que no se ha mirado, y por qué

- **Portfolio Stock Exchange (31)**: la página pública del mercado da nombre, ISIN, capitalización y precio; los documentos (cuentas, valoraciones, hechos relevantes) están tras el login de la plataforma. Su aviso legal prohíbe la reproducción del contenido; aquí solo se guardan esos cuatro datos con su URL.
- **Euronext Access París (46)**: el listado público se leyó una vez con navegador; la ficha de cada valor tiene cuentas auditadas y dividendos en PDF y una pestaña de información de empresa (perfil, cifras, accionistas, domicilio, de Cofisem). **No se recorren**: las condiciones de uso de Euronext prohíben, sin permiso escrito, el acceso con herramientas automáticas y la recopilación sistemática en bases de datos; la información de Cofisem además no puede reproducirse sin su consentimiento. La vía limpia son las webs de las propias sociedades. Decisión pendiente de Juan (PRD). Además el listado recorta los nombres y mezcla SOCIMIs con otras sociedades (biotecnológicas, gimnasios, colegios): `regimen_socimi` dice «sin confirmar» cuando la palabra no aparece.
- **Las 57 escaneadas** de BME: hasta el OCR del Mac, solo se ve lo de los avisos cortos.
- **Lar España** (antes Continuo) está como BME Scaleup: Helios la excluyó de bolsa en 2025 y la llevó a ese segmento (ficha por su NIF).
- Registro Mercantil, no cotizadas y BORME: fuera por decisión de Juan («céntrate en lo cotizado»).


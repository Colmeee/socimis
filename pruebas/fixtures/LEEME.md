# Fixtures: documentos reales, recortados, sin datos personales

Los lectores se prueban contra documentos **reales** de SOCIMIs cotizadas, bajados el **2026-10-26** de fuentes
públicas, y guardados aquí como **texto** (no como PDF: tamaño y derechos). Donde el original llevaba el nombre de una
persona (firmantes, accionistas personas físicas) se ha quitado o sustituido por uno inventado; lo demás es literal.

| Fichero | Origen | Huella SHA-256 del original | Qué se quitó |
|---|---|---|---|
| `ixbrl-merlin-2025-extracto.xhtml` | IFA 2025 consolidado de Merlin Properties, SOCIMI, S.A. (CNMV, registro 20913), `https://www.cnmv.es/webservices/verdocumento/ver?e=BkIsWwMBv1yEfg2Yc2JvuUvGON43wHHcXbrRTjRnO%2bCze5HLI2BThe6mgBjw3Gx%2f` | `22132dafe57d679c9c291ee2c93b8ddb159d8772ceb028ee7dc571505fc18f57` | Todo salvo los contextos, las unidades y los 80 hechos sin dimensión de los conceptos que lee `ixbrl.py` |
| `estados-alliron-2025.txt` | Cuentas anuales consolidadas 2025 de All Iron RE I SOCIMI, S.A. (BME Growth, OIR 21-5-2026), `https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf`, texto por `pdftotext -layout` | `19ea634a81dad934d7908655fe2b508a446cec27bbef78a0e53ad859e862815b` | Solo el balance, la cuenta de resultados y el estado de flujos (líneas 79-250 del texto) |
| `estados-advero-2025-miles-y-euros.txt` | Resultados auditados 2025 de Advero Properties SOCIMI, S.A. (BME Growth, OIR 29-4-2026), `https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/04/05448_OtraInfRelev_20260429.pdf`: el balance resumido «en miles de euros» y, tras un salto de página, el balance completo en euros | (ver `descargas/diario.jsonl` al bajarlo) | Solo esos dos bloques |
| `deuda-alliron-2025.txt` | Ídem, nota 9.1 (tabla de préstamos con vencimiento) | ídem | Nada (solo entidades) |
| `activos-alliron-2025.txt` | Ídem, nota 5 (tabla de inversiones inmobiliarias con ubicación) | ídem | Nada (direcciones de edificios, no de personas) |
| `aviso-valoracion-alliron-2025.txt` | Aviso «Valoración de activos a 31-12-2025», `…/2026/04/05495_OtraInfRelev_20260430.pdf` | `1e7732ca3a4ce23f6aecb8aaec350089387f63fbc12ea4155f356cb2bd506860` | Las líneas de la firma (nombre del secretario) |
| `aviso-dividendo-alliron-2026.txt` | Aviso «Distribución y pago de dividendos 2026», `…/2026/06/05495_OtraInfRelev_20260624.pdf` | `282adfe29a94b103d78dde19a946c7ed87ebd166d11212b52e085a1754043954` | Las líneas de la firma |
| `aviso-participaciones-ficticio.txt` | Formato literal de un aviso de participaciones significativas de BME Growth | — | Nombres y cifras **inventados** (el original lleva personas físicas) |
| `cnmv-ifa-merlin.html` | Tabla de «Informes financieros anuales» de la CNMV para el NIF A86977790 | — | Nada (auditores son sociedades) |
| `cnmv-participaciones-merlin.html` | Cabecera y tabla de «Notificaciones de derechos de voto» de la CNMV para A86977790 | — | La fila de la persona física, sustituida por «PERSONA FISICA FICTICIA, EJEMPLO» |

Regla: aquí **no entra ningún nombre de persona real**, ninguna cifra inventada que pase por real, ningún PDF.
Si un lector nuevo necesita otro documento, se recorta igual y se apunta en esta tabla con su huella.
| `portfolio-mercado-recortado.html` | Recorte de la página pública del mercado de Portfolio Stock Exchange (cabecera y tres filas: AC Residencial SOCIMI, La Verdosa Private Equity SCR, Libeen Properties), leída el 2026-10-27 | https://www.portfolio.exchange/portfolio-market | 3ba65adad5fa58fa55314ac3a2a14a708dfe73cc08a268d05fb9e539ae21a74e |

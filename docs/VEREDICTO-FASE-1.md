# Veredicto de la Fase 1 — ¿son públicas las tripas de las SOCIMIs?

Fecha de consulta de todo lo que sigue: **2026-10-26**, desde la sesión de nube (claude.ai/code). Gasto: **0 €**.

## Veredicto: **viable, con peros**

**Lo que se corrobora.** Para una SOCIMI **cotizada** las tripas sí son públicas y gratuitas: cuentas anuales
auditadas, semestrales, valoración de activos, dividendos y accionistas ≥ 5 % (BME Growth/Scaleup, Circular 3/2020)
o ≥ 3 % (mercado principal, CNMV). En la prueba con tres sociedades reales se extrajeron **15 de 21 cifras (71 %)**:
7/7 en Merlin, 7/7 en All Iron, **1/7 en Miciso** porque su semestral son 39 páginas escaneadas sin capa de texto.

**Los peros, por orden de peso:**

1. **El País Vasco no tiene SOCIMIs propias, por ley foral.** Las tres Normas Forales del Impuesto sobre Sociedades
   **eliminaron el régimen SOCIMI** (Bizkaia NF 11/2013, Álava NF 37/2013, Gipuzkoa NF 2/2014: «han sido eliminados
   los regímenes especiales … de las Sociedades Anónimas Cotizadas de Inversión en el Mercado Inmobiliario»); solo
   conservan una disposición adicional para **los socios vascos de SOCIMIs «sometidas a la normativa de territorio
   común»**. Una sociedad con domicilio fiscal en Álava, Bizkaia o Gipuzkoa tributa por norma foral salvo que facture
   más de 12 M€ y haga ≥ 75 % de sus operaciones en territorio común (Concierto Económico, art. 14, umbral de la Ley
   3/2025). Resultado esperado del censo vasco: **cero o casi cero**. Las dos SOCIMIs «vascas» que da la prensa
   (All Iron, fundada en Bilbao con activos en Bilbao, Vitoria y Donostia; Aofi Sheni, dueña de la sede de BBVA en
   Bilbao) tienen domicilio en Madrid o no publican el domicilio. **La prueba piloto hay que redefinirla** (pregunta 0).
2. **Las condiciones de BME.** Cada página dice: *«La información facilitada … está destinada, exclusivamente, al uso
   interno de la misma. Para cualquier otro uso con fines comerciales y/o que implique la redifusión a terceros de
   dicha información de forma no gratuita es necesario contar con la autorización expresa previa de BME Market Data»*.
   Para una base de uso propio de Juan, sin problema; para venderla como producto, hace falta esa autorización.
   El sitio se alimenta de una API JSON (`apiweb.bolsasymercados.es/Market/v1/…`) **no documentada**: no la he usado
   desde código (el clasificador de permisos lo frenó y es lo prudente); se leen las páginas y los PDF que la web enseña.
3. **Las pequeñas suben escaneos.** Miciso (BME Growth, 19 M€ de capitalización): 0 cifras extraíbles sin OCR. En la
   nube no hay `tesseract`; en el Mac se puede con la OCR de Apple (`ocrmac`, sin Homebrew). Cuenta con que una parte
   de las 98 de BME Growth/Scaleup exija OCR y revisión a mano.
4. **Los otros tres mercados pesan más que BME Growth y están peor servidos.** A 30-6-2026 (ArmanexT vía Brainsre):
   3 en el Continuo, 55 en BME Growth, **43 en BME Scaleup, 40 en Euronext Access París, 28 en Portfolio Stock
   Exchange** = 169 cotizadas. Portfolio SE enseña precio y NAV por emisor, pero ningún documento sin registro; en
   Euronext Access las cuentas salen como notas de prensa en live.euronext.com. No los he destripado.
5. **Las no cotizadas no tienen censo público.** La DT 1ª de la Ley 11/2009 da dos años para cotizar desde la opción
   por el régimen; la denominación debe llevar «SOCIMI, S.A.» (art. 5.4). Para encontrarlas hay que leer el BORME
   (nombre con «SOCIMI»): el BOE da la API de sumarios diarios con licencia de reutilización (atribución al BOE), pero el
   buscador por denominación del BOE ya no existe, OpenMercantil devuelve 0 para «SOCIMI» y LibreBORME bloquea la nube
   (Cloudflare 403). Es un barrido largo: trabajo de Mac, no de nube. Sus cuentas sí están en el Registro Mercantil (de
   pago; precio oficial **sin confirmar**: la sede es una aplicación JavaScript que no enseña tarifas sin iniciar el
   flujo; fuentes secundarias dicen 8,99-20 € por depósito, en ZIP con PDF + XBRL. Para las cotizadas no hace falta).
6. **Lo que la nube no alcanza:** `bmescaleup.es` (dominio viejo, el proxy lo rechaza), `opendata.registradores.org`
   (WAF), LibreBORME. Sí alcanza BME (`bolsasymercados.es`), CNMV, BOE, `sede.registradores.org`, Euronext y Portfolio.

## La prueba, cifra a cifra

| Cifra | Merlin Properties (Continuo) | All Iron RE I (BME Growth) | Miciso Real Estate (BME Growth) |
|---|---|---|---|
| Tesorería | 1.214.945 k€ ✅ iXBRL `CashAndCashEquivalents` | 13.217.301 € ✅ p. balance | ❌ escaneado |
| Deuda financiera bruta | 4.972.361 k€ ✅ (bonos 2.532.309 + 820.658; préstamos 1.573.449 + 45.945; el informe de resultados dice 4.968 M€) | 123.869.416 € ✅ (117.385.551 LP + 6.483.865 CP, entidades de crédito) | ❌ |
| Valor razonable inmuebles | 11.983.699 k€ ✅ `InvestmentProperty` | 363.437.000 € ✅ (balance y aviso de valoración Savills/Gloval) | ❌ |
| LTV | 28,9 % ✅ (informe FY25, deuda neta 3.742.566 k€; no está etiquetado en iXBRL) | 31,8 % EPRA ✅ (informe de gestión); calculado neto 30,4 % | ❌ |
| Ingresos por rentas | 538.963 k€ `Revenue` ✅; rentas brutas 541.856 k€ (informe) | 9.832.863 € ✅ | ❌ |
| Dividendos | 236.381 k€ pagados en 2025 ✅ `DividendsPaid` | 3.226.792,91 € con cargo a 2025 (0,2075 €/acc.) ✅ | ❌ |
| Accionistas significativos | Santander 22,268 %, Lao Hernández 6,271 %, BlackRock 4,632 % ✅ (CNMV, derechos de voto) | 5 sociedades ≥ 5 % (Ion Ion 5,73 %…), cada una con la persona física detrás ✅ | ✅ 5 sociedades y 5 personas físicas (familia) |
| **Extraídas** | **7/7** (5 por XBRL, 1 web, 1 PDF) | **7/7** (PDF con texto; tablas por regex) | **1/7** |

Los enlaces y la huella SHA-256 de cada documento están en `docs/fuentes-fase-1.md`.

## Fuentes, en una línea cada una (detalle y robots en `docs/fuentes-fase-1.md`)

- **BME Growth y BME Scaleup**: dos segmentos de BME MTF Equity (no se ha renombrado; Scaleup existe desde 2023 y
  tiene 52 cotizadas, 43 SOCIMIs). Ficha por sociedad con domicilio, NIF, auditor, asesor; pestañas de información
  privilegiada / otra información relevante / datos financieros, cada documento un **PDF** con URL estable. Páginas
  renderizadas por JavaScript (hace falta navegador). `robots.txt` permite; condiciones: uso interno (pero 2).
- **CNMV** (las 3 del Continuo): registros oficiales por NIF; informes anuales en **ESEF/iXBRL** (xhtml de 48 MB + zip)
  descargables sin clave; semestrales IPP en XBRL propio; participaciones significativas en HTML. Nota legal: uso libre
  privado, reproducción fiel, si se revende hay que decir que es gratis en la CNMV. `robots.txt` permite.
- **BOE/BORME**: API de datos abiertos (sumario diario → PDF por provincia), reutilización comercial permitida con
  atribución y RGPD. Sin búsqueda por nombre.
- **Registro Mercantil**: cuentas depositadas de pago (precio oficial sin confirmar), ZIP con XBRL; necesario solo para no
  cotizadas. Sin `robots.txt`.
- **Ley 11/2009** (texto consolidado BOE, actualizado 7-10-2026): art. 4 cotización en mercado regulado o SMN; art. 5.4
  denominación; art. 6 reparto 100 % / 50 % / 80 %; art. 11 memoria con apartado SOCIMI; DT 1ª dos años.
- **Webs corporativas**: Merlin publica el ESEF y los PDF en su web de inversores; las pequeñas remiten a BME.

## Esfuerzo y coste estimados

- Motor + parsers (PDF con texto, iXBRL, páginas de BME y CNMV): 2-3 sesiones de nube. Coste 0 €.
- Base de las 98 de BME Growth/Scaleup: ~1 hora de navegador por tanda de 20 (una ficha, 3-6 PDF por sociedad), con
  OCR en el Mac para las escaneadas. 0 €.
- Euronext Access + Portfolio SE (68): a estudiar; posible registro gratuito en Portfolio.
- No cotizadas: barrido del BORME en el Mac (horas de proceso) + Registro Mercantil a ~10-20 € por sociedad y ejercicio
  (solo si Juan lo autoriza).

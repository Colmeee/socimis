# Censo del piloto: SOCIMIs cotizadas con vínculo vasco

Generado el 2026-10-27 por `herramientas/censo_vasco.py` desde `base/fichas/` (178 sociedades). Las fuentes de cada dato están en las fichas y en `base/socimis.sqlite`.

## Lo primero: por domicilio no hay ninguna

Sociedades con domicilio social en Álava, Bizkaia o Gipuzkoa: **0 de 178**. Es lo esperado: las tres Normas Forales del Impuesto sobre Sociedades eliminaron el régimen SOCIMI (ver `VEREDICTO-FASE-1.md`, pero 1). Por eso el piloto mide el **vínculo**: activos, financiación y menciones en los documentos que la propia sociedad publica.

## Estado de la base

| Segmento | Sociedades |
|---|---|
| BME Growth | 54 |
| BME Scaleup | 45 |
| Continuo | 2 |
| Euronext Access | 46 |
| Portfolio SE | 31 |

- Con cuentas anuales leídas (tesorería en la base): **26**.
- Con las cuentas anuales **escaneadas** (sin capa de texto; a la cola de OCR del Mac, `python3 -m socimis ocr-pendientes`): **57**. En estas el vínculo solo puede verse en los avisos cortos (participaciones, dividendos, valoración), no en la memoria.
- Vínculo vasco **fuerte** (activos o financiación): **1**. **Indicio** (solo menciones): **15**. **Ninguno**: **162**.

## Vínculo fuerte

### ALL IRON RE I SOCIMI, S.A · BME Growth · 71.2 puntos (prioritaria)
Domicilio: C/ MONTESQUINZA 28, 28010 MADRID. NIF A87934741. Web: http://www.allironresocimi.es.
Valor en el País Vasco: **15.4 % del valor de los inmuebles con ubicación publicada**.

| Activo | Ubicación | Provincia | Valor | Fuente |
|---|---|---|---|---|
| Aparthotel Gasteiz | Avenida de Gasteiz 45, Vitoria | Álava | 34,8 M€ | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf |
| Koisi Hostel | Paseo Heriz 38, San Sebastián | Gipuzkoa | — | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf |
| Apartamentos Alameda de Recalde | Alameda de Recalde 1, Bilbao | Bizkaia | 3,8 M€ | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf |
| Apartamentos Bilbao la Vieja | Calle Vitoria Gasteiz 6. Bilbao | Bizkaia | 2,3 M€ | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf |
| Edificio Bilbao Ledesma | Calle Ledesma 5, Bilbao | Bizkaia | 15,0 M€ | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf |

Préstamos de entidades vascas (tabla de vencimientos de la memoria):

- Caja Laboral: 0,7 M€, vence 2035-12-24
- Caja Laboral: 1,0 M€, vence 2035-12-24
- Caja Laboral: 0 €, vence 2035-10-26
- Caja Laboral: 2,0 M€, vence 2036-04-21
- Kutxabank: 2,0 M€, vence 2036-04-21
- Abanca-Bankoa: 0 €, vence 2036-09-30
- Caja Laboral: 4,8 M€, vence 2037-02-04
- Kutxabank: 4,8 M€, vence 2037-02-04
- Kutxabank: 3,2 M€, vence 2037-02-11
- Abanca-Bankoa: 2,6 M€, vence 2037-09-01
- Caja Laboral: 8,2 M€, vence 2038-01-30
- Kutxabank: 8,2 M€, vence 2038-01-30
- … y 3 más

Menciones (41; las primeras):

- *Gasteiz* — «Aparthotel Gasteiz Avenida de Gasteiz 45, Vitoria 34.800.000 28.900.000»
- *San Sebastián* — «Koisi Hostel Paseo Heriz 38, San Sebastián - 6.100.000»
- *Bilbao* — «Apartamentos Alameda de Recalde Alameda de Recalde 1, Bilbao 3.800.000 3.669.769»
- *Bilbao* — «Apartamentos Bilbao la Vieja Calle Vitoria Gasteiz 6. Bilbao 2.300.000 2.277.883»
- *Bilbao* — «Edificio Bilbao Ledesma Calle Ledesma 5, Bilbao 15.000.000 14.590.000»

## Indicio (solo menciones en los textos)

- **MISTRAL IBERIA REAL ESTATE SOCIMI II, S.A.** (BME Scaleup): 3 menciones; p. ej. *Vizcaya* — «Viviendas de Vizcaya, S.A. 14,29%»
- **CUPULAS PROPERTIES SOCIMI, S.A.U.** (BME Scaleup): 1 menciones; p. ej. *Bilbao* — «PKF ATTEST SERVICIOS EMPRESARIALES, S.L. – Alameda de Recalde, 36 8º 48009 Bilbao - Reg. Merc. Biz., Tomo 4205, Sec 8, H»
- **INMOBILIARIA PARK ROSE IBEROAMERICANA SOCIMI, S.A** (BME Scaleup): 12 menciones; p. ej. *Eibar* — «Otaola Hiribidea 2 Eibar 6.228.332,31 6.228.332,31»
- **WELLDER SENIOR ASSETS SOCIMI, S.A.** (BME Scaleup): 6 menciones; p. ej. *Bilbao* — «Zamora, A Coruña, Pontevedra, León, Pamplona, Badalona, Alicante, Albacete y Bilbao. Con fecha 16 de»
- **SOLVENTO GROUP 2022 SOCIMI S.A.** (BME Scaleup): 1 menciones; p. ej. *Oñate* — «Local comercial en Oñate (Guipúzcoa) 01/12/2023»
- **FIDERE PATRIMONIO SOCIMI, S.A.** (BME Growth): 1 menciones; p. ej. *Oñate* — «Oñate Rino y Dña. Elena Piaia»
- **TANDER INVERSIONES, SOCIMI, S.A** (BME Growth): 12 menciones; p. ej. *San Sebastián* — «de Gracia 15, Paseo de Gracia 27) y en San Sebastián, Bilbao, Santander, Palma de 2%»
- **HELIOS RE SOCIMI, S.A.** (BME Scaleup): 28 menciones; p. ej. *Irún* — «• Locales comerciales situados en Parque Comercial de Txingudi, situados en Irún, aportados a»
- **VITRUVIO REAL ESTATE SOCIMI S.A** (BME Growth): 20 menciones; p. ej. *Bilbao* — «Oficinas en: Alicante, Barcelona, Bilbao, Madrid, Málaga, Valencia, Vigo»
- **GALIL CAPITAL RE SPAIN SOCIMI, S.A.** (BME Scaleup): 11 menciones; p. ej. *Hondarribia* — «Casco Histórico, Hondarribia 58,00 240.000,00 4.137,93 3.724,14»
- **GREENOAK SPAIN HOLDINGS SOCIMI II, S.A.** (BME Growth): 1 menciones; p. ej. *Amorebieta* — «2 Suelo Amorebieta Go Love Suelo logístico Vizcaya 19.442»
- **GAVARI PROPERTIES SOCIMI, S.A.** (BME Scaleup): 1 menciones; p. ej. *Santurce* — «Santurce 69, bajo a, p»
- **TRIVIUM REAL ESTATE SOCIMI, S.A.** (BME Growth): 1 menciones; p. ej. *Vizcaya* — «(Cantabria), Gran Casa (Zaragoza), y Max Center (Vizcaya), que suman una superficie»
- **ADRIANO CARE SOCIMI S.A.** (BME Growth): 5 menciones; p. ej. *Ortuella* — «comprometido y la concesión de Ortuella). Senior living Población»
- **KTESIOS REAL ESTATE SOCIMI S.A.** (BME Growth): 4 menciones; p. ej. *ÁLAVA* — «691 PLAZA MAYOR ABETXUCO 2 ÁLAVA ÁLAVA 34838 VIVIENDA 01/07/2023»

## Sin vínculo encontrado

Las 162 restantes no nombran ningún lugar vasco ni tienen préstamos de entidades vascas en lo leído. Para las escaneadas (57) esto no significa «no»: significa «no leído». La lista completa, con segmento y domicilio, está en `base/csv/sociedad.csv` y `base/csv/vinculo_vasco.csv`.

## Cómo se ha medido

`socimis/vinculo_vasco.py` con el gazetteer `socimis/vasco.json` (provincias en castellano y euskera, municipios de más de 15.000 habitantes y entidades financieras con sede vasca) sobre la tabla de inversiones inmobiliarias, la tabla de vencimientos y el texto de los documentos bajados (cuentas anuales, semestral, valoración, participaciones, dividendo). Un lugar que falte en el gazetteer no se detecta: se amplía el JSON y se repite `python3 -m socimis vasco todas`.

# Fuentes comprobadas en la Fase 1 (2026-10-26, desde la nube)

`robots` = resultado de `tools/robots_check.py` de Doc (MIT, © Juan Colmenarejo / repo `Colmeee/doc`), reutilizado tal cual.

| Fuente | URL comprobada | Qué es público | Formato | Programático | Coste | Actualización | Condiciones | robots |
|---|---|---|---|---|---|---|---|---|
| BME Growth, listado | https://www.bolsasymercados.es/es/bme-growth/cotizaciones-e-indices/empresas-cotizadas.html | 109 cotizadas, 55 SOCIMIs, con capitalización, sector y web | HTML (JS) | No documentado (la página llama a `apiweb.bolsasymercados.es/Market/v1/EQ/ListedCompanies`); no usado | 0 € | Diaria | «Uso interno»; comercial o redifusión no gratuita → BME Market Data | permite |
| BME Scaleup, listado | https://www.bolsasymercados.es/es/bme-scaleup/cotizaciones-e-indices/empresas-cotizadas.html | 52 cotizadas (43 SOCIMIs), 20 por página | HTML (JS) | ídem | 0 € | Diaria | ídem | permite |
| BME, ficha de sociedad | …/empresas-cotizadas/ficha.miciso-real-es0105707006.html (`#/company-details`, `#/financial-data`, `#/inside-info`) | Domicilio, NIF, auditor, asesor registrado, proveedor de liquidez; documentos | HTML (JS) + PDF | PDF con URL estable `apiweb.bolsasymercados.es/Market/MTFDocuments/<Tipo>/<AAAA>/<MM>/<código>_<tipo>_<fecha>.pdf` | 0 € | Al publicarse (semestral ≤ 4 meses; anual ≤ 4 meses tras cierre; participaciones ≥ 5 % semestrales) | ídem | permite |
| **BME, servidor de los PDF** | https://apiweb.bolsasymercados.es/robots.txt | Todos los PDF de BME Growth/Scaleup (OIR, cuentas, avisos, folletos) | PDF | URL estable por documento | 0 € | Al publicarse | Las de BME (uso interno) | **`User-agent: * / Disallow: /`** (visto el 2026-10-26 al bajar por código; en la Fase 1 los PDF se bajaron a mano con curl sin mirar este host). **Decisión de Juan por pantalla ese día: se bajan igual, uno a uno, 5 por sociedad** (PRD, decisión 6; `cortesia.EXCEPCIONES_ROBOTS`) |
| CNMV, entidad | https://www.cnmv.es/portal/Consultas/DatosEntidad.aspx?nif=A86977790 | Índice de 20 registros por NIF | HTML | URL por NIF | 0 € | Continua | Nota legal: uso privado libre; reproducción fiel; si se cobra, avisar de que es gratis | permite (`Disallow: *.shtml`) |
| CNMV, informes anuales | https://www.cnmv.es/portal/Consultas/ifa/listadoifa.aspx?id=0&nif=A86977790 | IFA 2014-2025, auditor, opinión | **ESEF xhtml/iXBRL** (48 MB) + ZIP, PDF | Sí: enlaces `webservices/verdocumento/ver?e=…` | 0 € | Anual (≤ 4 meses) | ídem | permite |
| CNMV, semestrales | https://www.cnmv.es/portal/Consultas/ifi/listaifi.aspx?nif=A86977790 | IPP desde 2005 | XBRL (taxonomía CNMV) + PDF | Sí (visor `cnmv.es/ipps`) | 0 € | Semestral | ídem | permite |
| CNMV, participaciones | https://www.cnmv.es/portal/Consultas/derechosvoto/ps_ac_ini.aspx?nif=A86977790 → Notificaciones | Accionistas ≥ 3 %, con fecha | HTML | Página (postback) | 0 € | Al notificarse | ídem | permite |
| BOE, API BORME | https://www.boe.es/datosabiertos/api/borme/sumario/20261023 | Sumario diario: sección A por provincia con PDF | JSON/XML → PDF | Sí | 0 € | Diaria | Reutilización comercial permitida; atribución «Basado en datos de la AEBOE»; RGPD | permite (`xml.php` no) |
| BOE, Ley 11/2009 | https://www.boe.es/buscar/act.php?id=BOE-A-2009-17000 | Texto consolidado (7-10-2026) | HTML | API legislación consolidada | 0 € | — | ídem | permite |
| Registro Mercantil, sede | https://sede.registradores.org/sede/sede-corpme-web/home/ | «Depósito de cuentas», «Nota informativa», «Sociedad con cuentas depositadas» | ZIP (PDF + XBRL/XML) según fuentes secundarias | No (aplicación JS con registro de usuario) | De pago; oficial **no confirmado**; secundarias 8,99-20 € | Tras el depósito (≤ 7 meses del cierre) | No leídas (menú JS) | sin robots.txt |
| Registradores, datos abiertos | https://opendata.registradores.org/ | — | — | — | — | — | — | **bloqueado desde la nube** (WAF) |
| Euronext Access París | https://live.euronext.com/ (documentos en `/sites/default/files/…pdf`, notas en `/listview/company-press-release/…`) | Information Document; cuentas anuales como nota de prensa | PDF | Buscador del sitio | 0 € | Anual | No leídas | permite |
| Portfolio Stock Exchange | https://www.portfolio.exchange/portfolio-market/aofi-sheni-socimi-AOFI-ES0105801007-9 | Precio, NAV, capitalización; **sin documentos sin registro** | HTML (Nuxt) | No | 0 € (registro) | — | No leídas | permite |
| LibreBORME | https://librebor.me/borme/search/?q=SOCIMI | Búsqueda por nombre | HTML | API | 0 € | Diaria | — | **403 Cloudflare desde la nube** |
| OpenMercantil | https://openmercantil.es/api/v1/search?q=SOCIMI | Devuelve 0 resultados para «SOCIMI» (busca por nombre exacto) | JSON | Sí (200/día) | 0 € | — | Atribución BOE | — |
| Normas Forales IS | Bizkaia https://www.bizkaia.eus/documents/880307/15187815/ca_11_2013.pdf ; Álava https://web.araba.eus/documents/d/araba/norma-foral-del-impuesto-sobre-sociedades_cas ; Gipuzkoa (vLex, NF 2/2014) | Régimen SOCIMI **eliminado**; DA 13ª solo para socios de SOCIMIs de territorio común | PDF | — | 0 € | — | — | — |
| ArmanexT (vía Brainsre) | https://brainsre.news/socimis-espana-2026-157-cotizadas-31010-millones/ | 169 SOCIMIs cotizadas a 30-6-2026 por mercado | HTML | — | 0 € | Semestral | Secundaria, sin contrastar con el estudio original | — |

## Documentos descargados (no suben al repo; solo URL y huella SHA-256)

| Sociedad | Documento | URL | SHA-256 |
|---|---|---|---|
| Merlin Properties | IFA 2025 consolidado, ESEF xhtml (CNMV reg. 20913) | https://www.cnmv.es/webservices/verdocumento/ver?e=BkIsWwMBv1yEfg2Yc2JvuUvGON43wHHcXbrRTjRnO%2bCze5HLI2BThe6mgBjw3Gx%2f | 22132dafe57d679c9c291ee2c93b8ddb159d8772ceb028ee7dc571505fc18f57 |
| Merlin Properties | Results report FY25 (LTV 28,9 %, rentas brutas 541.856 k€) | https://ir.merlinproperties.com/wp-content/uploads/2026/07/Results-report-FY25.pdf | (no calculada) |
| All Iron RE I | Cuentas anuales consolidadas 2025 (OIR 21-5-2026, 152 páginas, con texto) | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/05/05495_OtraInfRelev_20260521.pdf | 19ea634a81dad934d7908655fe2b508a446cec27bbef78a0e53ad859e862815b |
| All Iron RE I | Valoración de activos 31-12-2025 (363.437.000 €) | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/04/05495_OtraInfRelev_20260430.pdf | 1e7732ca3a4ce23f6aecb8aaec350089387f63fbc12ea4155f356cb2bd506860 |
| All Iron RE I | Participaciones significativas a 30-6-2026 | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/07/05495_OtraInfRelev_20260706.pdf | 7e443826b98691edb7016fb64182a7f20ea74a3068f5c66a142078966d8dea46 |
| All Iron RE I | Dividendo con cargo a 2025 | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/06/05495_OtraInfRelev_20260624.pdf | 282adfe29a94b103d78dde19a946c7ed87ebd166d11212b52e085a1754043954 |
| Miciso Real Estate | Estados financieros intermedios 30-6-2026 (39 páginas **escaneadas**, 24 MB) | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/10/05707_OtraInfRelev_20261023.pdf | 70ce45c914d8880452f2b02d16c1691999a861e27bfc3e0ff206f1392021f1eb |
| Miciso Real Estate | Participaciones significativas a 30-6-2026 | https://apiweb.bolsasymercados.es/Market/MTFDocuments/OtraInfRelevante/2026/07/05707_OtraInfRelev_20260708.pdf | ebc1dc7455dad6c4479935e2bde1da047d940c257d93d2abb7ca7e63b28f866f |

Domicilios leídos en la pestaña «Datos Empresa» de BME Growth: Miciso, Paseo de la Habana 74, 28036 Madrid (NIF A72793888);
All Iron RE I, C/ Montesquinza 28, 28010 Madrid (NIF A87934741).

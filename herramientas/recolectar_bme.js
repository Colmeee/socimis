// Recolecta las fichas de las SOCIMIs de BME Growth o BME Scaleup con un navegador (Playwright), despacio.
//
// Por qué un navegador: la ficha de cada sociedad en bolsasymercados.es se pinta con JavaScript; el HTML del servidor
// no trae ni el domicilio ni la lista de documentos. Aquí se hace lo que haría una persona —abrir el listado, abrir
// cada ficha, mirar «Datos Empresa» y «O. I. Relevante»— y se guarda lo visto en un JSON por sociedad. No se llama a
// la API interna del sitio. Pausa entre páginas (PAUSA_MS), reanudable (salta las fichas ya guardadas), y para si el
// sitio contesta con errores seguidos. Los PDF NO se bajan aquí: eso lo hace `python3 -m socimis bme <ficha.json>`
// por red.py, con robots.txt y su propio ritmo.
//
// Uso (en la nube, que es donde está Playwright):
//   node herramientas/recolectar_bme.js growth  [--max 10] [--solo-socimi] [--salida descargas/bme]
//   node herramientas/recolectar_bme.js scaleup [--max 10] [--solo-socimi] [--isin ES0105495008,ES0105707006]
// Deja: <salida>/<segmento>-listado.json y <salida>/fichas/<ISIN>.json
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const SEGMENTOS = {
  growth: { url: 'https://www.bolsasymercados.es/es/bme-growth/cotizaciones-e-indices/empresas-cotizadas.html', nombre: 'BME Growth' },
  scaleup: { url: 'https://www.bolsasymercados.es/es/bme-scaleup/cotizaciones-e-indices/empresas-cotizadas.html', nombre: 'BME Scaleup' },
};
const PAUSA_MS = 2500;
const UA = 'socimis/0.1 (+uso propio; base de SOCIMIs cotizadas)';

function arg(nombre, defecto) { const i = process.argv.indexOf(nombre); return i > 0 ? process.argv[i + 1] : defecto; }
const segmento = process.argv[2];
if (!SEGMENTOS[segmento]) { console.error('uso: node recolectar_bme.js growth|scaleup [--max N] [--solo-socimi] [--salida dir]'); process.exit(2); }
const MAX = parseInt(arg('--max', '1000'), 10);
const SOLO_SOCIMI = process.argv.includes('--solo-socimi');
const SOLO_ISIN = (arg('--isin', '') || '').toUpperCase().split(',').filter(Boolean);   // --isin ES0105495008,ES0105707006: solo esas
const SALIDA = arg('--salida', path.join(__dirname, '..', 'descargas', 'bme'));
fs.mkdirSync(path.join(SALIDA, 'fichas'), { recursive: true });
const dormir = (ms) => new Promise(r => setTimeout(r, ms));
const hoy = new Date().toISOString().slice(0, 10);

async function listado(page) {
  const seg = SEGMENTOS[segmento];
  await page.goto(seg.url, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(3000);
  const leerFilas = () => page.evaluate(() => Array.from(document.querySelectorAll('table tbody tr')).map(tr => {
    const tds = Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim());
    const a = tr.querySelector('a[href*="ficha."]');
    return { nombre: tds[0], capitalizacion: tds[1], sector: tds[tds.length - 2], web: tds[tds.length - 1], url: a ? a.href : null };
  }).filter(f => f.url));
  const filas = [];
  const sumar = (nuevas) => { for (const f of nuevas) if (!filas.find(x => x.url === f.url)) filas.push(f); };
  sumar(await leerFilas());
  // la lista va paginada de 20 en 20 (Scaleup: «1 2 3 Siguiente»); los enlaces de página no son visibles para Playwright,
  // así que se pulsan desde dentro de la página por su número
  for (let n = 2; n <= 30; n++) {
    const hay = await page.evaluate((n) => { const a = Array.from(document.querySelectorAll('a.six-pagination__page-link')).find(e => e.innerText.trim() === String(n)); if (!a) return false; a.click(); return true; }, n);
    if (!hay) break;
    await page.waitForTimeout(3500);
    const antes = filas.length; sumar(await leerFilas());
    if (filas.length === antes) break;
  }
  return filas.map(f => ({ ...f, segmento: seg.nombre, isin: (f.url.match(/-(es\w{10})\.html/i) || [])[1]?.toUpperCase() || null }));
}

function numero(t) { if (!t) return null; const v = parseFloat(t.replace(/\./g, '').replace(',', '.')); return isNaN(v) ? null : v; }

const CATEGORIAS = ['Informes financieros anuales y de auditoría', 'Informes financieros semestrales y de auditoría / revisiones limitadas',
  'Participaciones significativas', 'Informe anual de gobierno corporativo', 'Convocatorias y acuerdos de juntas', 'Operaciones sobre acciones propias',
  'Cambios en el consejo de administración', 'Cambio de asesor registrado', 'Cambio de proveedor de liquidez', 'Pago de dividendos', 'Otra información relevante',
  'Información privilegiada', 'Información financiera', 'Sobre negocio y situación financiera', 'Sobre instrumentos financieros',
  'Sobre operaciones de activos, valoraciones asociadas y endeudamiento', 'Sobre operaciones corporativas: fusiones, adquisiciones y otros',
  'Sobre ofertas públicas de suscripción y venta de instrumentos financieros', 'Sobre Gobierno corporativo', 'Operaciones realizadas por directivos',
  'Relacionado con: Otra Información Relevante', 'Relacionado con: Información Privilegiada', 'Aviso'];

async function recogerPaginas(page) {
  // la lista viene paginada («Siguiente»): se recogen los PDF de cada página hasta que no salga ninguno nuevo
  const porUrl = new Map();
  for (let pagina = 0; pagina < 12; pagina++) {
    for (const d of await page.evaluate(documentosDe)) if (!porUrl.has(d.url) || d.texto.length > porUrl.get(d.url).texto.length) porUrl.set(d.url, d);
    const antes = porUrl.size;
    const siguiente = page.getByRole('button', { name: /^Siguiente$/ }).first();
    const enlace = page.getByText(/^Siguiente$/).first();
    const boton = (await siguiente.count()) ? siguiente : enlace;
    if (!(await boton.count())) break;
    const activo = await boton.isEnabled().catch(() => true);
    if (!activo) break;
    await boton.click({ timeout: 4000 }).catch(() => {});
    await page.waitForTimeout(3000);
    for (const d of await page.evaluate(documentosDe)) if (!porUrl.has(d.url) || d.texto.length > porUrl.get(d.url).texto.length) porUrl.set(d.url, d);
    if (porUrl.size === antes) break;
  }
  return Array.from(porUrl.values());
}

async function irA(page, url) {
  // las pestañas son rutas con «#»; no se recarga (la recarga vuelve al resumen): se navega y se espera a que pinte
  await page.goto('about:blank');
  await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(2500);
}

async function esperarTexto(page, patron, ms) {
  await page.waitForFunction((p) => new RegExp(p).test(document.body.innerText), patron, { timeout: ms }).catch(() => {});
  await page.waitForTimeout(1200);
}

function documentosDe() {
  const vistos = new Set(); const docs = [];
  for (const a of document.querySelectorAll('a[href$=".pdf"]')) {
    if (vistos.has(a.href) || !/MTFDocuments/.test(a.href)) continue; vistos.add(a.href);
    let fila = a.closest('tr, li, article');
    if (!fila) { fila = a.parentElement; for (let i = 0; i < 4 && fila && fila.innerText.trim().length < 40; i++) fila = fila.parentElement; }
    const texto = (fila ? fila.innerText : '').replace(/\s+/g, ' ').trim().slice(0, 400);
    docs.push({ url: a.href, texto });
  }
  return docs;
}

function clasificarTexto(d) {
  let t = d.texto.replace(/Ver PDF/g, ' ').replace(/\s+/g, ' ').trim();
  const fecha = (t.match(/(\d{2})\/(\d{2})\/(\d{4})/) || []);
  let categoria = null;
  for (const c of CATEGORIAS) if (t.includes(c)) { categoria = c; t = t.replace(c, ' '); break; }
  t = t.replace(/Otra Información Relevante:|Información Privilegiada:|Hechos Relevantes:/g, ' ').replace(/\d{2}\/\d{2}\/\d{4}( - \d{2}:\d{2})?/g, ' ').replace(/\s+/g, ' ').trim();
  return { url: d.url, categoria, titulo: t.slice(0, 300), descripcion: null, fecha: fecha.length ? `${fecha[3]}-${fecha[2]}-${fecha[1]}` : null };
}

async function ficha(page, fila) {
  const base = fila.url;
  const salida = { ...fila, consultado: hoy, empresa: {}, documentos: [] };
  await irA(page, base); await esperarTexto(page, 'Capitalización', 20000);
  const cab = await page.evaluate(() => document.body.innerText);
  salida.ticker = (cab.match(/Ticker\n(\S+)/) || [])[1] || null;
  salida.cierre = numero((cab.match(/Cierre\n([\d.,]+)\n(\d{2}\/\d{2}\/\d{4})/) || [])[1]);
  salida.fecha_cierre = ((cab.match(/Cierre\n[\d.,]+\n(\d{2})\/(\d{2})\/(\d{4})/) || []).slice(1, 4).reverse().join('-')) || null;
  salida.capitalizacion = numero((cab.match(/Capitalización\n([\d.,]+)/) || [])[1]);
  await irA(page, base + '#/company-details'); await esperarTexto(page, 'Domicilio', 25000);
  const emp = await page.evaluate(() => document.body.innerText);
  for (const [clave, rotulo] of [['proveedor_liquidez', 'Proveedor de Liquidez'], ['asesor_registrado', 'Asesor Registrado'], ['auditor', 'Auditor'], ['domicilio', 'Domicilio'], ['nif', 'NIF']]) {
    const m = emp.match(new RegExp(rotulo + '\\n([^\\n]+)')); salida.empresa[clave] = m ? m[1].trim() : null;
  }
  await irA(page, base + '#/inside-info?dataParam=OtherRelevantInformation');
  // la lista completa tarda: se espera a que haya bastantes PDF o el «Mostrando N elementos» (hasta 45 s)
  await page.waitForFunction(() => document.querySelectorAll('a[href*="MTFDocuments"]').length >= 8 || /Mostrando \d+ elementos/.test(document.body.innerText), null, { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const oir = (await recogerPaginas(page)).map(clasificarTexto);
  await irA(page, base + '#/financial-data'); await esperarTexto(page, 'Mostrando|Ver PDF', 20000); await page.waitForTimeout(2000);
  const fin = (await recogerPaginas(page)).map(d => ({ ...clasificarTexto(d), categoria: clasificarTexto(d).categoria || 'Información financiera' }));
  const porUrl = new Map();   // la misma URL puede salir en el resumen (sin título) y en la lista completa (con título): se queda la más rica
  for (const d of [...oir, ...fin]) { const previo = porUrl.get(d.url); if (!previo || (d.titulo || '').length > (previo.titulo || '').length) porUrl.set(d.url, { ...previo, ...d, categoria: d.categoria || (previo && previo.categoria) || null }); }
  salida.documentos = Array.from(porUrl.values());
  return salida;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ userAgent: UA });
  let filas;
  const rutaListado = path.join(SALIDA, `${segmento}-listado.json`);
  if (fs.existsSync(rutaListado)) { filas = JSON.parse(fs.readFileSync(rutaListado, 'utf-8')); console.log(`listado ya recogido: ${filas.length} sociedades`); }
  else { filas = await listado(page); fs.writeFileSync(rutaListado, JSON.stringify(filas, null, 1)); console.log(`listado: ${filas.length} sociedades en ${SEGMENTOS[segmento].nombre}`); }
  const objetivo = filas.filter(f => (!SOLO_SOCIMI || /SOCIMI/i.test(f.nombre + ' ' + f.sector)) && (!SOLO_ISIN.length || SOLO_ISIN.includes(f.isin)));
  let hechas = 0, errores = 0;
  for (const f of objetivo) {
    if (hechas >= MAX) break;
    const destino = path.join(SALIDA, 'fichas', `${f.isin || f.nombre.replace(/\W+/g, '_')}.json`);
    if (fs.existsSync(destino)) continue;
    try {
      await dormir(PAUSA_MS);
      const datos = await ficha(page, f);
      fs.writeFileSync(destino, JSON.stringify(datos, null, 1));
      hechas++; errores = 0;
      console.log(`✓ ${f.nombre} · NIF ${datos.empresa.nif} · ${datos.empresa.domicilio} · ${datos.documentos.length} documentos`);
    } catch (e) {
      errores++; console.log(`✗ ${f.nombre}: ${e.message.slice(0, 120)}`);
      if (errores >= 3) { console.log('tres fallos seguidos: paro aquí (se reanuda al volver a lanzar)'); break; }
    }
  }
  await browser.close();
  console.log(`hechas ${hechas}; fichas en ${path.join(SALIDA, 'fichas')}`);
})();

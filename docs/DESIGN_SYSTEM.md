# Design system — cómo se ve socimis

Qué construimos: `PRD.md`. Cómo conecta: `ARCHITECTURE.md`. Cómo se trabaja: `../AGENTS.md`.

socimis no tiene pantalla: su salida son ficheros (Markdown, CSV, SQLite, JSON) y lo que imprime el Terminal. Este
documento fija cómo se escriben para que todo parezca una sola herramienta y se lea sin esfuerzo.

## Dirección

Sobrio y auditable, como un informe de analista: primero el número, después el porqué, siempre la fuente. Español,
frases cortas, sin adjetivos. Lo que no se sabe se dice («no consta»), nunca se rellena.

## Números y fechas

- Euros con punto de miles y coma decimal, en la unidad que se lee de un vistazo: «363,4 M€», «3.226.792,91 €».
- Porcentajes con coma y el signo pegado: «31,8 %». Los puntos del motor con un decimal: «64,3».
- Fechas ISO en los ficheros (`2025-12-31`) y en el informe; nunca «31/12/25».
- Lo derivado lleva su fórmula al lado la primera vez que aparece: «LTV neto 30,4 % (deuda neta / GAV)».

## El informe (`base/informe.md`)

1. Título con la fecha de puntuación.
2. Tabla del ranking: `# · Sociedad · Segmento · Puntos · Tramo · Cobertura · LTV · Dividendo · Mayor accionista · Vínculo vasco`.
3. Una ficha de puntuación por sociedad (`puntuacion.texto`): cabecera `### Nombre · puntos · tramo · cobertura`,
   una línea por dimensión con `puntos/max (estado)`, debajo cada parte con `puntos/max, estado — detalle · fuente: URL`.
4. Los avisos con ⚠️ al final de cada ficha, nunca escondidos.

## La consola

Una línea por cosa hecha, con ✓ / ✗ al principio cuando hay éxito o fallo, y la ruta del fichero al terminar:
`✓ cuentas_anuales: 2026-05-21, 12.297 KB, pdftotext` · `Ficha: base/fichas/A87934741.json`. Sin barras de progreso,
sin colores (el Terminal del Mac y la nube los pintan distinto).

## Los ficheros

- JSON con `ensure_ascii=False`, sangría 1, claves ordenadas: diffs legibles en Git.
- CSV con `;` y UTF-8 (lo abre Numbers y Excel en español sin preguntar), cabecera en la primera fila, vacío por `None`.
- Markdown sin HTML.

## Vocabulario fijo

«tramo»: prioritaria / interesante / de momento no / sin datos. «estado» de una parte: cumplida / parcial /
no cumplida / sin datos. «contraste»: oficial / mercado / empresa / derivado / prensa / no_consta. «vínculo vasco»:
fuerte / indicio / ninguno. No se inventan sinónimos.

## Accesibilidad y responsive

No aplican (no hay interfaz). Si algún día hay pantalla, se escribe aquí antes de la primera línea de HTML.

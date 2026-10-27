# socimis

La base de las SOCIMIs cotizadas españolas, con cada dato y su fuente, y el motor que las ordena. Uso propio de Juan
Colmenarejo. Qué es y qué no: `docs/PRD.md`. Cómo conecta: `docs/ARCHITECTURE.md`. El veredicto que lo justifica:
`docs/VEREDICTO-FASE-1.md`.

## En el Mac, paso a paso

1. Abre **Terminal** y entra en la carpeta: `cd ~/Proyectos/socimis`
2. Trae lo último: `git pull --ff-only`
3. Comprueba que todo está en verde: `bash probar.sh` → tiene que acabar en «N bien, 0 mal».
4. Mira el ranking: abre `base/informe.md` (Obsidian o cualquier editor) o `base/socimis.sqlite` con un visor de SQLite;
   los CSV de `base/csv/` se abren con Numbers.
5. Si hay PDF escaneados esperando OCR: `python3 -m socimis ocr-pendientes` los lista (el OCR lo hace el Mac).
6. Los tres documentos para leer sin abrir nada más: `docs/LISTA-SOCIMIS.md` (todas en una tabla), `docs/CENSO-ESPANA.md`
   (por mercado y provincia, y lo que no se ha mirado) y `docs/CENSO-VINCULO-VASCO.md` (el piloto vasco).

Lo que **no** hay que hacer en el Mac: recolectar fichas de BME (eso es Playwright, en la nube) ni bajar PDF en lote.

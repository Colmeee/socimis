#!/bin/bash
# Una tanda del lote educado: para cada ficha recolectada de BME que aún no tenga documentos leídos, baja sus PDF y la lee;
# después vínculo vasco, puntuación y base. Reanudable: lo ya hecho se salta (el diario de descargas y las fichas lo saben).
#   bash herramientas/tanda.sh [--max N]        (desde la raíz del repositorio; N fichas como mucho en esta tanda, 20 por defecto)
AQUI="$(cd "$(dirname "$0")/.." && pwd)"
cd "$AQUI" || exit 1
MAX=20; [ "$1" = "--max" ] && MAX="$2"
hechas=0; fallos=0
for f in descargas/bme/fichas/*.json; do
  [ -e "$f" ] || continue
  nif="$(python3 -c "import json,sys; print((json.load(open(sys.argv[1])).get('empresa') or {}).get('nif') or '')" "$f" | tr -d ' -' | tr a-z A-Z)"
  if [ -n "$nif" ] && [ -f "base/fichas/$nif.json" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('documentos') else 1)" "base/fichas/$nif.json"; then
    continue
  fi
  [ "$hechas" -ge "$MAX" ] && break
  echo "== $(date +%H:%M) $f"
  if python3 -m socimis bme "$f"; then hechas=$((hechas+1)); else fallos=$((fallos+1)); fi
done
echo "== fichas leídas en esta tanda: $hechas · fallos: $fallos"
python3 -m socimis vasco todas >/dev/null && python3 -m socimis puntuar todas >/dev/null && python3 -m socimis base
echo "== pendientes de OCR:"; python3 -m socimis ocr-pendientes

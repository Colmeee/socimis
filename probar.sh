#!/bin/bash
# Toda la batería SIN RED, más las comprobaciones de la casa: ningún secreto, ningún nombre de persona en los fixtures,
# ningún PDF en el repositorio, criterios que cuadran, sintaxis compatible con Python 3.9.
#   bash probar.sh      -> acaba en «N bien, 0 mal» y sale con 0 si todo está en verde
AQUI="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)" || { echo "FALLO: no encuentro python3"; exit 1; }
ok=0; mal=0
bien() { ok=$((ok+1)); echo "  ok      $1"; }
fallo() { mal=$((mal+1)); echo "  FALLO   $1"; }

echo "— La batería (Python $("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])'), sin red) —"
SOCIMIS_SIN_RED=1 "$PY" "$AQUI/pruebas/correr.py" && bien "pruebas unitarias en verde" || fallo "la batería tiene fallos"

echo "— Comprobaciones de la casa —"
# sintaxis 3.9: nada de match ni de X | Y en anotaciones
! grep -rnE "^\s*match\s+\w+.*:\s*$" "$AQUI/socimis" --include=*.py >/dev/null && bien "sin «match» (Python 3.9 del Mac)" || fallo "hay «match»"
! grep -rnE "\)\s*->\s*\w+\s*\|\s*\w+" "$AQUI/socimis" --include=*.py >/dev/null && bien "sin «X | Y» en tipos" || fallo "hay «X | Y»"
"$PY" -c "import sys; sys.path.insert(0,'$AQUI'); from socimis import puntuacion; puntuacion.cargar_criterios()" && bien "criterios.json cuadra (100 puntos)" || fallo "criterios.json no cuadra"
# ningún PDF ni xhtml real dentro del repositorio versionado
[ -z "$(cd "$AQUI" && git ls-files 2>/dev/null | grep -iE '\.(pdf|xhtml|xbri|zip)$' | grep -v 'pruebas/fixtures/ixbrl-merlin-2025-extracto.xhtml')" ] && bien "ningún PDF ni paquete ESEF versionado" || fallo "hay documentos versionados"
# ninguna clave: patrones habituales
! grep -rnE "(api[_-]?key|secret|token|password|contraseña)\s*[:=]\s*['\"][A-Za-z0-9/_+-]{12,}" "$AQUI" --include=*.py --include=*.js --include=*.json --include=*.md --include=*.sh 2>/dev/null | grep -v "pruebas/" >/dev/null && bien "ninguna clave escrita" || fallo "algo parece una clave"
# nombres de firmantes reales conocidos no entran en los fixtures (se añaden aquí los que se hayan tenido que quitar)
! LC_ALL=C.UTF-8 grep -rniE "asier|hern.ndez juez|pich-aguilera|lao hernandez|riberas|sala coll|g.mez laguna" "$AQUI/pruebas/fixtures" >/dev/null && bien "los fixtures no llevan nombres de personas reales" || fallo "un fixture lleva un nombre de persona real"
# el candado de red funciona
SOCIMIS_SIN_RED=1 "$PY" -c "import sys; sys.path.insert(0,'$AQUI'); from socimis import red
try:
    red.pedir_bytes('https://www.boe.es/', red.UA); sys.exit(1)
except RuntimeError: pass" && bien "SOCIMIS_SIN_RED=1 cierra la red" || fallo "la red no se cierra"
# la línea de mandos arranca sin red y sin datos
SOCIMIS_SIN_RED=1 SOCIMIS_DIR="$(mktemp -d)" "$PY" -m socimis >/dev/null 2>&1; [ $? -eq 2 ] && bien "python3 -m socimis enseña la ayuda" || fallo "la línea de mandos no arranca"

echo
echo "$ok bien, $mal mal"
[ "$mal" -eq 0 ]

#!/usr/bin/env sh
# Parse + typecheck das specs Z com CZT. Requer JDK e czt.jar (JAVA_EXE / CZT_JAR ou ~/.tools).
set -eu
cd "$(dirname "$0")/.."
JAVA="${JAVA_EXE:-$(command -v java || true)}"
CZT="${CZT_JAR:-$HOME/.tools/czt/czt.jar}"
[ -n "$JAVA" ] && [ -f "$CZT" ] || { echo "JDK/CZT ausentes (veja docs/decisions/tool-evaluation.md)"; exit 2; }
failed=0
for f in specs/formal-z/*.tex; do
  out="$("$JAVA" -jar "$CZT" "$f" 2>&1 || true)"
  if echo "$out" | grep -q "Exception" || ! echo "$out" | grep -q "0 warnings and errors"; then
    echo "FALHOU: $f"; echo "$out"; failed=$((failed + 1))
  else
    echo "OK (parse+typecheck, 0 warnings and errors): $f"
  fi
done
exit $failed

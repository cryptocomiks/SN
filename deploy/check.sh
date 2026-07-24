#!/usr/bin/env bash
# =====================================================================
#  Diagnostic : vérifie que le site et les sources de données répondent.
#  Usage :  bash deploy/check.sh
# =====================================================================
BASE="http://localhost"
OK=0; KO=0

c_ok(){   printf '  \033[32m✓\033[0m %s\n' "$1"; OK=$((OK+1)); }
c_ko(){   printf '  \033[31m✗\033[0m %s\n' "$1"; KO=$((KO+1)); }
c_head(){ printf '\n\033[1m%s\033[0m\n' "$1"; }

# test <libellé> <url> [motif attendu dans le corps]
test_url(){
  local label="$1" url="$2" needle="${3:-}"
  local tmp code
  tmp="$(mktemp)"
  # -L : suivre les redirections (files.data.gouv.fr renvoie des 302)
  code="$(curl -sL -o "$tmp" -w '%{http_code}' --max-time 45 "$url" 2>/dev/null)"
  local size; size="$(wc -c <"$tmp" | tr -d ' ')"
  if [ "$code" = "200" ]; then
    if [ -n "$needle" ] && ! grep -qi -- "$needle" "$tmp"; then
      c_ko "$label — HTTP 200 mais contenu inattendu (${size} o)"
      printf '      début: %s\n' "$(head -c 120 "$tmp" | tr -d '\n')"
    else
      c_ok "$label — HTTP 200 (${size} o)"
    fi
  else
    c_ko "$label — HTTP ${code:-timeout}"
  fi
  rm -f "$tmp"
}

c_head "1. Serveur web local"
test_url "Page du site (/)"        "$BASE/"           "Biens dormants"
test_url "Sonde proxy (/api/health)" "$BASE/api/health" "ok"

c_head "2. Sources de données via le reverse-proxy nginx"
test_url "BAN — géocodage" \
  "$BASE/api/ban/search/?q=15+rue+de+trion+lyon&limit=1" "FeatureCollection"

test_url "Cadastre IGN — parcelles (Lyon 5e)" \
  "$BASE/api/geopf/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle&OUTPUTFORMAT=application/json&SRSNAME=CRS:84&COUNT=5&BBOX=4.815,45.754,4.820,45.758,CRS:84" \
  "features"

test_url "DVF — mutations Lyon 1er" \
  "$BASE/api/dvf/geo-dvf/latest/geojson/communes/69/69381.json" "features"

c_head "3. Accès direct (sans proxy) — pour comparaison"
test_url "IGN direct" \
  "https://data.geopf.fr/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities" "WFS"
test_url "DVF direct" \
  "https://files.data.gouv.fr/geo-dvf/latest/geojson/communes/69/69381.json" "features"

c_head "Résultat"
printf '  %s réussis, %s échoués\n' "$OK" "$KO"
if [ "$KO" -gt 0 ]; then
  printf '\n  Si DVF échoue : le chemin du fichier a peut-être changé.\n'
  printf '  Explorer l'\''arborescence réelle avec :\n'
  printf '    curl -s https://files.data.gouv.fr/geo-dvf/latest/geojson/communes/69/ | head -50\n'
fi
echo

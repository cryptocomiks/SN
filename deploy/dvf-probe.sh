#!/usr/bin/env bash
# =====================================================================
#  Sonde DVF : trouve le chemin réel des fichiers de mutations.
#  Le serveur renvoie une redirection (302) ; on la suit et on explore
#  l'arborescence pour identifier le format publié actuellement.
#  Usage :  bash deploy/dvf-probe.sh
# =====================================================================
HOST="https://files.data.gouv.fr"
INSEE="69381"   # Lyon 1er

hr(){ printf '\n\033[1m%s\033[0m\n' "$1"; }

hr "1. Chaîne de redirection pour le chemin actuellement utilisé"
URL="${HOST}/geo-dvf/latest/geojson/communes/69/${INSEE}.json"
echo "  départ : ${URL}"
curl -sIL --max-time 40 "$URL" 2>/dev/null \
  | grep -iE '^(HTTP/|location:)' \
  | sed 's/^/    /'
FINAL="$(curl -so /dev/null -w '%{url_effective}|%{http_code}|%{size_download}' \
         -L --max-time 60 "$URL" 2>/dev/null)"
echo "    => final : ${FINAL}"

hr "2. Contenu des répertoires (identifie la vraie structure)"
for d in "/geo-dvf/latest/" \
         "/geo-dvf/latest/geojson/" \
         "/geo-dvf/latest/geojson/communes/" \
         "/geo-dvf/latest/geojson/communes/69/"; do
  echo "  --- ${d}"
  curl -sL --max-time 40 "${HOST}${d}" 2>/dev/null \
    | grep -oE 'href="[^"]+"' | head -18 | sed 's/^/      /'
done

hr "3. Chemins candidats (on cherche un HTTP 200)"
try(){
  local path="$1"
  local out; out="$(curl -so /dev/null -w '%{http_code}|%{size_download}|%{content_type}' \
                    -L --max-time 60 "${HOST}${path}" 2>/dev/null)"
  local code="${out%%|*}"
  if [ "$code" = "200" ]; then
    printf '  \033[32m✓ 200\033[0m %s  (%s)\n' "$path" "${out#*|}"
  else
    printf '  \033[31m✗ %s\033[0m %s\n' "$code" "$path"
  fi
}
try "/geo-dvf/latest/geojson/communes/69/${INSEE}.json"
try "/geo-dvf/latest/geojson/communes/69/${INSEE}.json.gz"
try "/geo-dvf/latest/geojson/communes/69/${INSEE}/mutations.geojson"
try "/geo-dvf/latest/geojson/communes/69/${INSEE}/mutations.geojson.gz"
try "/geo-dvf/latest/csv/communes/69/${INSEE}.csv"
try "/geo-dvf/latest/csv/2024/communes/69/${INSEE}.csv"
try "/geo-dvf/latest/csv/2023/communes/69/${INSEE}.csv"

hr "4. Aperçu du premier chemin qui répond"
for p in "/geo-dvf/latest/geojson/communes/69/${INSEE}.json" \
         "/geo-dvf/latest/geojson/communes/69/${INSEE}/mutations.geojson" \
         "/geo-dvf/latest/csv/communes/69/${INSEE}.csv"; do
  code="$(curl -so /dev/null -w '%{http_code}' -L --max-time 40 "${HOST}${p}" 2>/dev/null)"
  if [ "$code" = "200" ]; then
    echo "  ${p} :"
    curl -sL --max-time 60 "${HOST}${p}" 2>/dev/null | head -c 400 | sed 's/^/      /'
    echo; break
  fi
done
echo

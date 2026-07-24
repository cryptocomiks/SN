#!/usr/bin/env bash
# =====================================================================
#  Sonde complète : inspecte ce que renvoient RÉELLEMENT les APIs.
#  Objectif : voir les coordonnées et les noms de champs, pour comprendre
#  pourquoi les parcelles ne s'affichent pas.
#  Usage :  bash deploy/probe.sh
# =====================================================================
BBOX="4.8150,45.7540,4.8200,45.7580,CRS:84"
WFS="http://localhost/api/geopf/wfs/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=CADASTRALPARCELS.PARCELLAIRE_EXPRESS:parcelle&OUTPUTFORMAT=application/json&SRSNAME=CRS:84&COUNT=3&BBOX=${BBOX}"

echo "================ CADASTRE (via proxy) ================"
TMP="$(mktemp)"
CODE="$(curl -sL -o "$TMP" -w '%{http_code}' --max-time 45 "$WFS")"
echo "HTTP ${CODE} — $(wc -c <"$TMP" | tr -d ' ') octets"

python3 - "$TMP" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
except Exception as e:
    print("  JSON illisible:",e)
    print("  Début brut:",open(sys.argv[1],'rb').read()[:300])
    sys.exit()

feats=d.get("features") or []
print("  nb features :",len(feats))
print("  CRS annoncé :",json.dumps(d.get("crs","(absent)"))[:120])
if not feats:
    print("  >>> AUCUNE PARCELLE RENVOYEE pour cette bbox.")
    sys.exit()

f=feats[0]
print("  champs      :",", ".join(sorted((f.get("properties") or {}).keys())))
print("  exemple     :",json.dumps(f.get("properties"),ensure_ascii=False)[:220])

# première coordonnée
c=f.get("geometry",{}).get("coordinates")
def first(x):
    while isinstance(x,list) and x and isinstance(x[0],list): x=x[0]
    return x
p=first(c)
print("  type geom   :",f.get("geometry",{}).get("type"))
print("  1re coord   :",p)

if not (isinstance(p,list) and len(p)>=2):
    print("  >>> coordonnées illisibles")
    sys.exit()
a,b=p[0],p[1]
if abs(a)>1000 or abs(b)>1000:
    print("  >>> PROBLEME : coordonnées PROJETEES (Lambert-93 ?), pas du WGS84.")
    print("      Leaflet ne peut pas les afficher -> parcelles invisibles.")
elif 40<abs(a)<52 and abs(b)<10:
    print("  >>> ordre INVERSE (lat,lon) : le code doit permuter.")
elif abs(a)<10 and 40<abs(b)<52:
    print("  >>> OK : WGS84 lon,lat — conforme à ce qu'attend Leaflet.")
else:
    print("  >>> ordre/valeurs inattendus.")
PY
rm -f "$TMP"

echo
echo "================ DVF ================"
U="https://files.data.gouv.fr/geo-dvf/latest/geojson/communes/69/69381.json"
curl -sIL --max-time 40 "$U" 2>/dev/null | grep -iE '^(HTTP/|location:)' | head -6 | sed 's/^/  /'
echo "  final : $(curl -so /dev/null -w '%{http_code} — %{size_download} o' -L --max-time 90 "$U" 2>/dev/null)"

echo
echo "  Chemins candidats :"
for p in "geojson/communes/69/69381.json" \
         "geojson/communes/69/69381/mutations.geojson" \
         "csv/communes/69/69381.csv" \
         "csv/2024/communes/69/69381.csv"; do
  c="$(curl -so /dev/null -w '%{http_code}' -L --max-time 60 "https://files.data.gouv.fr/geo-dvf/latest/${p}" 2>/dev/null)"
  [ "$c" = "200" ] && echo "    ✓ 200 ${p}" || echo "    ✗ ${c} ${p}"
done
echo

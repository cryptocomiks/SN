#!/usr/bin/env bash
# =====================================================================
#  Installation de la carte "Biens dormants Lyon" sur un VPS Debian/Ubuntu
#  Usage :   sudo bash install.sh [domaine]
#  Exemple : sudo bash install.sh carte.mondomaine.fr
#  Sans domaine, le site est servi sur l'IP publique du VPS.
# =====================================================================
set -euo pipefail

# --- Élévation automatique : ce script a besoin des droits root ---
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    echo "==> Droits root requis, relance via sudo…"
    exec sudo -E bash "$0" "$@"
  fi
  echo "ERREUR : ce script doit être lancé en root (sudo bash $0)." >&2
  exit 1
fi

DOMAIN="${1:-}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ROOT="/var/www/lyon"

echo "==> Installation de nginx"
export DEBIAN_FRONTEND=noninteractive

# Sur un VPS neuf, unattended-upgrades tient souvent le verrou apt : on patiente.
for i in $(seq 1 30); do
  if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || \
     fuser /var/lib/apt/lists/lock   >/dev/null 2>&1; then
    [ "$i" = "1" ] && echo "    (apt occupé par une mise à jour automatique, attente…)"
    sleep 5
  else
    break
  fi
done

apt-get update -qq
apt-get install -y -qq nginx

echo "==> Copie du site vers ${WEB_ROOT}"
mkdir -p "${WEB_ROOT}" /var/cache/nginx/lyon
cp "${SRC_DIR}/lyon.html" "${WEB_ROOT}/"

# --- Leaflet hébergé en local : indispensable car les bloqueurs (Brave Shields,
#     uBlock…) empêchent souvent le chargement depuis un CDN tiers. ---
echo "==> Téléchargement de Leaflet en local (indépendance CDN)"
apt-get install -y -qq curl >/dev/null 2>&1 || true
LEAFLET_VER="1.9.4"
LEAFLET_DIR="${WEB_ROOT}/vendor/leaflet"
mkdir -p "${LEAFLET_DIR}/images"
CDN_A="https://unpkg.com/leaflet@${LEAFLET_VER}/dist"
CDN_B="https://cdnjs.cloudflare.com/ajax/libs/leaflet/${LEAFLET_VER}"

# fetch <chemin-relatif> <destination> : essaie unpkg puis cdnjs
fetch(){
  curl -fsSL --max-time 60 "${CDN_A}/$1" -o "$2" 2>/dev/null && return 0
  curl -fsSL --max-time 60 "${CDN_B}/$1" -o "$2" 2>/dev/null && return 0
  return 1
}

DL_OK=1
for f in leaflet.js leaflet.css; do
  fetch "${f}" "${LEAFLET_DIR}/${f}" || DL_OK=0
done
for img in layers.png layers-2x.png marker-icon.png marker-icon-2x.png marker-shadow.png; do
  fetch "images/${img}" "${LEAFLET_DIR}/images/${img}" || true
done
if [ "${DL_OK}" = "1" ] && [ -s "${LEAFLET_DIR}/leaflet.js" ]; then
  echo "    Leaflet ${LEAFLET_VER} installé dans ${LEAFLET_DIR}"
else
  echo "    ATTENTION : téléchargement de Leaflet impossible."
  echo "    Le site basculera sur le CDN (susceptible d'être bloqué par un adblocker)."
fi

chown -R www-data:www-data "${WEB_ROOT}" /var/cache/nginx/lyon

echo "==> Configuration nginx"
cp "${SRC_DIR}/deploy/nginx-lyon.conf" /etc/nginx/sites-available/lyon
if [ -n "${DOMAIN}" ]; then
  sed -i "s/server_name _;/server_name ${DOMAIN};/" /etc/nginx/sites-available/lyon
fi
ln -sf /etc/nginx/sites-available/lyon /etc/nginx/sites-enabled/lyon
rm -f /etc/nginx/sites-enabled/default

echo "==> Test de la configuration"
nginx -t
systemctl reload nginx
systemctl enable nginx >/dev/null 2>&1 || true

# Pare-feu (si ufw est actif)
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  echo "==> Ouverture des ports 80/443 dans ufw"
  ufw allow 'Nginx Full' >/dev/null
fi

echo
echo "======================================================"
if [ -n "${DOMAIN}" ]; then
  echo " Site en ligne : http://${DOMAIN}/"
  echo
  echo " Pour activer le HTTPS gratuit (Let's Encrypt) :"
  echo "   apt install -y certbot python3-certbot-nginx"
  echo "   certbot --nginx -d ${DOMAIN}"
else
  IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  echo " Site en ligne : http://${IP:-<IP-de-votre-VPS>}/"
fi
echo "======================================================"

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

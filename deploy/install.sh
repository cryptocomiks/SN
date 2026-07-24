#!/usr/bin/env bash
# =====================================================================
#  Installation de la carte "Biens dormants Lyon" sur un VPS Debian/Ubuntu
#  Usage (en root) :   bash install.sh [domaine]
#  Exemple        :   bash install.sh carte.mondomaine.fr
#  Sans domaine, le site est servi sur l'IP publique du VPS.
# =====================================================================
set -euo pipefail

DOMAIN="${1:-}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ROOT="/var/www/lyon"

echo "==> Installation de nginx"
export DEBIAN_FRONTEND=noninteractive
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

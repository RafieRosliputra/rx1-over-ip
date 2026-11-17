#!/usr/bin/env bash
# Install CUPS + Gutenprint + rx1print on Debian/Armbian/Raspberry Pi OS.
# Usage: sudo bash install.sh
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run as root: sudo bash $0"; exit 1; }

PRINTER_NAME="${RX1_PRINTER:-DNP-RX1HS}"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "==> 1/5 Packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y cups cups-filters printer-driver-gutenprint \
  avahi-daemon libnss-mdns python3 python3-pil usbutils

echo "==> 2/5 CUPS: share queues on the LAN"
usermod -aG lpadmin "${SUDO_USER:-root}" || true
cupsctl --remote-any --share-printers
systemctl enable --now cups avahi-daemon
systemctl restart cups

echo "==> 3/5 Add printer (RX1HS must be plugged in and ON)"
URI="$(lpinfo -v 2>/dev/null | awk '/usb:\/\/(DNP|Dai)|gutenprint.*usb/{print $2; exit}')"
PPD="$(lpinfo -m 2>/dev/null | awk 'tolower($0) ~ /rx1hs/ {print $1; exit}')"
[ -n "$PPD" ] || PPD="$(lpinfo -m 2>/dev/null | awk 'tolower($0) ~ /dsrx1|ds-rx1|dnp.*rx1/ {print $1; exit}')"
if [ -n "$URI" ] && [ -n "$PPD" ]; then
  lpadmin -p "$PRINTER_NAME" -E -v "$URI" -m "$PPD" -o printer-is-shared=true
  lpadmin -d "$PRINTER_NAME"
  echo "OK: $PRINTER_NAME  URI=$URI  PPD=$PPD"
else
  echo "WARNING: printer or driver not auto-detected."
  echo "  lpinfo -v | grep -i usb     (find the USB URI)"
  echo "  lpinfo -m | grep -i rx1     (find the driver)"
  echo "  or add it by hand at http://$(hostname).local:631 -> Administration"
fi

echo "==> 4/5 rx1print service"
install -d /opt/rx1print
install -m 0644 "$HERE/rx1print/server.py" /opt/rx1print/server.py
[ -f /etc/default/rx1print ] || install -m 0640 "$HERE/deploy/rx1print.env" /etc/default/rx1print
install -m 0644 "$HERE/deploy/rx1print.service" /etc/systemd/system/rx1print.service
systemctl daemon-reload
systemctl enable --now rx1print

echo "==> 5/5 Done"
IP="$(hostname -I | awk '{print $1}')"
cat <<EOF

Pi:   ${IP}  (${HOSTNAME}.local)
CUPS: ipp://${IP}:631/printers/${PRINTER_NAME}
API:  http://${IP}:8080/health
Edit /etc/default/rx1print to set a token / media, then: systemctl restart rx1print
EOF

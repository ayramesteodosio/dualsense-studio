#!/bin/sh
set -e
VERSAO="${1:-0.0.0}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PAINEL="${DUALSENSE_PAINEL:-$RAIZ/../dualsense-painel}"
TMP="$(mktemp -d)"
PKG="$TMP/pkg"
APP="$PKG/usr/share/dualsense-studio"
ICONES="$PKG/usr/share/icons/hicolor"
mkdir -p "$PKG/DEBIAN" "$APP/ui" "$PKG/usr/bin" "$PKG/usr/share/applications" "$PKG/usr/lib/udev/rules.d" \
  "$ICONES/scalable/apps" "$ICONES/symbolic/apps" "$RAIZ/dist"
cp -r "$RAIZ/dualsense_studio" "$PAINEL/dualsense_painel" "$APP/"
cp "$RAIZ/ui/index.html" "$APP/ui/"
find "$APP" -name __pycache__ -prune -exec rm -rf {} +
printf 'VERSAO = "%s"\n' "$VERSAO" > "$APP/dualsense_studio/versao.py"
rm -rf "$APP/dualsense_painel/qt" "$APP/dualsense_studio/web.py"

cat > "$PKG/usr/bin/dualsense-studio" <<'SH'
#!/bin/sh
cd /usr/share/dualsense-studio && exec python3 -m dualsense_studio "$@"
SH
chmod 755 "$PKG/usr/bin/dualsense-studio"

cat > "$PKG/usr/share/applications/com.ayrames.DualSenseStudio.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=DualSense Studio
Comment=Luz, gatilhos adaptativos e modo carregar do controle do PS5
Exec=dualsense-studio
Icon=com.ayrames.DualSenseStudio
StartupWMClass=com.ayrames.DualSenseStudio
Terminal=false
Categories=Settings;HardwareSettings;
Keywords=ps5;dualsense;controle;gatilho;
StartupNotify=true
DESKTOP

install -m644 "$RAIZ/dados/com.ayrames.DualSenseStudio.svg" "$ICONES/scalable/apps/"
install -m644 "$RAIZ/dados/com.ayrames.DualSenseStudio-symbolic.svg" "$ICONES/symbolic/apps/"
install -m644 "$PAINEL/dados/70-dualsense-painel.rules" "$PKG/usr/lib/udev/rules.d/70-dualsense-studio.rules"

cat > "$PKG/DEBIAN/control" <<CONTROL
Package: dualsense-studio
Version: $VERSAO
Section: utils
Priority: optional
Architecture: all
Maintainer: ayramesteodosio <ayrames.teodosio@gmail.com>
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, gir1.2-webkit2-4.1 | gir1.2-webkit2-4.0
Recommends: pulseaudio-utils
Homepage: https://github.com/ayramesteodosio/dualsense-studio
Description: Interface para o controle DualSense do PS5
 Controle desenhado na tela acompanhando tudo ao vivo, modo carregar, luz da
 barra, gatilhos adaptativos, teste do controle e informações de fábrica.
CONTROL

cat > "$PKG/DEBIAN/postinst" <<'SH'
#!/bin/sh
set -e
if [ "$1" = configure ] && command -v udevadm >/dev/null; then
  udevadm control --reload || true
  udevadm trigger --action=change --subsystem-match=input --subsystem-match=hidraw --subsystem-match=usb || true
fi
SH
chmod 755 "$PKG/DEBIAN/postinst"

dpkg-deb --root-owner-group --build "$PKG" "$RAIZ/dist/dualsense-studio_${VERSAO}_all.deb"
rm -rf "$TMP"

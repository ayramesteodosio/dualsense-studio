#!/bin/sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PAINEL="${DUALSENSE_PAINEL:-$DIR/../dualsense-painel}"
if [ ! -d "$PAINEL/dualsense_painel" ]; then
  echo "Não achei o dualsense-painel em $PAINEL. Clone ele ao lado deste repo ou defina DUALSENSE_PAINEL." >&2
  exit 1
fi
"$PAINEL/instalar.sh"
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS" "$HOME/.local/bin"
ln -sf "$DIR/dualsense-studio" "$HOME/.local/bin/dualsense-studio"
cat > "$APPS/com.ayrames.DualSenseStudio.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=DualSense Studio
Comment=Light bar, adaptive triggers and charging mode for the PS5 controller
Comment[pt_BR]=Luz, gatilhos adaptativos e modo carregar do controle do PS5
Exec=$DIR/dualsense-studio
Icon=$HOME/.local/share/icons/hicolor/scalable/apps/com.ayrames.DualSenseStudio.svg
StartupWMClass=com.ayrames.DualSenseStudio
Terminal=false
Categories=Settings;HardwareSettings;
Keywords=ps5;dualsense;controle;gatilho;
StartupNotify=true
DESKTOP
update-desktop-database "$APPS" 2>/dev/null || true
ICONS="$HOME/.local/share/icons/hicolor"
install -Dm644 "$DIR/dados/com.ayrames.DualSenseStudio.svg" "$ICONS/scalable/apps/com.ayrames.DualSenseStudio.svg"
install -Dm644 "$DIR/dados/com.ayrames.DualSenseStudio-symbolic.svg" "$ICONS/symbolic/apps/com.ayrames.DualSenseStudio-symbolic.svg"
gtk-update-icon-cache -q -t -f "$ICONS" 2>/dev/null || true
gio set "$DIR/dualsense-studio" metadata::custom-icon "file://$ICONS/scalable/apps/com.ayrames.DualSenseStudio.svg" 2>/dev/null || true
echo "Pronto. Procure por \"DualSense Studio\" no menu."

#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════╗"
echo "║   EFI HACKINTOSH — Ryzen 3 5300U        ║"
echo "║   SMBIOS: MacBookPro16,3 | Zen 2/Renoir  ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "Pasos disponibles:"
echo ""
echo "  1) Instalar OCAT y dependencias    → scripts/01_install_ocat.sh"
echo "  2) Descargar macOS Recovery        → scripts/02_download_recovery.sh"
echo "  3) Descargar Kexts                 → scripts/03_download_kexts.sh"
echo "  4) Guía interactiva OCAT            → scripts/04_generate_config.sh"
echo "  5) Ejecutar TODO en orden           → Automático (1→2→3→4)"
echo ""
echo "  d) Documentación (WiFi, notas)     → ver docs/"
echo ""
read -rp "Elige una opción [1-5/d]: " OPT

case "$OPT" in
    1) bash "$SCRIPT_DIR/scripts/01_install_ocat.sh" ;;
    2) bash "$SCRIPT_DIR/scripts/02_download_recovery.sh" ;;
    3) bash "$SCRIPT_DIR/scripts/03_download_kexts.sh" ;;
    4) bash "$SCRIPT_DIR/scripts/04_generate_config.sh" ;;
    5)
        bash "$SCRIPT_DIR/scripts/01_install_ocat.sh" && \
        bash "$SCRIPT_DIR/scripts/02_download_recovery.sh" && \
        bash "$SCRIPT_DIR/scripts/03_download_kexts.sh" && \
        bash "$SCRIPT_DIR/scripts/04_generate_config.sh"
        ;;
    d)
        echo ""
        echo "Archivos de documentación:"
        ls -la "$SCRIPT_DIR/docs/"
        echo ""
        which xdg-open && xdg-open "$SCRIPT_DIR/docs/" 2>/dev/null || true
        ;;
    *) echo "Opción inválida: $OPT" && exit 1 ;;
esac

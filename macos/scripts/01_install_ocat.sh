#!/usr/bin/env bash
# ============================================================
# 01_install_ocat.sh — Instalar OC Auxiliary Tools + deps
# Proyecto: EFI Hackintosh Ryzen 3 5300U (Renoir/Lucienne)
# SMBIOS:   MacBookPro16,3
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
LOG_FILE="./01_install_ocat.log"

log()  { echo -e "${GREEN}[✓]${NC} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[!]${NC} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}[✗]${NC} $*" | tee -a "$LOG_FILE"; }

cd "$(dirname "$0")/.." || exit 1
> "$LOG_FILE"

echo "===============================" | tee -a "$LOG_FILE"
echo " OCAT Installation for Arch Linux" | tee -a "$LOG_FILE"
echo " Date: $(date)" | tee -a "$LOG_FILE"
echo "===============================" | tee -a "$LOG_FILE"

# ── Paso 1: Instalar dependencias del sistema ──────────────────
log "Actualizando sistema e instalando dependencias base..."
sudo pacman -Sy --needed --noconfirm \
    git \
    python \
    python-pip \
    base-devel \
    curl \
    wget \
    unzip \
    2>&1 | tee -a "$LOG_FILE"

# ── Paso 2: Instalar OCAT desde AUR ────────────────────────────
log "Instalando OC Auxiliary Tools (ocat-bin) desde AUR..."

if command -v ocat &>/dev/null; then
    log "OCAT ya está instalado: $(which ocat)"
else
    if command -v yay &>/dev/null; then
        yay -S --noconfirm ocat-bin 2>&1 | tee -a "$LOG_FILE"
    elif command -v paru &>/dev/null; then
        paru -S --noconfirm ocat-bin 2>&1 | tee -a "$LOG_FILE"
    else
        warn "No se encontró yay ni paru. Instalando yay..."
        sudo pacman -S --needed --noconfirm git base-devel
        git clone https://aur.archlinux.org/yay.git /tmp/yay-install
        (cd /tmp/yay-install && makepkg -si --noconfirm)
        rm -rf /tmp/yay-install
        yay -S --noconfirm ocat-bin 2>&1 | tee -a "$LOG_FILE"
    fi
fi

# ── Paso 3: Verificar instalación ──────────────────────────────
if command -v ocat &>/dev/null; then
    log "OCAT instalado correctamente en: $(which ocat)"
else
    err "OCAT no se pudo instalar. Revisa $LOG_FILE"
    exit 1
fi

log "Instalación completada."
log "Para abrir OCAT ejecuta: ocat"
echo ""
echo "Siguiente paso: ./02_download_recovery.sh"

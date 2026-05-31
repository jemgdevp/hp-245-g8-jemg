#!/usr/bin/env bash
# 06_sync_usb_efi.sh — Sincronización completa y segura del EFI/OC al USB del instalador
# Uso (USB montado en ruta habitual de Linux):
#   USB_LABEL=MACOS MOUNT_POINT=/run/media/$USER/MACOS ./scripts/06_sync_usb_efi.sh
# O con montaje automático:
#   ./scripts/06_sync_usb_efi.sh
set -euo pipefail

USB_LABEL="${USB_LABEL:-MACOS}"
MOUNT_POINT="${MOUNT_POINT:-/run/media/${USER:-jemg}/MACOS}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_EFI_DIR="${PROJECT_ROOT}/EFI"
TARGET_EFI_DIR="${MOUNT_POINT}/EFI"
LOCAL_OCVALIDATE="${PROJECT_ROOT}/tools/ocvalidate"

log() { echo "[sync-usb] $*"; }
err() { echo "[sync-usb] ERROR: $*" >&2; }

if [[ ! -d "${SOURCE_EFI_DIR}/OC" ]]; then
    err "No existe ${SOURCE_EFI_DIR}/OC (genera primero con 05_generate_config.py)"
    exit 1
fi

# Montaje si es necesario
if ! mountpoint -q "${MOUNT_POINT}" 2>/dev/null; then
    DEVICE=""
    if [[ -e "/dev/disk/by-label/${USB_LABEL}" ]]; then
        DEVICE="$(readlink -f "/dev/disk/by-label/${USB_LABEL}" 2>/dev/null || true)"
    fi
    if [[ -z "${DEVICE}" ]]; then
        DEVICE="$(lsblk -nrpo NAME,LABEL 2>/dev/null | awk -v l="${USB_LABEL}" '$2==l {print $1; exit}' || true)"
    fi
    if [[ -z "${DEVICE}" ]]; then
        err "No se encontró dispositivo con etiqueta ${USB_LABEL}. Inserta el USB e inténtalo de nuevo."
        exit 1
    fi
    log "Montando ${DEVICE} en ${MOUNT_POINT}"
    sudo mkdir -p "${MOUNT_POINT}"
    sudo mount "${DEVICE}" "${MOUNT_POINT}"
else
    log "USB ya montada en ${MOUNT_POINT}"
fi

if [[ ! -d "${TARGET_EFI_DIR}/OC" ]]; then
    err "No existe ${TARGET_EFI_DIR}/OC. El USB no tiene la estructura EFI esperada (formatea como FAT32 + nombre EFI)."
    exit 1
fi

# Sincronización completa y segura de EFI/OC (excluye backups locales y temporales)
log "Sincronizando EFI completo (rsync --delete para mantener USB idéntico al repo)..."
sudo rsync -a --delete \
    --exclude="config_backup_*.plist" \
    --exclude=".*" \
    --exclude="__pycache__" \
    "${SOURCE_EFI_DIR}/" "${TARGET_EFI_DIR}/"

# Copia también Tools si existen (útil para ocvalidate en el USB)
if [[ -d "${PROJECT_ROOT}/tools" ]]; then
    sudo mkdir -p "${MOUNT_POINT}/tools"
    sudo rsync -a --delete --exclude=".*" "${PROJECT_ROOT}/tools/" "${MOUNT_POINT}/tools/" || true
fi

# Validación final
if [[ -x "${LOCAL_OCVALIDATE}" ]]; then
    log "Validando config del USB con ocvalidate..."
    "${LOCAL_OCVALIDATE}" "${TARGET_EFI_DIR}/OC/config.plist" || {
        err "ocvalidate falló en el USB (revisa errores arriba)."
        exit 1
    }
    log "ocvalidate: 0 errores en USB."
else
    log "ocvalidate no encontrado en ${LOCAL_OCVALIDATE}; se omite validación (descárgalo de OpenCorePkg)."
fi

sync
log "Sincronización completa."
log "USB lista en ${MOUNT_POINT}. Expulsa con seguridad antes de arrancar."
log "Comando de arranque recomendado: puerto USB 2.0 (negro) + -v + 2GB+ VRAM en BIOS."

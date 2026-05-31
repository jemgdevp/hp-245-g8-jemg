#!/usr/bin/env bash
# 06_sync_usb_efi.sh — Sincronización del EFI al USB (preferentemente SIN sudo)
#
# Uso recomendado (sin sudo cuando sea posible):
#   ./scripts/06_sync_usb_efi.sh
#
# Forzar sudo (comportamiento viejo):
#   FORCE_SUDO=1 ./scripts/06_sync_usb_efi.sh
#
# Variables útiles:
#   USB_LABEL=MACOS
#   MOUNT_POINT=/run/media/$USER/MACOS
set -euo pipefail

USB_LABEL="${USB_LABEL:-MACOS}"
MOUNT_POINT="${MOUNT_POINT:-/run/media/${USER:-jemg}/MACOS}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_EFI_DIR="${PROJECT_ROOT}/EFI"
TARGET_EFI_DIR="${MOUNT_POINT}/EFI"
LOCAL_OCVALIDATE="${PROJECT_ROOT}/tools/ocvalidate"
FORCE_SUDO="${FORCE_SUDO:-0}"

log() { echo "[sync-usb] $*"; }
err() { echo "[sync-usb] ERROR: $*" >&2; }

if [[ ! -d "${SOURCE_EFI_DIR}/OC" ]]; then
    err "No existe ${SOURCE_EFI_DIR}/OC (genera primero con 05_generate_config.py)"
    exit 1
fi

# =====================================================
# MONTAJE INTELIGENTE (prefiere udisksctl sin root)
# =====================================================
mount_usb() {
    if mountpoint -q "${MOUNT_POINT}" 2>/dev/null; then
        log "USB ya montada en ${MOUNT_POINT}"
        return 0
    fi

    # Buscar dispositivo por label
    local device=""
    if [[ -e "/dev/disk/by-label/${USB_LABEL}" ]]; then
        device="$(readlink -f "/dev/disk/by-label/${USB_LABEL}" 2>/dev/null || true)"
    fi
    if [[ -z "$device" ]]; then
        device="$(lsblk -nrpo NAME,LABEL 2>/dev/null | awk -v l="${USB_LABEL}" '$2==l {print $1; exit}' || true)"
    fi
    if [[ -z "$device" ]]; then
        err "No se encontró dispositivo con etiqueta ${USB_LABEL}."
        exit 1
    fi

    log "Dispositivo detectado: $device"

    # Intentar montar sin sudo usando udisksctl (recomendado)
    if command -v udisksctl &>/dev/null && [[ "$FORCE_SUDO" != "1" ]]; then
        log "Intentando montar con udisksctl (sin root)..."
        if udisksctl mount --block-device "$device" --no-user-interaction 2>/dev/null; then
            # udisksctl suele montar en /run/media/$USER/LABEL
            # Actualizamos MOUNT_POINT si cambió
            local auto_mount
            auto_mount=$(find /run/media/"$USER" -maxdepth 1 -name "*${USB_LABEL}*" -type d 2>/dev/null | head -1)
            if [[ -n "$auto_mount" && "$auto_mount" != "$MOUNT_POINT" ]]; then
                log "udisksctl montó en: $auto_mount (ajustando MOUNT_POINT)"
                MOUNT_POINT="$auto_mount"
                TARGET_EFI_DIR="${MOUNT_POINT}/EFI"
            fi
            log "Montado sin privilegios con udisksctl."
            return 0
        else
            log "udisksctl falló, intentando con sudo..."
        fi
    fi

    # Fallback con sudo
    log "Montando con sudo..."
    sudo mkdir -p "${MOUNT_POINT}"
    sudo mount "$device" "${MOUNT_POINT}"
}

mount_usb

if [[ ! -d "${TARGET_EFI_DIR}/OC" ]]; then
    err "No existe ${TARGET_EFI_DIR}/OC. El USB debe estar formateado como FAT32 y tener la carpeta EFI/OC."
    exit 1
fi

# =====================================================
# RSYNC INTELIGENTE (sin sudo cuando sea posible)
# =====================================================
can_write_without_sudo() {
    [[ -w "$TARGET_EFI_DIR" ]]
}

do_rsync() {
    local src="$1"
    local dst="$2"
    local extra="${3:-}"

    # Good progress flags for large transfers (especially on slow USB)
    local progress_flags="-h --info=progress2 --no-inc-recursive"

    if can_write_without_sudo && [[ "$FORCE_SUDO" != "1" ]]; then
        log "Sincronizando sin sudo (el punto de montaje es escribible por el usuario)..."
        rsync -a --delete $progress_flags $extra "$src" "$dst"
    else
        log "Sincronizando con sudo..."
        sudo rsync -a --delete $progress_flags $extra "$src" "$dst"
    fi
}

# =====================================================
# EXCLUSIONES DE RECURSOS PESADOS (OPCIONAL)
# =====================================================
# Por defecto copiamos TODO (incluyendo los archivos de audio).
# Esto es más seguro porque no sabemos si OpenCore puede quejarse
# de archivos faltantes aunque AudioSupport esté en false.
#
# Si quieres sync más rápido durante pruebas intensas, usa:
#   SYNC_FAST=1 ./scripts/06_sync_usb_efi.sh
# Esto excluirá la carpeta de audio (~360 archivos .mp3).

get_rsync_excludes() {
    local excludes="--exclude=config_backup_*.plist --exclude=.* --exclude=__pycache__"

    if [[ "${SYNC_FAST:-0}" == "1" ]]; then
        excludes="$excludes --exclude=OC/Resources/Audio/"
    fi

    echo "$excludes"
}

# Logging
if [[ "${SYNC_FAST:-0}" == "1" ]]; then
    log "SYNC_FAST=1 → excluyendo Resources/Audio/ para mayor velocidad"
else
    log "Sincronizando recursos completos (incluyendo audio)"
fi

RSYNC_EXCLUDES=$(get_rsync_excludes)

log "Sincronizando EFI completo (rsync --delete)..."
do_rsync "${SOURCE_EFI_DIR}/" "${TARGET_EFI_DIR}/" "$RSYNC_EXCLUDES"

# Tools (opcional)
if [[ -d "${PROJECT_ROOT}/tools" ]]; then
    mkdir -p "${MOUNT_POINT}/tools" 2>/dev/null || sudo mkdir -p "${MOUNT_POINT}/tools"
    do_rsync "${PROJECT_ROOT}/tools/" "${MOUNT_POINT}/tools/" "--exclude=.*" || true
fi

# =====================================================
# VALIDACIÓN
# =====================================================
if [[ -x "${LOCAL_OCVALIDATE}" ]]; then
    log "Validando config del USB con ocvalidate..."
    "${LOCAL_OCVALIDATE}" "${TARGET_EFI_DIR}/OC/config.plist" || {
        err "ocvalidate falló."
        exit 1
    }
    log "ocvalidate: 0 errores en USB."
else
    log "ocvalidate no encontrado (se omite)."
fi

sync
log "Sincronización completada."

# Mostrar perfil actual
GEN_SCRIPT="${SCRIPT_DIR}/05_generate_config.py"
if [[ -f "$GEN_SCRIPT" ]]; then
    if grep -q "USE_NRED_DP_DELAY" "$GEN_SCRIPT" 2>/dev/null; then
        NRED=$(grep "USE_NRED_DP_DELAY" "$GEN_SCRIPT" | head -1 | awk '{print $3}')
        MINIMAL=$(grep "USE_MINIMAL_ACPI_FOR_FB_TEST" "$GEN_SCRIPT" | head -1 | awk '{print $3}')
        log "Perfil sincronizado:"
        log "  -NRedDPDelay          = ${NRED:-?}"
        log "  ACPI Minimal (test)   = ${MINIMAL:-?}"
    fi
fi

log "USB lista en: ${MOUNT_POINT}"
log "Expulsa con seguridad (o usa 'udisksctl unmount -b /dev/sdX1')."
log "Recomendado: arrancar desde puerto USB 2.0 (negro) + monitor HDMI conectado desde antes."

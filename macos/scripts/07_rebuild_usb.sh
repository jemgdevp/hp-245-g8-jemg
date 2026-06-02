#!/usr/bin/env bash
# 07_rebuild_usb.sh — Reconstrucción COMPLETA del USB instalador macOS desde cero.
#
# A diferencia de 06_sync_usb_efi.sh (que solo sincroniza el EFI a un USB YA formateado),
# este FORMATEA el USB desde cero: limpia firmas residuales (wipefs — p.ej. una firma
# iso9660 de cuando el pendrive fue un USB de Debian, que confunde al firmware HP), crea
# GPT + FAT32 etiqueta MACOS, y copia el recovery + EFI completo, con validaciones.
#
# REQUIERE sudo (wipefs/parted/mkfs operan sobre el dispositivo de bloque).
#
# Uso:
#   sudo ./scripts/07_rebuild_usb.sh /dev/sdX            # dispositivo explícito (recomendado)
#   sudo TARGET_DEV=/dev/sdX ./scripts/07_rebuild_usb.sh
#   sudo FORCE=1 ./scripts/07_rebuild_usb.sh /dev/sdX    # sin confirmación interactiva
#
# Guardas de seguridad (abortan ANTES de borrar):
#   - El dispositivo debe medir 4–64 GB (rango de un USB).
#   - Su modelo NO debe parecer un disco interno (WDC / KINGSTON / SNV3).
#   - NO debe montar /, /home ni /boot.
# Así NUNCA toca el HDD (WDC, macOS) ni el NVMe (KINGSTON, Arch Linux cifrado).
#
# Diseño: usa cp (NO `rsync -a`) porque FAT32 no soporta ownership Unix y rsync -a
# falla con "chown ... Operation not permitted". Copia solo los .aml de ACPI (los .dsl
# son fuentes y no se cargan). NO regenera el config.plist: usa el existente para
# mantener el SystemUUID/ROM del SMBIOS estables (regenerarlo asigna unos nuevos).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
USB_LABEL="${USB_LABEL:-MACOS}"
MNT="${MNT:-/mnt/usb_macos_rebuild}"
FORCE="${FORCE:-0}"
TARGET_DEV="${TARGET_DEV:-${1:-}}"

REC_DIR="${PROJECT_ROOT}/recovery_ventura/com.apple.recovery.boot"
SRC_EFI="${PROJECT_ROOT}/EFI"
OCVALIDATE="${PROJECT_ROOT}/tools/ocvalidate"

log() { echo "[rebuild-usb] $*"; }
err() { echo "[rebuild-usb] ERROR: $*" >&2; }

# ---------- Requiere root ----------
if [[ $EUID -ne 0 ]]; then
    err "Este script SÍ requiere sudo (formatea el dispositivo): sudo $0 /dev/sdX"
    exit 1
fi

# ---------- Material fuente ----------
[[ -d "${SRC_EFI}/OC" ]]        || { err "No existe ${SRC_EFI}/OC (genera con 05_generate_config.py)"; exit 1; }
[[ -f "${REC_DIR}/BaseSystem.dmg" ]] || { err "Falta ${REC_DIR}/BaseSystem.dmg (descarga con 02_download_recovery.sh)"; exit 1; }
[[ -x "${OCVALIDATE}" ]]       || { err "No existe ${OCVALIDATE}"; exit 1; }

# ---------- Resolver dispositivo ----------
if [[ -z "${TARGET_DEV}" ]]; then
    err "Indica el dispositivo USB:  sudo $0 /dev/sdX   (mira 'lsblk -o NAME,SIZE,FSTYPE,LABEL,MODEL')"
    exit 1
fi
[[ -b "${TARGET_DEV}" ]] || { err "${TARGET_DEV} no es un dispositivo de bloque"; exit 1; }

DEV_NAME="$(basename "${TARGET_DEV}")"
PART="${TARGET_DEV}1"

# ---------- GUARDAS DE SEGURIDAD ----------
SIZE_GB=$(( $(blockdev --getsize64 "${TARGET_DEV}") / 1000000000 ))
MODEL="$(cat "/sys/block/${DEV_NAME}/device/model" 2>/dev/null || echo '?')"
log "Objetivo: ${TARGET_DEV}  (${SIZE_GB} GB, modelo: ${MODEL})"

[[ "${SIZE_GB}" -ge 4 && "${SIZE_GB}" -le 64 ]] || {
    err "Tamaño ${SIZE_GB}GB fuera de rango USB (4-64GB). ¿Dispositivo equivocado?"; exit 1; }

case "${MODEL}" in
    *WDC*|*KINGSTON*|*SNV3*) err "El modelo parece un disco interno, NO el USB. Abortado."; exit 1;;
esac

for crit in / /home /boot /boot/efi; do
    src="$(findmnt -n -o SOURCE "${crit}" 2>/dev/null || true)"
    case "${src}" in
        *"${DEV_NAME}"*) err "${TARGET_DEV} monta ${crit} (disco de sistema). Abortado."; exit 1;;
    esac
done

# ---------- Confirmación ----------
if [[ "${FORCE}" != "1" ]]; then
    echo ""
    echo "  Se va a BORRAR POR COMPLETO ${TARGET_DEV} (${SIZE_GB} GB, ${MODEL})."
    read -r -p "  Escribe MACOS para confirmar: " ans
    [[ "${ans}" == "MACOS" ]] || { err "Confirmación incorrecta. Abortado."; exit 1; }
fi

# ---------- Desmontar ----------
umount "${PART}" 2>/dev/null || true
umount "${MNT}"  2>/dev/null || true

# ---------- Limpiar firmas + particionar + formatear ----------
log "wipefs -a ${TARGET_DEV} (borra firmas residuales: iso9660, GPT, FAT viejas)"
wipefs -a "${TARGET_DEV}"

log "parted: GPT + partición FAT32"
parted "${TARGET_DEV}" --script mklabel gpt mkpart primary fat32 1MiB 100%
partprobe "${TARGET_DEV}"; sleep 2

log "mkfs.vfat -F 32 -n ${USB_LABEL} ${PART}"
mkfs.vfat -F 32 -n "${USB_LABEL}" "${PART}"

# ---------- Montar ----------
mkdir -p "${MNT}"
mount "${PART}" "${MNT}"

# ---------- Copiar recovery ----------
log "Copiando recovery (BaseSystem.dmg + chunklist)"
mkdir -p "${MNT}/com.apple.recovery.boot"
cp "${REC_DIR}/BaseSystem.dmg"       "${MNT}/com.apple.recovery.boot/"
cp "${REC_DIR}/BaseSystem.chunklist" "${MNT}/com.apple.recovery.boot/"

# ---------- Copiar EFI (cp, no rsync -a; solo .aml en ACPI) ----------
log "Copiando EFI completo"
mkdir -p "${MNT}/EFI/BOOT" "${MNT}/EFI/OC/ACPI" "${MNT}/EFI/OC/Drivers" "${MNT}/EFI/OC/Kexts" "${MNT}/EFI/OC/Tools"
cp "${SRC_EFI}/OC/ACPI/"*.aml   "${MNT}/EFI/OC/ACPI/"
cp -r "${SRC_EFI}/OC/Drivers/." "${MNT}/EFI/OC/Drivers/"
cp -r "${SRC_EFI}/OC/Kexts/."   "${MNT}/EFI/OC/Kexts/"
cp -r "${SRC_EFI}/OC/Tools/."   "${MNT}/EFI/OC/Tools/"
cp "${SRC_EFI}/OC/OpenCore.efi" "${MNT}/EFI/OC/"
cp "${SRC_EFI}/OC/config.plist" "${MNT}/EFI/OC/"
cp "${SRC_EFI}/BOOT/BOOTx64.efi" "${MNT}/EFI/BOOT/"
sync

# ---------- Validaciones ----------
echo ""
echo "===================== VALIDACIONES ====================="
B=$(stat -c%s "${MNT}/EFI/BOOT/BOOTx64.efi")
if [[ "${B}" -lt 100000 ]]; then echo "-- BOOTx64.efi = ${B} bytes  OK (Bootstrap ~24K)"
else echo "-- BOOTx64.efi = ${B} bytes  ERROR: demasiado grande (¿OpenCore.efi?)"; fi

echo "-- ocvalidate:"
"${OCVALIDATE}" "${MNT}/EFI/OC/config.plist" 2>&1 | tail -1

echo "-- md5 config (repo vs USB):"
md5sum "${SRC_EFI}/OC/config.plist" "${MNT}/EFI/OC/config.plist"

echo "-- BaseSystem.dmg (repo vs USB):"
cmp "${REC_DIR}/BaseSystem.dmg" "${MNT}/com.apple.recovery.boot/BaseSystem.dmg" && echo "   OK idéntico"

echo "-- Contenido: $(ls "${MNT}/EFI/OC/Kexts/" | wc -l) kexts | $(ls "${MNT}/EFI/OC/ACPI/"*.aml | wc -l) SSDTs | .dsl: $(ls "${MNT}/EFI/OC/ACPI/" | grep -c '\.dsl$' || true)"
echo "-- SystemUUID (estable):"
python3 -c "import plistlib; print('   ', plistlib.load(open('${MNT}/EFI/OC/config.plist','rb'))['PlatformInfo']['Generic']['SystemUUID'])"

# ---------- Desmontar limpio (sync, sin power-off / sin eject físico) ----------
sync
umount "${MNT}"
rmdir "${MNT}" 2>/dev/null || true

echo ""
log "USB reconstruido y desmontado (no expulsado)."
log "Arranca desde un puerto USB 2.0 (negro). Recovery → Utilidad de Discos → Erase"
log "del volumen destino (HDD WDC, NUNCA el NVMe) antes de reinstalar."

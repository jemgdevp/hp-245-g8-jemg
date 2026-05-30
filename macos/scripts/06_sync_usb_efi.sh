#!/usr/bin/env bash
  set -euo pipefail
  USB_LABEL="${USB_LABEL:-MACOS}"
  MOUNT_POINT="${MOUNT_POINT:-/mnt/MACOS}"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
  SOURCE_OC_DIR="${PROJECT_ROOT}/EFI/OC"
  TARGET_OC_DIR="${MOUNT_POINT}/EFI/OC"
  LOCAL_OCVALIDATE="${PROJECT_ROOT}/tools/ocvalidate"
  log() {
    echo "[sync-usb] $*"
  }
  err() {
    echo "[sync-usb] ERROR: $*" >&2
  }
  if [[ ! -d "${SOURCE_OC_DIR}" ]]; then
    err "No existe ${SOURCE_OC_DIR}"
    exit 1
  fi
  if ! mountpoint -q "${MOUNT_POINT}"; then
    DEVICE=""
    if [[ -e "/dev/disk/by-label/${USB_LABEL}" ]]; then
      DEVICE="$(readlink -f "/dev/disk/by-label/${USB_LABEL}")"
    fi
    if [[ -z "${DEVICE}" ]]; then
      DEVICE="$(lsblk -nrpo NAME,LABEL | awk -v l="${USB_LABEL}" '$2==l {print $1; exit}')"
    fi
    if [[ -z "${DEVICE}" ]]; then
      err "No se encontro dispositivo con etiqueta ${USB_LABEL}"
      exit 1
    fi
    log "Montando ${DEVICE} en ${MOUNT_POINT}"
    sudo mkdir -p "${MOUNT_POINT}"
    sudo mount "${DEVICE}" "${MOUNT_POINT}"
  else
    log "USB ya montada en ${MOUNT_POINT}"
  fi
  if [[ ! -d "${TARGET_OC_DIR}" ]]; then
    err "No existe ${TARGET_OC_DIR}. Verifica la estructura EFI/OC en el USB."
    exit 1
  fi
  log "Copiando config.plist"
  sudo cp "${SOURCE_OC_DIR}/config.plist" "${TARGET_OC_DIR}/config.plist"
  if [[ -d "${SOURCE_OC_DIR}/Kexts/AppleMCEReporterDisabler.kext" ]]; then
    log "Copiando AppleMCEReporterDisabler.kext"
    sudo rm -rf "${TARGET_OC_DIR}/Kexts/AppleMCEReporterDisabler.kext"
    sudo cp -r "${SOURCE_OC_DIR}/Kexts/AppleMCEReporterDisabler.kext" "${TARGET_OC_DIR}/Kexts/"
  fi
  if [[ -x "${LOCAL_OCVALIDATE}" ]]; then
    log "Validando config del USB con ocvalidate"
    "${LOCAL_OCVALIDATE}" "${TARGET_OC_DIR}/config.plist"
  else
    log "ocvalidate no encontrado en ${LOCAL_OCVALIDATE}; se omite validacion."
  fi
  sync
  log "Sincronizacion completa. USB permanece montada en ${MOUNT_POINT}."
